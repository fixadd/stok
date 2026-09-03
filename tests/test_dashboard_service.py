from datetime import datetime, timedelta

from app.models import HardwareType, InventoryItem, InventoryMaintenance, db
from app.services.dashboard_service import load_maintenance_metrics


def test_dashboard_maintenance_metrics_use_latest_record(app):
    with app.app_context():
        hardware_type = HardwareType(name="Laptop")
        db.session.add(hardware_type)
        db.session.flush()
        item = InventoryItem(
            inventory_no="DASH-TEST-001",
            status="aktif",
            hardware_type_id=hardware_type.id,
        )
        db.session.add(item)
        db.session.flush()
        db.session.add_all([
            InventoryMaintenance(
                item_id=item.id,
                performed_at=datetime.utcnow() - timedelta(days=200),
                performed_by="Test",
            ),
            InventoryMaintenance(
                item_id=item.id,
                performed_at=datetime.utcnow() - timedelta(days=5),
                performed_by="Test",
            ),
        ])
        db.session.commit()

        metrics = load_maintenance_metrics()

        assert metrics["maintenance_current_count"] >= 1
        assert metrics["maintenance_overdue_count"] == 0
