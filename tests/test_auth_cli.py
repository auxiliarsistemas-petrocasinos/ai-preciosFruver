from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import cli
from app.auth.models import User, UserSession
from app.auth.passwords import verify_password
from app.auth.services import create_user_session


def _password_input(monkeypatch: pytest.MonkeyPatch, *values: str) -> None:
    supplied: Iterator[str] = iter(values)
    monkeypatch.setattr(cli, "getpass", lambda prompt: next(supplied))


def test_cli_create_user_is_interactive_canonical_and_hashed(
    app_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "get_session_factory", lambda: app_session_factory)
    _password_input(monkeypatch, "  passphrase ñ segura  ", "  passphrase ñ segura  ")

    assert cli.main(["create-user", "  Compras.CLI "]) == 0
    assert capsys.readouterr().out == "Usuario creado.\n"
    with app_session_factory() as db:
        user = db.scalar(select(User).where(User.username == "compras.cli"))
        assert user is not None
        assert user.is_active is True
        assert user.password_hash != "  passphrase ñ segura  "
        assert verify_password(user.password_hash, "  passphrase ñ segura  ")


def test_cli_rejects_duplicate_and_password_confirmation_mismatch(
    app_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "get_session_factory", lambda: app_session_factory)
    _password_input(monkeypatch, "passphrase válida uno", "passphrase válida uno")
    assert cli.main(["create-user", "duplicado.cli"]) == 0
    capsys.readouterr()

    _password_input(monkeypatch, "passphrase válida dos", "passphrase válida dos")
    assert cli.main(["create-user", "DUPLICADO.CLI"]) == 1
    assert capsys.readouterr().out == "Error: El username ya existe.\n"

    _password_input(monkeypatch, "passphrase válida tres", "no coincide aquí")
    assert cli.main(["create-user", "otro.cli"]) == 1
    assert capsys.readouterr().out == "Error: Las contraseñas no coinciden.\n"


def test_cli_set_password_and_deactivate_revoke_all_sessions(
    app_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "get_session_factory", lambda: app_session_factory)
    _password_input(monkeypatch, "passphrase inicial segura", "passphrase inicial segura")
    assert cli.main(["create-user", "operador.cli"]) == 0
    with app_session_factory() as db:
        user = db.scalar(select(User).where(User.username == "operador.cli"))
        assert user is not None
        user_id = user.id
        create_user_session(db, user, 28800)

    _password_input(monkeypatch, "passphrase renovada segura", "passphrase renovada segura")
    assert cli.main(["set-password", "OPERADOR.CLI"]) == 0
    with app_session_factory() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert verify_password(user.password_hash, "passphrase renovada segura")
        assert list(db.scalars(select(UserSession))) == []
        create_user_session(db, user, 28800)

    assert cli.main(["deactivate-user", "operador.cli"]) == 0
    with app_session_factory() as db:
        user = db.get(User, user_id)
        assert user is not None and user.is_active is False
        assert list(db.scalars(select(UserSession))) == []

    assert cli.main(["activate-user", "operador.cli"]) == 0
    with app_session_factory() as db:
        user = db.get(User, user_id)
        assert user is not None and user.is_active is True
        assert list(db.scalars(select(UserSession))) == []


def test_cli_never_accepts_password_as_argument() -> None:
    with pytest.raises(SystemExit):
        cli.main(["create-user", "operador.cli", "password-en-argv"])
