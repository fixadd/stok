"""expand configurable lookup catalog

Revision ID: 0008_configuration_catalog
Revises: 0007_configurable_settings
"""

from alembic import op
from sqlalchemy import text

revision = "0008_configuration_catalog"
down_revision = "0007_configurable_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    seed = {
        "maintenance_status": ("Bakım Durumu", "maintenance", [("Planlandı", "planlandi"), ("Devam Ediyor", "devam_ediyor"), ("Tamamlandı", "tamamlandi"), ("İptal", "iptal")]),
        "maintenance_result": ("Bakım Sonucu", "maintenance", [("Çözüldü", "cozuldu"), ("Parça Bekleniyor", "parca_bekleniyor"), ("Serviste", "serviste"), ("Çözülemedi", "cozulemedi")]),
        "request_type": ("Talep Türü", "request", [("Yeni Ekipman", "yeni_ekipman"), ("Yazılım", "yazilim"), ("Erişim", "erisim"), ("Arıza", "ariza"), ("Sarf Malzeme", "sarf_malzeme"), ("Diğer", "diger")]),
        "request_priority": ("Talep Önceliği", "request", [("Düşük", "dusuk"), ("Normal", "normal"), ("Yüksek", "yuksek"), ("Kritik", "kritik")]),
        "license_type": ("Lisans Türü", "license", [("Abonelik", "abonelik"), ("Kalıcı", "kalici"), ("OEM", "oem"), ("Deneme", "deneme"), ("Diğer", "diger")]),
        "license_status": ("Lisans Durumu", "license", [("Aktif", "aktif"), ("Pasif", "pasif"), ("Beklemede", "beklemede"), ("Süresi Dolmuş", "suresi_dolmus")]),
        "stock_source": ("Stok Kaynağı", "stock", [("Satın Alma", "satin_alma"), ("Devir", "devir"), ("Bağış", "bagis"), ("Diğer", "diger")]),
    }
    for key, (label, scope, options) in seed.items():
        conn.execute(text("INSERT INTO setting_lists (key,label,scope,active,sort_order,created_at,updated_at) VALUES (:key,:label,:scope,TRUE,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) ON CONFLICT (key) DO NOTHING"), {"key": key, "label": label, "scope": scope})
        for order, (option_label, value) in enumerate(options):
            conn.execute(text("INSERT INTO setting_options (setting_list_id,label,value,sort_order,active,metadata_json,created_at,updated_at) SELECT id,:label,:value,:sort_order,TRUE,'{}'::jsonb,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM setting_lists WHERE key=:key ON CONFLICT (setting_list_id,value) DO NOTHING"), {"key": key, "label": option_label, "value": value, "sort_order": order})


def downgrade() -> None:
    pass
