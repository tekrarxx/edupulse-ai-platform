from app.core.config import Settings


def test_cors_origins_splits_and_strips_comma_separated_list() -> None:
    settings = Settings(api_cors_origins="http://a.test, http://b.test ,http://c.test")

    assert settings.cors_origins == ["http://a.test", "http://b.test", "http://c.test"]


def test_cors_origins_empty_string_yields_empty_list() -> None:
    settings = Settings(api_cors_origins="")

    assert settings.cors_origins == []
