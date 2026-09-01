from __future__ import annotations

from typing import Any


def serialize_license(license_record, InventoryLicense=None) -> dict[str, Any]:
    item = license_record.item
    responsible_user = item.responsible_user if item else None
    responsible_name = (
        f"{responsible_user.first_name} {responsible_user.last_name}"
        if responsible_user
        else "Atama bekliyor"
    )
    display_name = license_record.name
    key = ""
    if " - " in license_record.name:
        display_name, key = license_record.name.split(" - ", 1)
    return {
        "id": license_record.id,
        "display_name": display_name.strip() or license_record.name,
        "key": key.strip(),
        "raw_name": license_record.name,
        "status": (license_record.status or "aktif").lower(),
        "responsible_id": responsible_user.id if responsible_user else None,
        "responsible_name": responsible_name,
        "responsible_department": responsible_user.department if responsible_user else "",
        "email": responsible_user.email if responsible_user else "",
        "inventory_id": item.id if item else None,
        "inventory_no": item.inventory_no if item else "",
        "inventory_label": (
            f"{item.inventory_no} · {item.computer_name}"
            if item and item.computer_name
            else (item.inventory_no if item else "")
        ),
        "factory": item.factory.name if item and item.factory else "",
        "department": item.department if item else "",
        "ifs_no": item.ifs_no if item else "",
    }


def record_history(db, ActivityLog, current_actor_name, license_record, action: str, description: str) -> None:
    db.session.add(
        ActivityLog(
            area="lisans",
            action=action,
            description=description,
            actor=current_actor_name(),
            metadata_json={
                "license_id": license_record.id,
                "license_name": license_record.name,
                "inventory_id": license_record.item_id,
            },
        )
    )


def list_licenses(InventoryLicense, serialize) -> dict[str, Any]:
    records = InventoryLicense.query.order_by(InventoryLicense.id).all()
    return {"items": [serialize(record) for record in records]}


def list_inventory_licenses(db, InventoryItem, InventoryLicense, item_id: int, serialize):
    item = db.session.get(InventoryItem, item_id)
    if item is None:
        return {"error": "Envanter kaydı bulunamadı."}, 404
    records = (
        InventoryLicense.query
        .filter(InventoryLicense.item_id == item_id)
        .order_by(InventoryLicense.id)
        .all()
    )
    return {
        "inventory_id": item_id,
        "items": [serialize(record) for record in records],
    }, 200


def create_license(db, InventoryLicense, ActivityLog, current_actor_name, data, serialize):
    name = str(data.get("name") or "").strip()
    key = str(data.get("key") or "").strip()
    note = str(data.get("note") or "").strip()
    if not name:
        return {"error": "Lisans adı zorunludur."}, 400
    if not key:
        return {"error": "Lisans anahtarı zorunludur."}, 400

    raw_name = f"{name} - {key}"
    if InventoryLicense.query.filter_by(name=raw_name).first():
        return {"error": "Bu lisans kaydı zaten mevcut."}, 409

    license_record = InventoryLicense(name=raw_name, status="pasif", item_id=None)
    db.session.add(license_record)
    db.session.flush()
    record_history(
        db,
        ActivityLog,
        current_actor_name,
        license_record,
        "Lisans oluşturuldu",
        note or f"{name} lisans kaydı oluşturuldu.",
    )
    db.session.commit()
    return {"license": serialize(license_record)}, 201


def update_license(db, InventoryLicense, InventoryItem, ActivityLog, current_actor_name, license_id: int, data, serialize):
    license_record = db.session.get(InventoryLicense, license_id)
    if license_record is None:
        return {"error": "Lisans kaydı bulunamadı."}, 404

    name = str(data.get("name") or "").strip()
    key = str(data.get("key") or "").strip()
    status = str(data.get("status") or license_record.status or "aktif").strip().lower()
    if not name or not key:
        return {"error": "Lisans adı ve anahtarı zorunludur."}, 400
    if status not in {"aktif", "pasif", "beklemede"}:
        return {"error": "Geçersiz lisans durumu."}, 400

    raw_name = f"{name} - {key}"
    duplicate = InventoryLicense.query.filter(
        InventoryLicense.name == raw_name,
        InventoryLicense.id != license_id,
    ).first()
    if duplicate:
        return {"error": "Bu lisans kaydı zaten mevcut."}, 409

    old_name = license_record.name
    old_status = license_record.status
    license_record.name = raw_name
    license_record.status = status

    if "inventory_id" in data:
        raw_inventory_id = data.get("inventory_id")
        if raw_inventory_id in (None, ""):
            license_record.item = None
        else:
            try:
                inventory_id = int(raw_inventory_id)
            except (TypeError, ValueError):
                return {"error": "Geçersiz envanter seçimi."}, 400
            item = db.session.get(InventoryItem, inventory_id)
            if item is None:
                return {"error": "Seçilen envanter kaydı bulunamadı."}, 404
            license_record.item = item

    record_history(
        db,
        ActivityLog,
        current_actor_name,
        license_record,
        "Lisans düzenlendi",
        f"{old_name} → {license_record.name}; durum: {old_status} → {license_record.status}.",
    )
    db.session.commit()
    return {"license": serialize(license_record)}, 200


def assign_license(db, InventoryLicense, InventoryItem, ActivityLog, current_actor_name, license_id: int, inventory_id, serialize):
    license_record = db.session.get(InventoryLicense, license_id)
    if license_record is None:
        return {"error": "Lisans kaydı bulunamadı."}, 404
    if inventory_id in (None, ""):
        return {"error": "Lisans ataması için envanter seçilmelidir."}, 400
    try:
        inventory_id = int(inventory_id)
    except (TypeError, ValueError):
        return {"error": "Geçersiz envanter seçimi."}, 400

    item = db.session.get(InventoryItem, inventory_id)
    if item is None:
        return {"error": "Seçilen envanter kaydı bulunamadı."}, 404

    previous_inventory = license_record.item
    license_record.item = item
    license_record.status = "aktif"
    record_history(
        db,
        ActivityLog,
        current_actor_name,
        license_record,
        "Lisans atandı",
        f"{previous_inventory.inventory_no if previous_inventory else 'Atamasız'} → {item.inventory_no}.",
    )
    db.session.commit()
    return {"license": serialize(license_record)}, 200


def passive_license(db, InventoryLicense, ActivityLog, current_actor_name, license_id: int, serialize):
    license_record = db.session.get(InventoryLicense, license_id)
    if license_record is None:
        return {"error": "Lisans kaydı bulunamadı."}, 404
    license_record.status = "pasif"
    record_history(
        db,
        ActivityLog,
        current_actor_name,
        license_record,
        "Lisans pasife alındı",
        f"{license_record.name} pasif durumuna alındı.",
    )
    db.session.commit()
    return {"license": serialize(license_record)}, 200


def get_license_history(db, ActivityLog, InventoryLicense, license_id: int):
    license_record = db.session.get(InventoryLicense, license_id)
    if license_record is None:
        return {"error": "Lisans kaydı bulunamadı."}, 404
    records = (
        ActivityLog.query
        .filter(
            ActivityLog.metadata_json["license_id"].as_integer() == license_id,
            ActivityLog.area == "lisans",
        )
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .all()
    )
    history = [
        {
            "id": record.id,
            "title": record.action,
            "actor": record.actor,
            "note": record.description or "",
            "performed_at": record.created_at.strftime("%d.%m.%Y %H:%M"),
        }
        for record in records
    ]
    return {"license_id": license_id, "history": history, "count": len(history)}, 200
