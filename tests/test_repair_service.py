from datetime import datetime
from decimal import Decimal

from app.services.repair_service import (
    REPAIR_STATUSES,
    WARRANTY_STATUSES,
    _apply_item_status,
    _cost,
    _parse_datetime,
)


class DummyItem:
    status = "aktif"


def test_repair_status_catalog_contains_expected_flow():
    assert REPAIR_STATUSES["bekliyor"] == "Servise Gönderilecek"
    assert REPAIR_STATUSES["serviste"] == "Serviste"
    assert REPAIR_STATUSES["geri_geldi"] == "Geri Geldi"
    assert REPAIR_STATUSES["tamir_edilemedi"] == "Tamir Edilemedi"


def test_warranty_status_catalog_contains_expected_values():
    assert WARRANTY_STATUSES["garantili"] == "Garanti Kapsamında"
    assert WARRANTY_STATUSES["garantisiz"] == "Garanti Dışı"


def test_parse_datetime_accepts_iso_datetime():
    value, error = _parse_datetime("2026-09-02T09:30")
    assert error is None
    assert value == datetime(2026, 9, 2, 9, 30)


def test_parse_datetime_validates_required_and_invalid_values():
    value, error = _parse_datetime("", "Arıza tarihi", required=True)
    assert value is None
    assert error == "Arıza tarihi zorunludur."

    value, error = _parse_datetime("not-a-date", "Arıza tarihi")
    assert value is None
    assert error == "Arıza tarihi geçerli bir tarih olmalıdır."


def test_cost_accepts_decimal_and_rejects_negative_values():
    value, error = _cost("1250,50")
    assert error is None
    assert value == Decimal("1250.50")

    value, error = _cost("-1")
    assert value is None
    assert error == "Servis ücreti geçerli bir tutar olmalıdır."


def test_apply_item_status_follows_repair_lifecycle():
    item = DummyItem()

    _apply_item_status(item, "serviste")
    assert item.status == "arizali"

    _apply_item_status(item, "tamir_edildi")
    assert item.status == "aktif"

    _apply_item_status(item, "hurda")
    assert item.status == "hurda"
