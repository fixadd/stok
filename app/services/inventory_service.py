from __future__ import annotations

from typing import Any, Callable

from ..queries import catalog_queries, inventory_queries, user_queries
from .configuration_service import build_form_schema, setting_choices


def load_tracking_payload(*, serialize_item: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
    """Build the inventory tracking page payload from DB-backed configuration."""
    items = inventory_queries.list_tracking_items()
    payload = [serialize_item(item) for item in items]

    hidden_statuses = {"stokta", "hurda"}
    visible_items = [item for item in payload if item.get("status") not in hidden_statuses]
    faulty_count = sum(1 for item in visible_items if item.get("status") == "arizali")
    departments = {item["department"] for item in visible_items if item.get("department")}

    factories = [factory.to_dict() for factory in catalog_queries.list_factories()]
    hardware_types = [hardware_type.to_dict() for hardware_type in catalog_queries.list_hardware_types()]
    brand_models = [brand.to_dict(include_models=True) for brand in catalog_queries.list_brands_with_models()]
    users = [{"id": user.id, "name": f"{user.first_name} {user.last_name}", "department": user.department} for user in user_queries.list_active_users()]
    departments.update(user["department"] for user in users if user.get("department"))

    status_choices = setting_choices("inventory_status") or [
        {"value": "aktif", "label": "Aktif"},
        {"value": "beklemede", "label": "Beklemede"},
        {"value": "arizali", "label": "Arızalı"},
        {"value": "hurda", "label": "Hurda"},
        {"value": "stokta", "label": "Stokta"},
    ]
    return {
        "inventory_items": visible_items,
        "inventory_faulty_count": faulty_count,
        "factories": factories,
        "hardware_types": hardware_types,
        "brand_models": brand_models,
        "users": users,
        "departments": sorted(departments),
        "status_choices": status_choices,
        "custom_fields": build_form_schema("inventory"),
    }
