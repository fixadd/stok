from datetime import datetime

import pytest

from app.models import CustomField, CustomFieldOption, SettingList, db
from app.services.settings_service import get_setting_options, save_custom_values, validate_custom_value


def test_seeded_setting_lists_are_available():
    status = SettingList.query.filter_by(key="inventory_status").first()
    assert status is not None
    assert {item.value for item in status.options} >= {"aktif", "hurda", "stokta"}


def test_optional_custom_field_accepts_empty_value():
    field = CustomField(entity_type="inventory", field_key="optional_note", label="Not", field_type="text", required=False)
    db.session.add(field)
    db.session.flush()
    assert validate_custom_value(field, "") is None


def test_required_custom_field_rejects_empty_value():
    field = CustomField(entity_type="inventory", field_key="required_note", label="Not", field_type="text", required=True)
    db.session.add(field)
    db.session.flush()
    with pytest.raises(ValueError, match="zorunludur"):
        validate_custom_value(field, "")


def test_select_custom_field_rejects_inactive_or_unknown_option():
    field = CustomField(entity_type="inventory", field_key="device_color", label="Renk", field_type="select")
    field.options.append(CustomFieldOption(label="Siyah", value="siyah", active=True))
    field.options.append(CustomFieldOption(label="Eski", value="eski", active=False))
    db.session.add(field)
    db.session.flush()
    assert validate_custom_value(field, "siyah") == "siyah"
    with pytest.raises(ValueError, match="geçersiz seçenek"):
        validate_custom_value(field, "eski")


def test_save_and_load_optional_custom_value():
    field = CustomField(entity_type="inventory", field_key="purchase_ref", label="Satın Alma Referansı", field_type="text", required=False, visible_form=True)
    db.session.add(field)
    db.session.flush()
    saved = save_custom_values("inventory", 987654, {"purchase_ref": "ABC-123"})
    db.session.commit()
    assert saved
    row = saved[0]
    assert row.value_text == "ABC-123"
