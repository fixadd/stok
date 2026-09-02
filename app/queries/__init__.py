"""Database query/repository helpers grouped by application domain."""

from . import (
    assignment_queries,
    catalog_queries,
    inventory_event_queries,
    inventory_queries,
    inventory_stock_queries,
    license_queries,
    maintenance_extended_queries,
    maintenance_queries,
    repair_queries,
    request_queries,
    user_queries,
)

__all__ = [
    "assignment_queries",
    "catalog_queries",
    "inventory_event_queries",
    "inventory_queries",
    "inventory_stock_queries",
    "license_queries",
    "maintenance_extended_queries",
    "maintenance_queries",
    "repair_queries",
    "request_queries",
    "user_queries",
]
