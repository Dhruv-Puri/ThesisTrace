import os
import unittest
from pathlib import Path

from api.pipeline import config


class ConfigTests(unittest.TestCase):
    def test_default_data_dir_is_project_local(self):
        if os.environ.get("P2R_DATA_DIR"):
            self.skipTest("P2R_DATA_DIR is overridden (Docker mounts /data)")
        self.assertEqual(config.DATA_DIR.resolve(), (config.ROOT / ".data").resolve())
        self.assertTrue(config.UPLOAD_DIR.resolve().is_relative_to(config.ROOT.resolve()))

    def test_hugging_face_cache_defaults_inside_the_project(self):
        if os.environ.get("P2R_DATA_DIR"):
            self.skipTest("Docker sets HF_HOME explicitly to /models/hf")
        self.assertTrue(Path(os.environ["HF_HOME"]).resolve().is_relative_to(config.ROOT))

    def test_public_config_never_exposes_the_key(self):
        payload = config.public_config()
        self.assertNotIn("GEMINI_API_KEY", payload)
        self.assertNotIn("api_key", " ".join(payload).lower())
        self.assertIn("gemini_enabled", payload)

    def test_dirs_are_created_under_the_project(self):
        before = config.UPLOAD_DIR.exists()
        config.ensure_dirs()
        self.assertTrue(config.UPLOAD_DIR.is_dir())
        self.assertTrue(config.UPLOAD_DIR.resolve().is_relative_to(config.ROOT.resolve()))
        if not before:
            config.UPLOAD_DIR.rmdir()


if __name__ == "__main__":
    unittest.main()
