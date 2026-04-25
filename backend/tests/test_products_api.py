from app.seed import seed_products


def test_should_return_empty_list_when_no_products(client):
    # Given: no seed data
    # When
    response = client.get("/api/products")

    # Then
    assert response.status_code == 200
    assert response.json() == []


def test_should_return_eight_products_with_required_fields_via_api(client, db_session):
    # Given
    seed_products(db_session)

    # When
    response = client.get("/api/products")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 8
    assert set(body[0].keys()) == {"id", "name", "sku", "stock", "price", "image_url"}
