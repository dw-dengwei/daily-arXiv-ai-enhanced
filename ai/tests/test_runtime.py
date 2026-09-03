import unittest

from runtime import build_chat_openai_kwargs, raise_if_processing_failed


class BuildChatOpenAIKwargsTests(unittest.TestCase):
    def test_openai_configuration_strips_key_and_omits_provider_extensions(self):
        """Catches accidentally sending a provider-specific `thinking` field to OpenAI."""
        kwargs = build_chat_openai_kwargs(
            model_name="gpt-4.1-mini",
            base_url="https://api.openai.com/v1/",
            api_key="  sk-test-key  ",
        )

        self.assertEqual("gpt-4.1-mini", kwargs["model"])
        self.assertEqual("https://api.openai.com/v1", kwargs["base_url"])
        self.assertEqual("sk-test-key", kwargs["api_key"])
        self.assertNotIn("extra_body", kwargs)

    def test_volcengine_configuration_disables_thinking_with_extra_body(self):
        """Catches losing the Ark-specific request option required by the current model."""
        kwargs = build_chat_openai_kwargs(
            model_name="doubao-seed-1.6-250615",
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key="ark-test-key",
        )

        self.assertEqual(
            {"thinking": {"type": "disabled"}},
            kwargs["extra_body"],
        )

    def test_processing_error_is_reported_after_a_batch(self):
        """Catches swallowing authentication failures and publishing fallback summaries."""
        with self.assertRaisesRegex(RuntimeError, r"2 paper\(s\) failed"):
            raise_if_processing_failed(["401 Unauthorized", "401 Unauthorized"])


if __name__ == "__main__":
    unittest.main()
