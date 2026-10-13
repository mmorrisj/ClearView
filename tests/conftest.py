import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


def pytest_configure(config: pytest.Config) -> None:
    """Point the app at a dedicated, disposable test database.

    DB tests reset the schema (downgrade to base), so they must never run against a
    database holding real data. They use TEST_DATABASE_URL only, and refuse to start if it
    matches DATABASE_URL.
    """
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        return
    if test_url == os.environ.get("DATABASE_URL"):
        pytest.exit("TEST_DATABASE_URL must differ from DATABASE_URL (tests wipe it)", 2)
    os.environ["DATABASE_URL"] = test_url  # read by lt.config and alembic/env.py


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip DB-marked tests unless TEST_DATABASE_URL is set."""
    if os.environ.get("TEST_DATABASE_URL"):
        return
    skip_db = pytest.mark.skip(reason="TEST_DATABASE_URL not set; skipping database tests")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip_db)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    # Start every run from an empty schema so leftover rows can't affect results.
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    eng = create_engine(os.environ["DATABASE_URL"])
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back after each test, even if the code under test commits."""
    with engine.connect() as conn:
        trans = conn.begin()
        with Session(bind=conn, join_transaction_mode="create_savepoint") as s:
            yield s
        trans.rollback()
