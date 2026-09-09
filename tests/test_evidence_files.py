import asyncio
from collections.abc import Generator
from datetime import date
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.commercial_offers.models import CommercialOffer
from app.db.base import Base
from app.evidence.models import Evidence
from app.evidence.storage import (
    MAX_FILE_SIZE,
    EvidenceFileError,
    EvidenceFileNotFound,
    resolve_stored_file,
    store_upload,
    validate_original_filename,
)
from app.evidence.upload_limit import (
    MAX_UPLOAD_REQUEST_SIZE,
    EvidenceUploadBodyLimitMiddleware,
)
from app.prospecting.models import ProspectingRecord
from app.providers.models import Provider
from app.purchase_needs.models import PurchaseNeed
from app.sources.models import Source

PDF = b"%PDF-1.7\nminimal test evidence"
PNG = b"\x89PNG\r\n\x1a\nminimal test evidence"
JPEG = b"\xff\xd8\xff\xe0minimal test evidence"


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def _persist_evidence_targets(db_session: Session) -> tuple[int, int]:
    purchase_need = PurchaseNeed(
        product_name="Tomate chonto",
        quantity=100,
        unit_of_measure="kg",
        required_delivery_date=date(2026, 9, 15),
        destination_city="Bogotá",
        destination_location="Bodega central",
    )
    source = Source(name="Sitio web")
    provider = Provider(name="Agrícola Central")
    db_session.add_all([purchase_need, source, provider])
    db_session.flush()
    record = ProspectingRecord(
        purchase_need_id=purchase_need.id,
        source_id=source.id,
        provider_id=provider.id,
    )
    db_session.add(record)
    db_session.flush()
    offer = CommercialOffer(
        prospecting_record_id=record.id,
        price_amount=82500,
        price_unit="canastilla",
        currency="COP",
        obtained_on=date(2026, 9, 9),
    )
    db_session.add(offer)
    db_session.commit()
    return record.id, offer.id


def _purchase_need_data(product_name: str = "Tomate chonto") -> dict[str, str]:
    return {
        "product_name": product_name,
        "variety": "",
        "quality_standard": "Primera",
        "quantity": "100",
        "unit_of_measure": "kg",
        "required_delivery_date": "2026-09-15",
        "destination_city": "Bogotá",
        "destination_location": "Bodega central",
    }


def _setup_prospecting(
    client: TestClient, *, with_provider: bool = False, product_name: str = "Tomate chonto"
) -> tuple[int, int]:
    need_response = client.post(
        "/purchase-needs", data=_purchase_need_data(product_name), follow_redirects=False
    )
    need_id = int(need_response.headers["location"].rsplit("/", maxsplit=1)[1])
    source_response = client.post(
        "/sources", data={"name": f"Fuente {product_name}"}, follow_redirects=False
    )
    source_id = int(source_response.headers["location"].rsplit("/", maxsplit=1)[1])
    provider_id = ""
    if with_provider:
        provider_response = client.post(
            "/providers",
            data={"name": f"Proveedor {product_name}"},
            follow_redirects=False,
        )
        provider_id = provider_response.headers["location"].rsplit("/", maxsplit=1)[1]
    record_response = client.post(
        f"/purchase-needs/{need_id}/prospecting-records",
        data={"source_id": str(source_id), "provider_id": provider_id, "notes": ""},
    )
    record_id = max(
        record.id for record in record_response.context["purchase_need"].prospecting_records
    )
    return need_id, record_id


def _create_offer(client: TestClient, need_id: int, record_id: int) -> int:
    response = client.post(
        f"/purchase-needs/{need_id}/prospecting-records/{record_id}/commercial-offers",
        data={
            "price_amount": "82500",
            "price_unit": "canastilla",
            "currency": "COP",
            "obtained_on": "2026-09-08",
            "offered_description": "",
            "conditions": "",
        },
    )
    record = next(
        item
        for item in response.context["purchase_need"].prospecting_records
        if item.id == record_id
    )
    return max(offer.id for offer in record.commercial_offers)


def _record_upload_path(need_id: int, record_id: int) -> str:
    return f"/purchase-needs/{need_id}/prospecting-records/{record_id}/evidence/files"


def _offer_upload_path(need_id: int, record_id: int, offer_id: int) -> str:
    return (
        f"/purchase-needs/{need_id}/prospecting-records/{record_id}/"
        f"commercial-offers/{offer_id}/evidence/files"
    )


