from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..models import InventoryEvent, InventoryItem, InventoryMaintenance, db
from ..utils.parsing import sanitize_input_text

MAINTENANCE_INTERVAL_DAYS = 90
MAINTENANCE_WARNING_DAYS = 15

COMPUTER_KEYWORDS = {
    "bilgisayar", "laptop", "desktop", "notebook", "dizustu", "masaustu", "pc"
}


def is_computer_hardware_type(name: str | None) -> bool:
    normalized = (name or "").strip().lower()
    if not normalized:
        return False
    normalized = (normalized.replace("ı", "i").replace("ğ", "g").replace("ü", "u")
                  .replace("ş", "s").replace("ö", "o").replace("ç", "c"))
    tokens = set(normalized.replace("-", " ").replace("/", " ").split())
    fuzzy = COMPUTER_KEYWORDS - {"pc"}
    return any(keyword in normalized for keyword in fuzzy) or "pc" in tokens


def _next_maintenance(performed_at: datetime) -> datetime:
    return performed_at + timedelta(days=MAINTENANCE_INTERVAL_DAYS)


def _status(next_at: datetime | None) -> dict[str, Any]:
    if not next_at:
        return {"key": "none", "label": "Bakım Kaydı Yok", "class": "text-bg-secondary", "days_until": None}
    days = (next_at.date() - datetime.utcnow().date()).days
    if days < 0:
        return {"key": "overdue", "label": "Bakım Gecikti", "class": "text-bg-danger", "days_until": days}
    if days <= MAINTENANCE_WARNING_DAYS:
        return {"key": "warning", "label": "Bakım Yaklaşıyor", "class": "text-bg-warning", "days_until": days}
    return {"key": "ok", "label": "Bakım Güncel", "class": "text-bg-success", "days_until": days}


def _record_payload(record: InventoryMaintenance) -> dict[str, Any]:
    next_at = _next_maintenance(record.performed_at)
    status = _status(next_at)
    return {
        "id": record.id,
        "item_id": record.item_id,
        "performed_at": record.performed_at.isoformat(),
        "performed_at_display": record.performed_at.strftime("%d.%m.%Y %H:%M"),
        "performed_by": record.performed_by,
        "next_maintenance_at": next_at.isoformat(),
        "next_maintenance_at_display": next_at.strftime("%d.%m.%Y %H:%M"),
        "note": record.note or "",
        "status": status["key"],
        "status_label": status["label"],
        "status_class": status["class"],
        "days_until": status["days_until"],
        "created_at_display": record.created_at.strftime("%d.%m.%Y %H:%M"),
    }


def _item_payload(item: InventoryItem) -> dict[str, Any]:
    records = sorted(item.maintenances, key=lambda r: (r.performed_at, r.id), reverse=True)
    last = records[0] if records else None
    next_at = _next_maintenance(last.performed_at) if last else None
    status = _status(next_at)
    return {
        "id": item.id,
        "inventory_no": item.inventory_no,
        "computer_name": item.computer_name or "",
        "responsible": (f"{item.responsible_user.first_name} {item.responsible_user.last_name}" if item.responsible_user else "Atama bekliyor"),
        "department": item.department or "",
        "hardware_type": item.hardware_type.name if item.hardware_type else "",
        "brand_model": " ".join(x for x in [item.brand.name if item.brand else "", item.model.name if item.model else ""] if x) or "-",
        "last_maintenance_at": last.performed_at.strftime("%d.%m.%Y %H:%M") if last else "-",
        "next_maintenance_at": next_at.strftime("%d.%m.%Y %H:%M") if next_at else "-",
        "maintenance_status": status["label"],
        "maintenance_status_key": status["key"],
        "maintenance_status_class": status["class"],
        "maintenances": [_record_payload(r) for r in records],
        "search_index": " ".join(str(x) for x in [item.inventory_no, item.computer_name, item.department, item.hardware_type.name if item.hardware_type else "", item.brand.name if item.brand else "", item.model.name if item.model else "", status["label"]] if x).lower(),
    }


def _computer_item(item_id: int) -> InventoryItem | None:
    item = InventoryItem.query.get(item_id)
    if not item or not is_computer_hardware_type(item.hardware_type.name if item.hardware_type else None):
        return None
    return item


def _event(item: InventoryItem, action: str, actor: str, note: str | None = None) -> None:
    db.session.add(InventoryEvent(item=item, event_type=action, performed_by=actor or "Sistem", note=note or None))


