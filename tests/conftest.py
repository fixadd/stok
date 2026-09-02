import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_query_app_context(request):
    """Give query-layer unit tests a Flask context without sharing CI's DB."""
    if not request.node.fspath.basename.endswith("_queries.py"):
        yield
        return

    from app import create_app, db

    previous_database_url = os.environ.get("DATABASE_URL")
    previous_data_dir = os.environ.get("DATA_DIR")
    with tempfile.TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "query-tests.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["DATA_DIR"] = temp_dir
        test_app = create_app()
        try:
            with test_app.app_context():
                yield
        finally:
            db.session.remove()
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url
            if previous_data_dir is None:
                os.environ.pop("DATA_DIR", None)
            else:
                os.environ["DATA_DIR"] = previous_data_dir
