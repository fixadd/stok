from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..models import SettingList, db
from ..services.activity_service import record_activity
from ..services.settings_service import upsert_setting_option


def _require_admin(get_active_user, has_system_role):
    user = get_active_user()
    if not has_system_role(user, "admin"):
        return None, (jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403)
    return user, None


def register_settings_quick_routes(app, deps):
    get_active_user = deps["get_active_user"]
    has_system_role = deps["has_system_role"]
    bp = Blueprint("settings_quick", __name__)

    @bp.post("/api/settings/lists/by-key/<string:key>/options")
    def add_option_by_key(key: str):
        user, error = _require_admin(get_active_user, has_system_role)
        if error:
            return error
        setting = SettingList.query.filter_by(key=key, active=True).first()
        if setting is None:
            return jsonify({"error": "Ayar listesi bulunamadı."}), 404
        data = request.get_json(silent=True) or {}
        try:
            option = upsert_setting_option(setting.id, str(data.get("label", "")), data.get("value"), active=True)
            record_activity(area="sistem", action="ayar_secenegi_hizli_ekle", description=f"{setting.label}: {option.label} eklendi.", actor=user.username if user else "Sistem")
            db.session.commit()
            return jsonify({"ok": True, "id": option.id, "label": option.label, "value": option.value})
        except ValueError as exc:
            db.session.rollback()
            return jsonify({"error": str(exc)}), 400
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Seçenek kaydedilemedi."}), 500

    app.register_blueprint(bp)
