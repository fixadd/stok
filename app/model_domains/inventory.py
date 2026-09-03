from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db, NamedEntityMixin

class Factory(NamedEntityMixin, db.Model):
    __tablename__ = "factories"


class HardwareType(NamedEntityMixin, db.Model):
    __tablename__ = "hardware_types"


class Brand(NamedEntityMixin, db.Model):
    __tablename__ = "brands"

    models = db.relationship(
        "HardwareModel",
        cascade="all, delete-orphan",
        back_populates="brand",
        order_by="HardwareModel.name",
    )

    def to_dict(self, include_models: bool = False) -> dict:
        payload = super().to_dict()
        if include_models:
            payload["models"] = [model.to_dict() for model in self.models]
        return payload


class HardwareModel(NamedEntityMixin, db.Model):
    __tablename__ = "hardware_models"

    brand_id = db.Column(
        db.Integer, db.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False
    )
    brand = db.relationship("Brand", back_populates="models")


class InventoryItem(db.Model):
    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    inventory_no = db.Column(db.String(32), unique=True, nullable=False)
    computer_name = db.Column(db.String(64), nullable=True)
    factory_id = db.Column(db.Integer, db.ForeignKey("factories.id"), nullable=False)
    department = db.Column(db.String(128), nullable=False)
    hardware_type_id = db.Column(
        db.Integer, db.ForeignKey("hardware_types.id"), nullable=False
    )
    responsible_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False)
    model_id = db.Column(
        db.Integer, db.ForeignKey("hardware_models.id"), nullable=False
    )
    serial_no = db.Column(db.String(128), nullable=True)
    ifs_no = db.Column(db.String(64), nullable=True)
    related_machine_no = db.Column(db.String(64), nullable=True)
    machine_no = db.Column(db.String(64), nullable=True)
    note = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="aktif")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    factory = db.relationship("Factory")
    hardware_type = db.relationship("HardwareType")
    responsible_user = db.relationship("User")
    brand = db.relationship("Brand")
    model = db.relationship("HardwareModel")
    events = db.relationship(
        "InventoryEvent",
        cascade="all, delete-orphan",
        back_populates="item",
        order_by="InventoryEvent.performed_at.desc()",
    )
    licenses = db.relationship(
        "InventoryLicense",
        cascade="all, delete-orphan",
        back_populates="item",
        order_by="InventoryLicense.id",
    )
    maintenances = db.relationship(
        "InventoryMaintenance",
        cascade="all, delete-orphan",
        back_populates="item",
        order_by="InventoryMaintenance.performed_at.desc()",
    )
    assignments = db.relationship(
        "InventoryAssignment",
        cascade="all, delete-orphan",
        back_populates="item",
        order_by="InventoryAssignment.assigned_at.desc()",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "inventory_no": self.inventory_no,
            "computer_name": self.computer_name,
            "factory": self.factory.name if self.factory else None,
            "department": self.department,
            "hardware_type": self.hardware_type.name if self.hardware_type else None,
            "responsible": (
                self.responsible_user.first_name + " " + self.responsible_user.last_name
                if self.responsible_user
                else None
            ),
            "brand": self.brand.name if self.brand else None,
            "model": self.model.name if self.model else None,
            "serial_no": self.serial_no,
            "ifs_no": self.ifs_no,
            "related_machine_no": self.related_machine_no,
            "machine_no": self.machine_no,
            "note": self.note,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class InventoryEvent(db.Model):
    __tablename__ = "inventory_events"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = db.Column(db.String(64), nullable=False)
    performed_by = db.Column(db.String(128), nullable=False)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    note = db.Column(db.String(256), nullable=True)

    item = db.relationship("InventoryItem", back_populates="events")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "performed_by": self.performed_by,
            "performed_at": self.performed_at,
            "note": self.note,
        }


class InventoryAssignment(db.Model):
    __tablename__ = "inventory_assignments"

    id = db.Column(db.Integer, primary_key=True)

    item_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    assigned_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    assigned_to = db.Column(
        db.String(128),
        nullable=False,
    )

    assigned_department = db.Column(
        db.String(128),
        nullable=True,
    )

    assigned_factory_id = db.Column(
        db.Integer,
        db.ForeignKey("factories.id"),
        nullable=True,
    )

    assigned_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    returned_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    returned_to_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    delivered_by = db.Column(
        db.String(128),
        nullable=True,
    )

    note = db.Column(
        db.Text,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    item = db.relationship(
        "InventoryItem",
        back_populates="assignments",
    )

    assigned_user = db.relationship(
        "User",
        foreign_keys=[assigned_user_id],
    )

    returned_to_user = db.relationship(
        "User",
        foreign_keys=[returned_to_user_id],
    )

    assigned_factory = db.relationship(
        "Factory",
        foreign_keys=[assigned_factory_id],
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item_id": self.item_id,
            "assigned_user_id": self.assigned_user_id,
            "assigned_to": self.assigned_to,
            "assigned_department": self.assigned_department or "",
            "assigned_factory_id": self.assigned_factory_id,
            "assigned_factory": (
                self.assigned_factory.name
                if self.assigned_factory
                else ""
            ),
            "assigned_at": self.assigned_at,
            "returned_at": self.returned_at,
            "returned_to_user_id": self.returned_to_user_id,
            "returned_to_user": (
                f"{self.returned_to_user.first_name} "
                f"{self.returned_to_user.last_name}"
                if self.returned_to_user
                else ""
            ),
            "delivered_by": self.delivered_by or "",
            "note": self.note or "",
            "created_at": self.created_at,
        }


class InventoryLicense(db.Model):
    __tablename__ = "inventory_licenses"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="aktif")

    item = db.relationship("InventoryItem", back_populates="licenses")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
        }


