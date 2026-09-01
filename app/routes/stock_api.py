from __future__ import annotations

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from ..models import InventoryItem, StockItem, db
from ..services.authz import current_actor_name, get_active_user, has_system_role
from ..utils.parsing import parse_excel_date, parse_int_or_none, sanitize_input_text, sanitize_metadata_payload



def register_stock_api_routes(app):
    stock_api_bp = Blueprint("stock_api", __name__)

    def require_admin():
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403
        return None

    @stock_api_bp.post("/api/inventory/<int:item_id>/stock")
    def move_inventory_to_stock_api(item_id: int):
        denied = require_admin()
        if denied:
            return denied

        from .. import (
            build_inventory_stock_metadata,
            create_stock_item_from_inventory,
            determine_stock_category_from_inventory,
            get_inventory_item_with_relations,
            get_stock_item_with_relations,
            remove_assignment_only_metadata,
            normalize_stock_category,
            record_stock_log,
            serialize_inventory_item,
            serialize_stock_item,
            serialize_stock_log,
        )

        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return jsonify({"error": "Envanter kaydı bulunamadı."}), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400

        note = sanitize_input_text(data.get("note"), max_length=512)
        actor = sanitize_input_text(data.get("performed_by"), max_length=128) or current_actor_name() or "Sistem"

        existing_stock = (
            StockItem.query
            .filter(StockItem.inventory_item_id == item.id)
            .order_by(StockItem.id.desc())
            .first()
        )

        if existing_stock and existing_stock.status == "stokta":
            return jsonify({"error": "Bu envanter kaydı zaten stokta."}), 409

        category_value = determine_stock_category_from_inventory(item)
        if existing_stock:
            category_value = normalize_stock_category(existing_stock.category, fallback=category_value)

        item.status = "stokta"
        if existing_stock:
            metadata = remove_assignment_only_metadata(build_inventory_stock_metadata(item), category_value)
            existing_stock.status = "stokta"
            existing_stock.quantity = 1
            existing_stock.reference_code = item.inventory_no
            existing_stock.source_type = "inventory"
            existing_stock.inventory_item = item
            if note:
                existing_stock.note = note
            existing_stock.metadata_payload = {key: value for key, value in metadata.items() if value}
            stock_item = existing_stock
            log_entry = record_stock_log(
                stock_item,
                "Envanter stoğa geri alındı",
                action_type="in",
                performed_by=actor,
                quantity_change=0,
                note=note,
                metadata={"inventory_no": item.inventory_no},
            )
        else:
            stock_item = create_stock_item_from_inventory(item, note=note, actor=actor)
            log_entry = None

        from .. import add_inventory_event
        add_inventory_event(item, "Stok girişi", note, performed_by=actor)
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        fresh_stock = get_stock_item_with_relations(stock_item.id)
        response = {
            "message": "Envanter stok listesine taşındı.",
            "item": serialize_inventory_item(fresh_item),
            "stock_item": serialize_stock_item(fresh_stock) if fresh_stock else None,
        }
        if log_entry:
            response["log"] = serialize_stock_log(log_entry)
        return jsonify(response)

    @stock_api_bp.post("/api/inventory/<int:item_id>/scrap")
    def scrap_inventory_api(item_id: int):
        denied = require_admin()
        if denied:
            return denied

        from .. import add_inventory_event, get_inventory_item_with_relations, serialize_inventory_item

        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return jsonify({"error": "Envanter kaydı bulunamadı."}), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400

        note = sanitize_input_text(data.get("note"), max_length=512)
        actor = sanitize_input_text(data.get("performed_by"), max_length=128) or current_actor_name() or "Sistem"
        item.status = "hurda"
        if note:
            item.note = note
        add_inventory_event(item, "Hurdaya ayırma", note, performed_by=actor)
        db.session.commit()
        return jsonify({"item": serialize_inventory_item(get_inventory_item_with_relations(item.id))})

    @stock_api_bp.post("/api/stock")
    def create_stock_api():
        denied = require_admin()
        if denied:
            return denied

        from .. import (
            generate_unique_sku,
            normalize_stock_category,
            record_stock_audit,
            record_stock_log,
            record_stock_movement,
            resolve_stock_category,
            resolve_stock_unit,
            serialize_stock_item,
            get_stock_item_with_relations,
            prepare_stock_metadata,
        )

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400

        title = sanitize_input_text(data.get("title"))
        if not title:
            return jsonify({"error": "Stok adı zorunludur."}), 400

        category = normalize_stock_category(data.get("category"))
        quantity = parse_int_or_none(data.get("quantity")) or 1
        if quantity < 1:
            return jsonify({"error": "Miktar en az 1 olmalıdır."}), 400

        try:
            metadata = prepare_stock_metadata(
                category,
                sanitize_metadata_payload(data.get("metadata")),
                include_assignment_fields=False,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        unit = sanitize_input_text(data.get("unit"), max_length=32) or None
        reference_code = sanitize_input_text(data.get("reference_code"), max_length=128) or None
        note = sanitize_input_text(data.get("note"), max_length=512)
        actor = sanitize_input_text(data.get("performed_by"), max_length=128) or current_actor_name() or "Sistem"
        serial_no = sanitize_input_text(data.get("serial_no"), max_length=128) or None
        warranty_end_date = parse_excel_date(data.get("warranty_end_date"))

        if not reference_code:
            reference_code = metadata.get("inventory_no") or metadata.get("license_key") or None

        category_ref = resolve_stock_category(category)
        unit_ref = resolve_stock_unit(unit)
        stock_item = StockItem(
            source_type="manual",
            title=title,
            category=category,
            category_id=category_ref.id if category_ref else None,
            quantity=quantity,
            unit=unit,
            unit_id=unit_ref.id if unit_ref else None,
            status="stokta",
            reference_code=reference_code,
            note=note,
            sku=generate_unique_sku("STK"),
            serial_no=serial_no,
            warranty_end_date=warranty_end_date,
        )
        stock_item.metadata_payload = {k: v for k, v in metadata.items() if v}
        db.session.add(stock_item)
        db.session.flush()

        log_entry = record_stock_log(
            stock_item,
            "Manuel stok girişi",
            action_type="in",
            performed_by=actor,
            quantity_change=quantity,
            note=note,
        )
        record_stock_movement(stock_item, operation_type="giris", old_quantity=0, new_quantity=quantity, user=get_active_user())
        record_stock_audit(stock_item, old_quantity=0, new_quantity=quantity, performed_by=actor)
        db.session.commit()

        fresh_stock = get_stock_item_with_relations(stock_item.id)
        return jsonify({
            "stock_item": serialize_stock_item(fresh_stock),
            "log": serialize_stock_log(log_entry) if log_entry else None,
        }), 201

    app.register_blueprint(stock_api_bp)
