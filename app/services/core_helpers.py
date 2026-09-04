"""Core application helpers extracted from the historical legacy module.

These helpers intentionally contain no Flask route registration.  Keeping them
here makes them reusable by route/service modules and gives the remaining
``legacy.py`` compatibility layer a small, explicit migration seam.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func

from ..models import ProductCatalogEntry, StockItem, User
from ..utils.parsing import sanitize_input_text


def user_is_active(user: User | None) -> bool:
    if user is None:
        return False
    return (user.employment_status or "aktif").strip().lower() == "aktif"


def active_users_query(*, include_inactive: bool = False):
    query = User.query
    if not include_inactive:
        query = query.filter(func.lower(User.employment_status) == "aktif")
    return query


def active_user_by_id(
    user_id: int | None, *, include_inactive: bool = False
) -> User | None:
    if user_id is None:
        return None
    return (
        active_users_query(include_inactive=include_inactive)
        .filter(User.id == user_id)
        .first()
    )


def split_license_name(value: str) -> tuple[str, str]:
    if not value:
        return "", ""
    if " - " in value:
        name, key = value.split(" - ", 1)
        return name.strip(), key.strip()
    return value.strip(), ""


def build_qr_code_url(sku: str) -> str:
    code = sanitize_input_text(sku, max_length=64)
    return (
        f"https://api.qrserver.com/v1/create-qr-code/?size=160x160&data={code}"
        if code
        else ""
    )


def generate_unique_sku(prefix: str) -> str:
    cleaned_prefix = (prefix or "SKU").strip().upper()[:8] or "SKU"
    while True:
        code = f"{cleaned_prefix}-{uuid4().hex[:10].upper()}"
        exists_stock = StockItem.query.filter_by(sku=code).first()
        exists_catalog = ProductCatalogEntry.query.filter_by(sku=code).first()
        if not exists_stock and not exists_catalog:
            return code
