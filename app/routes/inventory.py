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

    @inventory_bp.post("/api/inventory/<int:item_id>/stock")
    def move_inventory_to_stock(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        note = sanitize_input_text(data.get("note"), max_length=512)
        actor = sanitize_input_text(data.get("performed_by")) or DEFAULT_EVENT_ACTOR

        existing_stock = (
            StockItem.query.options(
                joinedload(StockItem.inventory_item).joinedload(
                    InventoryItem.hardware_type
                ),
                joinedload(StockItem.inventory_item).joinedload(InventoryItem.factory),
                joinedload(StockItem.inventory_item).joinedload(InventoryItem.brand),
                joinedload(StockItem.inventory_item).joinedload(InventoryItem.model),
                joinedload(StockItem.logs),
            )
            .filter(StockItem.inventory_item_id == item.id)
            .order_by(StockItem.id.desc())
            .first()
        )

        if existing_stock and existing_stock.status == "stokta":
            return json_error("Bu envanter kaydı zaten stokta."), 409

        category_value = determine_stock_category_from_inventory(item)
        if existing_stock:
            category_value = normalize_stock_category(
                existing_stock.category, fallback=category_value
            )

        item.status = "stokta"
        add_inventory_event(item, "Stok girişi", note, performed_by=actor)

        log_entry = None
        if existing_stock:
            metadata_payload = build_inventory_stock_metadata(item)
            metadata_payload = remove_assignment_only_metadata(
                metadata_payload, category_value
            )
            existing_stock.status = "stokta"
            existing_stock.quantity = 1
            existing_stock.reference_code = item.inventory_no
            existing_stock.source_type = "inventory"
            existing_stock.inventory_item = item
            if note:
                existing_stock.note = note
            existing_stock.metadata_payload = {
                key: value for key, value in metadata_payload.items() if value
            }
            log_entry = record_stock_log(
                existing_stock,
                "Envanter stoğa geri alındı",
                action_type="in",
                performed_by=actor,
                quantity_change=0,
                note=note,
                metadata={"inventory_no": item.inventory_no},
            )
            stock_item = existing_stock
        else:
            stock_item = create_stock_item_from_inventory(
                item,
                note=note,
                actor=actor,
            )

        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        payload: dict[str, Any] = {"item": serialize_inventory_item(fresh_item)}
        if stock_item:
            fresh_stock = get_stock_item_with_relations(stock_item.id)
            if fresh_stock:
                payload["stock_item"] = serialize_stock_item(fresh_stock)
                if log_entry:
                    payload["log"] = serialize_stock_log(log_entry)
                elif fresh_stock.logs:
                    payload["log"] = serialize_stock_log(fresh_stock.logs[0])
        return jsonify(payload)

    @inventory_bp.post("/api/inventory/<int:item_id>/scrap")
    def scrap_inventory(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        note = sanitize_input_text(data.get("note"), max_length=512)
        item.status = "hurda"
        if note:
            item.note = note
        add_inventory_event(item, "Hurdaya ayırma", note)
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    @inventory_bp.post("/api/licenses/<int:license_id>/stock")
    def move_license_to_stock(license_id: int):
        license = (
            InventoryLicense.query.options(
                joinedload(InventoryLicense.item)
                .joinedload(InventoryItem.factory)
                .joinedload(InventoryItem.hardware_type),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.brand),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.model),
                joinedload(InventoryLicense.item).joinedload(
                    InventoryItem.responsible_user
                ),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.events),
            )
            .filter_by(id=license_id)
            .first()
        )
        if license is None:
            return json_error("Lisans kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        note = sanitize_input_text(data.get("note"), max_length=512)
        actor = sanitize_input_text(data.get("performed_by")) or DEFAULT_EVENT_ACTOR

        associated_item = license.item
        stock_item = create_stock_item_from_license(license, note=note, actor=actor)

        license.status = "pasif"
        license.item = None

        if associated_item:
            add_inventory_event(
                associated_item,
                "Lisans stoklandı",
                note or f"{license.name} lisansı stok listesine taşındı.",
                performed_by=actor,
            )

        fresh_license = (
            InventoryLicense.query.options(
                joinedload(InventoryLicense.item).joinedload(
                    InventoryItem.responsible_user
                ),
                joinedload(InventoryLicense.item).joinedload(
                    InventoryItem.hardware_type
                ),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.factory),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.events),
            )
            .filter_by(id=license.id)
            .first()
        )
        response: dict[str, Any] = {
            "message": "Lisans stok listesine taşındı.",
            "license": (
                serialize_license_record(fresh_license) if fresh_license else None
            ),
        }
        fresh_stock = get_stock_item_with_relations(stock_item.id)
        if fresh_stock:
            response["stock_item"] = serialize_stock_item(fresh_stock)
            if fresh_stock.logs:
                response["log"] = serialize_stock_log(fresh_stock.logs[0])
        return jsonify(response)

    @inventory_bp.post("/api/stock")
    def create_stock_entry():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        title = sanitize_input_text(data.get("title"))
        if not title:
            return json_error("Stok adı zorunludur."), 400

        category = normalize_stock_category(data.get("category"))
        quantity = parse_int_or_none(data.get("quantity"))
        if quantity is None:
            quantity = 1
        if quantity < 1:
            return json_error("Miktar en az 1 olmalıdır."), 400
        note = sanitize_input_text(data.get("note"), max_length=512)
        actor = sanitize_input_text(data.get("performed_by")) or DEFAULT_EVENT_ACTOR
        reference_code = sanitize_input_text(data.get("reference_code")) or None
        unit = sanitize_input_text(data.get("unit"), max_length=32) or None
        serial_no = sanitize_input_text(data.get("serial_no"), max_length=128) or None
        warranty_end_date = parse_excel_date(data.get("warranty_end_date"))

        try:
            metadata_payload = prepare_stock_metadata(
                category,
                sanitize_metadata_payload(data.get("metadata")),
                include_assignment_fields=False,
            )
        except ValueError as exc:
            return json_error(str(exc)), 400

        if not reference_code:
            reference_code = (
                metadata_payload.get("inventory_no")
                or metadata_payload.get("license_key")
                or None
            )

        active_user = get_active_user()
        category_ref = resolve_stock_category(category)
        unit_ref = resolve_stock_unit(unit)
        stock_item = StockItem(
            source_type="manual",
            title=title,
            category=category,
            category_id=category_ref.id if category_ref else None,
            quantity=quantity,
            status="stokta",
            reference_code=reference_code,
            unit=unit,
            unit_id=unit_ref.id if unit_ref else None,
            note=note or None,
            sku=generate_unique_sku("STK"),
            serial_no=serial_no,
            warranty_end_date=warranty_end_date,
        )
        stock_item.metadata_payload = {
            k: v for k, v in metadata_payload.items() if v
        }
        db.session.add(stock_item)
        db.session.flush()

        log_entry = record_stock_log(
            stock_item,
            "Manuel stok girişi",
            action_type="in",
            performed_by=actor,
            quantity_change=stock_item.quantity,
            note=note,
        )
        record_stock_movement(
            stock_item,
            operation_type="giris",
            old_quantity=0,
            new_quantity=stock_item.quantity,
            user=active_user,
        )
        record_stock_audit(
            stock_item,
            old_quantity=0,
            new_quantity=stock_item.quantity,
            performed_by=actor,
        )

        fresh_item = get_stock_item_with_relations(stock_item.id)
        response_payload: dict[str, Any] = {
            "stock_item": serialize_stock_item(fresh_item)
        }
        if log_entry:
            response_payload["log"] = serialize_stock_log(log_entry)
        return jsonify(response_payload), 201




    app.register_blueprint(inventory_bp)
