from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ..models import CustomField, CustomFieldOption, CustomFieldValue, FieldGroup, SettingList, SettingOption, db

FIELD_TYPES = {
    "text": "Metin",
    "textarea": "Uzun metin",
    "integer": "Tam sayı",
    "decimal": "Ondalık sayı",
    "boolean": "Evet/Hayır",
    "date": "Tarih",
    "datetime": "Tarih + saat",
    "select": "Seçim",
    "multiselect": "Çoklu seçim",
    "url": "URL",
    "json": "JSON",
}


def get_setting_lists(scope: str | None = None, *, active_only: bool = False):
    query = SettingList.query.order_by(SettingList.scope, SettingList.sort_order, SettingList.id)
    if scope:
        query = query.filter(SettingList.scope == scope)
    if active_only:
        query = query.filter(SettingList.active.is_(True))
    return query.all()


def get_setting_options(key: str, *, active_only: bool = True):
    setting = SettingList.query.filter_by(key=key).first()
    if not setting:
        return []
    return [option for option in setting.options if not active_only or option.active]


def get_setting_map(key: str) -> dict[str, str]:
    return {item.value: item.label for item in get_setting_options(key)}


def upsert_setting_option(list_id: int, label: str, value: str | None = None, *, active: bool = True, sort_order: int = 0, metadata: dict[str, Any] | None = None) -> SettingOption:
    setting = db.session.get(SettingList, list_id)
    if setting is None:
        raise ValueError("Ayar listesi bulunamadı.")
    label = label.strip()
    value = (value or label).strip().lower().replace(" ", "_")
    if not label or not value:
        raise ValueError("Seçenek adı boş olamaz.")
    option = SettingOption.query.filter_by(setting_list_id=list_id, value=value).first()
    if option is None:
        option = SettingOption(setting_list_id=list_id, label=label, value=value)
        db.session.add(option)
    option.label = label
    option.active = active
    option.sort_order = int(sort_order or 0)
    option.metadata_json = metadata or {}
    return option


def toggle_setting_option(option_id: int, active: bool) -> SettingOption:
    option = db.session.get(SettingOption, option_id)
    if option is None:
        raise ValueError("Seçenek bulunamadı.")
    option.active = bool(active)
    return option


def get_custom_fields(entity_type: str, *, form_only: bool = False, active_only: bool = True):
    query = CustomField.query.filter(CustomField.entity_type == entity_type).order_by(CustomField.sort_order, CustomField.id)
    if active_only:
        query = query.filter(CustomField.active.is_(True))
    if form_only:
        query = query.filter(CustomField.visible_form.is_(True))
    return query.all()


def validate_custom_value(field: CustomField, raw: Any) -> Any:
    value = raw
    if isinstance(value, str):
        value = value.strip()
    if value in (None, "", []):
        if field.required:
            raise ValueError(f"{field.label} alanı zorunludur.")
        return None
    if field.field_type in {"text", "textarea", "url"}:
        value = str(value)
        if field.regex_pattern and not re.fullmatch(field.regex_pattern, value):
            raise ValueError(f"{field.label} alanı geçerli formatta değil.")
    elif field.field_type == "integer":
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field.label} tam sayı olmalıdır.")
    elif field.field_type == "decimal":
        try:
            value = Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError):
            raise ValueError(f"{field.label} sayısal olmalıdır.")
    elif field.field_type == "boolean":
        value = bool(value) if not isinstance(value, str) else value.lower() in {"1", "true", "yes", "on", "evet"}
    elif field.field_type in {"date", "datetime"}:
        try:
            value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"{field.label} tarih formatı geçersiz.")
    elif field.field_type in {"select", "multiselect"}:
        allowed = {option.value for option in field.options if option.active}
        values = value if isinstance(value, list) else [value]
        if any(str(item) not in allowed for item in values):
            raise ValueError(f"{field.label} için geçersiz seçenek.")
        value = [str(item) for item in values] if field.field_type == "multiselect" else str(values[0])
    if field.validation_min is not None and isinstance(value, (int, float, Decimal)) and value < field.validation_min:
        raise ValueError(f"{field.label} minimum değerden küçük olamaz.")
    if field.validation_max is not None and isinstance(value, (int, float, Decimal)) and value > field.validation_max:
        raise ValueError(f"{field.label} maksimum değeri aşamaz.")
    return value


def _clear_value_columns(row: CustomFieldValue) -> None:
    row.value_text = None
    row.value_number = None
    row.value_date = None
    row.value_boolean = None
    row.value_json = None


def save_custom_values(entity_type: str, entity_id: int, payload: dict[str, Any]) -> list[CustomFieldValue]:
    """Persist only fields supplied by the caller; omitted fields remain unchanged."""
    fields = get_custom_fields(entity_type, form_only=True)
    saved = []
    for field in fields:
        if field.field_key not in payload:
            continue
        raw = payload.get(field.field_key)
        value = validate_custom_value(field, raw)
        row = CustomFieldValue.query.filter_by(field_id=field.id, entity_type=entity_type, entity_id=entity_id).first()
        if value is None:
            if row:
                db.session.delete(row)
            continue
        if row is None:
            row = CustomFieldValue(field_id=field.id, entity_type=entity_type, entity_id=entity_id)
            db.session.add(row)
        _clear_value_columns(row)
        if isinstance(value, bool):
            row.value_boolean = value
        elif isinstance(value, (int, float, Decimal)):
            row.value_number = value
        elif isinstance(value, datetime):
            row.value_date = value
        elif isinstance(value, list) or field.field_type == "json":
            row.value_json = value
        else:
            row.value_text = str(value)
        saved.append(row)
    return saved


def load_custom_values(entity_type: str, entity_id: int) -> dict[str, Any]:
    rows = CustomFieldValue.query.join(CustomField).filter(CustomFieldValue.entity_type == entity_type, CustomFieldValue.entity_id == entity_id, CustomField.active.is_(True)).all()
    result = {}
    for row in rows:
        if row.value_json is not None:
            value = row.value_json
        elif row.value_boolean is not None:
            value = row.value_boolean
        elif row.value_date is not None:
            value = row.value_date
        elif row.value_number is not None:
            value = row.value_number
        else:
            value = row.value_text
        result[row.field.field_key] = value
    return result


def serialize_custom_field(field: CustomField) -> dict[str, Any]:
    return {
        "id": field.id,
        "entity_type": field.entity_type,
        "field_key": field.field_key,
        "label": field.label,
        "field_type": field.field_type,
        "required": field.required,
        "active": field.active,
        "visible_form": field.visible_form,
        "visible_list": field.visible_list,
        "searchable": field.searchable,
        "sortable": field.sortable,
        "placeholder": field.placeholder or "",
        "help_text": field.help_text or "",
        "default_value": field.default_value or "",
        "sort_order": field.sort_order,
        "group_id": field.group_id,
        "options": [{"id": o.id, "label": o.label, "value": o.value, "active": o.active, "sort_order": o.sort_order} for o in field.options],
    }
