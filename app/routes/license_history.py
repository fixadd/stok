from __future__ import annotations

from flask import Blueprint, jsonify

from ..models import ActivityLog, InventoryLicense, db



def register_license_history_routes(app):
    license_history_bp = Blueprint("license_history", __name__)

    @license_history_bp.get("/api/licenses/<int:license_id>/history")
    def get_license_history(license_id: int):
        license_record = db.session.get(InventoryLicense, license_id)
        if license_record is None:
            return jsonify({"error": "Lisans kaydı bulunamadı."}), 404

        records = (
            ActivityLog.query
            .filter(
                ActivityLog.metadata_json["license_id"].as_integer() == license_id,
                ActivityLog.area.in_(["lisans", "stok"]),
            )
            .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
            .all()
        )

        history = [
            {
                "id": record.id,
                "title": record.action,
                "actor": record.actor,
                "note": record.description or "",
                "performed_at": record.created_at.strftime("%d.%m.%Y %H:%M"),
            }
            for record in records
        ]

        return jsonify(
            {
                "license_id": license_id,
                "history": history,
                "count": len(history),
            }
        )

    app.register_blueprint(license_history_bp)
