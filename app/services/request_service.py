from __future__ import annotations

from typing import Any, Callable

from ..queries import catalog_queries, request_queries


def load_tracking_payload(
    *,
    serialize_order: Callable[[Any], dict[str, Any]],
    metadata_config: dict[str, Any],
    support_options: dict[str, list[str]],
    category_labels: dict[str, str],
) -> dict[str, Any]:
    groups_payload: list[dict[str, Any]] = []
    for group in request_queries.list_groups_with_relations():
        groups_payload.append(
            {
                "key": group.key,
                "label": group.label,
                "description": group.description,
                "empty_message": group.empty_message,
                "orders": [serialize_order(order) for order in group.orders],
            }
        )

    brands = catalog_queries.list_brands_with_models()
    models_by_brand = {
        brand.name: [model.name for model in brand.models]
        for brand in brands
    }
    hardware_catalog = {
        "types": [hardware_type.name for hardware_type in catalog_queries.list_hardware_types()],
        "brands": [brand.name for brand in brands],
        "models": [model.name for model in _list_models()],
        "models_by_brand": models_by_brand,
    }

    return {
        "request_groups": groups_payload,
        "hardware_catalog": hardware_catalog,
        "stock_metadata_config": metadata_config,
        "stock_support_options": support_options,
        "stock_category_labels": category_labels,
    }


def _list_models():
    from ..models import HardwareModel

    return HardwareModel.query.order_by(HardwareModel.name).all()
