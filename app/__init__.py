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
from .services.activity_service import (
    load_activity_logs as _service_load_activity_logs,
    load_recent_activity as _service_load_recent_activity,
    record_activity as _service_record_activity,
)
from .services.dashboard_service import load_dashboard_metrics as _service_load_dashboard_metrics
from .services.inventory_payloads import build_inventory_stock_metadata as _service_build_inventory_stock_metadata
from .services.maintenance_helpers import (
    calculate_maintenance_status as _service_calculate_maintenance_status,
    format_datetime_display as _service_format_datetime_display,
    maintenance_row_class as _service_maintenance_row_class,
    maintenance_status_badge_class as _service_maintenance_status_badge_class,
    serialize_maintenance_record as _service_serialize_maintenance_record,
)
from .services.stock_audit_service import (
    record_stock_audit as _service_record_stock_audit,
    record_stock_log as _service_record_stock_log,
    record_stock_movement as _service_record_stock_movement,
)
from .services.stock_metadata import configure_stock_metadata
from .services.stock_payloads import (
    json_error as _service_json_error,
    prepare_stock_metadata as _service_prepare_stock_metadata,
)

configure_security(app)

_db_metadata = configure_stock_metadata()
_legacy_module = sys.modules.get("app.legacy")
if _legacy_module is not None:
    _legacy_module.build_inventory_stock_metadata = _service_build_inventory_stock_metadata
    _legacy_module.json_error = _service_json_error
    _legacy_module.record_activity = _service_record_activity
    _legacy_module.load_activity_logs = _service_load_activity_logs
    _legacy_module.load_recent_activity = _service_load_recent_activity
    _legacy_module.load_dashboard_metrics = _service_load_dashboard_metrics
    _legacy_module.record_stock_movement = _service_record_stock_movement
    _legacy_module.record_stock_audit = _service_record_stock_audit
    _legacy_module.record_stock_log = _service_record_stock_log
    _legacy_module.format_datetime_display = _service_format_datetime_display
    _legacy_module.serialize_maintenance_record = _service_serialize_maintenance_record
    _legacy_module.calculate_maintenance_status = _service_calculate_maintenance_status
    _legacy_module.maintenance_status_badge_class = _service_maintenance_status_badge_class
    _legacy_module.maintenance_row_class = _service_maintenance_row_class
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
