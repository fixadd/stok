from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request


inventory_bp = Blueprint("inventory", __name__)


def register_inventory_routes(app, helpers):
    db = helpers["db"]
    InventoryItem = helpers["InventoryItem"]
    InventoryAssignment = helpers["InventoryAssignment"]
    InventoryMaintenance = helpers["InventoryMaintenance"]
    InventoryLicense = helpers["InventoryLicense"]
    StockItem = helpers["StockItem"]
    User = helpers["User"]
    Factory = helpers["Factory"]
    HardwareType = helpers["HardwareType"]
    Brand = helpers["Brand"]
    HardwareModel = helpers["HardwareModel"]

    serialize_inventory_item = helpers["serialize_inventory_item"]
    serialize_maintenance_record = helpers["serialize_maintenance_record"]
    get_inventory_item_with_relations = helpers["get_inventory_item_with_relations"]
    add_inventory_event = helpers["add_inventory_event"]
    determine_stock_category_from_inventory = helpers["determine_stock_category_from_inventory"]
    build_inventory_stock_metadata = helpers["build_inventory_stock_metadata"]
    create_stock_item_from_inventory = helpers["create_stock_item_from_inventory"]

    @inventory_bp.post("/api/inventory")
    def create_inventory():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        inventory_no = (data.get("inventory_no") or "").strip()
        if not inventory_no:
            return json_error("Envanter numarası zorunludur."), 400

        existing = InventoryItem.query.filter_by(inventory_no=inventory_no).first()
        if existing:
            return json_error("Bu envanter numarası zaten kullanılıyor."), 409

        factory_id = parse_int_or_none(data.get("factory_id"))
        hardware_type_id = parse_int_or_none(data.get("hardware_type_id"))
        brand_id = parse_int_or_none(data.get("brand_id"))
        model_id = parse_int_or_none(data.get("model_id"))
        responsible_user_id = parse_int_or_none(data.get("responsible_user_id"))

        factory = Factory.query.get(factory_id) if factory_id else None
        hardware_type = (
            HardwareType.query.get(hardware_type_id) if hardware_type_id else None
        )
        brand = Brand.query.get(brand_id) if brand_id else None
        model = HardwareModel.query.get(model_id) if model_id else None
        responsible_user = (
            active_user_by_id(responsible_user_id) if responsible_user_id else None
        )

        if not factory:
            return json_error("Geçerli bir fabrika seçin."), 400
        if not hardware_type:
            return json_error("Geçerli bir donanım tipi seçin."), 400
        if not brand:
            return json_error("Geçerli bir marka seçin."), 400
        if not model:
            return json_error("Geçerli bir model seçin."), 400
        if responsible_user_id and not responsible_user:
            return json_error("Geçerli bir kullanıcı seçin."), 400

        department = sanitize_input_text(data.get("department"))
        if not department:
            return json_error("Departman alanı zorunludur."), 400

        item = InventoryItem(
            inventory_no=inventory_no,
            computer_name=(data.get("computer_name") or "").strip() or None,
            factory_id=factory_id,
            department=department,
            hardware_type_id=hardware_type_id,
            responsible_user_id=responsible_user_id,
            brand_id=brand_id,
            model_id=model_id,
            serial_no=(data.get("serial_no") or "").strip() or None,
            ifs_no=(data.get("ifs_no") or "").strip() or None,
            related_machine_no=(data.get("related_machine_no") or "").strip() or None,
            note=(data.get("note") or "").strip() or None,
        )
        db.session.add(item)
        db.session.flush()
        add_inventory_event(item, "Envanter oluşturuldu")
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return (
            jsonify({"item": serialize_inventory_item(fresh_item)}),
            201,
        )

    @inventory_bp.patch("/api/inventory/<int:item_id>")
    def update_inventory(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        inventory_no = (data.get("inventory_no") or item.inventory_no or "").strip()
        if not inventory_no:
            return json_error("Envanter numarası zorunludur."), 400

        if (
            inventory_no != item.inventory_no
            and InventoryItem.query.filter_by(inventory_no=inventory_no).first()
        ):
            return json_error("Bu envanter numarası zaten kullanılıyor."), 409

        factory_id = parse_int_or_none(data.get("factory_id"))
        hardware_type_id = parse_int_or_none(data.get("hardware_type_id"))
        brand_id = parse_int_or_none(data.get("brand_id"))
        model_id = parse_int_or_none(data.get("model_id"))
        responsible_user_id = parse_int_or_none(data.get("responsible_user_id"))

        factory = Factory.query.get(factory_id) if factory_id else None
        hardware_type = (
            HardwareType.query.get(hardware_type_id) if hardware_type_id else None
        )
        brand = Brand.query.get(brand_id) if brand_id else None
        model = HardwareModel.query.get(model_id) if model_id else None
        responsible_user = (
            active_user_by_id(responsible_user_id) if responsible_user_id else None
        )

        if not factory:
            return json_error("Geçerli bir fabrika seçin."), 400
        if not hardware_type:
            return json_error("Geçerli bir donanım tipi seçin."), 400
        if not brand:
            return json_error("Geçerli bir marka seçin."), 400
        if not model:
            return json_error("Geçerli bir model seçin."), 400
        if responsible_user_id and not responsible_user:
            return json_error("Geçerli bir kullanıcı seçin."), 400

        department = sanitize_input_text(data.get("department"))
        if not department:
            return json_error("Departman alanı zorunludur."), 400

        status = (data.get("status") or item.status or "aktif").strip().lower()
        if status not in INVENTORY_STATUSES:
            return json_error("Geçersiz durum değeri."), 400

        item.inventory_no = inventory_no
        item.computer_name = (data.get("computer_name") or "").strip() or None
        item.factory = factory
        item.department = department
        item.hardware_type = hardware_type
        item.responsible_user = responsible_user
        item.brand = brand
        item.model = model
        item.serial_no = (data.get("serial_no") or "").strip() or None
        item.ifs_no = (data.get("ifs_no") or "").strip() or None
        if "related_machine_no" in data:
            item.related_machine_no = (
                data.get("related_machine_no") or ""
            ).strip() or None
        if "machine_no" in data:
            item.machine_no = (data.get("machine_no") or "").strip() or None
        item.note = (data.get("note") or "").strip() or None
        item.status = status

        add_inventory_event(item, "Envanter bilgileri güncellendi")
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    @inventory_bp.post("/api/inventory/<int:item_id>/assign")
    def assign_inventory(item_id: int):
        item = get_inventory_item_with_relations(item_id)

        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}

        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        factory_id = parse_int_or_none(data.get("factory_id"))
        responsible_user_id = parse_int_or_none(
            data.get("responsible_user_id")
        )

        department = sanitize_input_text(
            data.get("department")
        )

        note = sanitize_input_text(
            data.get("note")
        )

        delivered_by = sanitize_input_text(
            data.get("delivered_by")
        )

        factory = (
            Factory.query.get(factory_id)
            if factory_id
            else None
        )

        responsible_user = (
            active_user_by_id(responsible_user_id)
            if responsible_user_id
            else None
        )

        if not factory:
            return json_error(
                "Geçerli bir fabrika seçin."
            ), 400

        if responsible_user_id and not responsible_user:
            return json_error(
                "Geçerli bir kullanıcı seçin."
            ), 400

        if not department:
            return json_error(
                "Departman alanı zorunludur."
            ), 400

        now = datetime.utcnow()

        # ====================================================
        # AÇIK ESKİ ZİMMETİ KAPAT
        # ====================================================

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
                old_assignment.returned_to_user_id = (
                    item.responsible_user_id
                )

        # ====================================================
        # YENİ ZİMMET
        # ====================================================

        responsible_name = (
            f"{responsible_user.first_name} "
            f"{responsible_user.last_name}"
            if responsible_user
            else "Atanmamış"
        )

        actor = (
            delivered_by
            or current_actor_name()
            or DEFAULT_EVENT_ACTOR
        )

        assignment = InventoryAssignment(
            item_id=item.id,
            assigned_user_id=(
                responsible_user.id
                if responsible_user
                else None
            ),
            assigned_to=responsible_name,
            assigned_department=department,
            assigned_factory_id=factory.id,
            assigned_at=now,
            delivered_by=actor,
            note=note,
        )

        db.session.add(assignment)

        # ====================================================
        # ENVANTERİN GÜNCEL SORUMLUSU
        # ====================================================

        item.factory = factory
        item.department = department
        item.responsible_user = responsible_user

        if "related_machine_no" in data:
            item.related_machine_no = (
                data.get("related_machine_no") or ""
            ).strip() or None

        note_parts = [
            f"Fabrika: {factory.name}",
            f"Departman: {department}",
            f"Sorumlu: {responsible_name}",
        ]

        if note:
            note_parts.append(
                f"Not: {note}"
            )

        add_inventory_event(
            item,
            "Zimmet ataması yapıldı",
            " • ".join(note_parts),
        )

        db.session.commit()

        fresh_item = get_inventory_item_with_relations(
            item.id
        )

        return jsonify({
            "item": serialize_inventory_item(fresh_item)
        })

    @inventory_bp.get("/api/inventory/<int:item_id>/assignments")
    def get_inventory_assignments(item_id: int):
        item = get_inventory_item_with_relations(item_id)

        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        assignments = (
            InventoryAssignment.query
            .filter(
                InventoryAssignment.item_id == item.id
            )
            .order_by(
                InventoryAssignment.assigned_at.desc()
            )
            .all()
        )

        return jsonify({
            "assignments": [
                {
                    "id": assignment.id,
                    "item_id": assignment.item_id,
                    "assigned_user_id": assignment.assigned_user_id,
                    "assigned_to": assignment.assigned_to,
                    "assigned_department": (
                        assignment.assigned_department or ""
                    ),
                    "assigned_factory_id": (
                        assignment.assigned_factory_id
                    ),
                    "assigned_factory": (
                        assignment.assigned_factory.name
                        if assignment.assigned_factory
                        else ""
                    ),
                    "assigned_at": (
                        format_datetime_display(
                            assignment.assigned_at
                        )
                    ),
                    "returned_at": (
                        format_datetime_display(
                            assignment.returned_at
                        )
                        if assignment.returned_at
                        else ""
                    ),
                    "returned_to_user_id": (
                        assignment.returned_to_user_id
                    ),
                    "returned_to_user": (
                        f"{assignment.returned_to_user.first_name} "
                        f"{assignment.returned_to_user.last_name}"
                        if assignment.returned_to_user
                        else ""
                    ),
                    "delivered_by": (
                        assignment.delivered_by or ""
                    ),
                    "note": assignment.note or "",
                    "active": (
                        assignment.returned_at is None
                    ),
                }
                for assignment in assignments
            ]
        })


    @inventory_bp.post("/api/inventory/<int:item_id>/return")
    def return_inventory_assignment(item_id: int):
        item = get_inventory_item_with_relations(item_id)

        if item is None:
            return json_error(
                "Envanter kaydı bulunamadı."
            ), 404

        assignment = (
            InventoryAssignment.query
            .filter(
                InventoryAssignment.item_id == item.id,
                InventoryAssignment.returned_at.is_(None),
            )
            .order_by(
                InventoryAssignment.assigned_at.desc()
            )
            .first()
        )

        if assignment is None:
            return json_error(
                "Bu envanter için aktif zimmet bulunamadı."
            ), 400

        data = request.get_json(silent=True) or {}

        if not isinstance(data, dict):
            return json_error(
                "Geçersiz JSON gövdesi."
            ), 400

        note = sanitize_input_text(
            data.get("note")
        )

        returned_to_user_id = parse_int_or_none(
            data.get("returned_to_user_id")
        )

        returned_to_user = (
            active_user_by_id(
                returned_to_user_id
            )
            if returned_to_user_id
            else None
        )

        if returned_to_user_id and not returned_to_user:
            return json_error(
                "Geçerli bir kullanıcı seçin."
            ), 400

        now = datetime.utcnow()

        assignment.returned_at = now
        assignment.returned_to_user_id = (
            returned_to_user.id
            if returned_to_user
            else None
        )

        if note:
            assignment.note = note

        # Güncel envanter sorumlusunu temizle
        item.responsible_user = None

        add_inventory_event(
            item,
            "Zimmet iade edildi",
            note or (
                f"İade edilen kişi: "
                f"{assignment.assigned_to}"
            ),
        )

        db.session.commit()

        fresh_item = get_inventory_item_with_relations(
            item.id
        )

        return jsonify({
            "item": serialize_inventory_item(
                fresh_item
            )
        })


    @inventory_bp.get("/api/users/<int:user_id>/inventory")
    def get_user_inventory_assignments(user_id: int):
        user = active_user_by_id(user_id)

        if user is None:
            return json_error(
                "Kullanıcı bulunamadı."
            ), 404

        assignments = (
            InventoryAssignment.query
            .filter(
                InventoryAssignment.assigned_user_id == user.id,
                InventoryAssignment.returned_at.is_(None),
            )
            .order_by(
                InventoryAssignment.assigned_at.desc()
            )
            .all()
        )

        result = []

        for assignment in assignments:
            item = assignment.item

            result.append({
                "assignment_id": assignment.id,
                "inventory_id": item.id,
                "inventory_no": item.inventory_no,
                "computer_name": (
                    item.computer_name or ""
                ),
                "serial_no": (
                    item.serial_no or ""
                ),
                "brand": (
                    item.brand.name
                    if item.brand
                    else ""
                ),
                "model": (
                    item.model.name
                    if item.model
                    else ""
                ),
                "factory": (
                    assignment.assigned_factory.name
                    if assignment.assigned_factory
                    else ""
                ),
                "department": (
                    assignment.assigned_department
                    or ""
                ),
                "assigned_at": (
                    format_datetime_display(
                        assignment.assigned_at
                    )
                ),
                "note": assignment.note or "",
            })

        return jsonify({
            "user": {
                "id": user.id,
                "name": (
                    f"{user.first_name} "
                    f"{user.last_name}"
                ),
            },
            "assignments": result,
            "count": len(result),
        })


    @inventory_bp.post("/api/inventory/<int:item_id>/mark-faulty")
    def mark_inventory_faulty(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        reason = (data.get("reason") or "").strip()
        location = (data.get("location") or "").strip()
        note_parts = []
        if reason:
            note_parts.append(f"Arıza Nedeni: {reason}")
        if location:
            note_parts.append(f"Gönderildiği Yer: {location}")

        item.status = "arizali"
        add_inventory_event(item, "Arıza bildirimi", " • ".join(note_parts))
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    

    

    

    













app.register_blueprint(inventory_bp)
