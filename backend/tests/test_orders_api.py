import pytest
from sqlalchemy.orm import sessionmaker

from app.seed import seed_orders, seed_products


@pytest.fixture
def api_client(client, db_session, monkeypatch):
    """组合 client fixture + tools.SessionLocal monkey-patch + seed。"""
    test_sessionmaker = sessionmaker(
        bind=db_session.get_bind(), autoflush=False, expire_on_commit=False
    )
    monkeypatch.setattr("app.agent.tools.SessionLocal", test_sessionmaker)
    seed_products(db_session)
    seed_orders(db_session)
    return client


def test_should_return_alex_orders_when_get_orders_by_username(api_client):
    # When
    response = api_client.get("/api/orders?username=alex")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {r["order_id"] for r in body} == {1, 2}


def test_should_return_empty_list_when_username_has_no_orders(api_client):
    # Given (AC10: 未知用户 200 + 空列表)
    # When
    response = api_client.get("/api/orders?username=nobody")

    # Then
    assert response.status_code == 200
    assert response.json() == []


def test_should_return_422_when_username_query_missing(api_client):
    # Given (AC11: 缺 query 参数 → FastAPI 自动 422)
    # When
    response = api_client.get("/api/orders")

    # Then
    assert response.status_code == 422


def test_should_return_order_detail_when_get_by_id(api_client):
    # Given (AC12: order 1 详情含 14 键、4 个物流事件、已签收)
    # When
    response = api_client.get("/api/orders/1")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["current_status"] == "已签收"
    assert len(body["tracking_history"]) == 4
    expected_keys = {
        "order_id", "username", "product_name", "product_sku", "quantity",
        "unit_price", "total_amount",
        "recipient", "address", "phone",
        "tracking_no", "courier", "current_status", "tracking_history",
    }
    assert expected_keys <= body.keys()


def test_should_return_404_when_order_id_unknown(api_client):
    # Given (AC13: 不存在的 order_id 返回 404 + detail)
    # When
    response = api_client.get("/api/orders/999")

    # Then
    assert response.status_code == 404
    assert "detail" in response.json()
