import pytest
from fastapi.testclient import TestClient


def purchase_need_data() -> dict[str, str]:
    return {
        "product_name": "Tomate chonto",
        "variety": "",
        "quality_standard": "Primera",
        "quantity": "100",
        "unit_of_measure": "kg",
        "required_delivery_date": "2026-09-15",
        "destination_city": "Bogotá",
        "destination_location": "Bodega central",
    }


def valid_offer_data() -> dict[str, str]:
    return {
        "price_amount": "82500.50",
        "price_unit": "canastilla",
        "currency": "COP",
        "obtained_on": "2026-09-08",
        "offered_description": "Tomate chonto primera de 22 kg",
        "conditions": "Flete incluido; pago a 30 días",
    }


def create_purchase_need(client: TestClient) -> int:
    response = client.post("/purchase-needs", data=purchase_need_data(), follow_redirects=False)
    return int(response.headers["location"].rsplit("/", maxsplit=1)[1])


def create_source(client: TestClient, name: str = "Directorio agrícola") -> int:
    response = client.post("/sources", data={"name": name}, follow_redirects=False)
    return int(response.headers["location"].rsplit("/", maxsplit=1)[1])


def create_provider(client: TestClient, name: str = "Agrícola Central") -> int:
    response = client.post("/providers", data={"name": name}, follow_redirects=False)
    return int(response.headers["location"].rsplit("/", maxsplit=1)[1])


def create_prospecting_record(
    client: TestClient, purchase_need_id: int, source_id: int, provider_id: int | None
) -> int:
    response = client.post(
        f"/purchase-needs/{purchase_need_id}/prospecting-records",
        data={
            "source_id": str(source_id),
            "provider_id": str(provider_id) if provider_id is not None else "",
            "notes": "",
        },
    )
    assert response.status_code == 200

    purchase_need = response.context["purchase_need"]
    prospecting_record = next(
        record for record in purchase_need.prospecting_records if record.source_id == source_id
    )
    return prospecting_record.id


def setup_prospecting(
    client: TestClient, *, with_provider: bool = True
) -> tuple[int, int, int, int]:
    purchase_need_id = create_purchase_need(client)
    source_id = create_source(client)
    provider_id = create_provider(client) if with_provider else None
    prospecting_record_id = create_prospecting_record(
        client, purchase_need_id, source_id, provider_id
    )
    return purchase_need_id, prospecting_record_id, source_id, provider_id or 0


def offer_collection_url(purchase_need_id: int, prospecting_record_id: int) -> str:
    return (
        f"/purchase-needs/{purchase_need_id}/prospecting-records/"
        f"{prospecting_record_id}/commercial-offers"
    )


