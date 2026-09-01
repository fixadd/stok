from __future__ import annotations

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from ..models import ActivityLog, InventoryItem, InventoryLicense, db
from ..services.authz import current_actor_name



def register_license_history_routes(app):
    license_bp = Blueprint("license", __name__)

    try:
        if db.engine.dialect.name == "postgresql":
            db.session.execute(
                text("ALTER TABLE inventory_licenses ALTER COLUMN item_id DROP NOT NULL")
            )
            db.session.commit()
    except Exception:
        db.session.rollback()

    def serialize_license(license_record: InventoryLicense) -> dict:
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

    def record_history(license_record: InventoryLicense, action: str, description: str):
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

    @license_bp.post("/api/licenses")
    def create_license():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400

        name = str(data.get("name") or "").strip()
        key = str(data.get("key") or "").strip()
        if not name:
            return jsonify({"error": "Lisans adı zorunludur."}), 400
        if not key:
            return jsonify({"error": "Lisans anahtarı zorunludur."}), 400

        raw_name = f"{name} - {key}"
        if InventoryLicense.query.filter_by(name=raw_name).first():
            return jsonify({"error": "Bu lisans kaydı zaten mevcut."}), 409

        license_record = InventoryLicense(name=raw_name, status="pasif", item_id=None)
        db.session.add(license_record)
        db.session.flush()
        record_history(license_record, "Lisans oluşturuldu", f"{name} lisans kaydı oluşturuldu.")
        db.session.commit()
        return jsonify({"license": serialize_license(license_record)}), 201

    @license_bp.patch("/api/licenses/<int:license_id>")
    def update_license(license_id: int):
        license_record = db.session.get(InventoryLicense, license_id)
        if license_record is None:
            return jsonify({"error": "Lisans kaydı bulunamadı."}), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400

        name = str(data.get("name") or "").strip()
        key = str(data.get("key") or "").strip()
        status = str(data.get("status") or license_record.status or "aktif").strip().lower()
        if not name or not key:
            return jsonify({"error": "Lisans adı ve anahtarı zorunludur."}), 400
        if status not in {"aktif", "pasif", "beklemede"}:
            return jsonify({"error": "Geçersiz lisans durumu."}), 400

        raw_name = f"{name} - {key}"
        duplicate = (
            InventoryLicense.query
            .filter(InventoryLicense.name == raw_name, InventoryLicense.id != license_id)
            .first()
        )
        if duplicate:
            return jsonify({"error": "Bu lisans kaydı zaten mevcut."}), 409

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
                    return jsonify({"error": "Geçersiz envanter seçimi."}), 400
                item = db.session.get(InventoryItem, inventory_id)
                if item is None:
                    return jsonify({"error": "Seçilen envanter kaydı bulunamadı."}), 404
                license_record.item = item

        record_history(
            license_record,
            "Lisans düzenlendi",
            f"{old_name} → {license_record.name}; durum: {old_status} → {license_record.status}.",
        )
        db.session.commit()
        return jsonify({"license": serialize_license(license_record)})

    @license_bp.post("/api/licenses/<int:license_id>/assign")
    def assign_license(license_id: int):
        license_record = db.session.get(InventoryLicense, license_id)
        if license_record is None:
            return jsonify({"error": "Lisans kaydı bulunamadı."}), 404

        data = request.get_json(silent=True) or {}
        raw_inventory_id = data.get("inventory_id") if isinstance(data, dict) else None
        if raw_inventory_id in (None, ""):
            return jsonify({"error": "Lisans ataması için envanter seçilmelidir."}), 400

        try:
            inventory_id = int(raw_inventory_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Geçersiz envanter seçimi."}), 400

        item = db.session.get(InventoryItem, inventory_id)
        if item is None:
            return jsonify({"error": "Seçilen envanter kaydı bulunamadı."}), 404

        previous_inventory = license_record.item
        license_record.item = item
        license_record.status = "aktif"
        record_history(
            license_record,
            "Lisans atandı",
            f"{previous_inventory.inventory_no if previous_inventory else 'Atamasız'} → {item.inventory_no}.",
        )
        db.session.commit()
        return jsonify({"license": serialize_license(license_record)})

    @license_bp.post("/api/licenses/<int:license_id>/passive")
    def passive_license(license_id: int):
        license_record = db.session.get(InventoryLicense, license_id)
        if license_record is None:
            return jsonify({"error": "Lisans kaydı bulunamadı."}), 404

        license_record.status = "pasif"
        record_history(
            license_record,
            "Lisans pasife alındı",
            f"{license_record.name} pasif durumuna alındı.",
        )
        db.session.commit()
        return jsonify({"license": serialize_license(license_record)})

    @license_bp.get("/api/licenses/<int:license_id>/history")
    def get_license_history(license_id: int):
        license_record = db.session.get(InventoryLicense, license_id)
        if license_record is None:
            return jsonify({"error": "Lisans kaydı bulunamadı."}), 404

        records = (
            ActivityLog.query
            .filter(
                ActivityLog.metadata_json["license_id"].as_integer() == license_id,
                ActivityLog.area.in_(["lisans", "stok"]),
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
        return jsonify({"license_id": license_id, "history": history, "count": len(history)})

    app.register_blueprint(license_bp)
