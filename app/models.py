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


def find_existing_by_name(model: type[NamedEntityMixin], name: str):
    normalized = name.strip()
    if not normalized:
        return None
    return model.query.filter(func.lower(model.name) == normalized.lower()).first()
