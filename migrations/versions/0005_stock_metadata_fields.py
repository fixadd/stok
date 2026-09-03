"""Move stock category field definitions into PostgreSQL.

Revision ID: 0005_stock_metadata_fields
Revises: 0004_operational_indexes
Create Date: 2026-09-03
"""

from alembic import op

revision = "0005_stock_metadata_fields"
down_revision = "0004_operational_indexes"
branch_labels = None
depends_on = None

FIELDS = {
    "envanter": [
        ("inventory_no", "Envanter No", "ENV-001", True, False, None),
        ("hardware_type", "Donanım Tipi", "Örn. Dizüstü Bilgisayar", True, False, None),
        ("brand", "Marka", "Marka", True, False, None),
        ("model", "Model", "Model", True, False, None),
        ("serial_no", "Seri No", "Seri numarası", False, False, None),
        ("computer_name", "Cihaz Adı", "Örn. IT-LAPTOP-01", False, False, None),
        ("factory", "Fabrika", "Fabrika adı", True, True, "factories"),
        ("department", "Departman", "Departman", True, True, "departments"),
        ("responsible", "Sorumlu", "Sorumlu kişi", True, True, "responsibles"),
        ("ifs_no", "IFS No", "IFS-00001", False, True, None),
    ],
    "cevre_birimi": [
        ("hardware_type", "Donanım Tipi", "Örn. Klavye", True, False, None),
        ("brand", "Marka", "Marka", False, False, None),
        ("model", "Model", "Model", False, False, None),
        ("serial_no", "Seri No", "Seri numarası", False, False, None),
        ("factory", "Fabrika", "Fabrika adı", False, True, "factories"),
        ("department", "Departman", "Departman", False, True, "departments"),
        ("responsible", "Sorumlu", "Teslim edilen kişi", True, True, "responsibles"),
    ],
    "yazici": [
        ("inventory_no", "Envanter No", "IPY-001", True, False, None),
        ("brand", "Marka", "Marka", True, False, None),
        ("model", "Model", "Model", True, False, None),
        ("serial_no", "Seri No", "Seri numarası", False, False, None),
        ("usage_area", "Kullanım Alanı", "Örn. Finans", False, True, "usage_areas"),
        ("factory", "Fabrika", "Fabrika adı", True, True, "factories"),
        ("hostname", "Hostname", "PRN-OFIS-01", False, True, None),
        ("ip_address", "IP Adresi", "10.0.0.10", False, True, None),
        ("mac_address", "MAC Adresi", "AA:BB:CC:DD:EE:FF", False, True, None),
        ("responsible", "Sorumlu", "Sorumlu kişi", True, True, "responsibles"),
    ],
    "lisans": [
        ("license_name", "Lisans Adı", "Ürün adı", True, False, "license_names"),
        ("license_key", "Lisans Anahtarı", "XXXX-XXXX-XXXX", True, False, None),
        ("inventory_no", "Bağlı Envanter", "ENV-001", False, False, "inventory_numbers"),
        ("factory", "Fabrika", "Fabrika adı", False, True, "factories"),
        ("department", "Departman", "Departman", False, True, "departments"),
        ("responsible", "Sorumlu", "Teslim edilen kişi", False, True, "responsibles"),
    ],
    "talep": [
        ("hardware_type", "Donanım Tipi", "Donanım tipi", True, False, None),
        ("brand", "Marka", "Marka", False, False, None),
        ("model", "Model", "Model", False, False, None),
        ("department", "Departman", "Departman", False, False, None),
    ],
    "manuel": [
        ("hardware_type", "Donanım Tipi", "Donanım tipi", True, False, None),
        ("brand", "Marka", "Marka", False, False, None),
        ("model", "Model", "Model", False, False, None),
    ],
}


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_metadata_fields (
            id SERIAL PRIMARY KEY,
            category VARCHAR(32) NOT NULL,
            field_key VARCHAR(64) NOT NULL,
            label VARCHAR(128) NOT NULL,
            placeholder VARCHAR(256),
            required BOOLEAN NOT NULL DEFAULT FALSE,
            assignment_only BOOLEAN NOT NULL DEFAULT FALSE,
            options_key VARCHAR(64),
            sort_order INTEGER NOT NULL DEFAULT 0,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            UNIQUE (category, field_key)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stock_metadata_fields_category_active "
        "ON stock_metadata_fields (category, active, sort_order)"
    )
    for category, fields in FIELDS.items():
        for sort_order, (key, label, placeholder, required, assignment_only, options_key) in enumerate(fields):
            op.execute(
                """
                INSERT INTO stock_metadata_fields
                    (category, field_key, label, placeholder, required, assignment_only, options_key, sort_order)
                VALUES (:category, :field_key, :label, :placeholder, :required, :assignment_only, :options_key, :sort_order)
                ON CONFLICT (category, field_key) DO UPDATE SET
                    label = EXCLUDED.label,
                    placeholder = EXCLUDED.placeholder,
                    required = EXCLUDED.required,
                    assignment_only = EXCLUDED.assignment_only,
                    options_key = EXCLUDED.options_key,
                    sort_order = EXCLUDED.sort_order,
                    active = TRUE
                """,
                {
                    "category": category,
                    "field_key": key,
                    "label": label,
                    "placeholder": placeholder,
                    "required": required,
                    "assignment_only": assignment_only,
                    "options_key": options_key,
                    "sort_order": sort_order,
                },
            )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stock_metadata_fields")
