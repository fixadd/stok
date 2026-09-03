import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_query_app_context(request):
    """Give query-layer unit tests an isolated Flask context without changing DB engine."""
    if not request.node.fspath.basename.endswith("_queries.py"):
        yield
        return

    from app import create_app, db

    previous_data_dir = os.environ.get("DATA_DIR")
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["DATA_DIR"] = temp_dir
        test_app = create_app()
        try:
            with test_app.app_context():
                yield
        finally:
            db.session.remove()
            if previous_data_dir is None:
                os.environ.pop("DATA_DIR", None)
            else:
                os.environ["DATA_DIR"] = previous_data_dir
