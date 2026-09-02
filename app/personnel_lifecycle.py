from __future__ import annotations

from datetime import datetime
from urllib.parse import quote_plus

from flask import Blueprint, jsonify, render_template, request

from .models import (
    ActivityLog,
    InventoryAssignment,
    InventoryEvent,
    InventoryItem,
    RequestOrder,
    StockAssignment,
    StockLog,
    User,
    db,
)
from .utils.parsing import sanitize_input_text

personnel_lifecycle_bp = Blueprint(
    "personnel_lifecycle",
    __name__,
    url_prefix="/personnel-lifecycle",
)

LIFECYCLE_STATUS_LABELS = {
    "aktif": "Aktif",
    "yer_degisti": "Yer Değişti",
    "ayrilis_bekliyor": "Ayrılış Bekliyor",
    "ayrildi": "Ayrıldı",
}

LIFECYCLE_STATUS_CLASSES = {
    "aktif": "bg-success-subtle text-success",
    "yer_degisti": "bg-info-subtle text-info",
    "ayrilis_bekliyor": "bg-warning-subtle text-warning",
    "ayrildi": "bg-secondary-subtle text-secondary",
}


def _person_key(value: str) -> str:
    return quote_plus((value or "").strip().lower())


def _person_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip()


def _find_user(person_key: str) -> User | None:
    for user in User.query.all():
        if _person_key(_person_name(user)) == person_key:
            return user
    return None


def _latest_lifecycle_flags() -> dict[str, str]:
    logs = (
        ActivityLog.query.filter(ActivityLog.area == "personnel_lifecycle")
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .all()
    )
    flags: dict[str, str] = {}
    for log in logs:
        metadata = log.metadata_payload or {}
        key = sanitize_input_text(metadata.get("person_key"), max_length=255)
        status = sanitize_input_text(metadata.get("lifecycle_status"), max_length=64)
        if key and key not in flags and status:
            flags[key] = status
    return flags


def build_personnel_lifecycle_payload() -> list[dict]:
    people: dict[str, dict] = {}

    for user in User.query.order_by(User.first_name, User.last_name).all():
        full_name = _person_name(user)
        if not full_name:
            continue
        key = _person_key(full_name)
        people[key] = {
            "person_key": key,
            "name": full_name,
            "department": user.department or "",
            "inventory_count": 0,
            "stock_assignment_count": 0,
            "open_request_count": 0,
        }

    for item in InventoryItem.query.filter(InventoryItem.responsible_user_id.isnot(None)).all():
        if not item.responsible_user:
            continue
        person_name = _person_name(item.responsible_user)
        key = _person_key(person_name)
        if key not in people:
            people[key] = {
                "person_key": key,
                "name": person_name,
                "department": item.department or "",
                "inventory_count": 0,
                "stock_assignment_count": 0,
                "open_request_count": 0,
            }
        people[key]["inventory_count"] += 1

    for assignment in StockAssignment.query.all():
        key = _person_key(assignment.assigned_to)
        if not key:
            continue
        if key not in people:
            people[key] = {
                "person_key": key,
                "name": assignment.assigned_to,
                "department": assignment.assigned_department or "",
                "inventory_count": 0,
                "stock_assignment_count": 0,
                "open_request_count": 0,
            }
        people[key]["stock_assignment_count"] += int(assignment.quantity or 0)

    for order in RequestOrder.query.join(RequestOrder.group).filter_by(key="acik").all():
        key = _person_key(order.requested_by)
        if key not in people:
            people[key] = {
                "person_key": key,
                "name": order.requested_by,
                "department": order.department or "",
                "inventory_count": 0,
                "stock_assignment_count": 0,
                "open_request_count": 0,
            }
        people[key]["open_request_count"] += 1

    lifecycle_flags = _latest_lifecycle_flags()
    payload: list[dict] = []
    for person in people.values():
        flag = lifecycle_flags.get(person["person_key"])
        if flag:
            status = flag
        elif person["inventory_count"] == 0 and person["stock_assignment_count"] == 0:
            status = "ayrildi"
        else:
            status = "aktif"
        person["status"] = status
        person["status_label"] = LIFECYCLE_STATUS_LABELS.get(status, status)
        person["status_class"] = LIFECYCLE_STATUS_CLASSES.get(status, "bg-light text-dark")
        payload.append(person)

    payload.sort(key=lambda row: row["name"].lower())
    return payload


