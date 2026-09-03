from decimal import Decimal

import pytest

from app.models import CustomField, CustomFieldOption, db
from app.services.configuration_service import build_form_schema
from app.services.settings_service import validate_custom_value


def test_optional_custom_field_accepts_empty(app):
    with app.app_context():
        field = CustomField(entity_type="inventory", field_key="test_optional", label="Test", field_type="text", required=False)
        db.session.add(field)
        db.session.commit()
        assert validate_custom_value(field, "") is None


def test_required_custom_field_rejects_empty(app):
    with app.app_context():
        field = CustomField(entity_type="inventory", field_key="test_required", label="Test", field_type="text", required=True)
        db.session.add(field)
        db.session.commit()
        with pytest.raises(ValueError, match="zorunludur"):
            validate_custom_value(field, "")


def test_select_schema_contains_only_active_options(app):
    with app.app_context():
        field = CustomField(entity_type="inventory", field_key="test_select", label="Test", field_type="select")
        db.session.add(field)
        db.session.flush()
        db.session.add_all([
            CustomFieldOption(field_id=field.id, label="Aktif", value="aktif", active=True),
            CustomFieldOption(field_id=field.id, label="Pasif", value="pasif", active=False),
        ])
        db.session.commit()
        schema = build_form_schema("inventory")
        item = next(x for x in schema if x["key"] == "test_select")
        assert [x["value"] for x in item["options"]] == ["aktif"]
