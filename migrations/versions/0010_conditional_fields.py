"""Add conditional custom field dependencies

Revision ID: 0010_conditional_fields
Revises: 0009_platform_config
Create Date: 2026-09-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_conditional_fields"
down_revision = "0009_platform_config"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("custom_fields", sa.Column("depends_on_field_id", sa.Integer(), nullable=True))
    op.add_column("custom_fields", sa.Column("depends_on_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.create_foreign_key("fk_custom_fields_depends_on_field", "custom_fields", "custom_fields", ["depends_on_field_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_custom_fields_depends_on_field_id", "custom_fields", ["depends_on_field_id"])
    op.alter_column("custom_fields", "depends_on_values", server_default=None)

def downgrade():
    op.drop_index("ix_custom_fields_depends_on_field_id", table_name="custom_fields")
    op.drop_constraint("fk_custom_fields_depends_on_field", "custom_fields", type_="foreignkey")
    op.drop_column("custom_fields", "depends_on_values")
    op.drop_column("custom_fields", "depends_on_field_id")
