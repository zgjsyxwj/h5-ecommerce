from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Product


def test_should_raise_integrity_error_when_inserting_duplicate_sku(db_session):
    # Given
    db_session.add(
        Product(name="A", sku="DUP-001", stock=1, price=Decimal("1.00"), image_url="x")
    )
    db_session.commit()

    # When
    db_session.add(
        Product(name="B", sku="DUP-001", stock=1, price=Decimal("1.00"), image_url="x")
    )

    # Then
    with pytest.raises(IntegrityError):
        db_session.commit()
