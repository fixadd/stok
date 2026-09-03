from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db, NamedEntityMixin

class StockItem(db.Model):
    __tablename__ = "stock_items"
    __table_args__ = (
        db.Index("ix_stock_items_reference_code", "reference_code"),
        db.Index("ix_stock_items_title", "title"),
    )

    id = db.Column(db.Integer, primary_key=True)
    source_type = db.Column(db.String(32), nullable=False, default="manual")
    source_id = db.Column(db.Integer, nullable=True)
    inventory_item_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    license_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_licenses.id", ondelete="SET NULL"),
        nullable=True,
    )
    reference_code = db.Column(db.String(128), nullable=True)
    sku = db.Column(db.String(64), unique=True, nullable=True)
    title = db.Column(db.String(256), nullable=False)
    category = db.Column(db.String(32), nullable=False, default="envanter")
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("stock_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit = db.Column(db.String(32), nullable=True)
    unit_id = db.Column(
        db.Integer,
        db.ForeignKey("stock_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = db.Column(db.String(32), nullable=False, default="stokta")
    note = db.Column(db.String(256), nullable=True)
    serial_no = db.Column(db.String(128), nullable=True)
    warranty_end_date = db.Column(db.Date, nullable=True)
    metadata_json = db.Column("metadata", db.JSON, nullable=True)
    is_deleted = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.text("FALSE")
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    inventory_item = db.relationship("InventoryItem")
    license = db.relationship("InventoryLicense")
    category_ref = db.relationship("StockCategory")
    unit_ref = db.relationship("StockUnit")

    logs = db.relationship(
        "StockLog",
        cascade="all, delete-orphan",
        back_populates="stock_item",
        order_by="StockLog.created_at.desc()",
    )
    movements = db.relationship(
        "StockMovement",
        cascade="all, delete-orphan",
        back_populates="stock_item",
        order_by="StockMovement.created_at.desc()",
    )
    assignments = db.relationship(
        "StockAssignment",
        cascade="all, delete-orphan",
        back_populates="stock_item",
        order_by="StockAssignment.created_at.desc()",
    )
    audit_trails = db.relationship(
        "StockAuditLog",
        cascade="all, delete-orphan",
        back_populates="stock_item",
        order_by="StockAuditLog.created_at.desc()",
    )

    @property
    def metadata_payload(self) -> dict | None:
        return self.metadata_json

    @metadata_payload.setter
    def metadata_payload(self, value: dict | None) -> None:
        self.metadata_json = value


class StockLog(db.Model):
    __tablename__ = "stock_logs"

    id = db.Column(db.Integer, primary_key=True)
    stock_item_id = db.Column(
        db.Integer,
        db.ForeignKey("stock_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    action = db.Column(db.String(128), nullable=False)
    action_type = db.Column(db.String(32), nullable=False, default="info")
    performed_by = db.Column(db.String(128), nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False, default=0)
    note = db.Column(db.String(256), nullable=True)
    metadata_json = db.Column("metadata", db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    stock_item = db.relationship("StockItem", back_populates="logs")

    @property
    def metadata_payload(self) -> dict | None:
        return self.metadata_json

    @metadata_payload.setter
    def metadata_payload(self, value: dict | None) -> None:
        self.metadata_json = value


class StockCategory(NamedEntityMixin, db.Model):
    __tablename__ = "stock_categories"


class StockUnit(NamedEntityMixin, db.Model):
    __tablename__ = "stock_units"


class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    stock_item_id = db.Column(
        db.Integer,
        db.ForeignKey("stock_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    operation_type = db.Column(db.String(32), nullable=False)
    old_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    stock_item = db.relationship("StockItem", back_populates="movements")
    user = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "stock_item_id": self.stock_item_id,
            "user_id": self.user_id,
            "operation_type": self.operation_type,
            "old_quantity": self.old_quantity,
            "new_quantity": self.new_quantity,
            "created_at": self.created_at,
        }


class StockAuditLog(db.Model):
    __tablename__ = "stok_hareketleri"

    id = db.Column(db.Integer, primary_key=True)
    stock_item_id = db.Column(
        db.Integer,
        db.ForeignKey("stock_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    old_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    performed_by = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    stock_item = db.relationship("StockItem", back_populates="audit_trails")


class StockAssignment(db.Model):
    __tablename__ = "stock_assignments"

    id = db.Column(db.Integer, primary_key=True)
    stock_item_id = db.Column(
        db.Integer,
        db.ForeignKey("stock_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_to = db.Column(db.String(128), nullable=False)
    assigned_department = db.Column(db.String(128), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    delivery_note = db.Column(db.String(512), nullable=True)
    delivered_by = db.Column(db.String(128), nullable=False)
    delivered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    receipt_code = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    stock_item = db.relationship("StockItem", back_populates="assignments")