def build_personnel_detail_payload(person_key: str) -> dict | None:
    person = next(
        (row for row in build_personnel_lifecycle_payload() if row["person_key"] == person_key),
        None,
    )
    if person is None:
        return None

    person_name = person["name"]
    assignments = (
        StockAssignment.query.filter(StockAssignment.assigned_to.ilike(person_name))
        .order_by(StockAssignment.delivered_at.desc())
        .limit(10)
        .all()
    )
    stock_assignments = [
        {
            "item": assignment.stock_item.title if assignment.stock_item else "—",
            "quantity": assignment.quantity,
            "department": assignment.assigned_department or "—",
            "delivered_at": assignment.delivered_at.strftime("%d.%m.%Y %H:%M"),
        }
        for assignment in assignments
    ]

    activities = (
        ActivityLog.query.filter(
            ActivityLog.metadata_json.isnot(None),
            ActivityLog.metadata_json["person_key"].as_string() == person_key,
        )
        .order_by(ActivityLog.created_at.desc())
        .limit(20)
        .all()
    )
    activity_rows = [
        {
            "action": activity.action,
            "description": activity.description or "—",
            "actor": activity.actor,
            "created_at": activity.created_at.strftime("%d.%m.%Y %H:%M"),
        }
        for activity in activities
    ]
    transfer_history = [
        row for row in activity_rows
        if "devir" in row["action"].lower() or "iade" in row["action"].lower()
    ]

    return {
        "person": person,
        "activities": activity_rows,
        "stock_assignments": stock_assignments,
        "transfer_history": transfer_history,
    }


def _log_lifecycle(
    *, person: dict, action: str, status: str, actor: str, metadata: dict | None = None
) -> None:
    payload = {
        "person_key": person["person_key"],
        "person_name": person["name"],
        "lifecycle_status": status,
        "lifecycle_flags": {
            "is_active": status == "aktif",
            "is_location_changed": status == "yer_degisti",
            "is_exit_pending": status == "ayrilis_bekliyor",
            "is_exited": status == "ayrildi",
        },
    }
    if metadata:
        payload.update(metadata)
    db.session.add(
        ActivityLog(
            area="personnel_lifecycle",
            action=action,
            description=f"{person['name']} için {action.lower()}.",
            actor=actor,
            metadata_payload=payload,
        )
    )


def _bulk_transfer(person: dict, target: User, actor: str) -> dict:
    source_name = person["name"]
    target_name = _person_name(target)
    now = datetime.utcnow()

    inventory_assignments = InventoryAssignment.query.filter(
        InventoryAssignment.returned_at.is_(None),
        InventoryAssignment.assigned_to.ilike(source_name),
    ).all()
    inventory_count = 0
    for assignment in inventory_assignments:
        assignment.returned_at = now
        assignment.returned_to_user_id = target.id
        assignment.note = (assignment.note or "")[:450] + (
            f" Toplu devir: {source_name} → {target_name}."
        )
        item = assignment.item
        item.responsible_user_id = target.id
        item.department = target.department or item.department
        item.status = "aktif"
        inventory_count += 1
        db.session.add(
            InventoryAssignment(
                item_id=item.id,
                assigned_user_id=target.id,
                assigned_to=target_name,
                assigned_department=target.department or item.department,
                assigned_factory_id=assignment.assigned_factory_id,
                assigned_at=now,
                delivered_by=actor,
                note=f"Toplu devir: {source_name} → {target_name}.",
            )
        )
        db.session.add(
            InventoryEvent(
                item_id=item.id,
                event_type="toplu_devir",
                performed_by=actor,
                performed_at=now,
                note=f"{source_name} personelinden {target_name} personeline devredildi.",
            )
        )

    stock_assignments = StockAssignment.query.filter(
        StockAssignment.assigned_to.ilike(source_name)
    ).all()
    stock_count = 0
    for assignment in stock_assignments:
        assignment.assigned_to = target_name
        assignment.assigned_department = target.department or assignment.assigned_department
        assignment.delivered_by = actor
        stock_count += int(assignment.quantity or 0)

    return {
        "inventory_items": inventory_count,
        "stock_quantity": stock_count,
        "target": target_name,
    }


def _bulk_return(person: dict, actor: str) -> dict:
    source_name = person["name"]
    now = datetime.utcnow()
    inventory_assignments = InventoryAssignment.query.filter(
        InventoryAssignment.returned_at.is_(None),
        InventoryAssignment.assigned_to.ilike(source_name),
    ).all()
    inventory_count = 0
    for assignment in inventory_assignments:
        assignment.returned_at = now
        assignment.returned_to_user_id = None
        assignment.delivered_by = actor
        assignment.note = (assignment.note or "")[:450] + " Toplu iade."
        item = assignment.item
        item.responsible_user_id = None
        item.status = "stokta"
        inventory_count += 1
        db.session.add(
            InventoryEvent(
                item_id=item.id,
                event_type="toplu_iade",
                performed_by=actor,
                performed_at=now,
                note=f"{source_name} personelinden toplu iade alındı.",
            )
        )

    stock_assignments = StockAssignment.query.filter(
        StockAssignment.assigned_to.ilike(source_name)
    ).all()
    stock_count = 0
    for assignment in stock_assignments:
        stock_item = assignment.stock_item
        quantity = int(assignment.quantity or 0)
        if stock_item:
            stock_item.quantity = int(stock_item.quantity or 0) + quantity
            db.session.add(
                StockLog(
                    stock_item_id=stock_item.id,
                    action="Toplu iade",
                    action_type="return",
                    performed_by=actor,
                    quantity_change=quantity,
                    note=f"{source_name} personelinden toplu iade.",
                    metadata_payload={"person_key": person["person_key"]},
                )
            )
        stock_count += quantity
        db.session.delete(assignment)

    return {
        "inventory_items": inventory_count,
        "stock_quantity": stock_count,
    }


