from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from urllib.parse import quote_plus

from flask import Blueprint, jsonify, render_template, request

from .models import ActivityLog, InventoryItem, RequestOrder, StockAssignment, User, db
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


def _latest_lifecycle_flags() -> dict[str, str]:
    logs = (
        ActivityLog.query.filter(ActivityLog.area == "personnel_lifecycle")
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .all()
    )
    flags: dict[str, str] = {}
    for log in logs:
        metadata = log.metadata_payload or {}
        person_key = sanitize_input_text(metadata.get("person_key"), max_length=255)
        status = sanitize_input_text(metadata.get("lifecycle_status"), max_length=64)
        if not person_key or person_key in flags or not status:
            continue
        flags[person_key] = status
    return flags


def build_personnel_lifecycle_payload() -> list[dict]:
    people: dict[str, dict] = {}

    for user in User.query.order_by(User.first_name, User.last_name).all():
        full_name = f"{user.first_name} {user.last_name}".strip()
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
        person_name = f"{item.responsible_user.first_name} {item.responsible_user.last_name}".strip()
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
    items = build_personnel_lifecycle_payload()
    person = next((row for row in items if row["person_key"] == person_key), None)
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
        row
        for row in activity_rows
        if "devir" in row["action"].lower() or "iade" in row["action"].lower()
    ]

    return {
        "person": person,
        "activities": activity_rows,
        "stock_assignments": stock_assignments,
        "transfer_history": transfer_history,
    }


@personnel_lifecycle_bp.get("/")
def list_page():
    people = build_personnel_lifecycle_payload()
    return render_template(
        "personnel_lifecycle/list.html",
        active_page="personnel_lifecycle",
        people=people,
        lifecycle_status_labels=LIFECYCLE_STATUS_LABELS,
    )


@personnel_lifecycle_bp.get("/<person_key>")
def detail_page(person_key: str):
    payload = build_personnel_detail_payload(person_key)
    if payload is None:
        return render_template("personnel_lifecycle/detail.html", not_found=True), 404
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
        "toplu_devir": ("Toplu devir planlandı", "yer_degisti"),
        "toplu_iade": ("Toplu iade planlandı", "ayrilis_bekliyor"),
        "surec_kapat": ("Süreç kapatıldı", "ayrildi"),
    }
    if action not in action_map:
        return jsonify({"error": "Geçersiz aksiyon."}), 400

    action_label, status = action_map[action]
    log = ActivityLog(
        area="personnel_lifecycle",
        action=action_label,
        description=f"{payload['person']['name']} için {action_label.lower()}.",
        actor=actor,
        metadata_payload={
            "person_key": person_key,
            "person_name": payload["person"]["name"],
            "lifecycle_status": status,
            "lifecycle_flags": {
                "is_active": status == "aktif",
                "is_location_changed": status == "yer_degisti",
                "is_exit_pending": status == "ayrilis_bekliyor",
                "is_exited": status == "ayrildi",
            },
        },
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(
        {
            "message": f"{action_label}.",
            "person_key": person_key,
            "lifecycle_status": status,
            "lifecycle_flags": {
                "is_active": status == "aktif",
                "is_location_changed": status == "yer_degisti",
                "is_exit_pending": status == "ayrilis_bekliyor",
                "is_exited": status == "ayrildi",
            },
        }
    )
