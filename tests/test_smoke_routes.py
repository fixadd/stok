import os
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from app import calculate_maintenance_status, create_app, load_dashboard_metrics
from app.legacy import seed_initial_data
from app.models import (
    HardwareType,
    InventoryEvent,
    InventoryItem,
    InventoryMaintenance,
    User,
    db,
)
from app.services.maintenance_service import MAINTENANCE_INTERVAL_DAYS


class SmokeRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DATA_DIR"] = self.tmp.name
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        with self.app.app_context():
            seed_initial_data()
            admin = User.query.filter_by(username="admin").first()
            admin.must_change_password = False
            self.admin_id = admin.id
            user = (
                User.query.filter(User.system_role == "user").order_by(User.id).first()
            )
            if user is None:
                user = User(
                    username="smoke_user",
                    first_name="Smoke",
                    last_name="User",
                    email="smoke_user@example.com",
                    password_hash="hash",
                    system_role="user",
                )
                db.session.add(user)
                db.session.flush()
            user.must_change_password = False
            self.user_id = user.id
            db.session.commit()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DATA_DIR", None)

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session["active_user_id"] = user_id

    def test_database_url_environment_overrides_default(self):
        previous_database_url = os.environ.get("DATABASE_URL")
        custom_database_url = "postgresql+psycopg://stok:stok_ci_password@127.0.0.1:5432/stok_ci"
        os.environ["DATABASE_URL"] = custom_database_url
        try:
            custom_app = create_app()
            self.assertEqual(custom_app.config["SQLALCHEMY_DATABASE_URI"], custom_database_url)
            self.assertEqual(custom_app.config["DATA_DIR"], Path(os.environ["DATA_DIR"]))
        finally:
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url

    def test_login_page(self):
        resp = self.client.get("/giris")
        self.assertEqual(resp.status_code, 200)

    def test_home_inventory_stock_requests_admin_access(self):
        self.login_as(self.admin_id)
        for path in ["/", "/envanter-takip", "/bakim", "/stok-takip", "/talep-takip", "/admin-panel"]:
            with self.subTest(path=path):
                resp = self.client.get(path)
                self.assertEqual(resp.status_code, 200)

    def test_sidebar_and_breadcrumb_are_metadata_driven(self):
        self.login_as(self.admin_id)
        resp = self.client.get("/stok-takip")
        html = resp.get_data(as_text=True)
        self.assertIn("Stok Takip", html)
        self.assertIn("breadcrumb", html)
        self.assertIn("Ana Sayfa", html)

    def test_calculate_maintenance_status_thresholds(self):
        now = datetime.utcnow()
        self.assertEqual(calculate_maintenance_status(None)["status"], "none")
        self.assertEqual(
            calculate_maintenance_status(now - timedelta(days=MAINTENANCE_INTERVAL_DAYS + 1))["status"],
            "overdue",
        )
        self.assertEqual(
            calculate_maintenance_status(now - timedelta(days=MAINTENANCE_INTERVAL_DAYS - 14))["status"],
            "warning",
        )
        self.assertEqual(
            calculate_maintenance_status(now - timedelta(days=MAINTENANCE_INTERVAL_DAYS - 16))["status"],
            "ok",
        )

    def test_maintenance_breadcrumb_follows_stock_parent(self):
        self.login_as(self.admin_id)
        resp = self.client.get("/bakim")
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        breadcrumb_start = html.index('<ol class="breadcrumb')
        breadcrumb_end = html.index("</ol>", breadcrumb_start)
        breadcrumb_html = html[breadcrumb_start:breadcrumb_end]
        self.assertIn('href="/stok-takip"', breadcrumb_html)
        self.assertLess(breadcrumb_html.index("Ana Sayfa"), breadcrumb_html.index("Stok Takip"))
        self.assertLess(breadcrumb_html.index("Stok Takip"), breadcrumb_html.index("Bakım"))

    def test_dashboard_includes_maintenance_counts(self):
        self.login_as(self.admin_id)
        with self.app.app_context():
            computer_type = HardwareType.query.filter(HardwareType.name.ilike("%laptop%")).first()
            self.assertIsNotNone(computer_type)
            item = InventoryItem.query.filter_by(hardware_type_id=computer_type.id).first()
            self.assertIsNotNone(item)
            db.session.add(
                InventoryMaintenance(
                    item_id=item.id,
                    performed_at=datetime.utcnow() - timedelta(days=100),
                    performed_by="Test Dashboard",
                    note="Dashboard sınırı için test bakımı",
                )
            )
            db.session.commit()
            metrics = load_dashboard_metrics()
        self.assertIn("maintenance_due_count", metrics)
        self.assertIn("maintenance_warning_count", metrics)
        self.assertGreaterEqual(metrics["maintenance_due_count"], 1)
        self.assertEqual(
            metrics["critical_alerts"],
            metrics["faulty_inventory"] + metrics["problem_stock"] + metrics["maintenance_due_count"],
        )
        resp = self.client.get("/")
        html = resp.get_data(as_text=True)
        self.assertIn("Bakım Zamanı Gelenler", html)
        self.assertIn("/bakim", html)

    def test_create_maintenance_record_adds_inventory_event(self):
        self.login_as(self.admin_id)
        with self.app.app_context():
            computer_type = HardwareType.query.filter(HardwareType.name.ilike("%laptop%")).first()
            item = InventoryItem.query.filter_by(hardware_type_id=computer_type.id).first()
            item_id = item.id
        resp = self.client.post(
            f"/api/inventory/{item_id}/maintenance",
            json={
                "performed_at": "2026-06-12T10:30",
                "performed_by": "BT Ekibi",
                "note": "Fan temizliği ve termal bakım yapıldı.",
            },
        )
        self.assertEqual(resp.status_code, 201)
        with self.app.app_context():
            self.assertEqual(InventoryMaintenance.query.filter_by(item_id=item_id).count(), 1)
            self.assertIsNotNone(
                InventoryEvent.query.filter_by(
                    item_id=item_id, event_type="Bakım Yapıldı", performed_by="BT Ekibi"
                ).first()
            )
