from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..models import db
from ..services.settings_service import load_custom_values, save_custom_values


def register_custom_field_routes(app, deps):
    get_active_user = deps["get_active_user"]
    has_system_role = deps["has_system_role"]
    bp = Blueprint("custom_fields", __name__)

    def require_login():
        user = get_active_user()
        if user is None:
            return jsonify({"error": "Oturum açmanız gerekir."}), 401
        return None

    def require_admin():
        user = get_active_user()
        if not has_system_role(user, "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403
        return None

    @bp.get("/api/custom-fields/<string:entity_type>/<int:entity_id>")
    def get_values(entity_type: str, entity_id: int):
        if (error := require_login()):
            return error
        return jsonify(load_custom_values(entity_type, entity_id))

    @bp.put("/api/custom-fields/<string:entity_type>/<int:entity_id>")
    def put_values(entity_type: str, entity_id: int):
        if (error := require_login()):
            return error
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "JSON nesnesi bekleniyor."}), 400
        try:
            save_custom_values(entity_type, entity_id, payload)
            db.session.commit()
            return jsonify({"ok": True, "values": load_custom_values(entity_type, entity_id)})
        except ValueError as exc:
            db.session.rollback()
            return jsonify({"error": str(exc)}), 400
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Özel alanlar kaydedilemedi."}), 500

    app.register_blueprint(bp)
