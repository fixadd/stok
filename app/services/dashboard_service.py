"""Dashboard read-model helpers.

Dashboard aggregation belongs in the service layer so the application entrypoint
and route modules do not need to know how maintenance state is calculated.
"""

from __future__ import annotations

from typing import Any

from .maintenance_service import load_payload as load_maintenance_payload


def load_dashboard_metrics() -> dict[str, Any]:
    """Return dashboard maintenance metrics from the canonical maintenance service."""
    payload = load_maintenance_payload({})
    return {
        key: value
        for key, value in payload.items()
        if key.startswith("maintenance_")
    }
