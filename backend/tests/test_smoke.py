def test_should_import_app_when_smoke():
    # Given / When
    from app.main import app

    # Then
    assert app is not None
