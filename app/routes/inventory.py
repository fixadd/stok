from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from ..services.authz import get_active_user, has_system_role
from ..services import inventory_service


def register_inventory_routes(app, helpers):
    inventory_bp = Blueprint("inventory", __name__)

    def require_admin():
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403
        return None

    @inventory_bp.get("/envanter-takip")
    def inventory_tracking():
        payload = helpers["load_inventory_payload"]()
        return render_template(
            "inventory_tracking.html",
            active_page="inventory_tracking",
            **payload,
        )

    @inventory_bp.post("/api/inventory")
    def create_inventory():
        denied = require_admin()
        if denied:
            return denied
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return helpers["json_error"]("Geçersiz JSON gövdesi."), 400
        payload, status_code = inventory_service.create_inventory(helpers, data)
        return jsonify(payload), status_code

    @inventory_bp.patch("/api/inventory/<int:item_id>")
    def update_inventory(item_id: int):
        denied = require_admin()
        if denied:
            return denied
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return helpers["json_error"]("Geçersiz JSON gövdesi."), 400
        payload, status_code = inventory_service.update_inventory(helpers, item_id, data)
        return jsonify(payload), status_code

    @inventory_bp.post("/api/inventory/<int:item_id>/mark-faulty")
    def mark_inventory_faulty(item_id: int):
        denied = require_admin()
        if denied:
            return denied
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return helpers["json_error"]("Geçersiz JSON gövdesi."), 400
        payload, status_code = inventory_service.mark_inventory_faulty(helpers, item_id, data)
        return jsonify(payload), status_code

    app.register_blueprint(inventory_bp)
