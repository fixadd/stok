from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import text

from ..models import InventoryEvent, InventoryItem, db
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


def ensure_table() -> None:
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory_repairs (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
            fault_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fault_type VARCHAR(128),
            problem_description TEXT NOT NULL,
            sent_to_service BOOLEAN NOT NULL DEFAULT FALSE,
            service_company VARCHAR(256),
            service_contact VARCHAR(128),
            service_ticket_no VARCHAR(128),
            warranty_status VARCHAR(32) NOT NULL DEFAULT 'belirsiz',
            sent_at TIMESTAMP,
            expected_return_at TIMESTAMP,
            returned_at TIMESTAMP,
            repair_description TEXT,
            service_cost NUMERIC(12,2),
            status VARCHAR(32) NOT NULL DEFAULT 'bekliyor',
            note TEXT,
            created_by VARCHAR(128) NOT NULL DEFAULT 'Sistem',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.session.commit()


def _parse_datetime(value: Any, field: str, required: bool = False) -> tuple[datetime | None, str | None]:
    if value in (None, ""):
        return (None, f"{field} zorunludur.") if required else (None, None)
    try:
        return datetime.fromisoformat(str(value).strip()), None
    except ValueError:
        return None, f"{field} geçerli bir tarih olmalıdır."


def _cost(value: Any) -> tuple[Decimal | None, str | None]:
    if value in (None, ""):
        return None, None
    try:
        amount = Decimal(str(value).replace(",", "."))
        if amount < 0:
            raise InvalidOperation
        return amount, None
    except (InvalidOperation, ValueError):
        return None, "Servis ücreti geçerli bir tutar olmalıdır."


def _item(item_id: int) -> InventoryItem | None:
    return InventoryItem.query.get(item_id)


def _row(row: Any) -> dict[str, Any]:
    data = dict(row._mapping)
    cost = data.get("service_cost")
    return {
        "id": data["id"],
        "item_id": data["item_id"],
        "inventory_no": data.get("inventory_no") or "",
        "computer_name": data.get("computer_name") or "",
        "hardware_type": data.get("hardware_type") or "",
        "brand_model": " ".join(x for x in [data.get("brand") or "", data.get("model") or ""] if x) or "-",
        "fault_date": data["fault_date"].isoformat() if data.get("fault_date") else None,
        "fault_date_display": data["fault_date"].strftime("%d.%m.%Y %H:%M") if data.get("fault_date") else "-",
        "fault_type": data.get("fault_type") or "",
        "problem_description": data.get("problem_description") or "",
        "sent_to_service": bool(data.get("sent_to_service")),
        "service_company": data.get("service_company") or "",
        "service_contact": data.get("service_contact") or "",
        "service_ticket_no": data.get("service_ticket_no") or "",
        "warranty_status": data.get("warranty_status") or "belirsiz",
        "warranty_status_label": WARRANTY_STATUSES.get(data.get("warranty_status"), "Belirtilmedi"),
        "sent_at": data["sent_at"].isoformat() if data.get("sent_at") else None,
        "sent_at_display": data["sent_at"].strftime("%d.%m.%Y %H:%M") if data.get("sent_at") else "-",
        "expected_return_at": data["expected_return_at"].isoformat() if data.get("expected_return_at") else None,
        "expected_return_at_display": data["expected_return_at"].strftime("%d.%m.%Y %H:%M") if data.get("expected_return_at") else "-",
        "returned_at": data["returned_at"].isoformat() if data.get("returned_at") else None,
        "returned_at_display": data["returned_at"].strftime("%d.%m.%Y %H:%M") if data.get("returned_at") else "-",
        "repair_description": data.get("repair_description") or "",
        "service_cost": float(cost) if cost is not None else None,
        "status": data.get("status") or "bekliyor",
        "status_label": REPAIR_STATUSES.get(data.get("status"), data.get("status") or "Bekliyor"),
        "note": data.get("note") or "",
        "created_by": data.get("created_by") or "Sistem",
        "created_at_display": data["created_at"].strftime("%d.%m.%Y %H:%M") if data.get("created_at") else "-",
    }


def _select(item_id: int | None = None) -> list[dict[str, Any]]:
    condition = "WHERE r.item_id = :item_id" if item_id is not None else ""
    rows = db.session.execute(text(f"""
        SELECT r.*, i.inventory_no, i.computer_name, ht.name AS hardware_type,
               b.name AS brand, hm.name AS model
        FROM inventory_repairs r
        JOIN inventory_items i ON i.id = r.item_id
        LEFT JOIN hardware_types ht ON ht.id = i.hardware_type_id
        LEFT JOIN brands b ON b.id = i.brand_id
        LEFT JOIN hardware_models hm ON hm.id = i.model_id
        {condition}
        ORDER BY r.fault_date DESC, r.id DESC
    """), {"item_id": item_id} if item_id is not None else {}).fetchall()
    return [_row(row) for row in rows]


def list_records(item_id: int) -> tuple[dict[str, Any], int]:
    ensure_table()
    if not _item(item_id):
        return {"error": "Envanter kaydı bulunamadı."}, 404
    return {"repairs": _select(item_id)}, 200


def create(item_id: int, data: Any, actor: str) -> tuple[dict[str, Any], int]:
    ensure_table()
    item = _item(item_id)
    if not item:
        return {"error": "Envanter kaydı bulunamadı."}, 404
    if not isinstance(data, dict):
        return {"error": "Geçersiz JSON gövdesi."}, 400
    problem = sanitize_input_text(data.get("problem_description"), max_length=5000)
    if not problem:
        return {"error": "Arıza / sorun açıklaması zorunludur."}, 400
    fault_date, error = _parse_datetime(data.get("fault_date"), "Arıza tarihi")
    if error: return {"error": error}, 400
    sent_at, error = _parse_datetime(data.get("sent_at"), "Gönderim tarihi")
    if error: return {"error": error}, 400
    expected, error = _parse_datetime(data.get("expected_return_at"), "Tahmini dönüş tarihi")
    if error: return {"error": error}, 400
    returned, error = _parse_datetime(data.get("returned_at"), "Dönüş tarihi")
    if error: return {"error": error}, 400
    cost, error = _cost(data.get("service_cost"))
    if error: return {"error": error}, 400
    sent = bool(data.get("sent_to_service"))
    status = sanitize_input_text(data.get("status"), max_length=32) or ("serviste" if sent else "bekliyor")
    if status not in REPAIR_STATUSES:
        return {"error": "Geçersiz tamir durumu."}, 400
    params = {
        "item_id": item_id, "fault_date": fault_date or datetime.utcnow(),
        "fault_type": sanitize_input_text(data.get("fault_type"), max_length=128),
        "problem_description": problem, "sent_to_service": sent,
        "service_company": sanitize_input_text(data.get("service_company"), max_length=256),
        "service_contact": sanitize_input_text(data.get("service_contact"), max_length=128),
        "service_ticket_no": sanitize_input_text(data.get("service_ticket_no"), max_length=128),
        "warranty_status": sanitize_input_text(data.get("warranty_status"), max_length=32) or "belirsiz",
        "sent_at": sent_at, "expected_return_at": expected, "returned_at": returned,
        "repair_description": sanitize_input_text(data.get("repair_description"), max_length=5000),
        "service_cost": cost, "status": status,
        "note": sanitize_input_text(data.get("note"), max_length=2000), "created_by": actor or "Sistem",
    }
    result = db.session.execute(text("""
        INSERT INTO inventory_repairs
        (item_id, fault_date, fault_type, problem_description, sent_to_service, service_company,
         service_contact, service_ticket_no, warranty_status, sent_at, expected_return_at,
         returned_at, repair_description, service_cost, status, note, created_by)
        VALUES (:item_id, :fault_date, :fault_type, :problem_description, :sent_to_service, :service_company,
         :service_contact, :service_ticket_no, :warranty_status, :sent_at, :expected_return_at,
         :returned_at, :repair_description, :service_cost, :status, :note, :created_by)
        RETURNING id
    """), params)
    repair_id = result.scalar_one()
    item.status = "hurda" if status == "hurda" else ("arizali" if status in {"bekliyor", "serviste", "tamir_edilemedi"} else ("aktif" if status in {"tamir_edildi", "geri_geldi"} else item.status))
    db.session.add(InventoryEvent(item=item, event_type="Tamir / Servis Kaydı Oluşturuldu", performed_by=actor or "Sistem", note=problem[:256]))
    db.session.commit()
    return {"repair": _select(item_id)[0], "repair_id": repair_id}, 201


def update(item_id: int, repair_id: int, data: Any, actor: str) -> tuple[dict[str, Any], int]:
    ensure_table()
    if not _item(item_id):
        return {"error": "Envanter kaydı bulunamadı."}, 404
    current = db.session.execute(text("SELECT * FROM inventory_repairs WHERE id=:id AND item_id=:item_id"), {"id": repair_id, "item_id": item_id}).fetchone()
    if not current:
        return {"error": "Tamir kaydı bulunamadı."}, 404
    if not isinstance(data, dict):
        return {"error": "Geçersiz JSON gövdesi."}, 400
    merged = dict(current._mapping)
    merged.update(data)
    return delete_then_create_update(item_id, repair_id, merged, actor)


def delete_then_create_update(item_id: int, repair_id: int, data: dict[str, Any], actor: str) -> tuple[dict[str, Any], int]:
    fault_date, error = _parse_datetime(data.get("fault_date"), "Arıza tarihi")
    if error: return {"error": error}, 400
    sent_at, error = _parse_datetime(data.get("sent_at"), "Gönderim tarihi")
    if error: return {"error": error}, 400
    expected, error = _parse_datetime(data.get("expected_return_at"), "Tahmini dönüş tarihi")
    if error: return {"error": error}, 400
    returned, error = _parse_datetime(data.get("returned_at"), "Dönüş tarihi")
    if error: return {"error": error}, 400
    cost, error = _cost(data.get("service_cost"))
    if error: return {"error": error}, 400
    problem = sanitize_input_text(data.get("problem_description"), max_length=5000)
    if not problem: return {"error": "Arıza / sorun açıklaması zorunludur."}, 400
    status = sanitize_input_text(data.get("status"), max_length=32) or "bekliyor"
    if status not in REPAIR_STATUSES: return {"error": "Geçersiz tamir durumu."}, 400
    params = {
        "id": repair_id, "fault_date": fault_date or datetime.utcnow(),
        "fault_type": sanitize_input_text(data.get("fault_type"), max_length=128),
        "problem_description": problem, "sent_to_service": bool(data.get("sent_to_service")),
        "service_company": sanitize_input_text(data.get("service_company"), max_length=256),
        "service_contact": sanitize_input_text(data.get("service_contact"), max_length=128),
        "service_ticket_no": sanitize_input_text(data.get("service_ticket_no"), max_length=128),
        "warranty_status": sanitize_input_text(data.get("warranty_status"), max_length=32) or "belirsiz",
        "sent_at": sent_at, "expected_return_at": expected, "returned_at": returned,
        "repair_description": sanitize_input_text(data.get("repair_description"), max_length=5000),
        "service_cost": cost, "status": status, "note": sanitize_input_text(data.get("note"), max_length=2000),
    }
    db.session.execute(text("""
        UPDATE inventory_repairs SET fault_date=:fault_date, fault_type=:fault_type,
        problem_description=:problem_description, sent_to_service=:sent_to_service,
        service_company=:service_company, service_contact=:service_contact,
        service_ticket_no=:service_ticket_no, warranty_status=:warranty_status,
        sent_at=:sent_at, expected_return_at=:expected_return_at, returned_at=:returned_at,
        repair_description=:repair_description, service_cost=:service_cost, status=:status,
        note=:note, updated_at=CURRENT_TIMESTAMP WHERE id=:id AND item_id=:item_id
    """), {**params, "item_id": item_id})
    item = _item(item_id)
    item.status = "hurda" if status == "hurda" else ("arizali" if status in {"bekliyor", "serviste", "tamir_edilemedi"} else ("aktif" if status in {"tamir_edildi", "geri_geldi"} else item.status))
    db.session.add(InventoryEvent(item=item, event_type="Tamir / Servis Kaydı Güncellendi", performed_by=actor or "Sistem", note=problem[:256]))
    db.session.commit()
    return {"success": True, "repair": _select(item_id)[0]}, 200


def delete(item_id: int, repair_id: int, actor: str) -> tuple[dict[str, Any], int]:
    ensure_table()
    row = db.session.execute(text("SELECT problem_description FROM inventory_repairs WHERE id=:id AND item_id=:item_id"), {"id": repair_id, "item_id": item_id}).fetchone()
    if not row:
        return {"error": "Tamir kaydı bulunamadı."}, 404
    item = _item(item_id)
    db.session.execute(text("DELETE FROM inventory_repairs WHERE id=:id AND item_id=:item_id"), {"id": repair_id, "item_id": item_id})
    db.session.add(InventoryEvent(item=item, event_type="Tamir / Servis Kaydı Silindi", performed_by=actor or "Sistem", note=(row.problem_description or "")[:256]))
    db.session.commit()
    return {"success": True}, 200


def load_payload() -> dict[str, Any]:
    ensure_table()
    rows = _select()
    return {
        "repair_records": rows,
        "repair_total_count": len(rows),
        "repair_waiting_count": sum(1 for r in rows if r["status"] == "bekliyor"),
        "repair_service_count": sum(1 for r in rows if r["status"] == "serviste"),
        "repair_returned_count": sum(1 for r in rows if r["status"] == "geri_geldi"),
        "repair_problem_count": sum(1 for r in rows if r["status"] in {"tamir_edilemedi", "hurda"}),
        "repair_statuses": REPAIR_STATUSES,
        "warranty_statuses": WARRANTY_STATUSES,
    }
