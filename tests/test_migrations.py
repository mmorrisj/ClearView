import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


@pytest.mark.db
def test_baseline_migration_enables_pgvector() -> None:
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        ext = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        assert ext.scalar_one() == "vector"
    engine.dispose()
