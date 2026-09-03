from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request, url_for, flash

from ..models import CustomField, CustomFieldOption, FieldGroup, SettingList, db
from ..services.activity_service import record_activity
from ..services.settings_service import FIELD_TYPES, get_setting_lists, serialize_custom_field, upsert_setting_option


def register_settings_routes(app, deps=None):
    get_active_user = deps["get_active_user"]
    has_system_role = deps["has_system_role"]

    bp = Blueprint("settings", __name__)

    def require_admin():
        user = get_active_user()
        if not has_system_role(user, "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403
        return None

    @bp.get("/ayarlar")
    def page():
        user = get_active_user()
        if not has_system_role(user, "admin"):
            flash("Ayarlar sayfasına erişmek için admin yetkisi gerekir.", "danger")
            return redirect(url_for("index"))
        lists = get_setting_lists()
        fields = CustomField.query.order_by(CustomField.entity_type, CustomField.sort_order, CustomField.id).all()
        groups = FieldGroup.query.order_by(FieldGroup.entity_type, FieldGroup.sort_order, FieldGroup.id).all()
        return render_template(
            "settings.html",
            active_page="settings",
            setting_lists=lists,
            custom_fields=fields,
            field_groups=groups,
            field_types=FIELD_TYPES,
        )

    @bp.get("/api/settings/lists")
    def api_lists():
        if (error := require_admin()):
            return error
        payload = []
        for item in get_setting_lists():
            payload.append({
                "id": item.id,
                "key": item.key,
                "label": item.label,
                "scope": item.scope,
                "description": item.description or "",
                "active": item.active,
                "options": [{"id": o.id, "label": o.label, "value": o.value, "active": o.active, "sort_order": o.sort_order} for o in item.options],
            })
        return jsonify(payload)

    @bp.post("/api/settings/lists/<int:list_id>/options")
    def api_add_option(list_id: int):
        if (error := require_admin()):
            return error
        data = request.get_json(silent=True) or request.form
        try:
            option = upsert_setting_option(
                list_id,
                str(data.get("label", "")),
                data.get("value"),
                active=bool(data.get("active", True)),
                sort_order=int(data.get("sort_order", 0) or 0),
            )
            record_activity(area="sistem", action="ayar_secenegi_ekle", description=f"{option.label} seçeneği güncellendi.", actor=get_active_user().username)
            db.session.commit()
            return jsonify({"ok": True, "id": option.id, "label": option.label, "value": option.value})
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            return jsonify({"error": str(exc)}), 400
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Seçenek kaydedilemedi."}), 500

    @bp.patch("/api/settings/options/<int:option_id>")
    def api_toggle_option(option_id: int):
        if (error := require_admin()):
            return error
        data = request.get_json(silent=True) or {}
        option = db.session.get(__import__("app.models", fromlist=["SettingOption"]).SettingOption, option_id)
        if option is None:
            return jsonify({"error": "Seçenek bulunamadı."}), 404
        option.active = bool(data.get("active", True))
        db.session.commit()
        return jsonify({"ok": True, "active": option.active})

    @bp.post("/api/settings/fields")
    def api_add_field():
        if (error := require_admin()):
            return error
        data = request.get_json(silent=True) or request.form
        entity_type = str(data.get("entity_type", "inventory")).strip()
        field_key = str(data.get("field_key", "")).strip()
        label = str(data.get("label", "")).strip()
        field_type = str(data.get("field_type", "text")).strip()
        if not field_key or not label:
            return jsonify({"error": "Alan anahtarı ve adı zorunludur."}), 400
        if field_type not in FIELD_TYPES:
            return jsonify({"error": "Geçersiz alan tipi."}), 400
        if CustomField.query.filter_by(entity_type=entity_type, field_key=field_key).first():
            return jsonify({"error": "Bu alan zaten mevcut."}), 409
        field = CustomField(
            entity_type=entity_type,
            field_key=field_key,
            label=label,
            field_type=field_type,
            required=bool(data.get("required", False)),
            active=True,
            visible_form=bool(data.get("visible_form", True)),
            visible_list=bool(data.get("visible_list", False)),
            searchable=bool(data.get("searchable", False)),
            sortable=bool(data.get("sortable", False)),
            placeholder=str(data.get("placeholder", "")).strip() or None,
            help_text=str(data.get("help_text", "")).strip() or None,
            default_value=str(data.get("default_value", "")).strip() or None,
            sort_order=int(data.get("sort_order", 0) or 0),
        )
        db.session.add(field)
        record_activity(area="sistem", action="ozel_alan_ekle", description=f"{label} alanı oluşturuldu.", actor=get_active_user().username)
        db.session.commit()
        return jsonify({"ok": True, "field": serialize_custom_field(field)})

    @bp.patch("/api/settings/fields/<int:field_id>")
    def api_update_field(field_id: int):
        if (error := require_admin()):
            return error
        field = db.session.get(CustomField, field_id)
        if field is None:
            return jsonify({"error": "Alan bulunamadı."}), 404
        data = request.get_json(silent=True) or {}
        for key in ("label", "placeholder", "help_text", "default_value", "field_type"):
            if key in data:
                if key == "field_type" and data[key] not in FIELD_TYPES:
                    return jsonify({"error": "Geçersiz alan tipi."}), 400
                setattr(field, key, str(data[key]).strip())
        for key in ("required", "active", "visible_form", "visible_list", "searchable", "sortable"):
            if key in data:
                setattr(field, key, bool(data[key]))
        if "sort_order" in data:
            field.sort_order = int(data["sort_order"])
        db.session.commit()
        return jsonify({"ok": True, "field": serialize_custom_field(field)})

    @bp.post("/api/settings/fields/<int:field_id>/options")
    def api_add_field_option(field_id: int):
        if (error := require_admin()):
            return error
        field = db.session.get(CustomField, field_id)
        if field is None:
            return jsonify({"error": "Alan bulunamadı."}), 404
        data = request.get_json(silent=True) or {}
        label = str(data.get("label", "")).strip()
        value = str(data.get("value", label)).strip().lower().replace(" ", "_")
        if not label or not value:
            return jsonify({"error": "Seçenek adı zorunludur."}), 400
        if CustomFieldOption.query.filter_by(field_id=field_id, value=value).first():
            return jsonify({"error": "Bu seçenek zaten mevcut."}), 409
        option = CustomFieldOption(field_id=field_id, label=label, value=value, sort_order=int(data.get("sort_order", 0) or 0))
        db.session.add(option)
        db.session.commit()
        return jsonify({"ok": True, "id": option.id, "label": option.label, "value": option.value})

    app.register_blueprint(bp)
