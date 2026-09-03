from app.services.responses import api_error, api_success, error, ok


def test_ok_response_sets_success_true():
    assert ok(message="Tamam") == {"success": True, "message": "Tamam"}


def test_error_response_sets_success_false_and_message():
    assert error("Geçersiz veri", field="name") == {
        "success": False,
        "error": "Geçersiz veri",
        "field": "name",
    }


def test_api_success_uses_standard_envelope():
    assert api_success(data={"id": 1}, message="Oluşturuldu") == {
        "success": True,
        "data": {"id": 1},
        "message": "Oluşturuldu",
    }


def test_api_error_uses_standard_error_object():
    assert api_error("VALIDATION_ERROR", "Geçersiz veri", details={"field": "name"}) == {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Geçersiz veri",
            "details": {"field": "name"},
        },
    }
