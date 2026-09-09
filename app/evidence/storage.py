"""Operaciones acotadas de filesystem para archivos de evidencia."""

import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO
from uuid import uuid4

MAX_FILE_SIZE = 20 * 1024 * 1024
COPY_CHUNK_SIZE = 1024 * 1024


class EvidenceFileError(Exception):
    """Error esperado al validar o persistir un archivo de evidencia."""


class EvidenceFileTooLarge(EvidenceFileError):
    """El archivo excede el límite permitido."""


class EvidenceFileNotFound(EvidenceFileError):
    """La clave no resuelve a un archivo regular y contenido en el storage."""


@dataclass(frozen=True, slots=True)
class StoredEvidenceFile:
    """Metadata derivada del archivo publicado."""

    storage_key: str
    original_filename: str
    media_type: str
    file_size: int


_FORMATS = {
    ".pdf": (".pdf", b"%PDF-", "application/pdf"),
    ".png": (".png", b"\x89PNG\r\n\x1a\n", "image/png"),
    ".jpg": (".jpg", b"\xff\xd8\xff", "image/jpeg"),
    ".jpeg": (".jpg", b"\xff\xd8\xff", "image/jpeg"),
}


def validate_original_filename(filename: str | None) -> tuple[str, bytes, str]:
    """Valida metadata presentable y devuelve extensión, firma y MIME esperados."""
    if not filename or not filename.strip() or filename in {".", ".."}:
        raise EvidenceFileError("Seleccione un archivo con un nombre válido.")
    if any(character in filename for character in ("\x00", "\r", "\n", "/", "\\")):
        raise EvidenceFileError("El nombre del archivo no puede contener rutas ni saltos de línea.")
    if Path(filename).is_absolute() or PureWindowsPath(filename).drive:
        raise EvidenceFileError("El nombre del archivo no puede ser una ruta.")

    dot = filename.rfind(".")
    if dot <= 0:
        raise EvidenceFileError("El archivo debe tener extensión PDF, PNG, JPG o JPEG.")
    format_details = _FORMATS.get(filename[dot:].lower())
    if format_details is None:
        raise EvidenceFileError("El archivo debe tener extensión PDF, PNG, JPG o JPEG.")
    return format_details


def _storage_root(storage_path: str | Path, *, create: bool) -> Path:
    root = Path(storage_path)
    if create:
        root.mkdir(parents=True, exist_ok=True)
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise EvidenceFileError("No fue posible acceder al almacenamiento de evidencias.") from exc
    if not resolved.is_dir():
        raise EvidenceFileError("El almacenamiento de evidencias no es un directorio.")
    return resolved


def _contained_path(root: Path, storage_key: str, *, strict: bool) -> Path:
    key = PurePosixPath(storage_key)
    if key.is_absolute() or ".." in key.parts or not key.parts or str(key) != storage_key:
        raise EvidenceFileNotFound("Archivo de evidencia no encontrado.")
    candidate = root.joinpath(*key.parts)
    try:
        resolved = candidate.resolve(strict=strict)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise EvidenceFileNotFound("Archivo de evidencia no encontrado.") from exc
    return candidate


def _detected_media_type(header: bytes) -> str | None:
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return None


def store_upload(
    storage_path: str | Path,
    source: BinaryIO,
    original_filename: str | None,
) -> StoredEvidenceFile:
    """Copia por chunks, valida y publica atómicamente sin sobrescribir."""
    normalized_extension, expected_signature, expected_media_type = validate_original_filename(
        original_filename
    )
    assert original_filename is not None
    root = _storage_root(storage_path, create=True)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(prefix=".upload-", dir=root, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            file_size = 0
            header = bytearray()
            while chunk := source.read(COPY_CHUNK_SIZE):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise EvidenceFileTooLarge("El archivo supera el límite de 20 MiB.")
                if len(header) < 8:
                    header.extend(chunk[: 8 - len(header)])
                temporary.write(chunk)

            if file_size == 0:
                raise EvidenceFileError("El archivo no puede estar vacío.")
            detected_media_type = _detected_media_type(bytes(header))
            if not bytes(header).startswith(expected_signature) or (
                detected_media_type != expected_media_type
            ):
                raise EvidenceFileError(
                    "La extensión no coincide con el contenido PDF, PNG o JPEG detectado."
                )
            temporary.flush()
            os.fsync(temporary.fileno())

        for _ in range(10):
            opaque_id = uuid4().hex
            storage_key = f"{opaque_id[:2]}/{opaque_id}{normalized_extension}"
            destination = _contained_path(root, storage_key, strict=False)
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(temporary_path, destination, follow_symlinks=False)
            except FileExistsError:
                continue
            temporary_path.unlink()
            temporary_path = None
            return StoredEvidenceFile(
                storage_key=storage_key,
                original_filename=original_filename,
                media_type=detected_media_type,
                file_size=file_size,
            )
        raise EvidenceFileError("No fue posible generar una clave única para el archivo.")
    except EvidenceFileError:
        raise
    except OSError as exc:
        raise EvidenceFileError("No fue posible guardar el archivo de evidencia.") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def resolve_stored_file(storage_path: str | Path, storage_key: str) -> Path:
    """Resuelve una clave relativa solo si apunta a un archivo regular seguro."""
    root = _storage_root(storage_path, create=False)
    candidate = _contained_path(root, storage_key, strict=True)
    try:
        file_status = candidate.lstat()
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise EvidenceFileNotFound("Archivo de evidencia no encontrado.") from exc
    if stat.S_ISLNK(file_status.st_mode) or not stat.S_ISREG(file_status.st_mode):
        raise EvidenceFileNotFound("Archivo de evidencia no encontrado.")
    return resolved


def delete_stored_file(storage_path: str | Path, storage_key: str) -> None:
    """Elimina un archivo publicado conocido durante compensación de una transacción."""
    try:
        path = resolve_stored_file(storage_path, storage_key)
        path.unlink()
    except EvidenceFileNotFound:
        return
