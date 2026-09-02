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
TESTING_STATUSES = {
    "bekliyor": "Test Bekliyor",
    "basarili": "Test Başarılı",
    "basarisiz": "Test Başarısız",
}
APPROVAL_STATUSES = {
    "bekliyor": "Onay Bekliyor",
    "onaylandi": "Onaylandı",
    "reddedildi": "Reddedildi",
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


def _parse_bool(value: Any, field: str) -> tuple[bool, str | None]:
    if isinstance(value, bool):
        return value, None
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value), None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on", "evet"}:
            return True, None
        if normalized in {"false", "0", "no", "off", "hayir", "hayır", ""}:
            return False, None
    return False, f"{field} geçerli bir boolean değeri olmalıdır."


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
        "brand_model": " ".join(
            x for x in [
                item.brand.name if item and item.brand else "",
                item.model.name if item and item.model else "",
            ]
            if x
        ) or "-",
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
        "updated_at": repair.updated_at.isoformat() if repair.updated_at else None,
        "testing_status": repair.testing_status or "bekliyor",
        "testing_status_label": TESTING_STATUSES.get(repair.testing_status, repair.testing_status or "Bekliyor"),
        "tested_at": repair.tested_at.isoformat() if repair.tested_at else None,
        "tested_at_display": repair.tested_at.strftime("%d.%m.%Y %H:%M") if repair.tested_at else "-",
        "tested_by": repair.tested_by or "",
        "approval_status": repair.approval_status or "bekliyor",
        "approval_status_label": APPROVAL_STATUSES.get(repair.approval_status, repair.approval_status or "Bekliyor"),
        "approved_at": repair.approved_at.isoformat() if repair.approved_at else None,
        "approved_at_display": repair.approved_at.strftime("%d.%m.%Y %H:%M") if repair.approved_at else "-",
        "approved_by": repair.approved_by or "",
        "sla_due_at": repair.sla_due_at.isoformat() if repair.sla_due_at else None,
        "sla_due_at_display": repair.sla_due_at.strftime("%d.%m.%Y %H:%M") if repair.sla_due_at else "-",
        "delay_reason": repair.delay_reason or "",
    }


def _apply_item_status(item: InventoryItem, status: str) -> None:
    if status == "hurda":
        item.status = "hurda"
    elif status in {"bekliyor", "serviste", "tamir_edilemedi"}:
        item.status = "arizali"
    elif status in {"tamir_edildi", "geri_geldi"}:
        item.status = "aktif"


def _sync_item_status(item: InventoryItem) -> None:
    latest = repair_queries.get_latest_record(item.id)
    if latest:
        _apply_item_status(item, latest.status)
    elif item.status == "arizali":
        # A deleted last repair must not leave a stale repair state behind.
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
    tested_at, error = _parse_datetime(value("tested_at"), "Test tarihi")
    if error:
        return None, error
    approved_at, error = _parse_datetime(value("approved_at"), "Onay tarihi")
    if error:
        return None, error
    sla_due_at, error = _parse_datetime(value("sla_due_at"), "SLA son tarihi")
    if error:
        return None, error
    cost, error = _parse_cost(value("service_cost"))
    if error:
        return None, error

    sent_to_service, error = _parse_bool(value("sent_to_service"), "Servise gönderildi")
    if error:
        return None, error

    status = sanitize_input_text(value("status"), max_length=32) or "bekliyor"
    if status not in REPAIR_STATUSES:
        return None, "Geçersiz tamir durumu."

    warranty = sanitize_input_text(value("warranty_status"), max_length=32) or "belirsiz"
    if warranty not in WARRANTY_STATUSES:
        return None, "Geçersiz garanti durumu."

    testing_status = sanitize_input_text(value("testing_status"), max_length=32) or "bekliyor"
    if testing_status not in TESTING_STATUSES:
        return None, "Geçersiz test durumu."

    approval_status = sanitize_input_text(value("approval_status"), max_length=32) or "bekliyor"
    if approval_status not in APPROVAL_STATUSES:
        return None, "Geçersiz onay durumu."

    tested_by = sanitize_input_text(value("tested_by"), max_length=128)
    approved_by = sanitize_input_text(value("approved_by"), max_length=128)
    delay_reason = sanitize_input_text(value("delay_reason"), max_length=5000)

    if expected and sent_at and expected < sent_at:
        return None, "Tahmini dönüş tarihi, gönderim tarihinden önce olamaz."
    if returned and sent_at and returned < sent_at:
        return None, "Dönüş tarihi, gönderim tarihinden önce olamaz."
    if sent_to_service and not sent_at:
        return None, "Servise gönderildi olarak işaretlenen kayıtta gönderim tarihi zorunludur."
    if not sent_to_service and any((sent_at, expected, returned)):
        return None, "Servise gönderilmedi olarak işaretlenen kayıtta servis tarihleri boş olmalıdır."
    if testing_status != "bekliyor" and (not tested_at or not tested_by):
        return None, "Test sonucu için test tarihi ve test eden kişi zorunludur."
    if approval_status != "bekliyor" and (not approved_at or not approved_by):
        return None, "Onay sonucu için onay tarihi ve onaylayan kişi zorunludur."
    if approval_status == "onaylandi" and testing_status != "basarili":
        return None, "Tamir onayı için test sonucu başarılı olmalıdır."
    if delay_reason and not sla_due_at:
        return None, "Gecikme nedeni girildiğinde SLA son tarihi de belirtilmelidir."

    return {
        "fault_date": fault_date or datetime.utcnow(),
        "fault_type": sanitize_input_text(value("fault_type"), max_length=128),
        "problem_description": problem,
        "sent_to_service": sent_to_service,
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
        "testing_status": testing_status,
        "tested_at": tested_at,
        "tested_by": tested_by,
        "approval_status": approval_status,
        "approved_at": approved_at,
        "approved_by": approved_by,
        "sla_due_at": sla_due_at,
        "delay_reason": delay_reason,
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
        _sync_item_status(item)
        db.session.add(InventoryEvent(item=item, event_type="Tamir / Servis Kaydı Oluşturuldu", performed_by=actor or "Sistem", note=repair.problem_description[:256]))
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
        _sync_item_status(item)
        db.session.add(InventoryEvent(item=item, event_type="Tamir / Servis Kaydı Güncellendi", performed_by=actor or "Sistem", note=repair.problem_description[:256]))
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
        db.session.flush()
        _sync_item_status(item)
        db.session.add(InventoryEvent(item=item, event_type="Tamir / Servis Kaydı Silindi", performed_by=actor or "Sistem", note=note))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return {"success": True}, 200
