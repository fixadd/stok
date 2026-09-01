from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from ..services.authz import get_active_user, has_system_role
from ..services import stock_service


def register_stock_routes(app, deps):
    stock_bp = Blueprint("stock", __name__)

    @stock_bp.route("/stok-takip")
    def stock_tracking():
        payload = deps["load_stock_payload"]()
        return render_template(
            "stock_tracking.html",
            active_page="stock_tracking",
            can_manage_stock_data=has_system_role(get_active_user(), "admin"),
            **payload,
        )

    @stock_bp.route("/hurdalar")
    def scrap_inventory_page():
        payload = deps["load_scrap_inventory_payload"]()
        return render_template(
            "scrap_inventory.html",
            active_page="scrap_inventory",
            can_restore_scrap=has_system_role(get_active_user(), "superadmin"),
            **payload,
        )

    @stock_bp.post("/api/inventory/<int:item_id>/stock")
    def move_inventory_to_stock(item_id: int):
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return deps["json_error"]("Geçersiz JSON gövdesi."), 400
        payload, status_code = stock_service.move_inventory_to_stock(deps, item_id, data)
        return jsonify(payload), status_code

    @stock_bp.post("/api/inventory/<int:item_id>/scrap")
    def scrap_inventory(item_id: int):
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return deps["json_error"]("Geçersiz JSON gövdesi."), 400
        payload, status_code = stock_service.scrap_inventory(deps, item_id, data)
        return jsonify(payload), status_code

    @stock_bp.post("/api/licenses/<int:license_id>/stock")
    def move_license_to_stock(license_id: int):
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return deps["json_error"]("Geçersiz JSON gövdesi."), 400
        payload, status_code = stock_service.move_license_to_stock(deps, license_id, data)
        return jsonify(payload), status_code

    @stock_bp.post("/api/stock")
    def create_stock_entry():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return deps["json_error"]("Geçersiz JSON gövdesi."), 400
        payload, status_code = stock_service.create_stock_entry(deps, data)
        return jsonify(payload), status_code

    app.register_blueprint(stock_bp)
