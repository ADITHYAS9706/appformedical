import unittest

from app.core.config import settings
from app.services.intelligence.llm import get_chat_model


class TestGeminiProvider(unittest.TestCase):
    def test_gemini_provider_builds_chat_model(self):
        original_provider = settings.llm_provider
        original_model = settings.llm_model
        original_key = settings.google_api_key

        settings.llm_provider = "gemini"
        settings.llm_model = "gemini-2.5-flash"
        settings.google_api_key = "test-key"
        get_chat_model.cache_clear()

        try:
            model = get_chat_model()
            self.assertIsNotNone(model)
            self.assertEqual(model.model, "gemini-2.5-flash")
        finally:
            settings.llm_provider = original_provider
            settings.llm_model = original_model
            settings.google_api_key = original_key
            get_chat_model.cache_clear()


if __name__ == "__main__":
    unittest.main()
