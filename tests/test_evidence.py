from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.commercial_offers.models import CommercialOffer
from app.db.base import Base
from app.evidence.models import Evidence
from app.prospecting.models import ProspectingRecord
from app.providers.models import Provider
from app.purchase_needs.models import PurchaseNeed
from app.sources.models import Source


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


def persist_evidence_targets(db_session: Session) -> tuple[int, int]:
    purchase_need = PurchaseNeed(
        product_name="Tomate chonto",
        quantity=Decimal("100"),
        unit_of_measure="kg",
        required_delivery_date=date(2026, 9, 15),
        destination_city="Bogotá",
        destination_location="Bodega central",
    )
    source = Source(name="Sitio web")
    provider = Provider(name="Agrícola Central")
    db_session.add_all([purchase_need, source, provider])
    db_session.flush()

    prospecting_record = ProspectingRecord(
        purchase_need_id=purchase_need.id,
        source_id=source.id,
        provider_id=provider.id,
    )
    db_session.add(prospecting_record)
    db_session.flush()

    commercial_offer = CommercialOffer(
        prospecting_record_id=prospecting_record.id,
        price_amount=Decimal("82500"),
        price_unit="canastilla",
        currency="COP",
        obtained_on=date(2026, 9, 8),
    )
    db_session.add(commercial_offer)
    db_session.commit()
    return prospecting_record.id, commercial_offer.id


def purchase_need_data(product_name: str = "Tomate chonto") -> dict[str, str]:
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


def evidence_data(
    title: str = "Consulta del precio publicado",
    url: str = "https://example.test/precios/tomate",
) -> dict[str, str]:
    return {
        "title": title,
        "url": url,
        "captured_on": "2026-09-08",
        "notes": "Referencia revisada por compras",
    }


def offer_data(price_amount: str = "82500") -> dict[str, str]:
    return {
        "price_amount": price_amount,
        "price_unit": "canastilla",
        "currency": "COP",
        "obtained_on": "2026-09-08",
        "offered_description": "Tomate chonto primera",
        "conditions": "Flete incluido",
    }


def create_purchase_need(client: TestClient, product_name: str = "Tomate chonto") -> int:
    response = client.post(
        "/purchase-needs", data=purchase_need_data(product_name), follow_redirects=False
    )
    return int(response.headers["location"].rsplit("/", maxsplit=1)[1])


def create_source(client: TestClient, name: str = "Sitio web") -> int:
    response = client.post("/sources", data={"name": name}, follow_redirects=False)
    return int(response.headers["location"].rsplit("/", maxsplit=1)[1])


def create_provider(client: TestClient, name: str = "Agrícola Central") -> int:
    response = client.post("/providers", data={"name": name}, follow_redirects=False)
    return int(response.headers["location"].rsplit("/", maxsplit=1)[1])


def create_prospecting_record(
    client: TestClient,
    purchase_need_id: int,
    source_id: int,
    provider_id: int | None = None,
) -> int:
    response = client.post(
        f"/purchase-needs/{purchase_need_id}/prospecting-records",
        data={
            "source_id": str(source_id),
            "provider_id": str(provider_id) if provider_id is not None else "",
            "notes": "",
        },
    )
    purchase_need = response.context["purchase_need"]
    return max(record.id for record in purchase_need.prospecting_records)


def create_offer(
    client: TestClient,
    purchase_need_id: int,
    prospecting_record_id: int,
    price_amount: str = "82500",
) -> int:
    response = client.post(
        commercial_offer_collection(purchase_need_id, prospecting_record_id),
        data=offer_data(price_amount),
    )
    purchase_need = response.context["purchase_need"]
    record = next(
        item for item in purchase_need.prospecting_records if item.id == prospecting_record_id
    )
    return max(offer.id for offer in record.commercial_offers)


def setup_prospecting(
    client: TestClient, *, with_provider: bool = False
) -> tuple[int, int, int | None]:
    purchase_need_id = create_purchase_need(client)
    source_id = create_source(client)
    provider_id = create_provider(client) if with_provider else None
    prospecting_record_id = create_prospecting_record(
        client, purchase_need_id, source_id, provider_id
    )
    return purchase_need_id, prospecting_record_id, provider_id


