from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from ..models import CustomField, CustomFieldOption, DashboardWidget, FieldGroup, SettingList, SettingOption, db
from ..services.activity_service import record_activity
from ..services.configuration_service import build_form_schema, serialize_groups
from ..services.settings_service import FIELD_TYPES, get_setting_lists, serialize_custom_field, toggle_setting_option, upsert_setting_option


def _bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "evet"}


def register_settings_routes(app, deps=None):
    get_active_user = deps["get_active_user"]
    has_system_role = deps["has_system_role"]
    bp = Blueprint("settings", __name__)

    def require_admin():
        user = get_active_user()
        if not has_system_role(user, "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403
        return None

    def audit(action, description):
        actor = get_active_user()
        record_activity(area="sistem", action=action, description=description, actor=actor.username if actor else "Sistem")

    @bp.get("/ayarlar")
    def page():
        user = get_active_user()
        if not has_system_role(user, "admin"):
            flash("Ayarlar sayfasına erişmek için admin yetkisi gerekir.", "danger")
            return redirect(url_for("index"))
        lists = get_setting_lists()
        fields = CustomField.query.order_by(CustomField.entity_type, CustomField.sort_order, CustomField.id).all()
        groups = FieldGroup.query.order_by(FieldGroup.entity_type, FieldGroup.sort_order, FieldGroup.id).all()
        widgets = DashboardWidget.query.order_by(DashboardWidget.sort_order, DashboardWidget.id).all()
        return render_template("settings.html", active_page="settings", setting_lists=lists, custom_fields=fields, field_groups=groups, dashboard_widgets=widgets, field_types=FIELD_TYPES)

    @bp.get("/api/settings/lists")
    def api_lists():
        if (error := require_admin()): return error
        return jsonify([
            {"id": item.id, "key": item.key, "label": item.label, "scope": item.scope, "description": item.description or "", "active": item.active,
             "options": [{"id": o.id, "label": o.label, "value": o.value, "active": o.active, "sort_order": o.sort_order} for o in item.options]}
            for item in get_setting_lists()
        ])

    @bp.get("/api/settings/lists/<string:key>/options")
    def api_options(key):
        if (error := require_admin()): return error
        setting = SettingList.query.filter_by(key=key, active=True).first()
        if setting is None:
            return jsonify({"error": "Ayar listesi bulunamadı."}), 404
        return jsonify([{"id": o.id, "label": o.label, "value": o.value, "sort_order": o.sort_order} for o in setting.options if o.active])

    @bp.post("/api/settings/lists/<int:list_id>/options")
    def api_add_option(list_id: int):
        if (error := require_admin()): return error
        data = request.get_json(silent=True) or request.form
        try:
            option = upsert_setting_option(list_id, str(data.get("label", "")), data.get("value"), active=True, sort_order=int(data.get("sort_order", 0) or 0))
            audit("ayar_secenegi_ekle", f"{option.label} seçeneği güncellendi.")
            db.session.commit()
            return jsonify({"ok": True, "id": option.id, "label": option.label, "value": option.value})
        except (ValueError, TypeError) as exc:
            db.session.rollback(); return jsonify({"error": str(exc)}), 400
        except Exception:
            db.session.rollback(); return jsonify({"error": "Seçenek kaydedilemedi."}), 500

    @bp.patch("/api/settings/options/<int:option_id>")
    def api_toggle_option(option_id: int):
        if (error := require_admin()): return error
        data = request.get_json(silent=True) or {}
        try:
            option = toggle_setting_option(option_id, _bool(data.get("active"), True))
            audit("ayar_secenegi_durum", f"{option.label} seçeneği {'aktif' if option.active else 'pasif'} yapıldı.")
            db.session.commit()
            return jsonify({"ok": True, "active": option.active})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @bp.post("/api/settings/fields")
    def api_add_field():
        if (error := require_admin()): return error
        data = request.get_json(silent=True) or request.form
        entity_type = str(data.get("entity_type", "inventory")).strip() or "inventory"
        field_key = str(data.get("field_key", "")).strip()
        label = str(data.get("label", "")).strip()
        field_type = str(data.get("field_type", "text")).strip() or "text"
        if not field_key or not label: return jsonify({"error": "Alan anahtarı ve adı zorunludur."}), 400
        if field_type not in FIELD_TYPES: return jsonify({"error": "Geçersiz alan tipi."}), 400
        if CustomField.query.filter_by(entity_type=entity_type, field_key=field_key).first(): return jsonify({"error": "Bu alan zaten mevcut."}), 409
        depends_on_field_id = int(data["depends_on_field_id"]) if data.get("depends_on_field_id") else None
        if depends_on_field_id:
            parent_field = db.session.get(CustomField, depends_on_field_id)
            if parent_field is None or parent_field.entity_type != entity_type:
                return jsonify({"error": "Bağımlı alan aynı modülde bulunan geçerli bir alan olmalıdır."}), 400
        try:
            field = CustomField(entity_type=entity_type, field_key=field_key, label=label, field_type=field_type,
                required=_bool(data.get("required")), active=True, visible_form=_bool(data.get("visible_form"), True),
                visible_list=_bool(data.get("visible_list")), searchable=_bool(data.get("searchable")), sortable=_bool(data.get("sortable")),
                placeholder=str(data.get("placeholder", "")).strip() or None, help_text=str(data.get("help_text", "")).strip() or None,
                default_value=str(data.get("default_value", "")).strip() or None, sort_order=int(data.get("sort_order", 0) or 0),
                group_id=int(data["group_id"]) if data.get("group_id") else None,
                depends_on_field_id=int(data["depends_on_field_id"]) if data.get("depends_on_field_id") else None,
                depends_on_values=data.get("depends_on_values") or [])
            db.session.add(field); audit("ozel_alan_ekle", f"{label} alanı oluşturuldu."); db.session.commit()
            return jsonify({"ok": True, "field": serialize_custom_field(field)})
        except (ValueError, TypeError) as exc:
            db.session.rollback(); return jsonify({"error": str(exc)}), 400

    @bp.patch("/api/settings/fields/<int:field_id>")
    def api_update_field(field_id: int):
        if (error := require_admin()): return error
        field = db.session.get(CustomField, field_id)
        if field is None: return jsonify({"error": "Alan bulunamadı."}), 404
        data = request.get_json(silent=True) or {}
        try:
            for key in ("label", "placeholder", "help_text", "default_value"):
                if key in data: setattr(field, key, str(data[key]).strip() or None)
            if "field_type" in data:
                if data["field_type"] not in FIELD_TYPES: return jsonify({"error": "Geçersiz alan tipi."}), 400
                field.field_type = data["field_type"]
            for key in ("required", "active", "visible_form", "visible_list", "searchable", "sortable"):
                if key in data: setattr(field, key, _bool(data[key]))
            if "sort_order" in data: field.sort_order = int(data["sort_order"])
            if "group_id" in data: field.group_id = int(data["group_id"]) if data["group_id"] else None
            if "depends_on_field_id" in data: field.depends_on_field_id = int(data["depends_on_field_id"]) if data["depends_on_field_id"] else None
            if "depends_on_values" in data: field.depends_on_values = data["depends_on_values"] or []
            audit("ozel_alan_guncelle", f"{field.label} alanı güncellendi."); db.session.commit()
            return jsonify({"ok": True, "field": serialize_custom_field(field)})
        except (ValueError, TypeError) as exc:
            db.session.rollback(); return jsonify({"error": str(exc)}), 400

    @bp.post("/api/settings/fields/<int:field_id>/options")
    def api_add_field_option(field_id: int):
        if (error := require_admin()): return error
        field = db.session.get(CustomField, field_id)
        if field is None: return jsonify({"error": "Alan bulunamadı."}), 404
        data = request.get_json(silent=True) or {}
        label = str(data.get("label", "")).strip(); value = str(data.get("value", label)).strip().lower().replace(" ", "_")
        if not label or not value: return jsonify({"error": "Seçenek adı zorunludur."}), 400
        if CustomFieldOption.query.filter_by(field_id=field_id, value=value).first(): return jsonify({"error": "Bu seçenek zaten mevcut."}), 409
        option = CustomFieldOption(field_id=field_id, label=label, value=value, sort_order=int(data.get("sort_order", 0) or 0)); db.session.add(option)
        audit("ozel_alan_secenegi_ekle", f"{field.label}: {label} seçeneği eklendi."); db.session.commit()
        return jsonify({"ok": True, "id": option.id, "label": option.label, "value": option.value})

    @bp.patch("/api/settings/fields/options/<int:option_id>")
    def api_toggle_field_option(option_id: int):
        if (error := require_admin()): return error
        option = db.session.get(CustomFieldOption, option_id)
        if option is None: return jsonify({"error": "Alan seçeneği bulunamadı."}), 404
        data = request.get_json(silent=True) or {}; option.active = _bool(data.get("active"), True)
        audit("ozel_alan_secenegi_durum", f"{option.label} alan seçeneği {'aktif' if option.active else 'pasif'} yapıldı."); db.session.commit()
        return jsonify({"ok": True, "active": option.active})

    @bp.post("/api/settings/groups")
    def api_add_group():
        if (error := require_admin()): return error
        data = request.get_json(silent=True) or {}
        entity_type = str(data.get("entity_type", "inventory")).strip() or "inventory"
        key = str(data.get("key", "")).strip(); label = str(data.get("label", "")).strip()
        if not key or not label: return jsonify({"error": "Grup anahtarı ve adı zorunludur."}), 400
        if FieldGroup.query.filter_by(entity_type=entity_type, key=key).first(): return jsonify({"error": "Bu grup zaten mevcut."}), 409
        group = FieldGroup(entity_type=entity_type, key=key, label=label, description=str(data.get("description", "")).strip() or None, sort_order=int(data.get("sort_order", 0) or 0))
        db.session.add(group); audit("alan_grubu_ekle", f"{label} alan grubu oluşturuldu."); db.session.commit()
        return jsonify({"ok": True, "group": {"id": group.id, "key": group.key, "label": group.label}})

    @bp.get("/api/settings/schema/<string:entity_type>")
    def api_schema(entity_type: str):
        if (error := require_admin()): return error
        return jsonify({"entity_type": entity_type, "entity_label": entity_type, "groups": serialize_groups(entity_type), "fields": build_form_schema(entity_type)})

    @bp.get("/api/settings/widgets")
    def api_widgets():
        if (error := require_admin()): return error
        return jsonify([{ "id": w.id, "key": w.widget_key, "label": w.label, "type": w.widget_type, "config": w.config_json, "active": w.active, "sort_order": w.sort_order } for w in DashboardWidget.query.order_by(DashboardWidget.sort_order, DashboardWidget.id)])

    @bp.post("/api/settings/widgets")
    def api_add_widget():
        if (error := require_admin()): return error
        data = request.get_json(silent=True) or {}
        key = str(data.get("key", "")).strip(); label = str(data.get("label", "")).strip()
        if not key or not label: return jsonify({"error": "Widget anahtarı ve adı zorunludur."}), 400
        if DashboardWidget.query.filter_by(widget_key=key).first(): return jsonify({"error": "Bu widget zaten mevcut."}), 409
        widget = DashboardWidget(widget_key=key, label=label, widget_type=str(data.get("type", "metric")), config_json=data.get("config") or {}, sort_order=int(data.get("sort_order", 0) or 0))
        db.session.add(widget); audit("dashboard_widget_ekle", f"{label} dashboard widget oluşturuldu."); db.session.commit()
        return jsonify({"ok": True, "id": widget.id})

    @bp.patch("/api/settings/widgets/<int:widget_id>")
    def api_update_widget(widget_id: int):
        if (error := require_admin()): return error
        widget = db.session.get(DashboardWidget, widget_id)
        if widget is None: return jsonify({"error": "Widget bulunamadı."}), 404
        data = request.get_json(silent=True) or {}
        if "label" in data: widget.label = str(data["label"]).strip()
        if "active" in data: widget.active = _bool(data["active"])
        if "sort_order" in data: widget.sort_order = int(data["sort_order"])
        if "config" in data: widget.config_json = data["config"] or {}
        audit("dashboard_widget_guncelle", f"{widget.label} dashboard widget güncellendi."); db.session.commit()
        return jsonify({"ok": True})

    app.register_blueprint(bp)
