from __future__ import annotations

from typing import Any

from ..models import CustomField, FieldGroup
from .settings_service import get_custom_fields, get_setting_options

ENTITY_LABELS = {
    "inventory": "Envanter",
    "stock": "Stok",
    "maintenance": "Bakım",
    "request": "Talep",
    "license": "Lisans",
    "user": "Kullanıcı",
}


def setting_choices(key: str) -> list[dict[str, str]]:
    return [{"value": option.value, "label": option.label} for option in get_setting_options(key)]


def build_form_schema(entity_type: str) -> list[dict[str, Any]]:
    fields = get_custom_fields(entity_type, form_only=True)
    groups = {group.id: group for group in FieldGroup.query.filter_by(entity_type=entity_type, active=True).all()}
    result: list[dict[str, Any]] = []
    for field in fields:
        result.append({
            "id": field.id,
            "key": field.field_key,
            "label": field.label,
            "type": field.field_type,
            "required": field.required,
            "placeholder": field.placeholder or "",
            "help_text": field.help_text or "",
            "default_value": field.default_value,
            "group_id": field.group_id,
            "group_label": groups[field.group_id].label if field.group_id in groups else None,
            "depends_on_field_id": field.depends_on_field_id,
            "depends_on_key": field.depends_on_field.field_key if field.depends_on_field_id and field.depends_on_field else None,
            "depends_on_values": field.depends_on_values or [],
            "options": [
                {"value": option.value, "label": option.label}
                for option in field.options if option.active
            ],
            "sort_order": field.sort_order,
        })
    return result


def serialize_groups(entity_type: str) -> list[dict[str, Any]]:
    groups = FieldGroup.query.filter_by(entity_type=entity_type).order_by(FieldGroup.sort_order, FieldGroup.id).all()
    return [
        {"id": group.id, "key": group.key, "label": group.label, "description": group.description or "", "active": group.active, "sort_order": group.sort_order}
        for group in groups
    ]
