from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .services.authz import has_system_role

NAV_ITEMS: dict[str, dict[str, Any]] = {
    "index": {"title": "Ana Sayfa", "endpoint": "index", "icon": "bi-house", "min_role": "user", "parent": None, "section": "general"},
    "inventory_tracking": {"title": "Envanter Takip", "endpoint": "inventory.inventory_tracking", "icon": "bi-box-seam", "min_role": "user", "parent": "index", "section": "inventory"},
    "license_tracking": {"title": "Lisans Takip", "endpoint": "license_tracking", "icon": "bi-key", "min_role": "user", "parent": "index", "section": "inventory"},
    "stock_tracking": {"title": "Stok Takip", "endpoint": "stock.stock_tracking", "icon": "bi-bar-chart", "min_role": "user", "parent": "index", "section": "inventory"},
    "maintenance_tracking": {"title": "Bakım", "endpoint": "maintenance.maintenance_tracking", "icon": "bi-tools", "min_role": "user", "parent": "stock_tracking", "section": "inventory"},
    "talep_takip": {"title": "Talep Takip", "endpoint": "talep_takip", "icon": "bi-file-earmark-text", "min_role": "user", "parent": "index", "section": "operations"},
    "personnel_lifecycle": {"title": "Personel Lifecycle", "endpoint": "personnel_lifecycle.list_page", "icon": "bi-people", "min_role": "user", "parent": "index", "section": "operations"},
    "information": {"title": "Bilgiler", "endpoint": "information_list", "icon": "bi-info-circle", "min_role": "user", "parent": "index", "section": "operations"},
    "scrap_inventory": {"title": "Hurdalar", "endpoint": "stock.scrap_inventory_page", "icon": "bi-trash", "min_role": "user", "parent": "stock_tracking", "section": "operations"},
    "profile": {"title": "Profil", "endpoint": "profile", "icon": "bi-person", "min_role": "user", "parent": "index", "section": "settings"},
    "admin_panel": {"title": "Admin Paneli", "endpoint": "admin_panel", "icon": "bi-speedometer2", "min_role": "admin", "parent": "index", "section": "settings"},
    "activity_logs": {"title": "Kayıtlar", "endpoint": "activity_logs", "icon": "bi-journal-text", "min_role": "admin", "parent": "admin_panel", "section": "settings"},
    "logout": {"title": "Çıkış", "endpoint": "logout", "icon": "bi-box-arrow-right", "min_role": "user", "parent": None, "section": "settings"},
}

NAV_SECTIONS = OrderedDict([
    ("general", "Genel"),
    ("inventory", "Envanter"),
    ("operations", "İşlemler"),
    ("settings", "Ayarlar"),
])

ENDPOINT_TO_NAV_KEY = {value["endpoint"]: key for key, value in NAV_ITEMS.items()}


def resolve_active_nav_key(active_page: str | None, endpoint: str | None) -> str | None:
    if active_page and active_page in NAV_ITEMS:
        return active_page
    if endpoint and endpoint in ENDPOINT_TO_NAV_KEY:
        return ENDPOINT_TO_NAV_KEY[endpoint]
    return None


def build_sidebar_sections(user, active_page: str | None, endpoint: str | None) -> list[dict[str, Any]]:
    active_key = resolve_active_nav_key(active_page, endpoint)
    sections: list[dict[str, Any]] = []
    for section_key, section_title in NAV_SECTIONS.items():
        items = []
        for key, item in NAV_ITEMS.items():
            if item["section"] != section_key:
                continue
            if not has_system_role(user, item["min_role"]):
                continue
            items.append({
                "key": key,
                "title": item["title"],
                "endpoint": item["endpoint"],
                "icon": item["icon"],
                "is_active": key == active_key,
            })
        if items:
            sections.append({"key": section_key, "title": section_title, "nav_items": items})
    return sections


def build_breadcrumbs(active_page: str | None, endpoint: str | None) -> list[dict[str, str]]:
    active_key = resolve_active_nav_key(active_page, endpoint)
    if not active_key:
        return []

    chain: list[dict[str, str]] = []
    cursor = active_key
    visited: set[str] = set()
    while cursor and cursor not in visited:
        visited.add(cursor)
        item = NAV_ITEMS.get(cursor)
        if not item:
            break
        chain.append({"title": item["title"], "endpoint": item["endpoint"]})
        cursor = item["parent"]

    return list(reversed(chain))
