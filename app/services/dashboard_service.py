from __future__ import annotations

from typing import Any

from sqlalchemy import func

from ..models import InventoryItem, RequestGroup, RequestOrder, StockItem, StockMovement
from .maintenance_helpers import calculate_maintenance_status


def load_maintenance_metrics() -> dict[str, int]:
    items = InventoryItem.query.filter(
        func.lower(InventoryItem.status).notin_(["hurda", "stokta"])
    ).all()
    current_count = warning_count = overdue_count = none_count = due_count = 0
    for item in items:
        records = sorted(item.maintenances or [], key=lambda row: (row.performed_at, row.id), reverse=True)
        if not records:
            none_count += 1
            continue
        status = calculate_maintenance_status(records[0].performed_at)
        if status == "overdue":
            overdue_count += 1
            due_count += 1
        elif status == "warning":
            warning_count += 1
            due_count += 1
        else:
            current_count += 1
    return {
        "maintenance_current_count": current_count,
        "maintenance_warning_count": warning_count,
        "maintenance_overdue_count": overdue_count,
        "maintenance_none_count": none_count,
        "maintenance_due_count": due_count,
    }


def load_dashboard_metrics() -> dict[str, Any]:
    available_stock = db_sum = (
        StockItem.query.with_entities(func.sum(StockItem.quantity))
        .filter(StockItem.status == "stokta")
        .scalar() or 0
    )
    total_stock = StockItem.query.with_entities(func.sum(StockItem.quantity)).scalar() or 0
    open_request_count = RequestOrder.query.join(RequestGroup).filter(func.lower(RequestGroup.key) == "acik").count()
    total_request_count = RequestOrder.query.count()
    faulty_inventory_count = InventoryItem.query.filter(InventoryItem.status == "arizali").count()
    critical_stock_count = StockItem.query.filter(StockItem.quantity <= 0).count()
    maintenance_counts = load_maintenance_metrics()
    critical_alerts = faulty_inventory_count + critical_stock_count + maintenance_counts["maintenance_due_count"]
    recent_stock_movements = (
        StockMovement.query.order_by(StockMovement.created_at.desc()).limit(5).all()
    )
    return {
        "available_stock": int(available_stock),
        "total_stock": int(total_stock),
        "open_requests": int(open_request_count),
        "total_requests": int(total_request_count),
        "critical_alerts": int(critical_alerts),
        "faulty_inventory": int(faulty_inventory_count),
        "problem_stock": int(critical_stock_count),
        "maintenance_due_count": int(maintenance_counts["maintenance_due_count"]),
        "maintenance_warning_count": int(maintenance_counts["maintenance_warning_count"]),
        "maintenance_overdue_count": int(maintenance_counts["maintenance_overdue_count"]),
        "maintenance_none_count": int(maintenance_counts["maintenance_none_count"]),
        "recent_stock_movements": recent_stock_movements,
    }
