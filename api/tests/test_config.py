import os
import unittest
from pathlib import Path
from unittest import mock

from api.pipeline import config


class ConfigTests(unittest.TestCase):
    def test_default_data_dir_is_project_local(self):
        if (os.environ.get("THESISTRACE_DATA_DIR") or os.environ.get("P2R_DATA_DIR")):
            self.skipTest("data directory is overridden")
        self.assertEqual(config.DATA_DIR.resolve(), (config.ROOT / ".data").resolve())
        self.assertTrue(config.UPLOAD_DIR.resolve().is_relative_to(config.ROOT.resolve()))

    def test_hugging_face_cache_defaults_inside_the_project(self):
        if (os.environ.get("THESISTRACE_DATA_DIR") or os.environ.get("P2R_DATA_DIR")):
            self.skipTest("Docker sets the data directory and HF_HOME explicitly")
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

    def test_new_env_prefix_wins_and_legacy_prefix_still_works(self):
        clean = {k: v for k, v in os.environ.items() if k not in {"P2R_MAX_PAGES", "THESISTRACE_MAX_PAGES"}}
        with mock.patch.dict(os.environ, clean, clear=True):
            self.assertEqual(config._env("MAX_PAGES", "60"), "60")
            os.environ["P2R_MAX_PAGES"] = "11"
            self.assertEqual(config._env("MAX_PAGES", "60"), "11")
            os.environ["THESISTRACE_MAX_PAGES"] = "22"
            self.assertEqual(config._env("MAX_PAGES", "60"), "22")

    def test_env_flag_reads_either_prefix(self):
        clean = {k: v for k, v in os.environ.items() if "TOKENIZER_STUDY" not in k}
        with mock.patch.dict(os.environ, clean, clear=True):
            self.assertTrue(config._env_flag("TOKENIZER_STUDY", "1"))
            os.environ["P2R_TOKENIZER_STUDY"] = "0"
            self.assertFalse(config._env_flag("TOKENIZER_STUDY", "1"))


if __name__ == "__main__":
    unittest.main()
