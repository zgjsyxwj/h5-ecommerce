import json

from app.models import Order
from app.schemas import LogisticsInfo, TrackingStatus
from app.seed import seed_orders, seed_products


def test_should_parse_logistics_info_with_valid_pydantic_schema_for_all_orders(db_session):
    # Given
    seed_products(db_session)
    seed_orders(db_session)

    # When / Then
    orders = db_session.query(Order).all()
    for o in orders:
        LogisticsInfo.model_validate_json(o.logistics_info)


def test_should_have_seven_top_level_fields_in_logistics_info(db_session):
    # Given (regression guard for spec AC #9)
    seed_products(db_session)
    seed_orders(db_session)

    expected_keys = {
        "recipient", "address", "phone", "tracking_no",
        "courier", "current_status", "tracking_history",
    }

    # When / Then
    for o in db_session.query(Order).all():
        keys = set(json.loads(o.logistics_info).keys())
        assert keys == expected_keys, f"order id={o.id} keys mismatch: {keys}"


def test_should_have_non_empty_tracking_history_with_four_fields_per_event(db_session):
    # Given (regression guard for spec AC #10)
    seed_products(db_session)
    seed_orders(db_session)

    expected_event_keys = {"timestamp", "status", "location", "description"}

    # When / Then
    for o in db_session.query(Order).all():
        info = json.loads(o.logistics_info)
        history = info["tracking_history"]
        assert len(history) >= 1
        for event in history:
            assert set(event.keys()) == expected_event_keys


def test_should_use_only_valid_status_enum_values(db_session):
    # Given (regression guard for spec AC #12)
    seed_products(db_session)
    seed_orders(db_session)
    valid_statuses = {s.value for s in TrackingStatus}

    # When / Then
    for o in db_session.query(Order).all():
        info = json.loads(o.logistics_info)
        assert info["current_status"] in valid_statuses
        for event in info["tracking_history"]:
            assert event["status"] in valid_statuses


def test_should_match_current_status_with_last_history_event(db_session):
    # Given (regression guard for spec AC #11)
    seed_products(db_session)
    seed_orders(db_session)

    # When / Then
    for o in db_session.query(Order).all():
        info = json.loads(o.logistics_info)
        assert info["current_status"] == info["tracking_history"][-1]["status"]


def test_should_cover_at_least_three_distinct_current_statuses_in_seed_orders(db_session):
    # Given (spec AC #13: 5 orders cover ≥3 distinct statuses for demo variety)
    seed_products(db_session)
    seed_orders(db_session)

    # When
    statuses = {
        json.loads(o.logistics_info)["current_status"]
        for o in db_session.query(Order).all()
    }

    # Then
    assert len(statuses) >= 3
