"""Shared pytest configuration for the PostgreSQL-backed test suite."""

import pytest


@pytest.fixture(autouse=True)
def application_context():
    """Keep Flask-SQLAlchemy model descriptors usable in unit tests.

    The fixture does not create tables or seed data. CI provisions the schema
    through Alembic before pytest starts.
    """
    from app import app

    with app.app_context():
        yield app


@pytest.fixture
def app(application_context):
    """Provide the conventional Flask app fixture name to focused tests."""
    return application_context