@personnel_lifecycle_bp.get("/")
def list_page():
    people = build_personnel_lifecycle_payload()
    users = [
        {"id": user.id, "name": _person_name(user), "department": user.department or ""}
        for user in User.query.order_by(User.first_name, User.last_name).all()
        if _person_name(user)
    ]
    return render_template(
        "personnel_lifecycle/list.html",
        active_page="personnel_lifecycle",
        people=people,
        lifecycle_status_labels=LIFECYCLE_STATUS_LABELS,
        lifecycle_users=users,
    )


@personnel_lifecycle_bp.get("/<person_key>")
def detail_page(person_key: str):
    payload = build_personnel_detail_payload(person_key)
    if payload is None:
        return render_template("personnel_lifecycle/detail.html", not_found=True), 404
    payload["lifecycle_users"] = [
        {"id": user.id, "name": _person_name(user), "department": user.department or ""}
        for user in User.query.order_by(User.first_name, User.last_name).all()
        if _person_key(_person_name(user)) != person_key and _person_name(user)
    ]
    return render_template(
        "personnel_lifecycle/detail.html",
        active_page="personnel_lifecycle",
        **payload,
    )


@personnel_lifecycle_bp.post("/api/<person_key>/action")
def process_action(person_key: str):
    payload = build_personnel_detail_payload(person_key)
    if payload is None:
        return jsonify({"error": "Personel bulunamadı."}), 404

    data = request.get_json(silent=True) or {}
    action = sanitize_input_text(data.get("action"), max_length=64)
    actor = sanitize_input_text(data.get("actor"), max_length=128) or "Sistem"
    action_map = {
        "yer_degisikligi_baslat": ("Yer değişikliği başlatıldı", "yer_degisti"),
        "ayrilis_baslat": ("Ayrılış başlatıldı", "ayrilis_bekliyor"),
        "surec_kapat": ("Süreç kapatıldı", "ayrildi"),
    }

    if action == "toplu_devir":
        target_id = data.get("target_user_id")
        try:
            target_id = int(target_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Devir yapılacak hedef personeli seçin."}), 400
        target = User.query.get(target_id)
        if target is None:
            return jsonify({"error": "Hedef personel bulunamadı."}), 404
        if _person_key(_person_name(target)) == person_key:
            return jsonify({"error": "Aynı personele devir yapılamaz."}), 400
        try:
            result = _bulk_transfer(payload["person"], target, actor)
            _log_lifecycle(
                person=payload["person"],
                action="Toplu devir tamamlandı",
                status="yer_degisti",
                actor=actor,
                metadata={"target_person_key": _person_key(_person_name(target)), "target_person_name": _person_name(target), **result},
            )
            db.session.commit()
            return jsonify({"message": f"Toplu devir tamamlandı. {result['inventory_items']} envanter, {result['stock_quantity']} stok adedi devredildi.", "lifecycle_status": "yer_degisti", **result})
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Toplu devir sırasında kayıtlar değiştirilemedi."}), 500

    if action == "toplu_iade":
        try:
            result = _bulk_return(payload["person"], actor)
            _log_lifecycle(
                person=payload["person"],
                action="Toplu iade tamamlandı",
                status="ayrilis_bekliyor",
                actor=actor,
                metadata=result,
            )
            db.session.commit()
            return jsonify({"message": f"Toplu iade tamamlandı. {result['inventory_items']} envanter, {result['stock_quantity']} stok adedi iade alındı.", "lifecycle_status": "ayrilis_bekliyor", **result})
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Toplu iade sırasında kayıtlar değiştirilemedi."}), 500

    if action not in action_map:
        return jsonify({"error": "Geçersiz aksiyon."}), 400

    action_label, status = action_map[action]
    try:
        _log_lifecycle(person=payload["person"], action=action_label, status=status, actor=actor)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "İşlem kaydedilemedi."}), 500

    return jsonify({
        "message": f"{action_label}.",
        "person_key": person_key,
        "lifecycle_status": status,
        "lifecycle_flags": {
            "is_active": status == "aktif",
            "is_location_changed": status == "yer_degisti",
            "is_exit_pending": status == "ayrilis_bekliyor",
            "is_exited": status == "ayrildi",
        },
    })
