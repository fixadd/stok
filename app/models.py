from __future__ import annotations

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func


db = SQLAlchemy()


class NamedEntityMixin:
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(128), nullable=True)
    department = db.Column(db.String(128), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "role": self.role,
            "department": self.department,
        }


class UsageArea(NamedEntityMixin, db.Model):
    __tablename__ = "usage_areas"


class LicenseName(NamedEntityMixin, db.Model):
    __tablename__ = "license_names"


class InfoCategory(NamedEntityMixin, db.Model):
    __tablename__ = "info_categories"


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

    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    brand = db.relationship("Brand", back_populates="models")


class LdapProfile(db.Model):
    __tablename__ = "ldap_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    host = db.Column(db.String(256), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=389)
    base_dn = db.Column(db.String(256), nullable=False)
    bind_dn = db.Column(db.String(256), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "base_dn": self.base_dn,
            "bind_dn": self.bind_dn,
        }


class RequestGroup(db.Model):
    __tablename__ = "request_groups"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(32), unique=True, nullable=False)
    label = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(256), nullable=False)
    empty_message = db.Column(db.String(256), nullable=False)

    orders = db.relationship(
        "RequestOrder",
        cascade="all, delete-orphan",
        back_populates="group",
        order_by="RequestOrder.opened_at.desc()",
    )


class RequestOrder(db.Model):
    __tablename__ = "request_orders"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(32), unique=True, nullable=False)
    requested_by = db.Column(db.String(128), nullable=False)
    department = db.Column(db.String(128), nullable=False)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    group_id = db.Column(db.Integer, db.ForeignKey("request_groups.id", ondelete="CASCADE"), nullable=False)
    group = db.relationship("RequestGroup", back_populates="orders")

    lines = db.relationship(
        "RequestLine",
        cascade="all, delete-orphan",
        back_populates="order",
        order_by="RequestLine.id",
    )


class RequestLine(db.Model):
    __tablename__ = "request_lines"

    id = db.Column(db.Integer, primary_key=True)
    hardware_type = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128), nullable=False)
    model = db.Column(db.String(128), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    note = db.Column(db.String(256), nullable=True)

    order_id = db.Column(db.Integer, db.ForeignKey("request_orders.id", ondelete="CASCADE"), nullable=False)
    order = db.relationship("RequestOrder", back_populates="lines")


class InventoryItem(db.Model):
    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    inventory_no = db.Column(db.String(32), unique=True, nullable=False)
    computer_name = db.Column(db.String(64), nullable=True)
    factory_id = db.Column(db.Integer, db.ForeignKey("factories.id"), nullable=False)
    department = db.Column(db.String(128), nullable=False)
    hardware_type_id = db.Column(db.Integer, db.ForeignKey("hardware_types.id"), nullable=False)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey("hardware_models.id"), nullable=False)
    serial_no = db.Column(db.String(128), nullable=True)
    ifs_no = db.Column(db.String(64), nullable=True)
    related_machine_no = db.Column(db.String(64), nullable=True)
    machine_no = db.Column(db.String(64), nullable=True)
    note = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="aktif")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "inventory_no": self.inventory_no,
            "computer_name": self.computer_name,
            "factory": self.factory.name if self.factory else None,
            "department": self.department,
            "hardware_type": self.hardware_type.name if self.hardware_type else None,
            "responsible": self.responsible_user.first_name + " " + self.responsible_user.last_name if self.responsible_user else None,
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


def find_existing_by_name(model: type[NamedEntityMixin], name: str):
    normalized = name.strip()
    if not normalized:
        return None
    return model.query.filter(func.lower(model.name) == normalized.lower()).first()
