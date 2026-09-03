from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db, NamedEntityMixin

class InventoryMaintenance(db.Model):
    __tablename__ = "inventory_maintenances"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    performed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    performed_by = db.Column(db.String(128), nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    item = db.relationship("InventoryItem", back_populates="maintenances")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item_id": self.item_id,
            "performed_at": self.performed_at,
            "performed_by": self.performed_by,
            "note": self.note,
            "created_at": self.created_at,
        }


