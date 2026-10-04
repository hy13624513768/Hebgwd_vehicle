import io
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.services.media_storage_service import delete_media, materialize, parse_reference, save_upload


class MediaStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_upload_dir = settings.upload_dir
        self.old_backend = settings.media_storage_backend
        settings.upload_dir = self.temp_dir.name
        settings.media_storage_backend = "local"

    def tearDown(self):
        settings.upload_dir = self.old_upload_dir
        settings.media_storage_backend = self.old_backend
        self.temp_dir.cleanup()

    @staticmethod
    def upload(filename: str, content_type: str, body: bytes) -> UploadFile:
        return UploadFile(filename=filename, file=io.BytesIO(body), headers={"content-type": content_type})

    def test_local_round_trip_uses_safe_reference_and_hash(self):
        body = b"\x89PNG\r\n\x1a\n" + b"payload"
        stored = save_upload(self.upload("receipt.png", "image/png", body), prefix="fuel/entries/1")

        self.assertEqual(parse_reference(stored.reference), ("local", "", stored.object_key))
        self.assertEqual(len(stored.sha256), 64)
        with materialize(stored.reference) as path:
            self.assertEqual(Path(path).read_bytes(), body)

        delete_media(stored)
        self.assertFalse((Path(self.temp_dir.name) / stored.object_key).exists())

    def test_rejects_spoofed_media_content(self):
        with self.assertRaises(HTTPException) as caught:
            save_upload(self.upload("fake.jpg", "image/jpeg", b"not-a-jpeg"), prefix="repair/records/1")
        self.assertEqual(caught.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
