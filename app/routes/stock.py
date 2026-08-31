from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy.orm import joinedload


stock_bp = Blueprint("stock", __name__)


def register_stock_routes(app, deps):
    get_active_user = deps["get_active_user"]
    has_system_role = deps["has_system_role"]

    load_stock_payload = deps["load_stock_payload"]
    load_scrap_inventory_payload = deps["load_scrap_inventory_payload"]


    db = deps["db"]
    InventoryItem = deps["InventoryItem"]
    InventoryLicense = deps["InventoryLicense"]
    StockItem = deps["StockItem"]

    get_inventory_item_with_relations = deps["get_inventory_item_with_relations"]
    add_inventory_event = deps["add_inventory_event"]

    determine_stock_category_from_inventory = deps["determine_stock_category_from_inventory"]
    build_inventory_stock_metadata = deps["build_inventory_stock_metadata"]
    create_stock_item_from_inventory = deps["create_stock_item_from_inventory"]
    create_stock_item_from_license = deps["create_stock_item_from_license"]

    get_stock_item_with_relations = deps["get_stock_item_with_relations"]
    serialize_stock_item = deps["serialize_stock_item"]
    serialize_stock_log = deps["serialize_stock_log"]
    serialize_license_record = deps["serialize_license_record"]

    record_stock_log = deps["record_stock_log"]
    record_stock_movement = deps["record_stock_movement"]
    record_stock_audit = deps["record_stock_audit"]

    prepare_stock_metadata = deps["prepare_stock_metadata"]
    sanitize_metadata_payload = deps["sanitize_metadata_payload"]
    remove_assignment_only_metadata = deps["remove_assignment_only_metadata"]

    normalize_stock_category = deps["normalize_stock_category"]
    resolve_stock_category = deps["resolve_stock_category"]
    resolve_stock_unit = deps["resolve_stock_unit"]

    generate_unique_sku = deps["generate_unique_sku"]
    parse_excel_date = deps["parse_excel_date"]
    parse_int_or_none = deps["parse_int_or_none"]
    sanitize_input_text = deps["sanitize_input_text"]
    json_error = deps["json_error"]

    DEFAULT_EVENT_ACTOR = deps["DEFAULT_EVENT_ACTOR"]

    @stock_bp.route("/stok-takip")
    def stock_tracking():
        payload = load_stock_payload()
        return render_template(
            "stock_tracking.html",
            active_page="stock_tracking",
            can_manage_stock_data=has_system_role(
                get_active_user(),
                "admin",
            ),
            **payload,
        )

    @stock_bp.route("/hurdalar")
    def scrap_inventory_page():
        payload = load_scrap_inventory_payload()
        can_restore = has_system_role(
            get_active_user(),
            "superadmin",
        )
        return render_template(
            "scrap_inventory.html",
            active_page="scrap_inventory",
            can_restore_scrap=can_restore,
            **payload,
        )

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

    app.register_blueprint(stock_bp)
