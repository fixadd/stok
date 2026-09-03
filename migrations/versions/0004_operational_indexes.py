"""Add operational indexes for common filters and relationship lookups.

Revision ID: 0004_operational_indexes
Revises: 0003_repair_qa_sla
Create Date: 2026-09-03
"""

from alembic import op

revision = "0004_operational_indexes"
down_revision = "0003_repair_qa_sla"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_inventory_items_status", "inventory_items", "status"),
    ("ix_inventory_items_factory_id", "inventory_items", "factory_id"),
    ("ix_inventory_items_responsible_user_id", "inventory_items", "responsible_user_id"),
    ("ix_inventory_items_hardware_type_id", "inventory_items", "hardware_type_id"),
    ("ix_inventory_items_brand_id", "inventory_items", "brand_id"),
    ("ix_inventory_items_model_id", "inventory_items", "model_id"),
    ("ix_inventory_items_serial_no", "inventory_items", "serial_no"),
    ("ix_inventory_events_item_id_performed_at", "inventory_events", "item_id, performed_at"),
    ("ix_inventory_assignments_item_id_returned_at", "inventory_assignments", "item_id, returned_at"),
    ("ix_inventory_assignments_assigned_user_id", "inventory_assignments", "assigned_user_id"),
    ("ix_inventory_maintenances_item_id_performed_at", "inventory_maintenances", "item_id, performed_at"),
    ("ix_inventory_licenses_item_id_status", "inventory_licenses", "item_id, status"),
    ("ix_stock_logs_stock_item_id_created_at", "stock_logs", "stock_item_id, created_at"),
    ("ix_stock_movements_stock_item_id_created_at", "stock_movements", "stock_item_id, created_at"),
    ("ix_stock_assignments_stock_item_id_created_at", "stock_assignments", "stock_item_id, created_at"),
    ("ix_stock_audit_logs_stock_item_id_created_at", "stok_hareketleri", "stock_item_id, created_at"),
    ("ix_request_orders_group_id_opened_at", "request_orders", "group_id, opened_at"),
    ("ix_request_lines_order_id", "request_lines", "order_id"),
    ("ix_request_line_snapshots_order_id", "request_line_snapshots", "order_id"),
    ("ix_info_entries_category_id_created_at", "info_entries", "category_id, created_at"),
    ("ix_info_attachments_entry_id", "info_attachments", "entry_id"),
)


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})")


def downgrade() -> None:
    for name, _table, _columns in reversed(INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")