def create(deps: dict[str, Any], item_id: int, data: Any) -> tuple[dict[str, Any], int]:
    item = _computer_item(item_id)
    if item is None:
        return {"error": "Bakım kaydı yalnızca bilgisayar envanterleri için oluşturulabilir."}, 400
    if not isinstance(data, dict):
        return {"error": "Geçersiz JSON gövdesi."}, 400
    actor = sanitize_input_text(data.get("performed_by"), max_length=128) or deps["current_actor_name"]()
    note = sanitize_input_text(data.get("note"), max_length=2000) or None
    try:
        performed_at = datetime.fromisoformat((data.get("performed_at") or "").strip()) if data.get("performed_at") else datetime.utcnow()
    except ValueError:
        return {"error": "Bakım tarihi geçerli bir tarih olmalıdır."}, 400
    record = InventoryMaintenance(item=item, performed_at=performed_at, performed_by=actor, note=note)
    db.session.add(record)
    db.session.flush()
    next_at = _next_maintenance(performed_at)
    _event(item, "Bakım Yapıldı", actor, note or f"Sonraki bakım: {next_at.strftime('%d.%m.%Y %H:%M')}")
    db.session.commit()
    return {"maintenance": _record_payload(record)}, 201


def list_records(deps: dict[str, Any], item_id: int) -> tuple[dict[str, Any], int]:
    item = _computer_item(item_id)
    if item is None:
        return {"error": "Bakım geçmişi yalnızca bilgisayar envanterleri için görüntülenebilir."}, 400
    records = InventoryMaintenance.query.filter_by(item_id=item.id).order_by(InventoryMaintenance.performed_at.desc(), InventoryMaintenance.id.desc()).all()
    return {"item": _item_payload(item), "maintenances": [_record_payload(r) for r in records]}, 200


def update(deps: dict[str, Any], item_id: int, maintenance_id: int, data: Any) -> tuple[dict[str, Any], int]:
    item = _computer_item(item_id)
    if item is None:
        return {"error": "Bakım kaydı yalnızca bilgisayar envanterleri için güncellenebilir."}, 400
    record = InventoryMaintenance.query.filter_by(id=maintenance_id, item_id=item_id).first()
    if record is None:
        return {"error": "Bakım kaydı bulunamadı."}, 404
    if not isinstance(data, dict):
        return {"error": "Geçersiz JSON gövdesi."}, 400
    actor = sanitize_input_text(data.get("performed_by"), max_length=128) or deps["current_actor_name"]()
    note = sanitize_input_text(data.get("note"), max_length=2000) or None
    try:
        performed_at = datetime.fromisoformat(str(data.get("performed_at") or "").strip())
    except ValueError:
        return {"error": "Bakım tarihi geçerli bir tarih olmalıdır."}, 400
    record.performed_at = performed_at
    record.performed_by = actor
    record.note = note
    next_at = _next_maintenance(performed_at)
    _event(item, "Bakım Kaydı Güncellendi", deps["current_actor_name"](), f"Bakım: {performed_at.strftime('%d.%m.%Y %H:%M')} · Sonraki: {next_at.strftime('%d.%m.%Y %H:%M')}")
    db.session.commit()
    return {"success": True, "maintenance": _record_payload(record)}, 200


def delete(deps: dict[str, Any], item_id: int, maintenance_id: int) -> tuple[dict[str, Any], int]:
    item = _computer_item(item_id)
    if item is None:
        return {"error": "Bakım kaydı yalnızca bilgisayar envanterleri için silinebilir."}, 400
    record = InventoryMaintenance.query.filter_by(id=maintenance_id, item_id=item_id).first()
    if record is None:
        return {"error": "Bakım kaydı bulunamadı."}, 404
    actor = deps["current_actor_name"]()
    _event(item, "Bakım Kaydı Silindi", actor, f"Silinen bakım: {record.performed_at.strftime('%d.%m.%Y %H:%M')}")
    db.session.delete(record)
    db.session.commit()
    return {"success": True, "message": "Bakım kaydı silindi.", "maintenance_id": maintenance_id}, 200


def load_payload(deps: dict[str, Any]) -> dict[str, Any]:
    items = InventoryItem.query.order_by(InventoryItem.inventory_no).all()
    computers = []
    for item in items:
        if not is_computer_hardware_type(item.hardware_type.name if item.hardware_type else None):
            continue
        if (item.status or "").lower() in {"hurda", "stokta"}:
            continue
        computers.append(_item_payload(item))
    return {
        "maintenance_items": computers,
        "maintenance_total_count": len(computers),
        "maintenance_current_count": sum(1 for x in computers if x["maintenance_status_key"] == "ok"),
        "maintenance_warning_count": sum(1 for x in computers if x["maintenance_status_key"] == "warning"),
        "maintenance_overdue_count": sum(1 for x in computers if x["maintenance_status_key"] == "overdue"),
        "maintenance_none_count": sum(1 for x in computers if x["maintenance_status_key"] == "none"),
        "maintenance_due_count": sum(1 for x in computers if x["maintenance_status_key"] in {"overdue", "warning", "none"}),
        "maintenance_interval_days": MAINTENANCE_INTERVAL_DAYS,
    }