def prospecting_evidence_base(purchase_need_id: int, prospecting_record_id: int) -> str:
    return (
        f"/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/evidence"
    )


def commercial_offer_collection(purchase_need_id: int, prospecting_record_id: int) -> str:
    return (
        f"/purchase-needs/{purchase_need_id}/prospecting-records/"
        f"{prospecting_record_id}/commercial-offers"
    )


def offer_evidence_base(
    purchase_need_id: int, prospecting_record_id: int, commercial_offer_id: int
) -> str:
    return (
        f"/purchase-needs/{purchase_need_id}/prospecting-records/{prospecting_record_id}/"
        f"commercial-offers/{commercial_offer_id}/evidence"
    )


def request_form_or_create(client: TestClient, method: str, collection_path: str):
    if method == "get":
        return client.get(f"{collection_path}/new")
    return client.post(collection_path, data=evidence_data())


def test_prospecting_evidence_can_be_created_without_provider_and_persists(
    client: TestClient,
) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client)
    path = prospecting_evidence_base(purchase_need_id, prospecting_record_id)

    form = client.get(f"{path}/new")
    response = client.post(path, data=evidence_data(), follow_redirects=False)

    assert form.status_code == 200
    assert "Tomate chonto" in form.text
    assert "Sitio web" in form.text
    assert "Sin proveedor" in form.text
    assert response.status_code == 303
    assert response.headers["location"] == f"/purchase-needs/{purchase_need_id}"

    detail = client.get(response.headers["location"])
    assert detail.status_code == 200
    assert "Consulta del precio publicado" in detail.text
    assert 'href="https://example.test/precios/tomate"' in detail.text
    assert "2026-09-08" in detail.text
    assert "Referencia revisada por compras" in detail.text


def test_prospecting_evidence_can_be_created_with_provider_and_without_offer(
    client: TestClient,
) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client, with_provider=True)

    response = client.post(
        prospecting_evidence_base(purchase_need_id, prospecting_record_id),
        data=evidence_data(),
        follow_redirects=False,
    )

    assert response.status_code == 303
    detail = client.get(response.headers["location"])
    assert "Agrícola Central" in detail.text
    assert "Consulta del precio publicado" in detail.text


def test_multiple_prospecting_evidence_is_ordered_and_kept_under_correct_record(
    client: TestClient,
) -> None:
    purchase_need_id, first_record_id, _ = setup_prospecting(client)
    second_source_id = create_source(client, "Directorio alterno")
    second_record_id = create_prospecting_record(client, purchase_need_id, second_source_id)
    path = prospecting_evidence_base(purchase_need_id, first_record_id)
    shared_url = "https://example.test/misma-referencia"

    client.post(
        path,
        data=evidence_data("Referencia anterior", shared_url) | {"captured_on": "2026-09-07"},
    )
    client.post(
        path,
        data=evidence_data("Referencia reciente", shared_url) | {"captured_on": "2026-09-09"},
    )

    detail = client.get(f"/purchase-needs/{purchase_need_id}")
    records = {record.id: record for record in detail.context["purchase_need"].prospecting_records}
    assert [item.title for item in records[first_record_id].evidence_items] == [
        "Referencia reciente",
        "Referencia anterior",
    ]
    assert records[second_record_id].evidence_items == []
    assert detail.text.count(f'href="{shared_url}"') == 2


