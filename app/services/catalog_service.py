from __future__ import annotations

from typing import Any

from ..queries import catalog_queries
from .responses import ok


CATALOGS = {
    "factories": catalog_queries.list_factories,
    "hardware_types": catalog_queries.list_hardware_types,
    "brands": catalog_queries.list_brands,
    "info_categories": catalog_queries.list_info_categories,
    "license_names": catalog_queries.list_license_names,
    "usage_areas": catalog_queries.list_usage_areas,
}


def load_catalogs(*, limit: int = 100) -> dict[str, Any]:
    """Load reference/catalog data through the query layer."""
    return {name: loader(limit=limit) for name, loader in CATALOGS.items()}


def load_catalog_response(*, limit: int = 100) -> dict[str, Any]:
    return ok(**load_catalogs(limit=limit))