def test_offer_can_be_created_and_shown_with_derived_context(client: TestClient) -> None:
    purchase_need_id, prospecting_record_id, source_id, provider_id = setup_prospecting(client)

    form = client.get(f"{offer_collection_url(purchase_need_id, prospecting_record_id)}/new")

    assert form.status_code == 200
    assert "Tomate chonto" in form.text
    assert "Directorio agrícola" in form.text
    assert "Agrícola Central" in form.text
    assert f'href="/sources/{source_id}"' in form.text
    assert f'href="/providers/{provider_id}"' in form.text

    response = client.post(
        offer_collection_url(purchase_need_id, prospecting_record_id),
        data=valid_offer_data(),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/purchase-needs/{purchase_need_id}"

    detail = client.get(response.headers["location"])
    assert detail.status_code == 200
    assert "COP 82500.5" in detail.text
    assert "por canastilla" in detail.text
    assert "2026-09-08" in detail.text
    assert "Tomate chonto primera de 22 kg" in detail.text
    assert "Flete incluido; pago a 30 días" in detail.text
    assert f'href="/sources/{source_id}"' in detail.text
    assert f'href="/providers/{provider_id}"' in detail.text


def test_multiple_offers_can_belong_to_same_prospecting_record(client: TestClient) -> None:
    purchase_need_id, prospecting_record_id, _, _ = setup_prospecting(client)
    first_offer = valid_offer_data()
    second_offer = valid_offer_data() | {
        "price_amount": "79000",
        "obtained_on": "2026-09-09",
        "offered_description": "Segunda respuesta del proveedor",
    }

    first_response = client.post(
        offer_collection_url(purchase_need_id, prospecting_record_id), data=first_offer
    )
    second_response = client.post(
        offer_collection_url(purchase_need_id, prospecting_record_id), data=second_offer
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert "COP 82500.5" in second_response.text
    assert "COP 79000" in second_response.text
    assert "Segunda respuesta del proveedor" in second_response.text


def test_offer_accepts_empty_optional_fields(client: TestClient) -> None:
    purchase_need_id, prospecting_record_id, _, _ = setup_prospecting(client)
    data = valid_offer_data() | {"offered_description": "   ", "conditions": ""}

    response = client.post(
        offer_collection_url(purchase_need_id, prospecting_record_id),
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 303


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("price_amount", "", "Ingrese un precio numérico mayor que cero."),
        ("price_amount", "no-numérico", "Ingrese un precio numérico mayor que cero."),
        ("price_amount", "NaN", "Ingrese un precio numérico mayor que cero."),
        ("price_amount", "Infinity", "Ingrese un precio numérico mayor que cero."),
        ("price_amount", "-Infinity", "Ingrese un precio numérico mayor que cero."),
        ("price_amount", "0", "Ingrese un precio numérico mayor que cero."),
        ("price_amount", "-100", "Ingrese un precio numérico mayor que cero."),
        ("price_unit", "   ", "Este campo es obligatorio."),
        ("currency", "", "Este campo es obligatorio."),
        ("obtained_on", "fecha-inválida", "Ingrese una fecha válida."),
    ],
)
def test_offer_rejects_invalid_required_values(
    client: TestClient, field: str, value: str, message: str
) -> None:
    purchase_need_id, prospecting_record_id, _, _ = setup_prospecting(client)
    data = valid_offer_data()
    data[field] = value

    response = client.post(offer_collection_url(purchase_need_id, prospecting_record_id), data=data)

    assert response.status_code == 422
    assert message in response.text


def test_offer_form_preserves_values_after_validation_error(client: TestClient) -> None:
    purchase_need_id, prospecting_record_id, _, _ = setup_prospecting(client)
    data = valid_offer_data() | {
        "price_amount": "0",
        "price_unit": "bulto especial",
        "currency": "USD",
        "obtained_on": "2026-09-10",
        "offered_description": "Descripción preservada",
        "conditions": "Condiciones preservadas",
    }

    response = client.post(offer_collection_url(purchase_need_id, prospecting_record_id), data=data)

    assert response.status_code == 422
    assert 'value="bulto especial"' in response.text
    assert 'value="USD"' in response.text
    assert 'value="2026-09-10"' in response.text
    assert "Descripción preservada" in response.text
    assert "Condiciones preservadas" in response.text


def test_offer_does_not_require_price_unit_to_match_purchase_need(client: TestClient) -> None:
    purchase_need_id, prospecting_record_id, _, _ = setup_prospecting(client)
    data = valid_offer_data() | {"price_unit": "caja de 12 unidades"}

    response = client.post(
        offer_collection_url(purchase_need_id, prospecting_record_id),
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 303


def test_prospecting_without_provider_does_not_offer_action_or_accept_offer(
    client: TestClient,
) -> None:
    purchase_need_id, prospecting_record_id, _, _ = setup_prospecting(client, with_provider=False)
    detail = client.get(f"/purchase-needs/{purchase_need_id}")

    assert "Sin proveedor" in detail.text
    assert "Registrar oferta comercial" not in detail.text

    form = client.get(f"{offer_collection_url(purchase_need_id, prospecting_record_id)}/new")
    response = client.post(
        offer_collection_url(purchase_need_id, prospecting_record_id), data=valid_offer_data()
    )

    assert form.status_code == 422
    assert response.status_code == 422
    assert "debe tener un proveedor asociado" in response.text


@pytest.mark.parametrize("method", ["get", "post"])
def test_offer_for_missing_purchase_need_returns_html_404(client: TestClient, method: str) -> None:
    path = offer_collection_url(404, 1)
    if method == "get":
        response = client.get(f"{path}/new")
    else:
        response = client.post(path, data=valid_offer_data())

    assert response.status_code == 404
    assert "Necesidad de compra no encontrada" in response.text


@pytest.mark.parametrize("method", ["get", "post"])
def test_missing_prospecting_record_returns_html_404(client: TestClient, method: str) -> None:
    purchase_need_id = create_purchase_need(client)
    path = offer_collection_url(purchase_need_id, 404)
    if method == "get":
        response = client.get(f"{path}/new")
    else:
        response = client.post(path, data=valid_offer_data())

    assert response.status_code == 404
    assert "Prospección no encontrada" in response.text


def test_prospecting_record_from_another_purchase_need_returns_html_404(
    client: TestClient,
) -> None:
    first_need_id, prospecting_record_id, _, _ = setup_prospecting(client)
    second_need_id = create_purchase_need(client)

    response = client.get(f"{offer_collection_url(second_need_id, prospecting_record_id)}/new")

    assert first_need_id != second_need_id
    assert response.status_code == 404
    assert "Prospección no encontrada" in response.text
