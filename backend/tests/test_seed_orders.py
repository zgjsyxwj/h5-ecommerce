from app.models import Order
from app.seed import seed_orders, seed_products


def test_should_have_five_seed_orders_with_at_least_three_distinct_users(db_session):
    # Given
    seed_products(db_session)

    # When
    seed_orders(db_session)

    # Then
    orders = db_session.query(Order).all()
    assert len(orders) == 5
    assert len({o.username for o in orders}) >= 3


def test_should_have_total_amount_equal_unit_price_times_quantity_for_all_orders(db_session):
    # Given
    seed_products(db_session)
    seed_orders(db_session)

    # When
    orders = db_session.query(Order).all()

    # Then
    for o in orders:
        assert o.total_amount == o.unit_price * o.quantity, (
            f"order id={o.id} sku={o.product_sku}: "
            f"total_amount={o.total_amount} != unit_price({o.unit_price}) × quantity({o.quantity})"
        )


def test_should_match_product_snapshot_at_order_time(db_session):
    # Given
    seed_products(db_session)
    seed_orders(db_session)

    # When
    orders = db_session.query(Order).all()

    # Then
    from app.models import Product
    for o in orders:
        product = db_session.query(Product).filter_by(sku=o.product_sku).one_or_none()
        assert product is not None, f"order id={o.id} references unknown sku={o.product_sku}"
        assert o.product_name == product.name
        assert o.unit_price == product.price
