from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.middleware import SESSION_COOKIE_NAME
from app.auth.models import User
from app.auth.passwords import hash_password
from app.auth.services import create_user_session
from app.db.base import Base
from app.db.session import get_session
from app.main import app

TEST_USERNAME = "compras.test"
TEST_PASSWORD = "passphrase de prueba segura"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


class AuthenticatedTestClient(TestClient):
    """Cliente de regresión que adjunta CSRF sin convertir cada test en uno de auth."""

    csrf_token: str

    def post(self, url: str, **kwargs: Any):
        if url != "/login":
            data = kwargs.get("data")
            if data is None:
                kwargs["data"] = {"_csrf_token": self.csrf_token}
            elif isinstance(data, dict):
                kwargs["data"] = dict(data) | {"_csrf_token": self.csrf_token}
        return super().post(url, **kwargs)


@pytest.fixture
def app_session_factory(tmp_path: Path) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.state.auth_session_factory = session_factory
    app.state.evidence_storage_path = tmp_path / "evidence"
    yield session_factory
    app.dependency_overrides.clear()
    del app.state.auth_session_factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def anonymous_client(
    app_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(
    app_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    with app_session_factory() as db:
        user = User(
            username=TEST_USERNAME,
            password_hash=TEST_PASSWORD_HASH,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_session, raw_token = create_user_session(db, user, 28800)
        csrf_token = user_session.csrf_token
    with TestClient(app) as test_client:
        test_client.cookies.set(SESSION_COOKIE_NAME, raw_token, domain="testserver.local", path="/")
        test_client.csrf_token = csrf_token  # type: ignore[attr-defined]
        yield test_client


@pytest.fixture
def client(
    app_session_factory: sessionmaker[Session],
) -> Generator[AuthenticatedTestClient, None, None]:
    with app_session_factory() as db:
        user = User(
            username=TEST_USERNAME,
            password_hash=TEST_PASSWORD_HASH,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_session, raw_token = create_user_session(db, user, 28800)
    with AuthenticatedTestClient(app) as test_client:
        test_client.cookies.set(SESSION_COOKIE_NAME, raw_token, domain="testserver.local", path="/")
        test_client.csrf_token = user_session.csrf_token
        yield test_client