def _upload(
    client: TestClient,
    path: str,
    filename: str,
    content: bytes,
    declared_media_type: str = "application/octet-stream",
    **fields: str,
):
    data = {
        "title": "Cotización adjunta",
        "captured_on": "2026-09-09",
        "notes": "Verificada manualmente",
    }
    data.update(fields)
    return client.post(
        path,
        data=data,
        files={"file": (filename, content, declared_media_type)},
        follow_redirects=False,
    )


def _record_evidence(client: TestClient, need_id: int, record_id: int) -> Evidence:
    detail = client.get(f"/purchase-needs/{need_id}")
    record = next(
        item for item in detail.context["purchase_need"].prospecting_records if item.id == record_id
    )
    return record.evidence_items[0]


@pytest.mark.parametrize(
    ("filename", "content", "expected_media_type", "expected_suffix"),
    [
        ("cotización.pdf", PDF, "application/pdf", ".pdf"),
        ("captura.png", PNG, "image/png", ".png"),
        ("foto.jpg", JPEG, "image/jpeg", ".jpg"),
        ("foto.jpeg", JPEG, "image/jpeg", ".jpg"),
    ],
)
def test_valid_file_is_persisted_with_content_derived_metadata(
    client: TestClient,
    filename: str,
    content: bytes,
    expected_media_type: str,
    expected_suffix: str,
) -> None:
    need_id, record_id = _setup_prospecting(client)

    response = _upload(
        client,
        _record_upload_path(need_id, record_id),
        filename,
        content,
        "text/html",
    )

    assert response.status_code == 303
    evidence = _record_evidence(client, need_id, record_id)
    assert evidence.url is None
    assert evidence.original_filename == filename
    assert evidence.media_type == expected_media_type
    assert evidence.file_size == len(content)
    assert evidence.storage_key is not None
    assert evidence.storage_key.endswith(expected_suffix)
    assert not Path(evidence.storage_key).is_absolute()
    stored_path = client.app.state.evidence_storage_path / evidence.storage_key
    assert stored_path.read_bytes() == content


def test_commercial_offer_accepts_multiple_files_and_keeps_target(
    client: TestClient,
) -> None:
    need_id, record_id = _setup_prospecting(client, with_provider=True)
    offer_id = _create_offer(client, need_id, record_id)
    path = _offer_upload_path(need_id, record_id, offer_id)

    assert _upload(client, path, "primera.pdf", PDF).status_code == 303
    assert _upload(client, path, "segunda.png", PNG).status_code == 303

    detail = client.get(f"/purchase-needs/{need_id}")
    record = detail.context["purchase_need"].prospecting_records[0]
    offer = record.commercial_offers[0]
    assert len(offer.evidence_items) == 2
    assert all(item.prospecting_record_id is None for item in offer.evidence_items)
    assert all(item.commercial_offer_id == offer_id for item in offer.evidence_items)


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("datos.txt", b"text"),
        ("invalido.pdf", b"not a pdf"),
        ("falso.pdf", PNG),
        ("contradictorio.png", JPEG),
        ("vacío.pdf", b""),
    ],
)
def test_invalid_format_or_empty_file_is_rejected(
    client: TestClient, filename: str, content: bytes
) -> None:
    need_id, record_id = _setup_prospecting(client)

    response = _upload(client, _record_upload_path(need_id, record_id), filename, content)

    assert response.status_code == 422
    detail = client.get(f"/purchase-needs/{need_id}")
    assert detail.context["purchase_need"].prospecting_records[0].evidence_items == []
    assert list(client.app.state.evidence_storage_path.rglob("*")) == []


def test_file_of_exactly_20_mib_is_accepted(client: TestClient) -> None:
    need_id, record_id = _setup_prospecting(client)
    content = b"%PDF-" + b"x" * (MAX_FILE_SIZE - len(b"%PDF-"))

    response = _upload(
        client, _record_upload_path(need_id, record_id), "limite-exacto.pdf", content
    )

    assert response.status_code == 303
    evidence = _record_evidence(client, need_id, record_id)
    assert evidence.file_size == MAX_FILE_SIZE
    assert evidence.storage_key is not None
    stored_path = client.app.state.evidence_storage_path / evidence.storage_key
    assert stored_path.stat().st_size == MAX_FILE_SIZE


def test_file_over_20_mib_returns_413_and_is_not_persisted(client: TestClient) -> None:
    need_id, record_id = _setup_prospecting(client)
    content = b"%PDF-" + b"x" * (MAX_FILE_SIZE - 4)

    response = _upload(client, _record_upload_path(need_id, record_id), "grande.pdf", content)

    assert response.status_code == 413
    assert _record_evidence_count(client, need_id, record_id) == 0
    assert not any(path.is_file() for path in client.app.state.evidence_storage_path.rglob("*"))


