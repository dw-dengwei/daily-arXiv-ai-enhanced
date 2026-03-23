"""Integration tests for MiniMax provider with the enhance pipeline.

These tests verify end-to-end configuration and LLM instantiation.
Tests that require actual API calls are skipped unless MINIMAX_API_KEY is set.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai"))

from providers import detect_provider, get_provider_config


class TestMiniMaxEndToEnd(unittest.TestCase):
    """Integration tests for MiniMax provider configuration flow."""

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key-123"}, clear=True)
    def test_full_autodetect_flow(self):
        """Test auto-detection -> config resolution -> LLM kwargs pipeline."""
        provider = detect_provider()
        self.assertEqual(provider, "minimax")

        config = get_provider_config(provider)
        self.assertEqual(config["base_url"], "https://api.minimax.io/v1")
        self.assertEqual(config["api_key"], "test-key-123")
        self.assertEqual(config["model_name"], "MiniMax-M2.7")

    @patch.dict(os.environ, {
        "LLM_PROVIDER": "minimax",
        "MINIMAX_API_KEY": "mk",
        "MODEL_NAME": "MiniMax-M2.5-highspeed",
    }, clear=True)
    def test_explicit_provider_with_model_override(self):
        """Test explicit provider + MODEL_NAME override."""
        provider = detect_provider()
        self.assertEqual(provider, "minimax")

        config = get_provider_config(provider)
        self.assertEqual(config["model_name"], "MiniMax-M2.5-highspeed")
        self.assertEqual(config["api_key"], "mk")

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "minimax-key",
        "OPENAI_BASE_URL": "https://api.minimax.io/v1",
        "MODEL_NAME": "MiniMax-M2.7",
    }, clear=True)
    def test_manual_openai_compat_config(self):
        """Test manual configuration via OPENAI_* env vars (no auto-detect)."""
        provider = detect_provider()
        self.assertIsNone(provider)

        config = get_provider_config(provider)
        self.assertEqual(config["base_url"], "https://api.minimax.io/v1")
        self.assertEqual(config["api_key"], "minimax-key")
        self.assertEqual(config["model_name"], "MiniMax-M2.7")


@unittest.skipUnless(
    os.environ.get("MINIMAX_API_KEY"),
    "MINIMAX_API_KEY not set — skipping live API tests",
)
class TestMiniMaxLiveAPI(unittest.TestCase):
    """Live API tests — only run when MINIMAX_API_KEY is available."""

    def test_chat_completion(self):
        """Test a real chat completion call to MiniMax API."""
        from langchain_openai import ChatOpenAI

        config = get_provider_config("minimax")
        llm = ChatOpenAI(
            model=config["model_name"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            temperature=0.1,
        )
        response = llm.invoke("Say 'hello' in one word.")
        self.assertIsNotNone(response.content)
        self.assertGreater(len(response.content), 0)

    def test_structured_output(self):
        """Test structured output (function calling) with MiniMax."""
        from langchain_openai import ChatOpenAI

        from structure import Structure

        config = get_provider_config("minimax")
        llm = ChatOpenAI(
            model=config["model_name"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            temperature=0.1,
        ).with_structured_output(Structure, method="function_calling")

        result = llm.invoke(
            "This paper proposes a new attention mechanism that reduces "
            "computational complexity from O(n^2) to O(n log n)."
        )
        self.assertIsInstance(result, Structure)
        self.assertGreater(len(result.tldr), 0)


if __name__ == "__main__":
    unittest.main()
