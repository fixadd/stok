import os
import tempfile
import unittest

from app import create_app
from app.models import User, db


class SmokeRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DATA_DIR"] = self.tmp.name
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        with self.app.app_context():
            admin = User.query.filter_by(username="admin").first()
            admin.must_change_password = False
            self.admin_id = admin.id
            user = User.query.filter(User.system_role == "user").order_by(User.id).first()
            user.must_change_password = False
            self.user_id = user.id
            db.session.commit()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("DATA_DIR", None)

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session["active_user_id"] = user_id

    def test_login_page(self):
        resp = self.client.get("/giris")
        self.assertEqual(resp.status_code, 200)

    def test_home_inventory_stock_requests_admin_access(self):
        self.login_as(self.admin_id)
        for path in ["/", "/envanter-takip", "/stok-takip", "/talep-takip", "/admin-panel"]:
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

    def test_admin_access_control_for_regular_user(self):
        self.login_as(self.user_id)
        resp = self.client.get("/admin-panel", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_sidebar_hides_admin_links_for_regular_user(self):
        self.login_as(self.user_id)
        resp = self.client.get("/")
        html = resp.get_data(as_text=True)
        self.assertNotIn("Admin Paneli", html)


if __name__ == "__main__":
    unittest.main()
