"""Platform extension metadata for rules, dependencies, reports and notifications.

Revision ID: 0009_platform_extensions
Revises: 0008_configuration_catalog
"""

from alembic import op

revision = "0009_platform_extensions"
down_revision = "0008_configuration_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS configuration_rules (
            id SERIAL PRIMARY KEY,
            entity_type VARCHAR(64) NOT NULL,
            field_key VARCHAR(128) NOT NULL,
            rule_type VARCHAR(32) NOT NULL,
            rule_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_configuration_rules_entity ON configuration_rules(entity_type, field_key, active);

        CREATE TABLE IF NOT EXISTS lookup_dependencies (
            id SERIAL PRIMARY KEY,
            parent_key VARCHAR(128) NOT NULL,
            child_key VARCHAR(128) NOT NULL,
            mapping_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_lookup_dependency UNIQUE(parent_key, child_key)
        );

        CREATE TABLE IF NOT EXISTS report_definitions (
            id SERIAL PRIMARY KEY,
            key VARCHAR(128) NOT NULL UNIQUE,
            label VARCHAR(160) NOT NULL,
            entity_type VARCHAR(64) NOT NULL,
            definition_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_report_definitions_entity ON report_definitions(entity_type, active);

        CREATE TABLE IF NOT EXISTS notification_rules (
            id SERIAL PRIMARY KEY,
            key VARCHAR(128) NOT NULL UNIQUE,
            label VARCHAR(160) NOT NULL,
            event_key VARCHAR(128) NOT NULL,
            channel VARCHAR(32) NOT NULL DEFAULT 'web',
            target_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            condition_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_notification_rules_event ON notification_rules(event_key, active);

        CREATE TABLE IF NOT EXISTS api_tokens (
            id SERIAL PRIMARY KEY,
            name VARCHAR(160) NOT NULL,
            token_hash VARCHAR(128) NOT NULL UNIQUE,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            last_used_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_api_tokens_user_active ON api_tokens(user_id, active);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS api_tokens")
    op.execute("DROP TABLE IF EXISTS notification_rules")
    op.execute("DROP TABLE IF EXISTS report_definitions")
    op.execute("DROP TABLE IF EXISTS lookup_dependencies")
    op.execute("DROP TABLE IF EXISTS configuration_rules")
