import os
import tempfile
from io import BytesIO
from pathlib import Path
import unittest

from app import create_app, db, MAX_INFO_UPLOAD_SIZE
from app.models import InfoAttachment, InfoCategory, User


class InformationUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database_tmp.close()

        self.original_data_dir = os.environ.get("DATA_DIR")
        self.original_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATA_DIR"] = self.temp_dir.name
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_tmp.name}"

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            category = InfoCategory(name="Test")
            user = User(
                username="tester",
                first_name="Test",
                last_name="User",
                email="test@example.com",
                password_hash="hash",
                system_role="admin",
                must_change_password=False,
            )
            db.session.add_all([category, user])
            db.session.commit()
            self.category_id = category.id
            self.user_id = user.id

    def tearDown(self):
        self.temp_dir.cleanup()
        Path(self.database_tmp.name).unlink(missing_ok=True)

        if self.original_data_dir is None:
            os.environ.pop("DATA_DIR", None)
        else:
            os.environ["DATA_DIR"] = self.original_data_dir

        if self.original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.original_database_url

    def login(self):
        with self.client.session_transaction() as session:
            session["active_user_id"] = self.user_id

    def test_rejects_disallowed_extension(self):
        self.login()
        response = self.client.post(
            "/bilgiler",
            data={
                "title": "Güvenlik",
                "category_id": str(self.category_id),
                "content": "Izin verilmeyen dosya denemesi",
                "attachments": (
                    BytesIO(b"<html></html>"),
                    "payload.html",
                    "text/html",
                ),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Bu dosya türüne izin verilmiyor", response.get_data(as_text=True))

        with self.app.app_context():
            self.assertIsNone(InfoAttachment.query.first())

    def test_rejects_oversized_file(self):
        self.login()
        too_large = BytesIO(b"x" * (MAX_INFO_UPLOAD_SIZE + 1))
        response = self.client.post(
            "/bilgiler",
            data={
                "title": "Buyuk Dosya",
                "category_id": str(self.category_id),
                "content": "Boyut kontrolu",
                "attachments": (
                    too_large,
                    "large.pdf",
                    "application/pdf",
                ),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Dosya boyutu en fazla 10 MB", response.get_data(as_text=True))

        with self.app.app_context():
            self.assertEqual(InfoAttachment.query.count(), 0)

    def test_document_download_is_attachment(self):
        self.login()
        upload_response = self.client.post(
            "/bilgiler",
            data={
                "title": "Döküman",
                "category_id": str(self.category_id),
                "content": "Dokuman eklendi",
                "attachments": (
                    BytesIO(b"%PDF-1.4 test"),
                    "manual.pdf",
                    "application/pdf",
                ),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(upload_response.status_code, 302)

        with self.app.app_context():
            attachment = InfoAttachment.query.first()
            self.assertIsNotNone(attachment)
            filename = attachment.filename

        download = self.client.get(f"/uploads/info/{filename}")
        disposition = download.headers.get("Content-Disposition", "")
        self.assertIn("attachment", disposition.lower())


if __name__ == "__main__":
    unittest.main()
