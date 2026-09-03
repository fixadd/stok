from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db, NamedEntityMixin

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    actor = db.Column(db.String(128), nullable=False)
    metadata_json = db.Column("metadata", db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def metadata_payload(self) -> dict | None:
        return self.metadata_json

    @metadata_payload.setter
    def metadata_payload(self, value: dict | None) -> None:
        self.metadata_json = value

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "area": self.area,
            "action": self.action,
            "description": self.description,
            "actor": self.actor,
            "metadata": self.metadata_payload,
            "created_at": self.created_at,
        }


