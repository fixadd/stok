from datetime import datetime
from decimal import Decimal

from app.services.repair_service import (
    APPROVAL_STATUSES,
    REPAIR_STATUSES,
    TESTING_STATUSES,
    WARRANTY_STATUSES,
    _apply_item_status,
    _parse_bool,
    _parse_cost,
    _parse_datetime,
    _validate,
)


class DummyItem:
    status = "aktif"


def test_repair_status_catalog_contains_expected_flow():
    assert REPAIR_STATUSES["bekliyor"] == "Servise Gönderilecek"
    assert REPAIR_STATUSES["serviste"] == "Serviste"
    assert REPAIR_STATUSES["geri_geldi"] == "Geri Geldi"
    assert REPAIR_STATUSES["tamir_edilemedi"] == "Tamir Edilemedi"


def test_warranty_and_quality_catalogs_are_defined():
    assert WARRANTY_STATUSES["garantili"] == "Garanti Kapsamında"
    assert WARRANTY_STATUSES["garantisiz"] == "Garanti Dışı"
    assert TESTING_STATUSES["basarili"] == "Test Başarılı"
    assert APPROVAL_STATUSES["onaylandi"] == "Onaylandı"


def test_parse_datetime_accepts_iso_datetime_and_rejects_invalid_values():
    value, error = _parse_datetime("2026-09-02T09:30", "Arıza tarihi")
    assert error is None
    assert value == datetime(2026, 9, 2, 9, 30)

    value, error = _parse_datetime("not-a-date", "Arıza tarihi")
    assert value is None
    assert error == "Arıza tarihi geçerli bir tarih olmalıdır."


def test_parse_cost_accepts_decimal_and_rejects_negative_values():
    value, error = _parse_cost("1250,50")
    assert error is None
    assert value == Decimal("1250.50")

    value, error = _parse_cost("-1")
    assert value is None
    assert error == "Servis ücreti negatif olamaz."


def test_parse_bool_handles_common_payload_values():
    assert _parse_bool(True, "Servis")[0] is True
    assert _parse_bool("true", "Servis")[0] is True
    assert _parse_bool("false", "Servis")[0] is False
    assert _parse_bool("0", "Servis")[0] is False


def test_parse_bool_rejects_ambiguous_values():
    value, error = _parse_bool("maybe", "Servis")
    assert value is False
    assert error == "Servis geçerli bir boolean değeri olmalıdır."


def test_apply_item_status_follows_repair_lifecycle():
    item = DummyItem()

    _apply_item_status(item, "serviste")
    assert item.status == "arizali"

    _apply_item_status(item, "tamir_edildi")
    assert item.status == "aktif"

    _apply_item_status(item, "hurda")
    assert item.status == "hurda"


def valid_payload():
    return {
        "problem_description": "Disk arızası",
        "sent_to_service": True,
        "sent_at": "2026-09-02T10:00",
        "expected_return_at": "2026-09-05T10:00",
        "status": "serviste",
        "warranty_status": "garantili",
        "sla_due_at": "2026-09-06T10:00",
    }


def test_validate_accepts_consistent_service_payload():
    values, error = _validate(valid_payload())
    assert error is None
    assert values["sent_to_service"] is True
    assert values["expected_return_at"] == datetime(2026, 9, 5, 10, 0)


def test_validate_rejects_expected_return_before_sent_at():
    payload = valid_payload()
    payload["expected_return_at"] = "2026-09-01T10:00"
    values, error = _validate(payload)
    assert values is None
    assert "gönderim tarihinden önce" in error


def test_validate_requires_sent_at_when_sent_to_service():
    payload = valid_payload()
    payload["sent_at"] = None
    payload["expected_return_at"] = None
    values, error = _validate(payload)
    assert values is None
    assert "gönderim tarihi zorunludur" in error


def test_validate_requires_test_actor_and_date_for_completed_test():
    payload = valid_payload()
    payload.update({"testing_status": "basarili"})
    values, error = _validate(payload)
    assert values is None
    assert "test tarihi" in error


def test_validate_requires_successful_test_for_approval():
    payload = valid_payload()
    payload.update({
        "testing_status": "basarisiz",
        "tested_at": "2026-09-06T10:00",
        "tested_by": "Teknisyen",
        "approval_status": "onaylandi",
        "approved_at": "2026-09-06T11:00",
        "approved_by": "Admin",
    })
    values, error = _validate(payload)
    assert values is None
    assert "test sonucu başarılı" in error
