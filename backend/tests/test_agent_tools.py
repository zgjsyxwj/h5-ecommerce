import pytest
from sqlalchemy.orm import sessionmaker

from app.agent.tools import list_products
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
