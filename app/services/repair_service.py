from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ..models import InventoryEvent, InventoryItem, db
from ..queries import repair_queries
from ..repair_model import InventoryRepair
from ..utils.parsing import sanitize_input_text

REPAIR_STATUSES = {
    "bekliyor": "Servise Gönderilecek",
    "serviste": "Serviste",
    "tamir_edildi": "Tamir Edildi",
    "geri_geldi": "Geri Geldi",
    "tamir_edilemedi": "Tamir Edilemedi",
    "hurda": "Hurdaya Ayrıldı",
    "iptal": "İptal",
}
WARRANTY_STATUSES = {
    "belirsiz": "Belirtilmedi",
    "garantili": "Garanti Kapsamında",
    "garantisiz": "Garanti Dışı",
}


def _parse_datetime(value: Any, field: str) -> tuple[datetime | None, str | None]:
    if value in (None, ""):
        return None, None
    try:
        return datetime.fromisoformat(str(value).strip()), None
    except ValueError:
        return None, f"{field} geçerli bir tarih olmalıdır."


def _parse_cost(value: Any) -> tuple[Decimal | None, str | None]:
    if value in (None, ""):
        return None, None
    try:
        amount = Decimal(str(value).replace(",", "."))
        if amount < 0:
            return None, "Servis ücreti negatif olamaz."
        return amount, None
    except (InvalidOperation, ValueError):
        return None, "Servis ücreti geçerli bir tutar olmalıdır."


def _item(item_id: int) -> InventoryItem | None:
    return repair_queries.get_item(item_id)


def _records(item_id: int | None = None) -> list[InventoryRepair]:
    return repair_queries.list_records(item_id)


def _serialize(repair: InventoryRepair) -> dict[str, Any]:
    item = repair.item
    cost = repair.service_cost
    return {
        "id": repair.id,
        "item_id": repair.item_id,
        "inventory_no": item.inventory_no if item else "",
        "computer_name": item.computer_name if item else "",
        "hardware_type": item.hardware_type.name if item and item.hardware_type else "",
        "brand_model": (
            " ".join(
                x for x in [
                    item.brand.name if item and item.brand else "",
                    item.model.name if item and item.model else "",
                ]
                if x
            )
            or "-"
        ),
        "fault_date": repair.fault_date.isoformat() if repair.fault_date else None,
        "fault_date_display": repair.fault_date.strftime("%d.%m.%Y %H:%M") if repair.fault_date else "-",
        "fault_type": repair.fault_type or "",
        "problem_description": repair.problem_description or "",
        "sent_to_service": bool(repair.sent_to_service),
        "service_company": repair.service_company or "",
        "service_contact": repair.service_contact or "",
        "service_ticket_no": repair.service_ticket_no or "",
        "warranty_status": repair.warranty_status or "belirsiz",
        "warranty_status_label": WARRANTY_STATUSES.get(repair.warranty_status, "Belirtilmedi"),
        "sent_at": repair.sent_at.isoformat() if repair.sent_at else None,
        "sent_at_display": repair.sent_at.strftime("%d.%m.%Y %H:%M") if repair.sent_at else "-",
        "expected_return_at": repair.expected_return_at.isoformat() if repair.expected_return_at else None,
        "expected_return_at_display": repair.expected_return_at.strftime("%d.%m.%Y %H:%M") if repair.expected_return_at else "-",
        "returned_at": repair.returned_at.isoformat() if repair.returned_at else None,
        "returned_at_display": repair.returned_at.strftime("%d.%m.%Y %H:%M") if repair.returned_at else "-",
        "repair_description": repair.repair_description or "",
        "service_cost": float(cost) if cost is not None else None,
        "status": repair.status or "bekliyor",
        "status_label": REPAIR_STATUSES.get(repair.status, repair.status or "Bekliyor"),
        "note": repair.note or "",
        "created_by": repair.created_by or "Sistem",
        "created_at_display": repair.created_at.strftime("%d.%m.%Y %H:%M") if repair.created_at else "-",
    }


def _apply_item_status(item: InventoryItem, status: str) -> None:
    if status == "hurda":
        item.status = "hurda"
    elif status in {"bekliyor", "serviste", "tamir_edilemedi"}:
        item.status = "arizali"
    elif status in {"tamir_edildi", "geri_geldi"}:
        item.status = "aktif"


