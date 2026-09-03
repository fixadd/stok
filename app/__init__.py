"""Application package entrypoint.

The historical monolithic implementation lives in ``legacy.py`` while the
package entrypoint stays intentionally small. Cross-cutting HTTP security and
DB-backed stock metadata are attached here so route modules do not need to
know about infrastructure.
"""

import sys

from .legacy import *  # noqa: F401,F403
from .legacy import app, db
from .bootstrap import configure_security
from .services.inventory_payloads import build_inventory_stock_metadata as _service_build_inventory_stock_metadata
from .services.stock_metadata import configure_stock_metadata
from .services.stock_payloads import (
    json_error as _service_json_error,
    prepare_stock_metadata as _service_prepare_stock_metadata,
)

configure_security(app)

# Alembic owns the schema. Metadata is loaded from PostgreSQL after the
# application has been created, so the existing route functions can consume
# the same global configuration without duplicating field definitions.
_db_metadata = configure_stock_metadata()
_legacy_module = sys.modules.get("app.legacy")
if _legacy_module is not None:
    # These helpers are being moved out of the historical monolith. Keeping
    # their old names avoids a flag-day rewrite of all legacy call sites.
    _legacy_module.build_inventory_stock_metadata = _service_build_inventory_stock_metadata
    _legacy_module.json_error = _service_json_error
    if _db_metadata:
        STOCK_METADATA_FIELDS = _db_metadata
        _legacy_module.STOCK_METADATA_FIELDS = _db_metadata
        _legacy_module.prepare_stock_metadata = lambda category, payload, **kwargs: _service_prepare_stock_metadata(
            category,
            payload,
            schema=_db_metadata,
            **kwargs,
        )

__all__ = ["app", "db"]
