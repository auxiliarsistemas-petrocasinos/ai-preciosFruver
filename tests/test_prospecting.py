import pytest
from fastapi.testclient import TestClient


def purchase_need_data(product_name: str = "Tomate chonto") -> dict[str, str]:
    return {
        "product_name": product_name,
        "variety": "",
        "quality_standard": "",
        "quantity": "100",
        "unit_of_measure": "kg",
        "required_delivery_date": "2026-09-15",
        "destination_city": "Bogotá",
        "destination_location": "Bodega central",
    }


def create_purchase_need(client: TestClient, product_name: str = "Tomate chonto") -> int:
    response = client.post(
        "/purchase-needs", data=purchase_need_data(product_name), follow_redirects=False
    )
    return int(response.headers["location"].rsplit("/", maxsplit=1)[1])


def create_source(client: TestClient, name: str = "Google Maps") -> int:
    response = client.post("/sources", data={"name": name}, follow_redirects=False)
    return int(response.headers["location"].rsplit("/", maxsplit=1)[1])


def create_provider(client: TestClient, name: str = "Fruver La Sabana") -> int:
    response = client.post("/providers", data={"name": name}, follow_redirects=False)
    return int(response.headers["location"].rsplit("/", maxsplit=1)[1])


def test_prospecting_record_can_be_created_with_provider_and_is_shown(
    client: TestClient,
) -> None:
    purchase_need_id = create_purchase_need(client)
    source_id = create_source(client)
    provider_id = create_provider(client)

    response = client.post(
        f"/purchase-needs/{purchase_need_id}/prospecting-records",
        data={
            "source_id": str(source_id),
            "provider_id": str(provider_id),
            "notes": "Respondió por teléfono",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/purchase-needs/{purchase_need_id}"

    detail = client.get(response.headers["location"])
    assert "Google Maps" in detail.text
    assert "Fruver La Sabana" in detail.text
    assert "Respondió por teléfono" in detail.text
    assert f'href="/sources/{source_id}"' in detail.text
    assert f'href="/providers/{provider_id}"' in detail.text


def test_prospecting_record_can_be_created_without_provider(client: TestClient) -> None:
    purchase_need_id = create_purchase_need(client)
    source_id = create_source(client, "Directorio comercial")

    response = client.post(
        f"/purchase-needs/{purchase_need_id}/prospecting-records",
        data={"source_id": str(source_id), "provider_id": "", "notes": "Sin resultados"},
    )

    assert response.status_code == 200
    assert "Directorio comercial" in response.text
    assert "Sin proveedor" in response.text
    assert "Sin resultados" in response.text


@pytest.mark.parametrize(
    ("invalid_field", "message"),
    [
        ("source_id", "Seleccione una fuente existente."),
        ("provider_id", "Seleccione un proveedor existente o deje el campo vacío."),
    ],
)
def test_prospecting_record_rejects_nonexistent_ids(
    client: TestClient, invalid_field: str, message: str
) -> None:
    purchase_need_id = create_purchase_need(client)
    source_id = create_source(client)
    record_data = {"source_id": str(source_id), "provider_id": "", "notes": ""}
    record_data[invalid_field] = "999"

    response = client.post(
        f"/purchase-needs/{purchase_need_id}/prospecting-records",
        data=record_data,
    )

    assert response.status_code == 422
    assert message in response.text
    assert "No hay prospecciones registradas para esta necesidad." in response.text


def test_sources_and_providers_are_reused_across_purchase_needs(client: TestClient) -> None:
    first_need_id = create_purchase_need(client, "Tomate")
    second_need_id = create_purchase_need(client, "Papa")
    source_id = create_source(client, "Sitio web del proveedor")
    provider_id = create_provider(client, "Agrícola Central")

    record_data = {"source_id": str(source_id), "provider_id": str(provider_id), "notes": ""}
    first_response = client.post(
        f"/purchase-needs/{first_need_id}/prospecting-records", data=record_data
    )
    second_response = client.post(
        f"/purchase-needs/{second_need_id}/prospecting-records", data=record_data
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert "Sitio web del proveedor" in first_response.text
    assert "Agrícola Central" in first_response.text
    assert "Sitio web del proveedor" in second_response.text
    assert "Agrícola Central" in second_response.text
    assert client.get("/sources").text.count("Sitio web del proveedor") == 1
    assert client.get("/providers").text.count("Agrícola Central") == 1


def test_prospecting_for_missing_purchase_need_returns_html_404(client: TestClient) -> None:
    source_id = create_source(client)

    response = client.post(
        "/purchase-needs/404/prospecting-records",
        data={"source_id": str(source_id), "provider_id": "", "notes": ""},
    )

    assert response.status_code == 404
    assert "Necesidad de compra no encontrada" in response.text
