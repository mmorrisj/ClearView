import pytest

from lt.config import Settings


def test_settings_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.database_url.get_secret_value() == "postgresql+psycopg://u:p@db:5432/x"
    assert settings.log_level == "DEBUG"


def test_database_url_is_not_leaked_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:secretpw@db:5432/x")

    assert "secretpw" not in repr(Settings())
