from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from werkzeug.security import generate_password_hash
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..models import (
    Brand, Factory, HardwareModel, HardwareType, InfoCategory, InfoEntry,
    InventoryEvent, InventoryItem, InventoryLicense, LdapProfile, LicenseName,
    RequestGroup, RequestLine, RequestOrder, StockCategory, StockItem, StockUnit,
    UsageArea, User, db, find_existing_by_name,
)
from .activity_service import record_activity
from .stock_audit_service import record_stock_log

STOCK_CATEGORY_LABELS = {
    'envanter': 'Envanter',
    'cevre_birimi': 'Çevre Birimi',
    'yazici': 'IP Yazıcı',
    'lisans': 'Lisans',
    'talep': 'Talep',
    'manuel': 'Manuel',
}

def __resolve_stock_category(name: str):
    existing = find_existing_by_name(StockCategory, name)
    if existing:
        return existing
    category = StockCategory(name=name)
    db.session.add(category)
    db.session.flush()
    return category

def __resolve_stock_unit(name: str):
    existing = find_existing_by_name(StockUnit, name)
    if existing:
        return existing
    unit = StockUnit(name=name)
    db.session.add(unit)
    db.session.flush()
    return unit


















