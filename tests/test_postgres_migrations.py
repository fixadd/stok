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

    required = {
        "alembic_version",
        "stock_metadata_fields",
        "login_attempts",
        "setting_lists",
        "setting_options",
        "custom_fields",
        "custom_field_values",
        "dashboard_widgets",
        "configuration_rules",
        "lookup_dependencies",
        "report_definitions",
        "notification_rules",
        "api_tokens",
    }
    assert required <= tables

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision == "0010_conditional_fields"
        metadata_count = connection.execute(
            text("SELECT COUNT(*) FROM stock_metadata_fields WHERE active = TRUE")
        ).scalar_one()
        assert metadata_count > 0
        setting_count = connection.execute(
            text("SELECT COUNT(*) FROM setting_lists WHERE active = TRUE")
        ).scalar_one()
        assert setting_count >= 7
