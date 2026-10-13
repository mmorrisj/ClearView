import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip DB-marked tests unless DATABASE_URL is explicitly set."""
    if os.environ.get("DATABASE_URL"):
        return
    skip_db = pytest.mark.skip(reason="DATABASE_URL not set; skipping database tests")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip_db)
