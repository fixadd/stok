"""Add post-repair QA, approval and SLA tracking fields.

Revision ID: 0003_repair_qa_sla
Revises: 0002_inventory_repairs
Create Date: 2026-09-02
"""

from alembic import op

revision = "0003_repair_qa_sla"
down_revision = "0002_inventory_repairs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE inventory_repairs "
        "ADD COLUMN IF NOT EXISTS testing_status VARCHAR(32) NOT NULL DEFAULT 'bekliyor'"
    )
    op.execute(
        "ALTER TABLE inventory_repairs "
        "ADD COLUMN IF NOT EXISTS tested_at TIMESTAMP"
    )
    op.execute(
        "ALTER TABLE inventory_repairs "
        "ADD COLUMN IF NOT EXISTS tested_by VARCHAR(128)"
    )
    op.execute(
        "ALTER TABLE inventory_repairs "
        "ADD COLUMN IF NOT EXISTS approval_status VARCHAR(32) NOT NULL DEFAULT 'bekliyor'"
    )
    op.execute(
        "ALTER TABLE inventory_repairs "
        "ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP"
    )
    op.execute(
        "ALTER TABLE inventory_repairs "
        "ADD COLUMN IF NOT EXISTS approved_by VARCHAR(128)"
    )
    op.execute(
        "ALTER TABLE inventory_repairs "
        "ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP"
    )
    op.execute(
        "ALTER TABLE inventory_repairs "
        "ADD COLUMN IF NOT EXISTS delay_reason TEXT"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_repairs_sla_due_at "
        "ON inventory_repairs (sla_due_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_repairs_testing_status "
        "ON inventory_repairs (testing_status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_repairs_approval_status "
        "ON inventory_repairs (approval_status)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_inventory_repairs_approval_status")
    op.execute("DROP INDEX IF EXISTS ix_inventory_repairs_testing_status")
    op.execute("DROP INDEX IF EXISTS ix_inventory_repairs_sla_due_at")
    op.execute("ALTER TABLE inventory_repairs DROP COLUMN IF EXISTS delay_reason")
    op.execute("ALTER TABLE inventory_repairs DROP COLUMN IF EXISTS sla_due_at")
    op.execute("ALTER TABLE inventory_repairs DROP COLUMN IF EXISTS approved_by")
    op.execute("ALTER TABLE inventory_repairs DROP COLUMN IF EXISTS approved_at")
    op.execute("ALTER TABLE inventory_repairs DROP COLUMN IF EXISTS approval_status")
    op.execute("ALTER TABLE inventory_repairs DROP COLUMN IF EXISTS tested_by")
    op.execute("ALTER TABLE inventory_repairs DROP COLUMN IF EXISTS tested_at")
    op.execute("ALTER TABLE inventory_repairs DROP COLUMN IF EXISTS testing_status")
