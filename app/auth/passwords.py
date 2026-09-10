"""Normalización de credenciales y hashing de contraseñas."""

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,64}$")
MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 128

password_hasher = PasswordHasher(
    memory_cost=19456,
    time_cost=2,
    parallelism=1,
    salt_len=16,
    hash_len=32,
    type=Type.ID,
)

# Evita que un usuario inexistente omita el trabajo dominante de Argon2.
DUMMY_PASSWORD_HASH = password_hasher.hash("dummy password that is never accepted")


class CredentialValidationError(ValueError):
    """Una credencial no cumple el formato o la política aprobados."""


def normalize_username(username: str) -> str:
    """Devuelve el identificador canónico de login."""
    return username.strip().lower()


def validate_username(username: str) -> str:
    """Normaliza y valida el formato aprobado para usernames."""
    canonical = normalize_username(username)
    if not USERNAME_PATTERN.fullmatch(canonical):
        raise CredentialValidationError(
            "El username debe tener de 3 a 64 caracteres: a-z, 0-9, punto, guion o guion bajo."
        )
    return canonical


def validate_password(password: str) -> str:
    """Valida longitud sin transformar, recortar ni normalizar la contraseña."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise CredentialValidationError(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise CredentialValidationError(
            f"La contraseña debe tener como máximo {MAX_PASSWORD_LENGTH} caracteres."
        )
    return password


def hash_password(password: str) -> str:
    """Valida y genera un hash Argon2id autocontenido."""
    return password_hasher.hash(validate_password(password))


def verify_password(password_hash: str, password: str) -> bool:
    """Verifica con la implementación constant-time provista por Argon2."""
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False
