"""Application service layer grouped by domain."""

from . import (
    assignment_service,
    catalog_service,
    dashboard_service,
    event_service,
    inventory_query_service,
    license_service,
    maintenance_query_service,
    request_query_service,
    stock_query_service,
    user_query_service,
)

__all__ = [
    "assignment_service",
    "catalog_service",
    "dashboard_service",
    "event_service",
    "inventory_query_service",
    "license_service",
    "maintenance_query_service",
    "request_query_service",
    "stock_query_service",
    "user_query_service",
]