def _validate(data: Any, current: InventoryRepair | None = None) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(data, dict):
        return None, "Geçersiz JSON gövdesi."

    def value(key: str) -> Any:
        if key in data:
            return data[key]
        return getattr(current, key, None) if current else None

    problem = sanitize_input_text(value("problem_description"), max_length=5000)
    if not problem:
        return None, "Arıza / sorun açıklaması zorunludur."

    fault_date, error = _parse_datetime(value("fault_date"), "Arıza tarihi")
    if error:
        return None, error
    sent_at, error = _parse_datetime(value("sent_at"), "Gönderim tarihi")
    if error:
        return None, error
    expected, error = _parse_datetime(value("expected_return_at"), "Tahmini dönüş tarihi")
    if error:
        return None, error
    returned, error = _parse_datetime(value("returned_at"), "Dönüş tarihi")
    if error:
        return None, error
    cost, error = _parse_cost(value("service_cost"))
    if error:
        return None, error

    status = sanitize_input_text(value("status"), max_length=32) or "bekliyor"
    if status not in REPAIR_STATUSES:
        return None, "Geçersiz tamir durumu."

    warranty = sanitize_input_text(value("warranty_status"), max_length=32) or "belirsiz"
    if warranty not in WARRANTY_STATUSES:
        return None, "Geçersiz garanti durumu."

    return {
        "fault_date": fault_date or datetime.utcnow(),
        "fault_type": sanitize_input_text(value("fault_type"), max_length=128),
        "problem_description": problem,
        "sent_to_service": bool(value("sent_to_service")),
        "service_company": sanitize_input_text(value("service_company"), max_length=256),
        "service_contact": sanitize_input_text(value("service_contact"), max_length=128),
        "service_ticket_no": sanitize_input_text(value("service_ticket_no"), max_length=128),
        "warranty_status": warranty,
        "sent_at": sent_at,
        "expected_return_at": expected,
        "returned_at": returned,
        "repair_description": sanitize_input_text(value("repair_description"), max_length=5000),
        "service_cost": cost,
        "status": status,
        "note": sanitize_input_text(value("note"), max_length=2000),
    }, None


def list_records(item_id: int) -> tuple[dict[str, Any], int]:
    if not _item(item_id):
        return {"error": "Envanter kaydı bulunamadı."}, 404
    return {"repairs": [_serialize(r) for r in _records(item_id)]}, 200


def create(item_id: int, data: Any, actor: str) -> tuple[dict[str, Any], int]:
    item = _item(item_id)
    if not item:
        return {"error": "Envanter kaydı bulunamadı."}, 404

    values, error = _validate(data)
    if error:
        return {"error": error}, 400

    repair = InventoryRepair(item_id=item_id, created_by=actor or "Sistem", **values)
    try:
        db.session.add(repair)
        db.session.flush()
        _apply_item_status(item, repair.status)
        db.session.add(InventoryEvent(
            item=item,
            event_type="Tamir / Servis Kaydı Oluşturuldu",
            performed_by=actor or "Sistem",
            note=repair.problem_description[:256],
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {"success": True, "repair": _serialize(repair), "repair_id": repair.id}, 201


def update(item_id: int, repair_id: int, data: Any, actor: str) -> tuple[dict[str, Any], int]:
    item = _item(item_id)
    if not item:
        return {"error": "Envanter kaydı bulunamadı."}, 404

    repair = repair_queries.get_record(item_id, repair_id)
    if not repair:
        return {"error": "Tamir kaydı bulunamadı."}, 404

    values, error = _validate(data, repair)
    if error:
        return {"error": error}, 400

    for key, value in values.items():
        setattr(repair, key, value)

    try:
        _apply_item_status(item, repair.status)
        db.session.add(InventoryEvent(
            item=item,
            event_type="Tamir / Servis Kaydı Güncellendi",
            performed_by=actor or "Sistem",
            note=repair.problem_description[:256],
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {"success": True, "repair": _serialize(repair)}, 200


def delete(item_id: int, repair_id: int, actor: str) -> tuple[dict[str, Any], int]:
    item = _item(item_id)
    if not item:
        return {"error": "Envanter kaydı bulunamadı."}, 404

    repair = repair_queries.get_record(item_id, repair_id)
    if not repair:
        return {"error": "Tamir kaydı bulunamadı."}, 404

    note = (repair.problem_description or "")[:256]
    try:
        db.session.delete(repair)
        db.session.add(InventoryEvent(
            item=item,
            event_type="Tamir / Servis Kaydı Silindi",
            performed_by=actor or "Sistem",
            note=note,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {"success": True}, 200


def load_payload() -> dict[str, Any]:
    rows = _records()
    inventory = repair_queries.list_items()
    options = []
    for item in inventory:
        name = item.computer_name or " ".join(
            x for x in [
                item.brand.name if item.brand else "",
                item.model.name if item.model else "",
            ]
            if x
        ) or (item.hardware_type.name if item.hardware_type else "Cihaz")
        options.append({"id": item.id, "label": f"{item.inventory_no} · {name}"})

    return {
        "repair_records": [_serialize(r) for r in rows],
        "repair_inventory_options": options,
        "repair_total_count": len(rows),
        "repair_waiting_count": sum(r.status == "bekliyor" for r in rows),
        "repair_service_count": sum(r.status == "serviste" for r in rows),
        "repair_returned_count": sum(r.status == "geri_geldi" for r in rows),
        "repair_problem_count": sum(r.status in {"tamir_edilemedi", "hurda"} for r in rows),
        "repair_statuses": REPAIR_STATUSES,
        "warranty_statuses": WARRANTY_STATUSES,
    }