def test_offer_evidence_can_be_created_and_shown_under_correct_offer(
    client: TestClient,
) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client, with_provider=True)
    first_offer_id = create_offer(client, purchase_need_id, prospecting_record_id)
    second_offer_id = create_offer(client, purchase_need_id, prospecting_record_id, "79000")
    path = offer_evidence_base(purchase_need_id, prospecting_record_id, first_offer_id)

    form = client.get(f"{path}/new")
    first_response = client.post(path, data=evidence_data("Cotización web"))
    second_response = client.post(
        path,
        data=evidence_data("Condiciones publicadas", "https://example.test/condiciones")
        | {"captured_on": "2026-09-09"},
    )

    assert form.status_code == 200
    purchase_need = form.context["purchase_need"]
    prospecting_record = form.context["prospecting_record"]
    commercial_offer = form.context["commercial_offer"]
    displayed_price = f"{commercial_offer.price_amount:f}".rstrip("0").rstrip(".")
    assert commercial_offer.id == first_offer_id
    assert purchase_need.product_name in form.text
    assert prospecting_record.source.name in form.text
    assert prospecting_record.provider.name in form.text
    assert commercial_offer.currency in form.text
    assert displayed_price in form.text
    assert f"por {commercial_offer.price_unit}" in form.text
    assert first_response.status_code == 200
    assert second_response.status_code == 200

    detail = client.get(f"/purchase-needs/{purchase_need_id}")
    record = next(
        item
        for item in detail.context["purchase_need"].prospecting_records
        if item.id == prospecting_record_id
    )
    offers = {offer.id: offer for offer in record.commercial_offers}
    assert [item.title for item in offers[first_offer_id].evidence_items] == [
        "Condiciones publicadas",
        "Cotización web",
    ]
    assert offers[second_offer_id].evidence_items == []


@pytest.mark.parametrize("method", ["get", "post"])
def test_evidence_for_missing_purchase_need_returns_html_404(
    client: TestClient, method: str
) -> None:
    response = request_form_or_create(client, method, prospecting_evidence_base(404, 1))

    assert response.status_code == 404
    assert "Necesidad de compra no encontrada" in response.text


@pytest.mark.parametrize("method", ["get", "post"])
def test_missing_prospecting_record_returns_html_404(client: TestClient, method: str) -> None:
    purchase_need_id = create_purchase_need(client)

    response = request_form_or_create(
        client, method, prospecting_evidence_base(purchase_need_id, 404)
    )

    assert response.status_code == 404
    assert "Prospección no encontrada" in response.text


@pytest.mark.parametrize("method", ["get", "post"])
def test_prospecting_record_from_another_purchase_need_returns_html_404(
    client: TestClient, method: str
) -> None:
    first_need_id, prospecting_record_id, _ = setup_prospecting(client)
    second_need_id = create_purchase_need(client, "Papa pastusa")

    response = request_form_or_create(
        client, method, prospecting_evidence_base(second_need_id, prospecting_record_id)
    )

    assert first_need_id != second_need_id
    assert response.status_code == 404
    assert "Prospección no encontrada" in response.text


@pytest.mark.parametrize("method", ["get", "post"])
def test_missing_commercial_offer_returns_html_404(client: TestClient, method: str) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client, with_provider=True)

    response = request_form_or_create(
        client,
        method,
        offer_evidence_base(purchase_need_id, prospecting_record_id, 404),
    )

    assert response.status_code == 404
    assert "Oferta comercial no encontrada" in response.text


@pytest.mark.parametrize("method", ["get", "post"])
def test_offer_from_another_prospecting_record_returns_html_404(
    client: TestClient, method: str
) -> None:
    purchase_need_id, first_record_id, provider_id = setup_prospecting(client, with_provider=True)
    source_id = create_source(client, "Segundo sitio")
    second_record_id = create_prospecting_record(client, purchase_need_id, source_id, provider_id)
    offer_id = create_offer(client, purchase_need_id, first_record_id)

    response = request_form_or_create(
        client,
        method,
        offer_evidence_base(purchase_need_id, second_record_id, offer_id),
    )

    assert response.status_code == 404
    assert "Oferta comercial no encontrada" in response.text


@pytest.mark.parametrize("method", ["get", "post"])
def test_offer_indirectly_from_another_purchase_need_returns_html_404(
    client: TestClient, method: str
) -> None:
    first_need_id, first_record_id, _ = setup_prospecting(client, with_provider=True)
    offer_id = create_offer(client, first_need_id, first_record_id)
    second_need_id = create_purchase_need(client, "Papa pastusa")
    second_source_id = create_source(client, "Fuente para papa")
    second_provider_id = create_provider(client, "Proveedor de papa")
    second_record_id = create_prospecting_record(
        client, second_need_id, second_source_id, second_provider_id
    )

    response = request_form_or_create(
        client,
        method,
        offer_evidence_base(second_need_id, second_record_id, offer_id),
    )

    assert response.status_code == 404
    assert "Oferta comercial no encontrada" in response.text


