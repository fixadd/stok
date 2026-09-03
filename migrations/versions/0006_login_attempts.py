"""Add persistent login attempt tracking.

Revision ID: 0006_login_attempts
Revises: 0005_stock_metadata_fields
Create Date: 2026-09-03
"""

from alembic import op

revision = "0006_login_attempts"
down_revision = "0005_stock_metadata_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS login_attempts (
            id BIGSERIAL PRIMARY KEY,
            subject_hash VARCHAR(128) NOT NULL,
            ip_hash VARCHAR(128) NOT NULL,
            attempted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN NOT NULL DEFAULT FALSE
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_login_attempts_subject_time "
        "ON login_attempts (subject_hash, attempted_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_login_attempts_ip_time "
        "ON login_attempts (ip_hash, attempted_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS login_attempts")
