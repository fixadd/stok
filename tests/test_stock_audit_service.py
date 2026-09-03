from app.services.stock_audit_service import record_stock_audit, record_stock_movement


def test_stock_audit_clamps_quantities_and_uses_actor(monkeypatch):
    added = []

    class FakeSession:
        def add(self, value):
            added.append(value)

    class FakeDB:
        session = FakeSession()

    monkeypatch.setattr("app.services.stock_audit_service.db", FakeDB())

    class FakeItem:
        id = 10

    audit = record_stock_audit(
        FakeItem(),
        old_quantity=-4,
        new_quantity=3,
        performed_by="  Admin  ",
    )

    assert audit.stock_item_id == 10
    assert audit.old_quantity == 0
    assert audit.new_quantity == 3
    assert audit.performed_by == "Admin"
    assert added[-1] is audit


def test_stock_movement_keeps_user_id_and_non_negative_quantities(monkeypatch):
    added = []

    class FakeSession:
        def add(self, value):
            added.append(value)

    class FakeDB:
        session = FakeSession()

    monkeypatch.setattr("app.services.stock_audit_service.db", FakeDB())

    class FakeItem:
        id = 11

    class FakeUser:
        id = 22

    movement = record_stock_movement(
        FakeItem(),
        operation_type="giris",
        old_quantity=-1,
        new_quantity=5,
        user=FakeUser(),
    )

    assert movement.stock_item_id == 11
    assert movement.user_id == 22
    assert movement.old_quantity == 0
    assert movement.new_quantity == 5
    assert added[-1] is movement
