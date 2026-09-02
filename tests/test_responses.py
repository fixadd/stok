from app.services.responses import error, ok


def test_ok_response_sets_success_true():
    assert ok(message="Tamam") == {"success": True, "message": "Tamam"}


def test_error_response_sets_success_false_and_message():
    assert error("Geçersiz veri", field="name") == {
        "success": False,
        "error": "Geçersiz veri",
        "field": "name",
    }
