from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db, NamedEntityMixin

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

    group_id = db.Column(
        db.Integer,
        db.ForeignKey("request_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    group = db.relationship("RequestGroup", back_populates="orders")

    lines = db.relationship(
        "RequestLine",
        cascade="all, delete-orphan",
        back_populates="order",
        order_by="RequestLine.id",
    )
    snapshots = db.relationship(
        "RequestLineSnapshot",
        cascade="all, delete-orphan",
        back_populates="order",
        order_by="RequestLineSnapshot.created_at",
    )


class RequestLine(db.Model):
    __tablename__ = "request_lines"

    id = db.Column(db.Integer, primary_key=True)
    hardware_type = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128), nullable=False)
    model = db.Column(db.String(128), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    note = db.Column(db.String(256), nullable=True)
    category = db.Column(db.String(32), nullable=False, default="envanter")

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("request_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    order = db.relationship("RequestOrder", back_populates="lines")


class RequestLineSnapshot(db.Model):
    __tablename__ = "request_line_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey("request_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    hardware_type = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128), nullable=False)
    model = db.Column(db.String(128), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    note = db.Column(db.String(256), nullable=True)
    category = db.Column(db.String(32), nullable=False, default="envanter")
    action = db.Column(db.String(32), nullable=False, default="stok")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    order = db.relationship("RequestOrder", back_populates="snapshots")