def _record_evidence_count(client: TestClient, need_id: int, record_id: int) -> int:
    detail = client.get(f"/purchase-needs/{need_id}")
    record = next(
        item for item in detail.context["purchase_need"].prospecting_records if item.id == record_id
    )
    return len(record.evidence_items)


@pytest.mark.parametrize(
    "filename",
    [
        "../archivo.pdf",
        "/tmp/archivo.pdf",
        "C:\\temp\\archivo.pdf",
        "carpeta\\archivo.pdf",
        "archivo\r.pdf",
        "archivo\n.pdf",
        "archivo\x00.pdf",
    ],
)
def test_dangerous_original_filename_is_rejected(filename: str) -> None:
    # Se prueba el validador directamente porque los clientes HTTP normalizan algunos
    # nombres de ruta y caracteres de control antes de construir el multipart.
    with pytest.raises(EvidenceFileError):
        validate_original_filename(filename)


def test_safe_unicode_filename_and_repeated_names_get_distinct_opaque_keys(
    client: TestClient,
) -> None:
    need_id, record_id = _setup_prospecting(client)
    path = _record_upload_path(need_id, record_id)

    assert _upload(client, path, "Cotización número ágil.pdf", PDF).status_code == 303
    assert _upload(client, path, "Cotización número ágil.pdf", PDF).status_code == 303

    detail = client.get(f"/purchase-needs/{need_id}")
    items = detail.context["purchase_need"].prospecting_records[0].evidence_items
    assert len({item.storage_key for item in items}) == 2
    assert all(item.original_filename == "Cotización número ágil.pdf" for item in items)
    assert all(len(Path(item.storage_key).parts) == 2 for item in items)
    assert all("Cotización" not in item.storage_key for item in items)


def test_download_returns_exact_bytes_and_safe_attachment_headers(client: TestClient) -> None:
    need_id, record_id = _setup_prospecting(client)
    _upload(client, _record_upload_path(need_id, record_id), "cotización ágil.pdf", PDF)
    evidence = _record_evidence(client, need_id, record_id)

    response = client.get(
        f"/purchase-needs/{need_id}/prospecting-records/{record_id}/evidence/{evidence.id}/download"
    )

    assert response.status_code == 200
    assert response.content == PDF
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert "utf-8''" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"


def test_file_is_visible_with_controlled_link_and_url_does_not_get_none_href(
    client: TestClient,
) -> None:
    need_id, record_id = _setup_prospecting(client)
    _upload(client, _record_upload_path(need_id, record_id), "captura.png", PNG)

    detail = client.get(f"/purchase-needs/{need_id}")

    assert "Cotización adjunta" in detail.text
    assert "captura.png" in detail.text
    assert "image/png" in detail.text
    assert f"{len(PNG)} bytes" in detail.text
    assert "Descargar archivo" in detail.text
    assert 'href="None"' not in detail.text
    assert "Añadir referencia URL" in detail.text
    assert "Subir archivo" in detail.text


def test_offer_download_works_only_through_its_complete_hierarchy(client: TestClient) -> None:
    need_id, record_id = _setup_prospecting(client, with_provider=True)
    offer_id = _create_offer(client, need_id, record_id)
    _upload(client, _offer_upload_path(need_id, record_id, offer_id), "oferta.jpg", JPEG)
    detail = client.get(f"/purchase-needs/{need_id}")
    evidence = (
        detail.context["purchase_need"]
        .prospecting_records[0]
        .commercial_offers[0]
        .evidence_items[0]
    )

    good = client.get(
        f"/purchase-needs/{need_id}/prospecting-records/{record_id}/commercial-offers/"
        f"{offer_id}/evidence/{evidence.id}/download"
    )
    wrong_target = client.get(
        f"/purchase-needs/{need_id}/prospecting-records/{record_id}/evidence/{evidence.id}/download"
    )

    assert good.status_code == 200
    assert good.content == JPEG
    assert wrong_target.status_code == 404


