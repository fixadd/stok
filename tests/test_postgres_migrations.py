from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text


def test_postgresql_schema_contains_operational_tables():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for PostgreSQL integration tests")
    if not database_url.startswith("postgresql"):
        pytest.fail("CI and integration tests must use PostgreSQL, not SQLite")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    required = {"alembic_version", "stock_metadata_fields", "login_attempts"}
    assert required <= tables

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision == "0006_login_attempts"
        metadata_count = connection.execute(
            text("SELECT COUNT(*) FROM stock_metadata_fields WHERE active = TRUE")
        ).scalar_one()
        assert metadata_count > 0
