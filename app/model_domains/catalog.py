from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db, NamedEntityMixin

class UsageArea(NamedEntityMixin, db.Model):
    __tablename__ = "usage_areas"


class ProductCatalogEntry(db.Model):
    __tablename__ = "product_catalog_entries"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=True)
    is_deleted = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.text("FALSE")
    )
    department = db.Column(db.String(128), nullable=True)
    usage_area_id = db.Column(
        db.Integer,
        db.ForeignKey("usage_areas.id"),
        nullable=False,
    )
    license_name_id = db.Column(
        db.Integer,
        db.ForeignKey("license_names.id"),
        nullable=False,
    )
    info_category_id = db.Column(
        db.Integer,
        db.ForeignKey("info_categories.id"),
        nullable=False,
    )
    factory_id = db.Column(
        db.Integer,
        db.ForeignKey("factories.id"),
        nullable=False,
    )
    hardware_type_id = db.Column(
        db.Integer,
        db.ForeignKey("hardware_types.id"),
        nullable=False,
    )
    brand_id = db.Column(
        db.Integer,
        db.ForeignKey("brands.id"),
        nullable=False,
    )
    model_id = db.Column(
        db.Integer,
        db.ForeignKey("hardware_models.id"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    usage_area = db.relationship("UsageArea")
    license_name = db.relationship("LicenseName")
    info_category = db.relationship("InfoCategory")
    factory = db.relationship("Factory")
    hardware_type = db.relationship("HardwareType")
    brand = db.relationship("Brand")
    model = db.relationship("HardwareModel")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "department": self.department,
            "usage_area": self.usage_area.to_dict() if self.usage_area else None,
            "license_name": self.license_name.to_dict() if self.license_name else None,
            "info_category": (
                self.info_category.to_dict() if self.info_category else None
            ),
            "factory": self.factory.to_dict() if self.factory else None,
            "hardware_type": (
                self.hardware_type.to_dict() if self.hardware_type else None
            ),
            "brand": self.brand.to_dict() if self.brand else None,
            "model": self.model.to_dict() if self.model else None,
            "created_at": self.created_at,
        }


