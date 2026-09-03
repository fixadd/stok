from __future__ import annotations

from typing import Any, Callable

from ..queries import catalog_queries, inventory_queries, license_queries, user_queries


def load_tracking_payload(
    *,
    serialize_license: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    licenses = license_queries.list_tracking_licenses()
    license_records = [serialize_license(record) for record in licenses]

    users = [
        {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "department": user.department or "",
        }
        for user in user_queries.list_active_users()
    ]

    inventory_options = [
        {
            "id": item.id,
            "inventory_no": item.inventory_no,
            "label": (
                f"{item.inventory_no} · {item.computer_name}"
                if item.computer_name
                else (
                    f"{item.inventory_no} · {item.hardware_type.name}"
                    if item.hardware_type
                    else item.inventory_no
                )
            ),
            "ifs_no": item.ifs_no or "",
            "department": item.department or "",
        }
        for item in inventory_queries.list_inventory_items_for_license_options()
    ]

    return {
        "license_records": license_records,
        "license_users": users,
        "license_inventory_options": inventory_options,
        "license_names": [
            name.to_dict() for name in catalog_queries.list_license_names()
        ],
        "license_status_counts": {
            "total": len(license_records),
            "active": sum(1 for record in license_records if record["status"] == "aktif"),
            "passive": sum(1 for record in license_records if record["status"] == "pasif"),
        },
    }
