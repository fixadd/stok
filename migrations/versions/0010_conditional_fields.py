"""Add conditional custom field dependencies

Revision ID: 0010_conditional_fields
Revises: 0009_platform_extensions
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_conditional_fields"
down_revision = "0009_platform_extensions"
branch_labels = None
depends_on = None


def upgrade():
    # This migration must also be safe for databases where the application
    # schema already contains one or both conditional-field columns.
    conn = op.get_bind()

    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'custom_fields'
                  AND column_name = 'depends_on_field_id'
            ) THEN
                ALTER TABLE custom_fields
                    ADD COLUMN depends_on_field_id INTEGER;
            END IF;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'custom_fields'
                  AND column_name = 'depends_on_values'
            ) THEN
                ALTER TABLE custom_fields
                    ADD COLUMN depends_on_values JSONB NOT NULL DEFAULT '[]'::jsonb;
            END IF;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_custom_fields_depends_on_field'
                  AND conrelid = 'custom_fields'::regclass
            ) THEN
                ALTER TABLE custom_fields
                    ADD CONSTRAINT fk_custom_fields_depends_on_field
                    FOREIGN KEY (depends_on_field_id)
                    REFERENCES custom_fields(id)
                    ON DELETE SET NULL;
            END IF;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'custom_fields'
                  AND indexname = 'ix_custom_fields_depends_on_field_id'
            ) THEN
                CREATE INDEX ix_custom_fields_depends_on_field_id
                    ON custom_fields(depends_on_field_id);
            END IF;
        END $$;
    """))

    # Keep the column without a persistent server-side default after migration.
    conn.execute(sa.text("""
        ALTER TABLE custom_fields
        ALTER COLUMN depends_on_values DROP DEFAULT
    """))


def downgrade():
    conn = op.get_bind()

    conn.execute(sa.text("""
        DROP INDEX IF EXISTS ix_custom_fields_depends_on_field_id
    """))
    conn.execute(sa.text("""
        ALTER TABLE custom_fields
        DROP CONSTRAINT IF EXISTS fk_custom_fields_depends_on_field
    """))
    conn.execute(sa.text("""
        ALTER TABLE custom_fields
        DROP COLUMN IF EXISTS depends_on_values
    """))
    conn.execute(sa.text("""
        ALTER TABLE custom_fields
        DROP COLUMN IF EXISTS depends_on_field_id
    """))
