from app.models import Order, Product
from app.seed import seed_orders, seed_products


def test_should_not_duplicate_seed_data_on_repeated_init(db_session):
    # Given: first init
    seed_products(db_session)
    seed_orders(db_session)

    # When: second init (simulating app restart)
    seed_products(db_session)
    seed_orders(db_session)

    # Then: counts unchanged
    assert db_session.query(Product).count() == 8
    assert db_session.query(Order).count() == 5
