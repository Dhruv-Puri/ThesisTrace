import unittest
from unittest.mock import patch

from api import prompts
from api.pipeline import config, llm


class PromptTests(unittest.TestCase):
    def test_claims_template_renders_without_leftover_placeholders(self):
        rendered = prompts.render(
            "claims", examples_block="EXAMPLE", context="The method is fast."
        )
        self.assertIn("scientific claim extractor", rendered["system"].lower())
        self.assertIn("EXAMPLE", rendered["user"])
        self.assertIn("The method is fast.", rendered["user"])
        self.assertNotIn("{{", rendered["user"])
        self.assertIn("<document>", rendered["user"])

    def test_unknown_template_is_explicit(self):
        with self.assertRaises(FileNotFoundError):
            prompts.load("does-not-exist")

    def test_llm_is_disabled_without_a_key(self):
        with patch.object(config, "GEMINI_API_KEY", ""):
            self.assertFalse(llm.enabled())
            with self.assertRaises(llm.LLMError) as context:
                llm.generate("hello")
            self.assertEqual(context.exception.code, "LLM_DISABLED")


if __name__ == "__main__":
    unittest.main()
