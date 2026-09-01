from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..services import assignment_service
from ..services.permissions import require_admin


def register_assignment_routes(app, helpers):
    assignment_bp = Blueprint("assignment", __name__)

    @assignment_bp.post("/api/inventory/<int:item_id>/assign")
    def assign_inventory(item_id: int):
        denied = require_admin()
        if denied:
            return denied
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return helpers["json_error"]("Geçersiz JSON gövdesi."), 400
        payload, status_code = assignment_service.assign_inventory(helpers, item_id, data)
        return jsonify(payload), status_code

    @assignment_bp.get("/api/inventory/<int:item_id>/assignments")
    def get_inventory_assignments(item_id: int):
        payload, status_code = assignment_service.list_inventory_assignments(helpers, item_id)
        return jsonify(payload), status_code

    @assignment_bp.post("/api/inventory/<int:item_id>/return")
    def return_inventory_assignment(item_id: int):
        denied = require_admin()
        if denied:
            return denied
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return helpers["json_error"]("Geçersiz JSON gövdesi."), 400
        payload, status_code = assignment_service.return_inventory_assignment(helpers, item_id, data)
        return jsonify(payload), status_code

    @assignment_bp.get("/api/users/<int:user_id>/inventory")
    def get_user_inventory_assignments(user_id: int):
        payload, status_code = assignment_service.list_user_inventory_assignments(helpers, user_id)
        return jsonify(payload), status_code

    app.register_blueprint(assignment_bp)
