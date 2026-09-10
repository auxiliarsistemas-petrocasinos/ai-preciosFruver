import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from argon2 import PasswordHasher
from argon2.low_level import Type
from conftest import TEST_PASSWORD, TEST_USERNAME
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.auth.middleware import (
    SESSION_COOKIE_NAME,
    AuthenticationMiddleware,
    set_session_cookie,
)
from app.auth.models import User, UserSession
from app.auth.passwords import (
    DUMMY_PASSWORD_HASH,
    CredentialValidationError,
    hash_password,
    password_hasher,
    validate_password,
    validate_username,
    verify_password,
)
from app.auth.security import safe_next_path
from app.auth.services import (
    create_user,
    hash_session_token,
)
from app.core.config import Settings
from app.evidence.upload_limit import (
    MAX_UPLOAD_REQUEST_SIZE,
    EvidenceUploadBodyLimitMiddleware,
)
from app.main import create_app

APP_ORIGIN = "http://127.0.0.1:8000"
GENERIC_LOGIN_ERROR = "Usuario o contraseña incorrectos"


def _create_user(
    session_factory: sessionmaker[Session],
    *,
    username: str = "login.test",
    password: str = TEST_PASSWORD,
    active: bool = True,
) -> User:
    with session_factory() as db:
        user = create_user(db, username, password)
        if not active:
            user.is_active = False
            db.commit()
            db.refresh(user)
        return user


def _login(
    client: TestClient,
    *,
    username: str = "login.test",
    password: str = TEST_PASSWORD,
    next_path: str = "/",
    headers: dict[str, str] | None = None,
):
    return client.post(
        "/login",
        data={"username": username, "password": password, "next": next_path},
        headers={"Origin": APP_ORIGIN} if headers is None else headers,
        follow_redirects=False,
    )


def _create_prospecting_context(client: TestClient) -> tuple[int, int]:
    need_response = client.post(
        "/purchase-needs",
        data={
            "product_name": "Tomate de prueba",
            "quantity": "10",
            "unit_of_measure": "kg",
            "required_delivery_date": "2026-09-15",
            "destination_city": "Bogotá",
            "destination_location": "Bodega de prueba",
        },
        follow_redirects=False,
    )
    need_id = int(need_response.headers["location"].rsplit("/", 1)[1])
    source_response = client.post(
        "/sources", data={"name": "Fuente de prueba"}, follow_redirects=False
    )
    source_id = int(source_response.headers["location"].rsplit("/", 1)[1])
    provider_response = client.post(
        "/providers", data={"name": "Proveedor de prueba"}, follow_redirects=False
    )
    provider_id = int(provider_response.headers["location"].rsplit("/", 1)[1])
    record_response = client.post(
        f"/purchase-needs/{need_id}/prospecting-records",
        data={"source_id": str(source_id), "provider_id": str(provider_id)},
    )
    record_id = max(
        record.id for record in record_response.context["purchase_need"].prospecting_records
    )
    return need_id, record_id


