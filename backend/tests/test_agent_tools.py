import pytest
from sqlalchemy.orm import sessionmaker

from app.agent.tools import get_product_info, list_products
from app.seed import seed_products


@pytest.fixture
def tools_session(db_session, monkeypatch):
    """Bind app.agent.tools.SessionLocal to the test in-memory engine."""
    TestSessionLocal = sessionmaker(
        bind=db_session.get_bind(), autoflush=False, expire_on_commit=False
    )
    monkeypatch.setattr("app.agent.tools.SessionLocal", TestSessionLocal)
    return db_session


def test_should_return_8_products_when_listing_all(tools_session):
    # Given
    seed_products(tools_session)

    # When
    result = list_products()

    # Then
    assert len(result) == 8
    assert all({"id", "name", "sku", "stock", "price", "image_url"} <= p.keys() for p in result)


def test_should_return_AUDIO_001_when_searching_by_chinese_name(tools_session):
    # Given
    seed_products(tools_session)

    # When
    result = get_product_info("蓝牙耳机")

    # Then
    assert len(result) == 1
    assert result[0]["sku"] == "AUDIO-001"
    assert result[0]["price"] == "299.00"


def test_should_return_KB_001_when_searching_by_sku(tools_session):
    # Given (AC6: get_product_info 也支持 SKU 模糊匹配)
    seed_products(tools_session)

    # When
    result = get_product_info("KB-001")

    # Then
    assert len(result) == 1
    assert result[0]["name"] == "机械键盘·87 键"


def test_should_return_empty_when_searching_unknown_product(tools_session):
    # Given (AC7: 无匹配返回空列表，不抛异常)
    seed_products(tools_session)

    # When
    result = get_product_info("不存在的商品")

    # Then
    assert result == []
