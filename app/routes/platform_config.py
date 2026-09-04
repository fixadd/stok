from __future__ import annotations

import json

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from ..models import db


def register_platform_config_routes(app, deps):
    get_active_user = deps["get_active_user"]
    has_system_role = deps["has_system_role"]
    bp = Blueprint("platform_config", __name__)

    def admin_error():
        user = get_active_user()
        if not has_system_role(user, "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403
        return None

    @bp.get("/api/platform/rules")
    def list_rules():
        if (error := admin_error()): return error
        rows = db.session.execute(text("SELECT id, entity_type, field_key, rule_type, rule_json, active, sort_order FROM configuration_rules ORDER BY entity_type, sort_order, id")).mappings().all()
        return jsonify([dict(row) for row in rows])

    @bp.post("/api/platform/rules")
    def create_rule():
        if (error := admin_error()): return error
        data = request.get_json(silent=True) or {}
        entity = str(data.get("entity_type", "")).strip(); field = str(data.get("field_key", "")).strip(); rule_type = str(data.get("rule_type", "")).strip()
        if not entity or not field or not rule_type: return jsonify({"error": "entity_type, field_key ve rule_type zorunludur."}), 400
        row = db.session.execute(text("INSERT INTO configuration_rules(entity_type, field_key, rule_type, rule_json, active, sort_order) VALUES (:entity,:field,:rule_type,CAST(:rule AS jsonb),:active,:sort_order) RETURNING id"), {"entity": entity, "field": field, "rule_type": rule_type, "rule": json.dumps(data.get("rule") or {}), "active": bool(data.get("active", True)), "sort_order": int(data.get("sort_order", 0) or 0)}).scalar_one()
        db.session.commit(); return jsonify({"ok": True, "id": row}), 201

    @bp.get("/api/platform/dependencies")
    def list_dependencies():
        if (error := admin_error()): return error
        rows = db.session.execute(text("SELECT id, parent_key, child_key, mapping_json, active FROM lookup_dependencies ORDER BY id")).mappings().all()
        return jsonify([dict(row) for row in rows])

    @bp.post("/api/platform/dependencies")
    def create_dependency():
        if (error := admin_error()): return error
        data = request.get_json(silent=True) or {}
        parent = str(data.get("parent_key", "")).strip(); child = str(data.get("child_key", "")).strip()
        if not parent or not child or parent == child: return jsonify({"error": "Geçerli üst ve alt seçim alanları gerekir."}), 400
        db.session.execute(text("INSERT INTO lookup_dependencies(parent_key, child_key, mapping_json, active) VALUES (:parent_key,:child_key,CAST(:mapping AS jsonb),:active) ON CONFLICT (parent_key,child_key) DO UPDATE SET mapping_json=EXCLUDED.mapping_json, active=EXCLUDED.active, updated_at=CURRENT_TIMESTAMP"), {"parent_key": parent, "child_key": child, "mapping": json.dumps(data.get("mapping") or {}), "active": bool(data.get("active", True))})
        db.session.commit(); return jsonify({"ok": True})

    @bp.get("/api/platform/reports")
    def list_reports():
        if (error := admin_error()): return error
        rows = db.session.execute(text("SELECT id, key, label, entity_type, definition_json, active FROM report_definitions ORDER BY label, id")).mappings().all()
        return jsonify([dict(row) for row in rows])

    @bp.post("/api/platform/reports")
    def create_report():
        if (error := admin_error()): return error
        data = request.get_json(silent=True) or {}
        key = str(data.get("key", "")).strip(); label = str(data.get("label", "")).strip(); entity = str(data.get("entity_type", "")).strip()
        if not key or not label or not entity: return jsonify({"error": "Rapor anahtarı, adı ve modülü zorunludur."}), 400
        try:
            row = db.session.execute(text("INSERT INTO report_definitions(key,label,entity_type,definition_json,active) VALUES (:key,:label,:entity,CAST(:definition AS jsonb),:active) RETURNING id"), {"key": key, "label": label, "entity": entity, "definition": json.dumps(data.get("definition") or {}), "active": bool(data.get("active", True))}).scalar_one()
            db.session.commit()
        except Exception:
            db.session.rollback(); return jsonify({"error": "Rapor oluşturulamadı."}), 400
        return jsonify({"ok": True, "id": row}), 201

    @bp.get("/api/platform/notifications")
    def list_notifications():
        if (error := admin_error()): return error
        rows = db.session.execute(text("SELECT id, key, label, event_key, channel, target_json, condition_json, active FROM notification_rules ORDER BY label, id")).mappings().all()
        return jsonify([dict(row) for row in rows])

    @bp.post("/api/platform/notifications")
    def create_notification():
        if (error := admin_error()): return error
        data = request.get_json(silent=True) or {}
        key = str(data.get("key", "")).strip(); label = str(data.get("label", "")).strip(); event_key = str(data.get("event_key", "")).strip()
        if not key or not label or not event_key: return jsonify({"error": "Bildirim anahtarı, adı ve olay anahtarı zorunludur."}), 400
        try:
            row = db.session.execute(text("INSERT INTO notification_rules(key,label,event_key,channel,target_json,condition_json,active) VALUES (:key,:label,:event_key,:channel,CAST(:target AS jsonb),CAST(:condition AS jsonb),:active) RETURNING id"), {"key": key, "label": label, "event_key": event_key, "channel": str(data.get("channel", "web")), "target": json.dumps(data.get("target") or {}), "condition": json.dumps(data.get("condition") or {}), "active": bool(data.get("active", True))}).scalar_one()
            db.session.commit()
        except Exception:
            db.session.rollback(); return jsonify({"error": "Bildirim kuralı oluşturulamadı."}), 400
        return jsonify({"ok": True, "id": row}), 201


    @bp.get("/api/platform/reports/<string:key>/data")
    def report_data(key):
        if (error := admin_error()): return error
        row = db.session.execute(text("SELECT key, label, entity_type, definition_json FROM report_definitions WHERE key=:key AND active=TRUE"), {"key": key}).mappings().first()
        if row is None: return jsonify({"error": "Rapor bulunamadı."}), 404
        definition = row["definition_json"] or {}
        allowed = {"inventory": ("inventory_items", ["id", "inventory_no", "brand", "model", "status"]), "stock": ("stock_items", ["id", "title", "category", "quantity", "status"])}
        if row["entity_type"] not in allowed: return jsonify({"error": "Bu rapor tipi henüz desteklenmiyor."}), 400
        table, default_columns = allowed[row["entity_type"]]
        columns = [x for x in (definition.get("columns") or default_columns) if x in default_columns] or default_columns
        rows = db.session.execute(text("SELECT " + ", ".join(columns) + " FROM " + table + " ORDER BY id DESC LIMIT 500")).mappings().all()
        return jsonify({"report": {"key": row["key"], "label": row["label"], "columns": columns}, "rows": [dict(item) for item in rows]})

    @bp.post("/api/platform/notifications/dispatch")
    def dispatch_notification():
        if (error := admin_error()): return error
        data = request.get_json(silent=True) or {}
        event_key = str(data.get("event_key", "")).strip()
        if not event_key: return jsonify({"error": "event_key zorunludur."}), 400
        rows = db.session.execute(text("SELECT key, label, channel, target_json FROM notification_rules WHERE active=TRUE AND event_key=:event_key"), {"event_key": event_key}).mappings().all()
        return jsonify({"ok": True, "event_key": event_key, "matched_rules": [dict(row) for row in rows]})

    app.register_blueprint(bp)
