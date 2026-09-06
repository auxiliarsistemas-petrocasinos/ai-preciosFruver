from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def valid_form_data() -> dict[str, str]:
    return {
        "product_name": "Tomate chonto",
        "variety": "",
        "quality_standard": "",
        "quantity": "125.5",
        "unit_of_measure": "kg",
        "required_delivery_date": "2026-09-15",
        "destination_city": "Bogotá",
        "destination_location": "Bodega central, calle 1",
    }


def test_purchase_need_can_be_created_and_consulted(client: TestClient) -> None:
    response = client.post("/purchase-needs", data=valid_form_data(), follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/purchase-needs/1"

    detail = client.get(response.headers["location"])

    assert detail.status_code == 200
    assert "Tomate chonto" in detail.text
    assert "No registrada" in detail.text
    assert "No registrado" in detail.text


def test_purchase_need_list_shows_registered_needs(client: TestClient) -> None:
    client.post("/purchase-needs", data=valid_form_data())

    response = client.get("/purchase-needs")

    assert response.status_code == 200
    assert "Tomate chonto" in response.text
    assert "125.5 kg" in response.text


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("product_name", "   ", "Este campo es obligatorio."),
        ("unit_of_measure", "", "Este campo es obligatorio."),
        ("quantity", "0", "Ingrese una cantidad numérica mayor que cero."),
        ("quantity", "no-numérica", "Ingrese una cantidad numérica mayor que cero."),
        ("required_delivery_date", "not-a-date", "Ingrese una fecha válida."),
        ("destination_city", "", "Este campo es obligatorio."),
        ("destination_location", "", "Este campo es obligatorio."),
    ],
)
def test_purchase_need_rejects_invalid_required_values(
    client: TestClient, field: str, value: str, message: str
) -> None:
    data = valid_form_data()
    data[field] = value

    response = client.post("/purchase-needs", data=data)

    assert response.status_code == 422
    assert message in response.text


def test_missing_purchase_need_returns_html_404(client: TestClient) -> None:
    response = client.get("/purchase-needs/404")

    assert response.status_code == 404
    assert "Necesidad de compra no encontrada" in response.text
