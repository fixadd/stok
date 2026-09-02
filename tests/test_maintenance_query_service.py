from app.services import maintenance_query_service


def test_maintenance_query_service_exports_expected_operations():
    assert callable(maintenance_query_service.get_item)
    assert callable(maintenance_query_service.get_record)
    assert callable(maintenance_query_service.list_records)
    assert callable(maintenance_query_service.list_items)
    assert callable(maintenance_query_service.list_recent)
    assert callable(maintenance_query_service.list_by_performer)
