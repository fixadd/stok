"""Application package entrypoint.

The historical monolithic implementation lives in ``legacy.py`` while the
package entrypoint stays intentionally small. Cross-cutting HTTP security and
DB-backed stock metadata are attached here so route modules do not need to
know about infrastructure.
"""

from .legacy import *  # noqa: F401,F403
from .legacy import app, db
from .bootstrap import configure_security
from .services.stock_metadata import configure_stock_metadata

configure_security(app)

# Alembic owns the schema. Metadata is loaded from PostgreSQL after the
# application has been created, so the existing route functions can consume
# the same global configuration without duplicating field definitions.
_db_metadata = configure_stock_metadata()
if _db_metadata:
    STOCK_METADATA_FIELDS = _db_metadata
    try:
        import sys
        _legacy_module = sys.modules.get("app.legacy")
        if _legacy_module is not None:
            _legacy_module.STOCK_METADATA_FIELDS = _db_metadata
    except Exception:
        pass

__all__ = ["app", "db"]
