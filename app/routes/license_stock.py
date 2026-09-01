from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..models import InventoryLicense, db
from ..services.authz import current_actor_name, get_active_user, has_system_role



def register_license_stock_routes(app, deps):
    license_stock_bp = Blueprint("license_stock", __name__)

    create_stock_item_from_license = deps["create_stock_item_from_license"]
    serialize_stock_item = deps["serialize_stock_item"]
    serialize_license_record = deps["serialize_license_record"]
    get_stock_item_with_relations = deps["get_stock_item_with_relations"]
    add_inventory_event = deps["add_inventory_event"]
    record_stock_log = deps["record_stock_log"]
    sanitize_input_text = deps["sanitize_input_text"]
    DEFAULT_EVENT_ACTOR = deps["DEFAULT_EVENT_ACTOR"]

    @license_stock_bp.post("/api/licenses/<int:license_id>/stock")
    def move_license_to_stock_api(license_id: int):
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403

        license_record = db.session.get(InventoryLicense, license_id)
        if license_record is None:
            return jsonify({"error": "Lisans kaydı bulunamadı."}), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400

        note = sanitize_input_text(data.get("note"), max_length=512)
        actor = sanitize_input_text(data.get("performed_by")) or current_actor_name() or DEFAULT_EVENT_ACTOR

        associated_item = license_record.item
        stock_item = create_stock_item_from_license(
            license_record,
            note=note,
            actor=actor,
        )

        license_record.status = "pasif"
        license_record.item = None

        if associated_item:
            add_inventory_event(
                associated_item,
                "Lisans stoklandı",
                note or f"{license_record.name} lisansı stok listesine taşındı.",
                performed_by=actor,
            )

        db.session.commit()

        fresh_license = db.session.get(InventoryLicense, license_id)
        fresh_stock = get_stock_item_with_relations(stock_item.id)
        response = {
            "message": "Lisans stok listesine taşındı.",
            "license": serialize_license_record(fresh_license) if fresh_license else None,
            "stock_item": serialize_stock_item(fresh_stock) if fresh_stock else None,
        }
        return jsonify(response)

    app.register_blueprint(license_stock_bp)
