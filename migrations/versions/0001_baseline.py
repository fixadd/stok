"""Mark the existing application schema as the migration baseline.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-02
"""

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing installations must be stamped with this revision once.
    # The baseline intentionally makes no schema changes.
    pass


def downgrade() -> None:
    pass
