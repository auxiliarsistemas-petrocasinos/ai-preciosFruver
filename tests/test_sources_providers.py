from fastapi.testclient import TestClient


def test_source_can_be_created_listed_and_consulted_with_non_url_reference(
    client: TestClient,
) -> None:
    response = client.post(
        "/sources",
        data={
            "name": "Directorio comercial",
            "reference": "Edición impresa 2026, sección agrícola",
            "notes": "Consultado por compras",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    source_id = int(response.headers["location"].rsplit("/", maxsplit=1)[1])
    assert response.headers["location"] == f"/sources/{source_id}"

    listing = client.get("/sources")
    detail = client.get(f"/sources/{source_id}")

    assert listing.status_code == 200
    assert "Directorio comercial" in listing.text
    assert detail.status_code == 200
    assert "Edición impresa 2026, sección agrícola" in detail.text
    assert "Consultado por compras" in detail.text


def test_source_reference_is_optional(client: TestClient) -> None:
    response = client.post("/sources", data={"name": "Referido", "reference": "", "notes": ""})

    assert response.status_code == 200
    assert "Referido" in response.text
    assert "No registrada" in response.text


def test_source_rejects_blank_name(client: TestClient) -> None:
    response = client.post(
        "/sources", data={"name": "   ", "reference": "Texto libre", "notes": ""}
    )

    assert response.status_code == 422
    assert "Este campo es obligatorio." in response.text
    assert "Texto libre" in response.text


def test_missing_source_returns_html_404(client: TestClient) -> None:
    response = client.get("/sources/404")

    assert response.status_code == 404
    assert "Fuente no encontrada" in response.text


def test_provider_can_be_created_listed_and_consulted(client: TestClient) -> None:
    response = client.post(
        "/providers",
        data={
            "name": "Cultivos del Norte",
            "contact_name": "Ana Díaz",
            "email": "compras@example.test",
            "phone": "+57 300 123 4567",
            "location": "Tunja, Boyacá",
            "notes": "Atención mayorista",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    provider_id = int(response.headers["location"].rsplit("/", maxsplit=1)[1])
    assert response.headers["location"] == f"/providers/{provider_id}"

    listing = client.get("/providers")
    detail = client.get(f"/providers/{provider_id}")

    assert listing.status_code == 200
    assert "Cultivos del Norte" in listing.text
    assert detail.status_code == 200
    assert "Ana Díaz" in detail.text
    assert "compras@example.test" in detail.text
    assert "+57 300 123 4567" in detail.text
    assert "Tunja, Boyacá" in detail.text
    assert "Atención mayorista" in detail.text


def test_provider_is_valid_with_name_only(client: TestClient) -> None:
    response = client.post("/providers", data={"name": "Proveedor mínimo"})

    assert response.status_code == 200
    assert "Proveedor mínimo" in response.text
    assert "No registrado" in response.text


def test_provider_rejects_blank_name(client: TestClient) -> None:
    response = client.post("/providers", data={"name": "   ", "location": "Medellín"})

    assert response.status_code == 422
    assert "Este campo es obligatorio." in response.text
    assert "Medellín" in response.text


def test_missing_provider_returns_html_404(client: TestClient) -> None:
    response = client.get("/providers/404")

    assert response.status_code == 404
    assert "Proveedor no encontrado" in response.text
