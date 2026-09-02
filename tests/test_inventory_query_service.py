from app.services import inventory_query_service


def test_inventory_query_service_exports_expected_operations():
    assert callable(inventory_query_service.get_item)
    assert callable(inventory_query_service.get_by_inventory_no)
    assert callable(inventory_query_service.list_items)
    assert callable(inventory_query_service.list_scrap_items)
    assert callable(inventory_query_service.list_by_responsible_user)
    assert callable(inventory_query_service.list_by_factory)
    assert callable(inventory_query_service.count_by_status)
