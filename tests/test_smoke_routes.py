import os
from datetime import date
from pathlib import Path
import tempfile
import unittest

from app import calculate_maintenance_status, create_app, load_dashboard_metrics
from app.models import (
    ActivityLog,
    HardwareType,
    InventoryEvent,
    InventoryItem,
    InventoryMaintenance,
    InventoryLicense,
    User,
    db,
)


class SmokeRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.database_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database_tmp.close()
        self.previous_data_dir = os.environ.get("DATA_DIR")
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATA_DIR"] = self.tmp.name
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_tmp.name}"

        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        with self.app.app_context():
            admin = User.query.filter_by(username="admin").first()
            admin.must_change_password = False
            self.admin_id = admin.id
            user = (
                User.query.filter(User.system_role == "user").order_by(User.id).first()
            )
            user.must_change_password = False
            self.user_id = user.id
            db.session.commit()

    def tearDown(self):
        self.tmp.cleanup()
        Path(self.database_tmp.name).unlink(missing_ok=True)
        if self.previous_data_dir is None:
            os.environ.pop("DATA_DIR", None)
        else:
            os.environ["DATA_DIR"] = self.previous_data_dir
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session["active_user_id"] = user_id

    def test_database_url_configures_database(self):
        with self.app.app_context():
            self.assertEqual(
                self.app.config["SQLALCHEMY_DATABASE_URI"],
                f"sqlite:///{self.database_tmp.name}",
            )

    def test_login_page(self):
        resp = self.client.get("/giris")
        self.assertEqual(resp.status_code, 200)

    def test_home_inventory_stock_requests_admin_access(self):
        self.login_as(self.admin_id)
        for path in [
            "/",
            "/envanter-takip",
            "/bakim",
            "/stok-takip",
            "/talep-takip",
            "/lisans-takip",
            "/personnel-lifecycle/",
            "/admin-panel",
        ]:
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
        today = date(2026, 6, 17)

        self.assertEqual(
            calculate_maintenance_status(None, today=today)["status"], "none"
        )
        self.assertEqual(
            calculate_maintenance_status(date(2025, 6, 17), today=today)["status"],
            "overdue",
        )
        self.assertEqual(
            calculate_maintenance_status(date(2025, 7, 17), today=today)["status"],
            "warning",
        )
        self.assertEqual(
            calculate_maintenance_status(date(2025, 7, 17), today=today)["label"],
            "1 ay içinde bakım",
        )
        self.assertEqual(
            calculate_maintenance_status(date(2025, 7, 18), today=today)["status"],
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
        self.assertLess(
            breadcrumb_html.index("Ana Sayfa"), breadcrumb_html.index("Stok Takip")
        )
        self.assertLess(
            breadcrumb_html.index("Stok Takip"), breadcrumb_html.index("Bakım")
        )

    def test_dashboard_includes_maintenance_counts(self):
        self.login_as(self.admin_id)
        with self.app.app_context():
            metrics = load_dashboard_metrics()

        self.assertIn("maintenance_due_count", metrics)
        self.assertIn("maintenance_warning_count", metrics)
        self.assertGreaterEqual(metrics["maintenance_due_count"], 1)
        self.assertEqual(
            metrics["critical_alerts"],
            metrics["faulty_inventory"]
            + metrics["problem_stock"]
            + metrics["maintenance_due_count"],
        )

        resp = self.client.get("/")
        html = resp.get_data(as_text=True)
        self.assertIn("Bakım Zamanı Gelenler", html)
        self.assertIn("/bakim", html)

    def test_create_maintenance_record_adds_inventory_event(self):
        self.login_as(self.admin_id)
        with self.app.app_context():
            computer_type = HardwareType.query.filter(
                HardwareType.name.ilike("%laptop%")
            ).first()
            item = InventoryItem.query.filter_by(
                hardware_type_id=computer_type.id
            ).first()
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
            self.assertEqual(
                InventoryMaintenance.query.filter_by(item_id=item_id).count(), 1
            )
            self.assertIsNotNone(
                InventoryEvent.query.filter_by(
                    item_id=item_id,
                    event_type="Bakım Yapıldı",
                    performed_by="BT Ekibi",
                ).first()
            )

    def test_admin_access_control_for_regular_user(self):
        self.login_as(self.user_id)
        resp = self.client.get("/admin-panel", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_sidebar_hides_admin_links_for_regular_user(self):
        self.login_as(self.user_id)
        resp = self.client.get("/")
        html = resp.get_data(as_text=True)
        self.assertNotIn("Admin Paneli", html)

    def test_regular_user_cannot_mutate_inventory(self):
        self.login_as(self.user_id)
        with self.app.app_context():
            computer_type = HardwareType.query.filter(
                HardwareType.name.ilike("%laptop%")
            ).first()
            item = InventoryItem.query.filter_by(
                hardware_type_id=computer_type.id
            ).first()
            item_id = item.id

        resp = self.client.post(
            f"/api/inventory/{item_id}/mark-faulty",
            json={"reason": "test"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_license_history_is_record_based(self):
        self.login_as(self.admin_id)
        with self.app.app_context():
            license_record = InventoryLicense.query.first()
            license_id = license_record.id

            db.session.add(
                ActivityLog(
                    area="lisans",
                    action="Test geçmiş kaydı",
                    description="Kayıt bazlı geçmiş testi.",
                    actor="Test",
                    metadata_payload={"license_id": license_id},
                )
            )
            db.session.commit()

        resp = self.client.get(f"/api/licenses/{license_id}/history")
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertEqual(payload["license_id"], license_id)
        self.assertTrue(any(item["title"] == "Test geçmiş kaydı" for item in payload["history"]))


if __name__ == "__main__":
    unittest.main()
