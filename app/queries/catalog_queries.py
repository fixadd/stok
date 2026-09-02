from __future__ import annotations

from sqlalchemy import func

from ..models import Brand, Factory, HardwareModel, HardwareType, InfoCategory, LicenseName, UsageArea
from .common import apply_limit


def _get_by_name(model, name: str | None):
    value = (name or "").strip()
    if not value:
        return None
    return model.query.filter(func.lower(model.name) == value.lower()).first()


def list_named(model, *, limit: int = 100):
    query = model.query.order_by(func.lower(model.name), model.id)
    return apply_limit(query, limit=limit).all()


def get_factory(factory_id: int | None):
    return None if factory_id is None else Factory.query.filter(Factory.id == factory_id).first()


def get_hardware_type(hardware_type_id: int | None):
    return None if hardware_type_id is None else HardwareType.query.filter(HardwareType.id == hardware_type_id).first()


def get_brand(brand_id: int | None):
    return None if brand_id is None else Brand.query.filter(Brand.id == brand_id).first()


def get_model(model_id: int | None):
    return None if model_id is None else HardwareModel.query.filter(HardwareModel.id == model_id).first()


def get_info_category(category_id: int | None):
    return None if category_id is None else InfoCategory.query.filter(InfoCategory.id == category_id).first()


def get_license_name(license_name_id: int | None):
    return None if license_name_id is None else LicenseName.query.filter(LicenseName.id == license_name_id).first()


def get_usage_area(usage_area_id: int | None):
    return None if usage_area_id is None else UsageArea.query.filter(UsageArea.id == usage_area_id).first()


def find_factory(name: str | None): return _get_by_name(Factory, name)
def find_hardware_type(name: str | None): return _get_by_name(HardwareType, name)
def find_brand(name: str | None): return _get_by_name(Brand, name)
def find_info_category(name: str | None): return _get_by_name(InfoCategory, name)
def find_license_name(name: str | None): return _get_by_name(LicenseName, name)
def find_usage_area(name: str | None): return _get_by_name(UsageArea, name)


def list_factories(*, limit: int = 100): return list_named(Factory, limit=limit)
def list_hardware_types(*, limit: int = 100): return list_named(HardwareType, limit=limit)
def list_brands(*, limit: int = 100): return list_named(Brand, limit=limit)
def list_info_categories(*, limit: int = 100): return list_named(InfoCategory, limit=limit)
def list_license_names(*, limit: int = 100): return list_named(LicenseName, limit=limit)
def list_usage_areas(*, limit: int = 100): return list_named(UsageArea, limit=limit)