def test_download_missing_wrong_target_url_and_missing_file_are_safe_404s(
    client: TestClient,
) -> None:
    need_id, record_id = _setup_prospecting(client)
    second_need_id, second_record_id = _setup_prospecting(client, product_name="Papa")
    _upload(client, _record_upload_path(need_id, record_id), "archivo.pdf", PDF)
    evidence = _record_evidence(client, need_id, record_id)
    url_response = client.post(
        f"/purchase-needs/{need_id}/prospecting-records/{record_id}/evidence",
        data={
            "title": "URL",
            "url": "https://example.test/evidence",
            "captured_on": "2026-09-09",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert url_response.status_code == 303
    items = (
        client.get(f"/purchase-needs/{need_id}")
        .context["purchase_need"]
        .prospecting_records[0]
        .evidence_items
    )
    url_evidence = next(item for item in items if item.url is not None)
    base = f"/purchase-needs/{need_id}/prospecting-records/{record_id}/evidence"

    assert client.get(f"{base}/999999/download").status_code == 404
    assert client.get(f"{base}/{url_evidence.id}/download").status_code == 404
    assert (
        client.get(
            f"/purchase-needs/{second_need_id}/prospecting-records/{second_record_id}/"
            f"evidence/{evidence.id}/download"
        ).status_code
        == 404
    )
    stored_path = client.app.state.evidence_storage_path / evidence.storage_key
    stored_path.unlink()
    assert client.get(f"{base}/{evidence.id}/download").status_code == 404


@pytest.mark.parametrize("method", ["get", "post"])
def test_file_routes_validate_missing_and_crossed_hierarchy(
    client: TestClient, method: str
) -> None:
    first_need_id, first_record_id = _setup_prospecting(client)
    second_need_id, _ = _setup_prospecting(client, product_name="Papa")
    paths = [
        _record_upload_path(999999, first_record_id),
        _record_upload_path(first_need_id, 999999),
        _record_upload_path(second_need_id, first_record_id),
    ]
    for path in paths:
        response = (
            client.get(f"{path}/new")
            if method == "get"
            else _upload(client, path, "archivo.pdf", PDF)
        )
        assert response.status_code == 404


def test_offer_file_routes_validate_offer_hierarchy(client: TestClient) -> None:
    need_id, first_record_id = _setup_prospecting(client, with_provider=True)
    _, second_record_id = _setup_prospecting(client, with_provider=True, product_name="Papa")
    offer_id = _create_offer(client, need_id, first_record_id)

    missing = _upload(client, _offer_upload_path(need_id, first_record_id, 999999), "a.pdf", PDF)
    wrong_record = _upload(
        client, _offer_upload_path(need_id, second_record_id, offer_id), "a.pdf", PDF
    )

    assert missing.status_code == 404
    assert wrong_record.status_code == 404


def test_file_form_preserves_text_but_not_file_input_value(client: TestClient) -> None:
    need_id, record_id = _setup_prospecting(client)

    response = _upload(
        client,
        _record_upload_path(need_id, record_id),
        "mal.txt",
        b"bad",
        title="  Título conservado  ",
        captured_on="2026-09-10",
        notes="Notas conservadas",
    )

    assert response.status_code == 422
    assert 'value="  Título conservado  "' in response.text
    assert 'value="2026-09-10"' in response.text
    assert "Notas conservadas" in response.text
    assert 'type="file" required' in response.text
    assert 'type="file" required value=' not in response.text


def test_upload_rejects_more_than_one_file(client: TestClient) -> None:
    need_id, record_id = _setup_prospecting(client)

    response = client.post(
        _record_upload_path(need_id, record_id),
        data={"title": "Dos archivos", "captured_on": "2026-09-09", "notes": ""},
        files=[
            ("file", ("uno.pdf", PDF, "application/pdf")),
            ("file", ("dos.pdf", PDF, "application/pdf")),
        ],
    )

    assert response.status_code == 422
    assert "exactamente un archivo" in response.text
    assert _record_evidence_count(client, need_id, record_id) == 0


def test_storage_failure_does_not_create_database_row(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    need_id, record_id = _setup_prospecting(client)

    def fail_storage(*args, **kwargs):
        raise EvidenceFileError("No fue posible guardar el archivo de evidencia.")

    monkeypatch.setattr("app.web.routes.evidence.store_upload", fail_storage)
    response = _upload(client, _record_upload_path(need_id, record_id), "archivo.pdf", PDF)

    assert response.status_code == 422
    assert _record_evidence_count(client, need_id, record_id) == 0


def test_request_body_limit_checks_declared_and_actual_size() -> None:
    async def run_case(headers: list[tuple[bytes, bytes]], chunks: list[bytes]) -> int:
        messages = [
            {
                "type": "http.request",
                "body": chunk,
                "more_body": index < len(chunks) - 1,
            }
            for index, chunk in enumerate(chunks)
        ]
        sent: list[dict[str, object]] = []

        async def receive():
            return messages.pop(0)

        async def send(message):
            sent.append(message)

        async def downstream(scope, receive, send):
            while True:
                message = await receive()
                if not message.get("more_body"):
                    break
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        middleware = EvidenceUploadBodyLimitMiddleware(downstream)
        await middleware(
            {
                "type": "http",
                "method": "POST",
                "path": "/purchase-needs/1/prospecting-records/2/evidence/files",
                "headers": headers,
            },
            receive,
            send,
        )
        return int(sent[0]["status"])

    declared = asyncio.run(
        run_case([(b"content-length", str(MAX_UPLOAD_REQUEST_SIZE + 1).encode())], [b""])
    )
    forged = asyncio.run(
        run_case(
            [(b"content-length", b"1")],
            [b"x" * MAX_UPLOAD_REQUEST_SIZE, b"x"],
        )
    )

    assert declared == 413
    assert forged == 413


def test_storage_rejects_escape_and_symlink_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(PDF)
    (root / "link.pdf").symlink_to(outside)

    with pytest.raises(EvidenceFileNotFound):
        resolve_stored_file(root, "../outside.pdf")
    with pytest.raises(EvidenceFileNotFound):
        resolve_stored_file(root, str(outside))
    with pytest.raises(EvidenceFileNotFound):
        resolve_stored_file(root, "link.pdf")


def test_atomic_publication_never_overwrites_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed_uuid = SimpleNamespace(hex="ab" + "1" * 30)
    monkeypatch.setattr("app.evidence.storage.uuid4", lambda: fixed_uuid)
    first = store_upload(tmp_path, BytesIO(PDF), "igual.pdf")
    first_path = tmp_path / first.storage_key

    with pytest.raises(EvidenceFileError):
        store_upload(tmp_path, BytesIO(PDF + b"different"), "igual.pdf")

    assert first_path.read_bytes() == PDF
    assert not any(path.name.startswith(".upload-") for path in tmp_path.rglob("*"))


def test_write_and_publication_failures_leave_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenSource:
        def read(self, size: int) -> bytes:
            raise OSError("write source failed")

    with pytest.raises(EvidenceFileError):
        store_upload(tmp_path / "write", BrokenSource(), "archivo.pdf")
    assert not any(path.is_file() for path in (tmp_path / "write").rglob("*"))

    def fail_publish(*args, **kwargs) -> None:
        raise OSError("publish failed")

    monkeypatch.setattr("app.evidence.storage.os.link", fail_publish)
    with pytest.raises(EvidenceFileError):
        store_upload(tmp_path / "publish", BytesIO(PDF), "archivo.pdf")
    assert not any(path.is_file() for path in (tmp_path / "publish").rglob("*"))


def test_representation_xor_accepts_each_representation_and_rejects_partial_states(
    db_session: Session,
) -> None:
    record_id, _ = _persist_evidence_targets(db_session)
    valid_file = Evidence(
        prospecting_record_id=record_id,
        title="Archivo válido",
        url=None,
        storage_key="ab/ab123.pdf",
        original_filename="archivo.pdf",
        media_type="application/pdf",
        file_size=len(PDF),
        captured_on=date(2026, 9, 9),
    )
    db_session.add(valid_file)
    db_session.commit()
    assert valid_file.id is not None

    invalid_rows = [
        Evidence(
            prospecting_record_id=record_id,
            title="Sin representación",
            url=None,
            captured_on=date(2026, 9, 9),
        ),
        Evidence(
            prospecting_record_id=record_id,
            title="Ambas",
            url="https://example.test",
            storage_key="cd/cd123.pdf",
            original_filename="archivo.pdf",
            media_type="application/pdf",
            file_size=1,
            captured_on=date(2026, 9, 9),
        ),
        Evidence(
            prospecting_record_id=record_id,
            title="Parcial",
            url=None,
            storage_key="ef/ef123.pdf",
            captured_on=date(2026, 9, 9),
        ),
    ]
    for evidence in invalid_rows:
        db_session.add(evidence)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


def test_db_failure_after_publication_removes_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    need_id, record_id = _setup_prospecting(client)

    def fail_commit(session: Session) -> None:
        raise RuntimeError("database unavailable")

    with monkeypatch.context() as context:
        context.setattr(Session, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="database unavailable"):
            _upload(client, _record_upload_path(need_id, record_id), "archivo.pdf", PDF)

    assert not any(path.is_file() for path in client.app.state.evidence_storage_path.rglob("*"))
    assert _record_evidence_count(client, need_id, record_id) == 0