def test_user_is_canonical_active_unique_and_never_stores_plain_password(
    app_session_factory: sessionmaker[Session],
) -> None:
    user = _create_user(app_session_factory, username="  Compras.Uno  ")

    assert user.username == "compras.uno"
    assert user.is_active is True
    assert user.password_hash != TEST_PASSWORD
    assert TEST_PASSWORD not in user.password_hash
    assert user.password_hash.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert verify_password(user.password_hash, TEST_PASSWORD)

    with app_session_factory() as db:
        db.add(
            User(
                username="compras.uno",
                password_hash=hash_password("otra passphrase válida"),
                is_active=True,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


@pytest.mark.parametrize("username", ["ab", "con espacio", "correo@test", "ábc", "a" * 65])
def test_invalid_username_format_is_rejected(username: str) -> None:
    with pytest.raises(CredentialValidationError):
        validate_username(username)


def test_password_boundaries_unicode_and_spaces_are_preserved() -> None:
    with pytest.raises(CredentialValidationError):
        validate_password("a" * 14)
    assert validate_password("a" * 15) == "a" * 15
    with pytest.raises(CredentialValidationError):
        validate_password("a" * 129)

    passphrase = "  pássphrase ñ segura  "
    password_hash = hash_password(passphrase)
    assert verify_password(password_hash, passphrase)
    assert not verify_password(password_hash, passphrase.strip())


def test_valid_login_rehashes_an_outdated_argon2_hash(
    anonymous_client: TestClient,
    app_session_factory: sessionmaker[Session],
) -> None:
    old_hasher = PasswordHasher(
        memory_cost=8192,
        time_cost=1,
        parallelism=1,
        salt_len=16,
        hash_len=32,
        type=Type.ID,
    )
    old_hash = old_hasher.hash(TEST_PASSWORD)
    with app_session_factory() as db:
        user = User(username="rehash.test", password_hash=old_hash, is_active=True)
        db.add(user)
        db.commit()
        user_id = user.id

    response = _login(anonymous_client, username="rehash.test")
    assert response.status_code == 303
    with app_session_factory() as db:
        updated_hash = db.get(User, user_id).password_hash  # type: ignore[union-attr]
    assert updated_hash != old_hash
    assert not password_hasher.check_needs_rehash(updated_hash)


def test_login_creates_fresh_server_side_session_and_cookie(
    anonymous_client: TestClient,
    app_session_factory: sessionmaker[Session],
) -> None:
    user = _create_user(app_session_factory)

    response = _login(
        anonymous_client,
        username="  LOGIN.TEST ",
        next_path="/purchase-needs?estado=abierto",
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/purchase-needs?estado=abierto"
    raw_token = anonymous_client.cookies.get(SESSION_COOKIE_NAME)
    assert raw_token is not None
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert "Domain=" not in cookie
    assert "Max-Age=" not in cookie
    assert "expires=" not in cookie.lower()
    assert "Secure" not in cookie

    with app_session_factory() as db:
        stored = db.scalar(select(UserSession))
        assert stored is not None
        assert stored.user_id == user.id
        assert stored.token_hash == hash_session_token(raw_token)
        assert stored.token_hash != raw_token
        assert raw_token not in stored.csrf_token
        assert stored.csrf_token != raw_token
        assert stored.expires_at - stored.created_at == timedelta(hours=8)


def test_login_replaces_any_presented_session(
    authenticated_client: TestClient,
    app_session_factory: sessionmaker[Session],
) -> None:
    old_token = authenticated_client.cookies.get(SESSION_COOKIE_NAME)
    with app_session_factory() as db:
        old_csrf = db.scalar(select(UserSession.csrf_token))

    response = _login(
        authenticated_client,
        username=TEST_USERNAME,
        password=TEST_PASSWORD,
    )

    assert response.status_code == 303
    new_token = authenticated_client.cookies.get(SESSION_COOKIE_NAME)
    assert new_token and new_token != old_token
    with app_session_factory() as db:
        sessions = list(db.scalars(select(UserSession)))
    assert len(sessions) == 1
    assert sessions[0].token_hash == hash_session_token(new_token)
    assert sessions[0].csrf_token != old_csrf


@pytest.mark.parametrize(
    ("username", "password", "active"),
    [
        ("login.test", "password incorrecta", True),
        ("no.existe", TEST_PASSWORD, True),
        ("login.test", TEST_PASSWORD, False),
    ],
)
def test_login_failures_are_indistinguishable(
    anonymous_client: TestClient,
    app_session_factory: sessionmaker[Session],
    username: str,
    password: str,
    active: bool,
) -> None:
    _create_user(app_session_factory, active=active)

    response = _login(anonymous_client, username=username, password=password)

    assert response.status_code == 401
    assert GENERIC_LOGIN_ERROR in response.text
    assert "no encontrado" not in response.text.lower()
    assert "inactivo" not in response.text.lower()
    assert SESSION_COOKIE_NAME not in anonymous_client.cookies


def test_unknown_user_runs_dummy_argon2_verification(
    anonymous_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_hashes: list[str] = []

    def record_verify(password_hash: str, password: str) -> bool:
        observed_hashes.append(password_hash)
        return False

    monkeypatch.setattr("app.auth.services.verify_password", record_verify)
    response = _login(anonymous_client, username="no.existe")

    assert response.status_code == 401
    assert observed_hashes == [DUMMY_PASSWORD_HASH]


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"Origin": APP_ORIGIN}, 401),
        ({"Origin": "https://evil.test"}, 403),
        ({"Referer": f"{APP_ORIGIN}/login"}, 401),
        ({"Referer": "https://evil.test/login"}, 403),
        ({}, 403),
        ({"Origin": "https://evil.test", "Referer": f"{APP_ORIGIN}/login"}, 403),
    ],
)
def test_login_csrf_origin_and_referer_policy(
    anonymous_client: TestClient,
    headers: dict[str, str],
    expected: int,
) -> None:
    response = _login(anonymous_client, username="no.existe", headers=headers)
    assert response.status_code == expected