@pytest.mark.parametrize("title", ["", "   "])
def test_evidence_rejects_blank_title(client: TestClient, title: str) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client)
    data = evidence_data() | {"title": title}

    response = client.post(
        prospecting_evidence_base(purchase_need_id, prospecting_record_id), data=data
    )

    assert response.status_code == 422
    assert "Este campo es obligatorio." in response.text


@pytest.mark.parametrize(
    "invalid_url",
    [
        "",
        "ruta/relativa",
        "javascript:alert(1)",
        "data:text/plain,contenido",
        "file:///etc/passwd",
        "mailto:compras@example.test",
        "http://",
        "https://",
    ],
)
def test_evidence_rejects_invalid_url(client: TestClient, invalid_url: str) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client)
    data = evidence_data() | {"url": invalid_url}

    response = client.post(
        prospecting_evidence_base(purchase_need_id, prospecting_record_id), data=data
    )

    assert response.status_code == 422
    assert "URL" in response.text


def test_evidence_rejects_invalid_date(client: TestClient) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client)
    data = evidence_data() | {"captured_on": "fecha-inválida"}

    response = client.post(
        prospecting_evidence_base(purchase_need_id, prospecting_record_id), data=data
    )

    assert response.status_code == 422
    assert "Ingrese una fecha válida." in response.text


def test_empty_notes_are_stored_as_null(client: TestClient) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client)

    response = client.post(
        prospecting_evidence_base(purchase_need_id, prospecting_record_id),
        data=evidence_data()
        | {
            "title": "  Título sin espacios externos  ",
            "url": "  https://example.test/referencia-limpia  ",
            "notes": "   ",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    detail = client.get(response.headers["location"])
    record = next(
        item
        for item in detail.context["purchase_need"].prospecting_records
        if item.id == prospecting_record_id
    )
    evidence = record.evidence_items[0]
    assert evidence.title == "Título sin espacios externos"
    assert evidence.url == "https://example.test/referencia-limpia"
    assert evidence.notes is None


def test_evidence_form_preserves_values_after_validation_error(client: TestClient) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client)
    data = {
        "title": "  Referencia conservada  ",
        "url": "ruta-inválida",
        "captured_on": "2026-09-10",
        "notes": "Notas conservadas",
    }

    response = client.post(
        prospecting_evidence_base(purchase_need_id, prospecting_record_id), data=data
    )

    assert response.status_code == 422
    assert 'value="  Referencia conservada  "' in response.text
    assert 'value="ruta-inválida"' in response.text
    assert 'value="2026-09-10"' in response.text
    assert "Notas conservadas" in response.text


def test_unreachable_http_url_is_accepted_without_remote_verification(client: TestClient) -> None:
    purchase_need_id, prospecting_record_id, _ = setup_prospecting(client)

    response = client.post(
        prospecting_evidence_base(purchase_need_id, prospecting_record_id),
        data=evidence_data(url="https://unreachable.invalid/evidence"),
        follow_redirects=False,
    )

    assert response.status_code == 303


def test_database_xor_rejects_both_or_neither_target(db_session: Session) -> None:
    prospecting_record_id, offer_id = persist_evidence_targets(db_session)

    for prospecting_id, commercial_offer_id in [(None, None), (prospecting_record_id, offer_id)]:
        db_session.add(
            Evidence(
                prospecting_record_id=prospecting_id,
                commercial_offer_id=commercial_offer_id,
                title="Estado inválido",
                url="https://example.test/invalida",
                captured_on=date(2026, 9, 8),
            )
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


def test_database_xor_allows_each_valid_target(db_session: Session) -> None:
    prospecting_record_id, offer_id = persist_evidence_targets(db_session)
    prospecting_evidence = Evidence(
        prospecting_record_id=prospecting_record_id,
        title="Evidencia de prospección",
        url="https://example.test/prospeccion",
        captured_on=date(2026, 9, 8),
    )
    offer_evidence = Evidence(
        commercial_offer_id=offer_id,
        title="Evidencia de oferta",
        url="https://example.test/oferta",
        captured_on=date(2026, 9, 8),
    )

    db_session.add_all([prospecting_evidence, offer_evidence])
    db_session.commit()

    assert prospecting_evidence.id is not None
    assert offer_evidence.id is not None
    assert db_session.get(CommercialOffer, offer_id) is not None
