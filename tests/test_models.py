import os

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine

from lt.db import models  # noqa: F401  (register tables on Base.metadata)
from lt.db.base import Base


@pytest.mark.db
def test_migrations_match_models(engine: Engine) -> None:
    """Fails if a model changes without a matching Alembic migration."""
    assert os.environ["DATABASE_URL"]
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []
