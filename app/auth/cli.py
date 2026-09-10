"""CLI administrativa mínima para identidades locales."""

import argparse
from collections.abc import Sequence
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.passwords import CredentialValidationError, hash_password, validate_username
from app.auth.services import create_user, revoke_all_user_sessions
from app.db.session import get_session_factory


def _password_with_confirmation() -> str:
    password = getpass("Contraseña: ")
    confirmation = getpass("Confirme la contraseña: ")
    if password != confirmation:
        raise CredentialValidationError("Las contraseñas no coinciden.")
    return password


def _existing_user(db: Session, username: str) -> User:
    canonical = validate_username(username)
    user = db.scalar(select(User).where(User.username == canonical))
    if user is None:
        raise CredentialValidationError("Usuario no encontrado.")
    return user


def _create(db: Session, username: str) -> None:
    create_user(db, username, _password_with_confirmation())
    print("Usuario creado.")


def _set_password(db: Session, username: str) -> None:
    user = _existing_user(db, username)
    user.password_hash = hash_password(_password_with_confirmation())
    revoke_all_user_sessions(db, user.id)
    print("Contraseña actualizada y sesiones revocadas.")


def _set_active(db: Session, username: str, *, active: bool) -> None:
    user = _existing_user(db, username)
    user.is_active = active
    if not active:
        revoke_all_user_sessions(db, user.id)
        print("Usuario desactivado y sesiones revocadas.")
    else:
        db.commit()
        print("Usuario activado.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Administra usuarios locales de ai-preciosFruver.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("create-user", "set-password", "deactivate-user", "activate-user"):
        subparser = commands.add_parser(command)
        subparser.add_argument("username")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        with get_session_factory()() as db:
            if args.command == "create-user":
                _create(db, args.username)
            elif args.command == "set-password":
                _set_password(db, args.username)
            elif args.command == "deactivate-user":
                _set_active(db, args.username, active=False)
            else:
                _set_active(db, args.username, active=True)
    except (CredentialValidationError, IntegrityError) as exc:
        if isinstance(exc, IntegrityError):
            message = "El username ya existe."
        else:
            message = str(exc)
        print(f"Error: {message}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
