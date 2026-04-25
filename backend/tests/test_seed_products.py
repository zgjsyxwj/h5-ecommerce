from app.models import Product
from app.seed import seed_products


def test_should_have_eight_seed_products(db_session):
    # Given / When
    seed_products(db_session)

    # Then
    assert db_session.query(Product).count() == 8


def test_should_have_all_products_with_positive_stock(db_session):
    # Given (regression guard: no sold-out concept this phase, all stock > 0)
    seed_products(db_session)

    # When
    products = db_session.query(Product).all()

    # Then
    assert all(p.stock > 0 for p in products)
