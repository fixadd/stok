from app.services import (
    assignment_service,
    catalog_service,
    event_service,
    inventory_query_service,
    license_service,
    maintenance_query_service,
    request_query_service,
    stock_query_service,
)


def test_domain_services_are_exported():
    assert assignment_service is not None
    assert catalog_service is not None
    assert event_service is not None
    assert inventory_query_service is not None
    assert license_service is not None
    assert maintenance_query_service is not None
    assert request_query_service is not None
    assert stock_query_service is not None
