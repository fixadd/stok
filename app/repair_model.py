from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from .models import db


class InventoryRepair(db.Model):
    """SQLAlchemy representation of an inventory repair/service record."""

    __tablename__ = "inventory_repairs"
    __table_args__ = (
        db.Index("ix_inventory_repairs_item_id", "item_id"),
        db.Index("ix_inventory_repairs_status", "status"),
        db.Index("ix_inventory_repairs_expected_return_at", "expected_return_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    fault_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fault_type = db.Column(db.String(128), nullable=True)
    problem_description = db.Column(db.Text, nullable=False)
    sent_to_service = db.Column(db.Boolean, nullable=False, default=False)
    service_company = db.Column(db.String(256), nullable=True)
    service_contact = db.Column(db.String(128), nullable=True)
    service_ticket_no = db.Column(db.String(128), nullable=True)
    warranty_status = db.Column(db.String(32), nullable=False, default="belirsiz")
    sent_at = db.Column(db.DateTime, nullable=True)
    expected_return_at = db.Column(db.DateTime, nullable=True)
    returned_at = db.Column(db.DateTime, nullable=True)
    repair_description = db.Column(db.Text, nullable=True)
    service_cost = db.Column(db.Numeric(12, 2), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="bekliyor")
    note = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.String(128), nullable=False, default="Sistem")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Post-repair quality control / approval
    testing_status = db.Column(db.String(32), nullable=False, default="bekliyor")
    tested_at = db.Column(db.DateTime, nullable=True)
    tested_by = db.Column(db.String(128), nullable=True)
    approval_status = db.Column(db.String(32), nullable=False, default="bekliyor")
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.String(128), nullable=True)

    # SLA / delay tracking
    sla_due_at = db.Column(db.DateTime, nullable=True)
    delay_reason = db.Column(db.Text, nullable=True)

    item = db.relationship("InventoryItem", foreign_keys=[item_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item_id": self.item_id,
            "fault_date": self.fault_date,
            "fault_type": self.fault_type,
            "problem_description": self.problem_description,
            "sent_to_service": self.sent_to_service,
            "service_company": self.service_company,
            "service_contact": self.service_contact,
            "service_ticket_no": self.service_ticket_no,
            "warranty_status": self.warranty_status,
            "sent_at": self.sent_at,
            "expected_return_at": self.expected_return_at,
            "returned_at": self.returned_at,
            "repair_description": self.repair_description,
            "service_cost": (
                str(self.service_cost)
                if isinstance(self.service_cost, Decimal)
                else self.service_cost
            ),
            "status": self.status,
            "note": self.note,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "testing_status": self.testing_status,
            "tested_at": self.tested_at,
            "tested_by": self.tested_by,
            "approval_status": self.approval_status,
            "approved_at": self.approved_at,
            "approved_by": self.approved_by,
            "sla_due_at": self.sla_due_at,
            "delay_reason": self.delay_reason,
        }
