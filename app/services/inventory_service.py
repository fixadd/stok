from __future__ import annotations

from typing import Any


def create_inventory(deps: dict[str, Any], data: dict[str, Any]):
    db = deps["db"]
    InventoryItem = deps["InventoryItem"]
    Factory = deps["Factory"]
    HardwareType = deps["HardwareType"]
    Brand = deps["Brand"]
    HardwareModel = deps["HardwareModel"]
    parse_int_or_none = deps["parse_int_or_none"]
    sanitize_input_text = deps["sanitize_input_text"]
    active_user_by_id = deps["active_user_by_id"]
    add_inventory_event = deps["add_inventory_event"]
    get_inventory_item_with_relations = deps["get_inventory_item_with_relations"]
    serialize_inventory_item = deps["serialize_inventory_item"]
    json_error = deps["json_error"]

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
    hardware_type = HardwareType.query.get(hardware_type_id) if hardware_type_id else None
    brand = Brand.query.get(brand_id) if brand_id else None
    model = HardwareModel.query.get(model_id) if model_id else None
    responsible_user = active_user_by_id(responsible_user_id) if responsible_user_id else None

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
    return {"item": serialize_inventory_item(fresh_item)}, 201


def update_inventory(deps: dict[str, Any], item_id: int, data: dict[str, Any]):
    db = deps["db"]
    InventoryItem = deps["InventoryItem"]
    Factory = deps["Factory"]
    HardwareType = deps["HardwareType"]
    Brand = deps["Brand"]
    HardwareModel = deps["HardwareModel"]
    parse_int_or_none = deps["parse_int_or_none"]
    sanitize_input_text = deps["sanitize_input_text"]
    active_user_by_id = deps["active_user_by_id"]
    add_inventory_event = deps["add_inventory_event"]
    get_inventory_item_with_relations = deps["get_inventory_item_with_relations"]
    serialize_inventory_item = deps["serialize_inventory_item"]
    json_error = deps["json_error"]
    inventory_statuses = deps["INVENTORY_STATUSES"]

    item = get_inventory_item_with_relations(item_id)
    if item is None:
        return json_error("Envanter kaydı bulunamadı."), 404

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
    hardware_type = HardwareType.query.get(hardware_type_id) if hardware_type_id else None
    brand = Brand.query.get(brand_id) if brand_id else None
    model = HardwareModel.query.get(model_id) if model_id else None
    responsible_user = active_user_by_id(responsible_user_id) if responsible_user_id else None

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
    if status not in inventory_statuses:
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
        item.related_machine_no = (data.get("related_machine_no") or "").strip() or None
    if "machine_no" in data:
        item.machine_no = (data.get("machine_no") or "").strip() or None

    item.note = (data.get("note") or "").strip() or None
    item.status = status

    add_inventory_event(item, "Envanter bilgileri güncellendi")
    db.session.commit()

    fresh_item = get_inventory_item_with_relations(item.id)
    return {"item": serialize_inventory_item(fresh_item)}, 200


def mark_inventory_faulty(deps: dict[str, Any], item_id: int, data: dict[str, Any]):
    db = deps["db"]
    add_inventory_event = deps["add_inventory_event"]
    get_inventory_item_with_relations = deps["get_inventory_item_with_relations"]
    serialize_inventory_item = deps["serialize_inventory_item"]
    json_error = deps["json_error"]

    item = get_inventory_item_with_relations(item_id)
    if item is None:
        return json_error("Envanter kaydı bulunamadı."), 404

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
    return {"item": serialize_inventory_item(fresh_item)}, 200
