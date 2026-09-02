from app.services import request_query_service


def test_request_query_service_exports_expected_operations():
    assert callable(request_query_service.get_group)
    assert callable(request_query_service.get_group_by_key)
    assert callable(request_query_service.list_groups)
    assert callable(request_query_service.get_order)
    assert callable(request_query_service.get_order_by_number)
    assert callable(request_query_service.list_orders)
    assert callable(request_query_service.list_orders_by_requester)
    assert callable(request_query_service.list_orders_by_department)
    assert callable(request_query_service.list_order_lines)