@pytest.mark.parametrize(
    "unsafe",
    [
        "https://evil.test",
        "http://evil.test",
        "//evil.test",
        "%2F%2Fevil.test",
        "/%2fevil.test",
        "/\\evil.test",
        "/%5cevil.test",
        "/ok%0d%0aLocation:%20https://evil.test",
        "javascript:alert(1)",
        "/login",
        "/login?next=/purchase-needs",
    ],
)
def test_safe_next_rejects_external_encoded_control_and_login_targets(unsafe: str) -> None:
    assert safe_next_path(unsafe) == "/"


@pytest.mark.parametrize("safe", ["/", "/purchase-needs", "/providers/7?desde=home"])
def test_safe_next_accepts_internal_absolute_paths(safe: str) -> None:
    assert safe_next_path(safe) == safe


def test_login_rejects_open_redirect_integration(
    anonymous_client: TestClient,
    app_session_factory: sessionmaker[Session],
) -> None:
    _create_user(app_session_factory)
    response = _login(anonymous_client, next_path="https://evil.test")
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_get_login_redirects_an_already_authenticated_user(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_valid_session_exposes_username_and_private_navigation(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/")
    assert response.status_code == 200
    assert f"Usuario: {TEST_USERNAME}" in response.text
    assert "Necesidades de compra" in response.text


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/purchase-needs",
        "/purchase-needs/new",
        "/sources",
        "/providers",
        "/purchase-needs/999/prospecting-records",
        "/purchase-needs/999/prospecting-records/999/commercial-offers/new",
        "/purchase-needs/999/prospecting-records/999/evidence/new",
        "/purchase-needs/999/prospecting-records/999/evidence/files/new",
        "/purchase-needs/999/prospecting-records/999/evidence/999/download",
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
)
def test_anonymous_gets_are_redirected_before_route_resolution(
    anonymous_client: TestClient, path: str
) -> None:
    response = anonymous_client.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=")


@pytest.mark.parametrize(
    "path",
    [
        "/purchase-needs",
        "/sources",
        "/providers",
        "/purchase-needs/999/prospecting-records",
        "/purchase-needs/999/prospecting-records/999/commercial-offers",
        "/purchase-needs/999/prospecting-records/999/evidence",
        "/purchase-needs/999/prospecting-records/999/evidence/files",
    ],
)
def test_anonymous_posts_redirect_to_login_without_next(
    anonymous_client: TestClient, path: str
) -> None:
    response = anonymous_client.post(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_htmx_anonymous_request_uses_hx_redirect(anonymous_client: TestClient) -> None:
    response = anonymous_client.get("/purchase-needs", headers={"HX-Request": "true"})
    assert response.status_code == 204
    assert response.headers["hx-redirect"] == "/login"


def test_only_approved_public_routes_are_available(anonymous_client: TestClient) -> None:
    login = anonymous_client.get("/login")
    assert login.status_code == 200
    assert "Iniciar sesión" in login.text
    assert "Necesidades de compra" not in login.text
    assert anonymous_client.get("/health").status_code == 200
    assert anonymous_client.get("/static/styles.css").status_code == 200
    assert _login(anonymous_client, username="no.existe").status_code == 401


def test_invalid_cookie_is_deleted(anonymous_client: TestClient) -> None:
    anonymous_client.cookies.set(
        SESSION_COOKIE_NAME, "token-modificado", domain="testserver.local", path="/"
    )
    response = anonymous_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert SESSION_COOKIE_NAME not in anonymous_client.cookies


def test_expired_session_is_deleted_and_rejected(
    authenticated_client: TestClient,
    app_session_factory: sessionmaker[Session],
) -> None:
    raw_token = authenticated_client.cookies.get(SESSION_COOKIE_NAME)
    with app_session_factory() as db:
        stored = db.get(UserSession, hash_session_token(raw_token))
        assert stored is not None
        stored.created_at = datetime.now(UTC) - timedelta(hours=2)
        stored.expires_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()

    response = authenticated_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    with app_session_factory() as db:
        assert db.get(UserSession, hash_session_token(raw_token)) is None


def test_inactive_user_invalidates_session_and_cookie(
    authenticated_client: TestClient,
    app_session_factory: sessionmaker[Session],
) -> None:
    raw_token = authenticated_client.cookies.get(SESSION_COOKIE_NAME)
    with app_session_factory() as db:
        user = db.scalar(select(User).where(User.username == TEST_USERNAME))
        assert user is not None
        user.is_active = False
        db.commit()

    response = authenticated_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert SESSION_COOKIE_NAME not in authenticated_client.cookies
    with app_session_factory() as db:
        assert db.get(UserSession, hash_session_token(raw_token)) is None


def test_session_survives_application_recreation_when_database_is_preserved(
    authenticated_client: TestClient,
    app_session_factory: sessionmaker[Session],
) -> None:
    raw_token = authenticated_client.cookies.get(SESSION_COOKIE_NAME)
    restarted_app = create_app()
    restarted_app.state.auth_session_factory = app_session_factory

    with TestClient(restarted_app) as restarted_client:
        restarted_client.cookies.set(
            SESSION_COOKIE_NAME, raw_token, domain="testserver.local", path="/"
        )
        assert restarted_client.get("/").status_code == 200


def test_logout_requires_valid_csrf_and_revokes_session(
    authenticated_client: TestClient,
    app_session_factory: sessionmaker[Session],
) -> None:
    raw_token = authenticated_client.cookies.get(SESSION_COOKIE_NAME)
    csrf_token = authenticated_client.csrf_token  # type: ignore[attr-defined]

    assert authenticated_client.post("/logout").status_code == 403
    assert (
        authenticated_client.post("/logout", data={"_csrf_token": "incorrecto"}).status_code == 403
    )
    with app_session_factory() as db:
        assert db.get(UserSession, hash_session_token(raw_token)) is not None

    response = authenticated_client.post(
        "/logout", data={"_csrf_token": csrf_token}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert "Max-Age=0" in response.headers["set-cookie"]
    with app_session_factory() as db:
        assert db.get(UserSession, hash_session_token(raw_token)) is None

    authenticated_client.cookies.set(
        SESSION_COOKIE_NAME, raw_token, domain="testserver.local", path="/"
    )
    assert authenticated_client.get("/", follow_redirects=False).status_code == 303


@pytest.mark.parametrize(
    "path",
    [
        "/purchase-needs",
        "/sources",
        "/providers",
        "/purchase-needs/999/prospecting-records",
        "/purchase-needs/999/prospecting-records/999/commercial-offers",
        "/purchase-needs/999/prospecting-records/999/evidence",
    ],
)
def test_authenticated_post_groups_reject_missing_and_invalid_csrf(
    authenticated_client: TestClient, path: str
) -> None:
    assert authenticated_client.post(path).status_code == 403
    assert authenticated_client.post(path, data={"_csrf_token": "incorrecto"}).status_code == 403


def test_evidence_file_upload_rejects_missing_and_invalid_csrf(
    client: TestClient,
) -> None:
    need_id, record_id = _create_prospecting_context(client)
    path = f"/purchase-needs/{need_id}/prospecting-records/{record_id}/evidence/files"
    data = {"title": "Archivo", "captured_on": "2026-09-09", "notes": ""}

    missing = TestClient.post(
        client, path, data=data, files={"file": ("evidencia.pdf", b"%PDF-1.7", "application/pdf")}
    )
    invalid = TestClient.post(
        client,
        path,
        data=data | {"_csrf_token": "incorrecto"},
        files={"file": ("evidencia.pdf", b"%PDF-1.7", "application/pdf")},
    )
    assert missing.status_code == 403
    assert invalid.status_code == 403


def test_valid_csrf_reaches_each_current_post_group(client: TestClient) -> None:
    need_id, record_id = _create_prospecting_context(client)
    provider = client.post("/providers", data={"name": "Proveedor CSRF"}, follow_redirects=False)
    assert provider.status_code == 303

    offer = client.post(
        f"/purchase-needs/{need_id}/prospecting-records/{record_id}/commercial-offers",
        data={
            "price_amount": "10000",
            "price_unit": "kg",
            "currency": "COP",
            "obtained_on": "2026-09-09",
        },
        follow_redirects=False,
    )
    assert offer.status_code == 303, offer.text
    detail = client.get(offer.headers["location"])
    offer_id = max(
        commercial_offer.id
        for record in detail.context["purchase_need"].prospecting_records
        for commercial_offer in record.commercial_offers
    )

    url_evidence = client.post(
        f"/purchase-needs/{need_id}/prospecting-records/{record_id}/evidence",
        data={
            "title": "URL CSRF",
            "url": "https://example.test/precio",
            "captured_on": "2026-09-09",
        },
        follow_redirects=False,
    )
    assert url_evidence.status_code == 303

    file_evidence = client.post(
        f"/purchase-needs/{need_id}/prospecting-records/{record_id}/commercial-offers/"
        f"{offer_id}/evidence/files",
        data={"title": "Archivo CSRF", "captured_on": "2026-09-09"},
        files={"file": ("evidencia.pdf", b"%PDF-1.7\nprueba", "application/pdf")},
        follow_redirects=False,
    )
    assert file_evidence.status_code == 303


def test_anonymous_large_upload_is_rejected_without_reading_body() -> None:
    downstream_called = False
    received = False
    messages: list[dict[str, object]] = []

    async def downstream(scope, receive, send) -> None:
        nonlocal downstream_called
        downstream_called = True

    async def receive() -> dict[str, object]:
        nonlocal received
        received = True
        raise AssertionError("El body anónimo no debe consumirse")

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    protected = AuthenticationMiddleware(EvidenceUploadBodyLimitMiddleware(downstream))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/purchase-needs/1/prospecting-records/1/evidence/files",
        "query_string": b"",
        "headers": [(b"content-length", str(MAX_UPLOAD_REQUEST_SIZE + 1).encode())],
    }
    asyncio.run(protected(scope, receive, send))  # type: ignore[arg-type]

    assert received is False
    assert downstream_called is False
    assert messages[0]["status"] == 303


def test_authenticated_oversized_upload_is_rejected_by_size_middleware(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/purchase-needs/1/prospecting-records/1/evidence/files",
        content=b"",
        headers={"Content-Length": str(MAX_UPLOAD_REQUEST_SIZE + 1)},
    )
    assert response.status_code == 413


def test_secure_cookie_flag_follows_valid_secure_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = Response()
    monkeypatch.setattr("app.auth.middleware.settings", SimpleNamespace(session_cookie_secure=True))
    set_session_cookie(response, "raw-token")
    assert "Secure" in response.headers["set-cookie"]


def test_auth_configuration_allows_only_loopback_http_or_https_secure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ORIGIN", "http://localhost:8000")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    assert Settings.from_environment().session_cookie_secure is False

    monkeypatch.setenv("APP_ORIGIN", "https://compras.example.test")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    assert Settings.from_environment().session_cookie_secure is True

    monkeypatch.setenv("APP_ORIGIN", "http://192.168.1.20:8000")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    with pytest.raises(ValueError):
        Settings.from_environment()

    monkeypatch.setenv("APP_ORIGIN", "http://localhost:8000/path")
    with pytest.raises(ValueError):
        Settings.from_environment()


def test_user_session_model_contains_only_approved_columns() -> None:
    assert set(User.__table__.columns.keys()) == {
        "id",
        "username",
        "password_hash",
        "is_active",
        "created_at",
    }
    assert set(UserSession.__table__.columns.keys()) == {
        "token_hash",
        "user_id",
        "csrf_token",
        "created_at",
        "expires_at",
    }


def test_new_app_keeps_docs_protected() -> None:
    new_app: FastAPI = create_app()
    with TestClient(new_app) as client:
        response = client.get("/openapi.json", follow_redirects=False)
    assert response.status_code == 303
