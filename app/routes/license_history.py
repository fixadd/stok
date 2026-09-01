from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from ..models import ActivityLog, InventoryItem, InventoryLicense, db
from ..services.authz import get_active_user, has_system_role, current_actor_name
from ..services import license_service


def register_license_history_routes(app, deps=None):
    license_bp = Blueprint("license", __name__)
    deps = deps or {}

    load_license_payload = deps.get("load_license_payload")
    if load_license_payload is None:
        from .. import load_license_payload as default_loader
        load_license_payload = default_loader

    def require_admin():
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403
        return None

    serialize_license = license_service.serialize_license

    @license_bp.get("/api/licenses")
    def list_licenses():
        return jsonify(license_service.list_licenses(InventoryLicense, serialize_license))

    @license_bp.get("/api/inventory/<int:item_id>/licenses")
    def list_inventory_licenses(item_id: int):
        payload, status_code = license_service.list_inventory_licenses(
            db, InventoryItem, InventoryLicense, item_id, serialize_license
        )
        return jsonify(payload), status_code

    @license_bp.route("/lisans-takip")
    def license_tracking():
        return render_template(
            "license_tracking.html",
            active_page="license_tracking",
            **load_license_payload(),
        )

    @license_bp.post("/api/licenses")
    def create_license():
        denied = require_admin()
        if denied:
            return denied
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400
        payload, status_code = license_service.create_license(
            db, InventoryLicense, ActivityLog, current_actor_name, data, serialize_license
        )
        return jsonify(payload), status_code

    @license_bp.patch("/api/licenses/<int:license_id>")
    def update_license(license_id: int):
        denied = require_admin()
        if denied:
            return denied
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400
        payload, status_code = license_service.update_license(
            db, InventoryLicense, InventoryItem, ActivityLog,
            current_actor_name, license_id, data, serialize_license
        )
        return jsonify(payload), status_code

    @license_bp.post("/api/licenses/<int:license_id>/assign")
    def assign_license(license_id: int):
        denied = require_admin()
        if denied:
            return denied
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400
        payload, status_code = license_service.assign_license(
            db, InventoryLicense, InventoryItem, ActivityLog,
            current_actor_name, license_id, data.get("inventory_id"), serialize_license
        )
        return jsonify(payload), status_code

    @license_bp.post("/api/licenses/<int:license_id>/passive")
    def passive_license(license_id: int):
        denied = require_admin()
        if denied:
            return denied
        payload, status_code = license_service.passive_license(
            db, InventoryLicense, ActivityLog, current_actor_name, license_id, serialize_license
        )
        return jsonify(payload), status_code

    @license_bp.get("/api/licenses/<int:license_id>/history")
    def get_license_history(license_id: int):
        payload, status_code = license_service.get_license_history(
            db, ActivityLog, InventoryLicense, license_id
        )
        return jsonify(payload), status_code

    app.register_blueprint(license_bp)
