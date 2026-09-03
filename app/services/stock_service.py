from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from ..queries import inventory_stock_queries


_IN_STOCK_STATUSES = {"stokta", "arizali"}
_CATEGORY_LABELS = {
    "envanter": "Envanter",
    "cevre_birimi": "Çevre Birimi",
    "yazici": "IP Yazıcı",
    "lisans": "Lisans",
    "talep": "Talep",
    "manuel": "Manuel",
}
_STATUS_LABELS = {
    "stokta": "Stokta",
    "devredildi": "Devredildi",
    "arizali": "Arızalı",
    "hurda": "Hurda",
}


def load_tracking_payload(
    *,
    serialize_item: Callable[[Any], dict[str, Any]],
    serialize_log: Callable[[Any], dict[str, Any]],
    metadata_config: dict[str, Any],
    support_options: dict[str, list[str]],
) -> dict[str, Any]:
    """Build the stock tracking page payload from query-layer results."""
    items = inventory_stock_queries.list_tracking_items()
    all_stock_items = [serialize_item(item) for item in items]
    stock_items = [
        item for item in all_stock_items if item.get("status") in _IN_STOCK_STATUSES
    ]

    category_counts = Counter(item["category"] for item in stock_items)
    status_counts = Counter(item["status"] for item in stock_items)

    assignment_map: dict[str, list[dict[str, Any]]] = {}
    for item in all_stock_items:
        if item.get("status") != "devredildi":
            continue
        responsible = (item.get("metadata") or {}).get("responsible")
        if not responsible:
            continue
        assignment_map.setdefault(responsible, []).append(
            {
                "id": item["id"],
                "title": item["title"],
                "hardware_type": item.get("hardware_type") or item.get("title"),
                "category_label": item.get("category_label"),
                "quantity": item.get("quantity"),
                "status": item.get("status"),
                "status_label": item.get("status_label"),
                "updated_display": item.get("updated_display"),
            }
        )

    user_assignments = [
        {
            "responsible": name,
            "items": sorted(
                entries,
                key=lambda payload: payload.get("updated_display") or "",
                reverse=True,
            ),
        }
        for name, entries in sorted(assignment_map.items())
    ]

    categories = [
        {
            "value": key,
            "label": _CATEGORY_LABELS[key],
            "count": category_counts.get(key, 0),
        }
        for key in _CATEGORY_LABELS
    ]
    status_summary = [
        {
            "value": key,
            "label": _STATUS_LABELS[key],
            "count": status_counts.get(key, 0),
        }
        for key in _STATUS_LABELS
        if key in _IN_STOCK_STATUSES
    ]

    logs = inventory_stock_queries.list_recent_logs(limit=40)
    assignments = inventory_stock_queries.list_recent_assignments(limit=100)

    return {
        "stock_items": stock_items,
        "stock_logs": [serialize_log(log) for log in logs],
        "stock_categories": categories,
        "stock_status_summary": status_summary,
        "stock_faulty_count": status_counts.get("arizali", 0),
        "stock_metadata_config": metadata_config,
        "stock_support_options": support_options,
        "stock_user_assignments": user_assignments,
        "stock_assignments": [
            {
                "id": assignment.id,
                "stock_item_id": assignment.stock_item_id,
                "assigned_to": assignment.assigned_to,
                "assigned_department": assignment.assigned_department or "",
                "quantity": assignment.quantity,
                "delivery_note": assignment.delivery_note or "",
                "delivered_by": assignment.delivered_by,
                "delivered_at": (
                    assignment.delivered_at.strftime("%d.%m.%Y %H:%M")
                    if assignment.delivered_at
                    else ""
                ),
                "receipt_code": assignment.receipt_code,
            }
            for assignment in assignments
        ],
    }


def load_scrap_inventory_payload(
    *, serialize_item: Callable[[Any], dict[str, Any]]
) -> dict[str, Any]:
    items = inventory_stock_queries.list_scrap_inventory_items()
    scrap_items = [serialize_item(item) for item in items]
    return {"scrap_items": scrap_items, "scrap_count": len(scrap_items)}
