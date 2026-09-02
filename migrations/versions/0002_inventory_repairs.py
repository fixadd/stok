"""Create the inventory repair/service table and supporting indexes.

Revision ID: 0002_inventory_repairs
Revises: 0001_baseline
Create Date: 2026-09-02
"""

from alembic import op

revision = "0002_inventory_repairs"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_repairs (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
            fault_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fault_type VARCHAR(128),
            problem_description TEXT NOT NULL,
            sent_to_service BOOLEAN NOT NULL DEFAULT FALSE,
            service_company VARCHAR(256),
            service_contact VARCHAR(128),
            service_ticket_no VARCHAR(128),
            warranty_status VARCHAR(32) NOT NULL DEFAULT 'belirsiz',
            sent_at TIMESTAMP,
            expected_return_at TIMESTAMP,
            returned_at TIMESTAMP,
            repair_description TEXT,
            service_cost NUMERIC(12,2),
            status VARCHAR(32) NOT NULL DEFAULT 'bekliyor',
            note TEXT,
            created_by VARCHAR(128) NOT NULL DEFAULT 'Sistem',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_repairs_item_id "
        "ON inventory_repairs (item_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_repairs_status "
        "ON inventory_repairs (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_repairs_expected_return_at "
        "ON inventory_repairs (expected_return_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_inventory_repairs_expected_return_at")
    op.execute("DROP INDEX IF EXISTS ix_inventory_repairs_status")
    op.execute("DROP INDEX IF EXISTS ix_inventory_repairs_item_id")
    op.execute("DROP TABLE IF EXISTS inventory_repairs")
