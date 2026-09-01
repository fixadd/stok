from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request

from ..services.authz import get_active_user, has_system_role



def register_assignment_routes(app, helpers):
    assignment_bp = Blueprint("assignment", __name__)
    db = helpers["db"]
    InventoryItem = helpers["InventoryItem"]
    InventoryAssignment = helpers["InventoryAssignment"]
    User = helpers["User"]
    Factory = helpers["Factory"]

    active_user_by_id = helpers["active_user_by_id"]
    parse_int_or_none = helpers["parse_int_or_none"]
    sanitize_input_text = helpers["sanitize_input_text"]
    format_datetime_display = helpers["format_datetime_display"]

    serialize_inventory_item = helpers["serialize_inventory_item"]
    get_inventory_item_with_relations = helpers[
        "get_inventory_item_with_relations"
    ]
    add_inventory_event = helpers["add_inventory_event"]

    current_actor_name = helpers["current_actor_name"]
    DEFAULT_EVENT_ACTOR = helpers["DEFAULT_EVENT_ACTOR"]
    json_error = helpers["json_error"]

    def require_admin():
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403
        return None

    @assignment_bp.post("/api/inventory/<int:item_id>/assign")
    def assign_inventory(item_id: int):
        denied = require_admin()
        if denied:
            return denied

        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        factory_id = parse_int_or_none(data.get("factory_id"))
        responsible_user_id = parse_int_or_none(data.get("responsible_user_id"))
        department = sanitize_input_text(data.get("department"))
        note = sanitize_input_text(data.get("note"))
        delivered_by = sanitize_input_text(data.get("delivered_by"))

        factory = Factory.query.get(factory_id) if factory_id else None
        responsible_user = (
            active_user_by_id(responsible_user_id) if responsible_user_id else None
        )

        if not factory:
            return json_error("Geçerli bir fabrika seçin."), 400
        if responsible_user_id and not responsible_user:
            return json_error("Geçerli bir kullanıcı seçin."), 400
        if not department:
            return json_error("Departman alanı zorunludur."), 400

        now = datetime.utcnow()
        open_assignments = (
            InventoryAssignment.query
            .filter(
                InventoryAssignment.item_id == item.id,
                InventoryAssignment.returned_at.is_(None),
            )
            .all()
        )
        for old_assignment in open_assignments:
            old_assignment.returned_at = now
            if item.responsible_user_id:
                old_assignment.returned_to_user_id = item.responsible_user_id

        responsible_name = (
            f"{responsible_user.first_name} {responsible_user.last_name}"
            if responsible_user
            else "Atanmamış"
        )
        actor = delivered_by or current_actor_name() or DEFAULT_EVENT_ACTOR

        assignment = InventoryAssignment(
            item_id=item.id,
            assigned_user_id=responsible_user.id if responsible_user else None,
            assigned_to=responsible_name,
            assigned_department=department,
            assigned_factory_id=factory.id,
            assigned_at=now,
            delivered_by=actor,
            note=note,
        )
        db.session.add(assignment)
        item.factory = factory
        item.department = department
        item.responsible_user = responsible_user

        if "related_machine_no" in data:
            item.related_machine_no = (data.get("related_machine_no") or "").strip() or None

        note_parts = [
            f"Fabrika: {factory.name}",
            f"Departman: {department}",
            f"Sorumlu: {responsible_name}",
        ]
        if note:
            note_parts.append(f"Not: {note}")
        add_inventory_event(item, "Zimmet ataması yapıldı", " • ".join(note_parts))
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    @assignment_bp.get("/api/inventory/<int:item_id>/assignments")
    def get_inventory_assignments(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404
        assignments = (
            InventoryAssignment.query
            .filter(InventoryAssignment.item_id == item.id)
            .order_by(InventoryAssignment.assigned_at.desc())
            .all()
        )
        return jsonify({
            "assignments": [
                {
                    "id": assignment.id,
                    "item_id": assignment.item_id,
                    "assigned_user_id": assignment.assigned_user_id,
                    "assigned_to": assignment.assigned_to,
                    "assigned_department": assignment.assigned_department or "",
                    "assigned_factory_id": assignment.assigned_factory_id,
                    "assigned_factory": assignment.assigned_factory.name if assignment.assigned_factory else "",
                    "assigned_at": format_datetime_display(assignment.assigned_at),
                    "returned_at": format_datetime_display(assignment.returned_at) if assignment.returned_at else "",
                    "returned_to_user_id": assignment.returned_to_user_id,
                    "returned_to_user": (
                        f"{assignment.returned_to_user.first_name} {assignment.returned_to_user.last_name}"
                        if assignment.returned_to_user else ""
                    ),
                    "delivered_by": assignment.delivered_by or "",
                    "note": assignment.note or "",
                    "active": assignment.returned_at is None,
                }
                for assignment in assignments
            ]
        })

    @assignment_bp.post("/api/inventory/<int:item_id>/return")
    def return_inventory_assignment(item_id: int):
        denied = require_admin()
        if denied:
            return denied

        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404
        assignment = (
            InventoryAssignment.query
            .filter(
                InventoryAssignment.item_id == item.id,
                InventoryAssignment.returned_at.is_(None),
            )
            .order_by(InventoryAssignment.assigned_at.desc())
            .first()
        )
        if assignment is None:
            return json_error("Bu envanter için aktif zimmet bulunamadı."), 400

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400
        note = sanitize_input_text(data.get("note"))
        returned_to_user_id = parse_int_or_none(data.get("returned_to_user_id"))
        returned_to_user = (
            active_user_by_id(returned_to_user_id) if returned_to_user_id else None
        )
        if returned_to_user_id and not returned_to_user:
            return json_error("Geçerli bir kullanıcı seçin."), 400

        assignment.returned_at = datetime.utcnow()
        assignment.returned_to_user_id = returned_to_user.id if returned_to_user else None
        if note:
            assignment.note = note
        item.responsible_user = None
        add_inventory_event(
            item,
            "Zimmet iade edildi",
            note or f"İade edilen kişi: {assignment.assigned_to}",
        )
        db.session.commit()
        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    @assignment_bp.get("/api/users/<int:user_id>/inventory")
    def get_user_inventory_assignments(user_id: int):
        user = active_user_by_id(user_id)
        if user is None:
            return json_error("Kullanıcı bulunamadı."), 404
        assignments = (
            InventoryAssignment.query
            .filter(
                InventoryAssignment.assigned_user_id == user.id,
                InventoryAssignment.returned_at.is_(None),
            )
            .order_by(InventoryAssignment.assigned_at.desc())
            .all()
        )
        result = []
        for assignment in assignments:
            item = assignment.item
            result.append({
                "assignment_id": assignment.id,
                "inventory_id": item.id,
                "inventory_no": item.inventory_no,
                "computer_name": item.computer_name or "",
                "serial_no": item.serial_no or "",
                "brand": item.brand.name if item.brand else "",
                "model": item.model.name if item.model else "",
                "factory": assignment.assigned_factory.name if assignment.assigned_factory else "",
                "department": assignment.assigned_department or "",
                "assigned_at": format_datetime_display(assignment.assigned_at),
                "note": assignment.note or "",
            })
        return jsonify({
            "user": {
                "id": user.id,
                "name": f"{user.first_name} {user.last_name}",
            },
            "assignments": result,
            "count": len(result),
        })

    app.register_blueprint(assignment_bp)
