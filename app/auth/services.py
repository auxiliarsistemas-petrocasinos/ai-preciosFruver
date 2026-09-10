"""Servicios de usuarios y sesiones sin acoplamiento a HTTP."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.auth.models import User, UserSession
from app.auth.passwords import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    normalize_username,
    password_hasher,
    validate_username,
    verify_password,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def hash_session_token(raw_token: str) -> str:
    """Deriva la clave persistida a partir de un token de alta entropía."""
    return sha256(raw_token.encode("utf-8")).hexdigest()


def create_user(db: Session, username: str, password: str) -> User:
    """Crea un usuario activo usando exclusivamente credenciales canónicas/hasheadas."""
    user = User(
        username=validate_username(username),
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Autentica sin distinguir públicamente las causas del rechazo."""
    canonical = normalize_username(username)
    user = db.scalar(select(User).where(User.username == canonical))
    candidate_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_matches = verify_password(candidate_hash, password)
    if user is None or not user.is_active or not password_matches:
        return None
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = password_hasher.hash(password)
        db.commit()
        db.refresh(user)
    return user


def create_user_session(db: Session, user: User, lifetime_seconds: int) -> tuple[UserSession, str]:
    """Crea sesión y devuelve el token crudo una sola vez para la cookie."""
    raw_token = token_urlsafe(32)
    now = utc_now()
    user_session = UserSession(
        token_hash=hash_session_token(raw_token),
        user_id=user.id,
        csrf_token=token_urlsafe(32),
        created_at=now,
        expires_at=now + timedelta(seconds=lifetime_seconds),
    )
    db.add(user_session)
    db.commit()
    db.refresh(user_session)
    return user_session, raw_token


def find_user_session(db: Session, raw_token: str | None) -> UserSession | None:
    """Resuelve solo sesiones emitidas, vigentes y pertenecientes a usuarios activos."""
    if not raw_token or len(raw_token) > 128:
        return None
    user_session = db.scalar(
        select(UserSession)
        .where(UserSession.token_hash == hash_session_token(raw_token))
        .options(joinedload(UserSession.user))
    )
    if user_session is None:
        return None
    if _aware(user_session.expires_at) <= utc_now() or not user_session.user.is_active:
        db.delete(user_session)
        db.commit()
        return None
    return user_session


def revoke_session(db: Session, raw_token: str | None) -> bool:
    """Elimina la sesión identificada por un token presentado."""
    if not raw_token or len(raw_token) > 128:
        return False
    result = db.execute(
        delete(UserSession).where(UserSession.token_hash == hash_session_token(raw_token))
    )
    db.commit()
    return bool(result.rowcount)


def revoke_all_user_sessions(db: Session, user_id: int) -> None:
    """Revoca todas las sesiones al retirar acceso o cambiar credenciales."""
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    db.commit()


def cleanup_expired_sessions(db: Session) -> None:
    """Realiza limpieza oportunista sin scheduler."""
    db.execute(delete(UserSession).where(UserSession.expires_at <= utc_now()))
    db.commit()


def detached_identity(db: Session, raw_token: str) -> tuple[User, UserSession] | None:
    """Carga y separa la identidad antes de cerrar la sesión SQLAlchemy."""
    user_session = find_user_session(db, raw_token)
    if user_session is None:
        return None
    user = user_session.user
    db.expunge(user_session)
    db.expunge(user)
    return user, user_session
