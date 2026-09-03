"""Bootstrap the existing application schema as the migration baseline.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-02
"""

from alembic import op

from app.models import db

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the baseline schema for a brand-new PostgreSQL database."""
    db.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Keep the baseline irreversible for existing installations."""
    pass
