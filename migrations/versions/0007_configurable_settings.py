"""configurable settings and custom fields

Revision ID: 0007_configurable_settings
Revises: 0006_login_attempts
"""

from alembic import op
from sqlalchemy import text

revision = "0007_configurable_settings"
down_revision = "0006_login_attempts"
branch_labels = None
depends_on = None

DDL = [
    """CREATE TABLE IF NOT EXISTS setting_lists (
        id SERIAL PRIMARY KEY, key VARCHAR(128) NOT NULL UNIQUE, label VARCHAR(160) NOT NULL,
        scope VARCHAR(64) NOT NULL DEFAULT 'general', description VARCHAR(500), active BOOLEAN NOT NULL DEFAULT TRUE,
        sort_order INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS ix_setting_lists_scope ON setting_lists(scope)",
    "CREATE INDEX IF NOT EXISTS ix_setting_lists_active ON setting_lists(active)",
    """CREATE TABLE IF NOT EXISTS setting_options (
        id SERIAL PRIMARY KEY, setting_list_id INTEGER NOT NULL REFERENCES setting_lists(id) ON DELETE CASCADE,
        label VARCHAR(160) NOT NULL, value VARCHAR(160) NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE,
        sort_order INTEGER NOT NULL DEFAULT 0, metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_setting_option_list_value UNIQUE(setting_list_id, value)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_setting_options_list ON setting_options(setting_list_id)",
    "CREATE INDEX IF NOT EXISTS ix_setting_options_active ON setting_options(active)",
    """CREATE TABLE IF NOT EXISTS field_groups (
        id SERIAL PRIMARY KEY, entity_type VARCHAR(64) NOT NULL, key VARCHAR(128) NOT NULL, label VARCHAR(160) NOT NULL,
        description VARCHAR(500), active BOOLEAN NOT NULL DEFAULT TRUE, sort_order INTEGER NOT NULL DEFAULT 0,
        CONSTRAINT uq_field_group_entity_key UNIQUE(entity_type, key)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_field_groups_entity ON field_groups(entity_type)",
    "CREATE INDEX IF NOT EXISTS ix_field_groups_active ON field_groups(active)",
    """CREATE TABLE IF NOT EXISTS custom_fields (
        id SERIAL PRIMARY KEY, entity_type VARCHAR(64) NOT NULL, field_key VARCHAR(128) NOT NULL, label VARCHAR(160) NOT NULL,
        field_type VARCHAR(32) NOT NULL DEFAULT 'text', group_id INTEGER REFERENCES field_groups(id) ON DELETE SET NULL,
        required BOOLEAN NOT NULL DEFAULT FALSE, active BOOLEAN NOT NULL DEFAULT TRUE, visible_form BOOLEAN NOT NULL DEFAULT TRUE,
        visible_list BOOLEAN NOT NULL DEFAULT FALSE, searchable BOOLEAN NOT NULL DEFAULT FALSE, sortable BOOLEAN NOT NULL DEFAULT FALSE,
        placeholder VARCHAR(250), help_text VARCHAR(500), default_value VARCHAR(500), validation_min NUMERIC, validation_max NUMERIC,
        regex_pattern VARCHAR(500), sort_order INTEGER NOT NULL DEFAULT 0, settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        CONSTRAINT uq_custom_field_entity_key UNIQUE(entity_type, field_key)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_custom_fields_entity ON custom_fields(entity_type)",
    "CREATE INDEX IF NOT EXISTS ix_custom_fields_group ON custom_fields(group_id)",
    "CREATE INDEX IF NOT EXISTS ix_custom_fields_active ON custom_fields(active)",
    """CREATE TABLE IF NOT EXISTS custom_field_options (
        id SERIAL PRIMARY KEY, field_id INTEGER NOT NULL REFERENCES custom_fields(id) ON DELETE CASCADE,
        label VARCHAR(160) NOT NULL, value VARCHAR(160) NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE, sort_order INTEGER NOT NULL DEFAULT 0,
        CONSTRAINT uq_custom_field_option_value UNIQUE(field_id, value)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_custom_field_options_field ON custom_field_options(field_id)",
    """CREATE TABLE IF NOT EXISTS custom_field_values (
        id SERIAL PRIMARY KEY, field_id INTEGER NOT NULL REFERENCES custom_fields(id) ON DELETE CASCADE,
        entity_type VARCHAR(64) NOT NULL, entity_id INTEGER NOT NULL, value_text TEXT, value_number NUMERIC,
        value_date TIMESTAMP, value_boolean BOOLEAN, value_json JSONB, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_custom_field_value_target UNIQUE(field_id, entity_type, entity_id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_custom_field_values_target ON custom_field_values(entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS ix_custom_field_values_field ON custom_field_values(field_id)",
    """CREATE TABLE IF NOT EXISTS dashboard_widgets (
        id SERIAL PRIMARY KEY, widget_key VARCHAR(128) NOT NULL UNIQUE, label VARCHAR(160) NOT NULL,
        widget_type VARCHAR(32) NOT NULL DEFAULT 'metric', config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        active BOOLEAN NOT NULL DEFAULT TRUE, sort_order INTEGER NOT NULL DEFAULT 0
    )""",
]


def upgrade() -> None:
    conn = op.get_bind()
    for statement in DDL:
        conn.execute(text(statement))

    seed = {
        "inventory_status": ("Envanter Durumu", "inventory", [("Aktif", "aktif"), ("Beklemede", "beklemede"), ("Arızalı", "arizali"), ("Hurda", "hurda"), ("Stokta", "stokta")]),
        "license_status": ("Lisans Durumu", "license", [("Aktif", "aktif"), ("Pasif", "pasif"), ("Beklemede", "beklemede")]),
        "stock_status": ("Stok Durumu", "stock", [("Stokta", "stokta"), ("Devredildi", "devredildi"), ("Arızalı", "arizali"), ("Hurda", "hurda")]),
        "stock_unit": ("Stok Birimi", "stock", [("Adet", "adet"), ("Kutu", "kutu"), ("Paket", "paket"), ("Metre", "metre")]),
        "maintenance_type": ("Bakım Türü", "maintenance", [("Periyodik", "periyodik"), ("Arıza", "ariza"), ("Temizlik", "temizlik"), ("Parça Değişimi", "parca_degisimi"), ("Diğer", "diger")]),
        "priority": ("Öncelik", "general", [("Düşük", "dusuk"), ("Normal", "normal"), ("Yüksek", "yuksek"), ("Kritik", "kritik")]),
        "request_status": ("Talep Durumu", "request", [("Yeni", "yeni"), ("İnceleniyor", "inceleniyor"), ("Onay Bekliyor", "onay_bekliyor"), ("Onaylandı", "onaylandi"), ("Reddedildi", "reddedildi"), ("Tamamlandı", "tamamlandi"), ("İptal", "iptal")]),
        "employment_status": ("İstihdam Durumu", "users", [("Aktif", "aktif"), ("Pasif", "pasif")]),
    }
    for key, (label, scope, options) in seed.items():
        conn.execute(text("INSERT INTO setting_lists (key,label,scope,active,sort_order,created_at,updated_at) VALUES (:key,:label,:scope,TRUE,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) ON CONFLICT (key) DO NOTHING"), {"key": key, "label": label, "scope": scope})
        for order, (option_label, value) in enumerate(options):
            conn.execute(text("INSERT INTO setting_options (setting_list_id,label,value,sort_order,active,metadata_json,created_at,updated_at) SELECT id,:label,:value,:sort_order,TRUE,'{}'::jsonb,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM setting_lists WHERE key=:key ON CONFLICT (setting_list_id,value) DO NOTHING"), {"key": key, "label": option_label, "value": value, "sort_order": order})


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dashboard_widgets")
    op.execute("DROP TABLE IF EXISTS custom_field_values")
    op.execute("DROP TABLE IF EXISTS custom_field_options")
    op.execute("DROP TABLE IF EXISTS custom_fields")
    op.execute("DROP TABLE IF EXISTS field_groups")
    op.execute("DROP TABLE IF EXISTS setting_options")
    op.execute("DROP TABLE IF EXISTS setting_lists")
