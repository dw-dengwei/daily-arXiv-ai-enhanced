"""Unit tests for the LLM provider configuration system."""

import os
import sys
import unittest
from unittest.mock import patch

# Add ai/ directory to path so we can import providers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai"))

from providers import (
    PROVIDER_PRESETS,
    clamp_temperature,
    detect_provider,
    get_provider_config,
)


class TestProviderPresets(unittest.TestCase):
    """Tests for PROVIDER_PRESETS structure."""

    def test_all_presets_have_required_keys(self):
        required_keys = {"base_url", "api_key_env", "default_model", "temperature_range"}
        for name, preset in PROVIDER_PRESETS.items():
            for key in required_keys:
                self.assertIn(key, preset, f"Provider '{name}' missing key '{key}'")

    def test_minimax_preset_values(self):
        p = PROVIDER_PRESETS["minimax"]
        self.assertEqual(p["base_url"], "https://api.minimax.io/v1")
        self.assertEqual(p["api_key_env"], "MINIMAX_API_KEY")
        self.assertEqual(p["default_model"], "MiniMax-M2.7")
        self.assertEqual(p["temperature_range"], (0.0, 1.0))
        self.assertIn("MiniMax-M2.5-highspeed", p["models"])

    def test_deepseek_preset_values(self):
        p = PROVIDER_PRESETS["deepseek"]
        self.assertEqual(p["base_url"], "https://api.deepseek.com/v1")
        self.assertEqual(p["default_model"], "deepseek-chat")

    def test_openai_preset_values(self):
        p = PROVIDER_PRESETS["openai"]
        self.assertEqual(p["base_url"], "https://api.openai.com/v1")
        self.assertEqual(p["default_model"], "gpt-4o")


class TestDetectProvider(unittest.TestCase):
    """Tests for detect_provider() auto-detection."""

    @patch.dict(os.environ, {}, clear=True)
    def test_no_env_returns_none(self):
        self.assertIsNone(detect_provider())

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "key123"}, clear=True)
    def test_minimax_api_key_detected(self):
        self.assertEqual(detect_provider(), "minimax")

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "key456"}, clear=True)
    def test_deepseek_api_key_detected(self):
        self.assertEqual(detect_provider(), "deepseek")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "k1", "DEEPSEEK_API_KEY": "k2"}, clear=True)
    def test_minimax_takes_priority_over_deepseek(self):
        self.assertEqual(detect_provider(), "minimax")

    @patch.dict(os.environ, {"LLM_PROVIDER": "minimax"}, clear=True)
    def test_explicit_llm_provider_env(self):
        self.assertEqual(detect_provider(), "minimax")

    @patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True)
    def test_explicit_openai_provider(self):
        self.assertEqual(detect_provider(), "openai")

    @patch.dict(os.environ, {"LLM_PROVIDER": "unknown_provider"}, clear=True)
    def test_unknown_llm_provider_falls_through(self):
        self.assertIsNone(detect_provider())


class TestClampTemperature(unittest.TestCase):
    """Tests for temperature clamping per provider."""

    def test_minimax_clamp_within_range(self):
        self.assertEqual(clamp_temperature(0.7, "minimax"), 0.7)

    def test_minimax_clamp_upper_bound(self):
        self.assertEqual(clamp_temperature(1.5, "minimax"), 1.0)

    def test_minimax_clamp_lower_bound(self):
        self.assertEqual(clamp_temperature(-0.1, "minimax"), 0.0)

    def test_minimax_zero_temperature(self):
        self.assertEqual(clamp_temperature(0.0, "minimax"), 0.0)

    def test_openai_allows_higher_temp(self):
        self.assertEqual(clamp_temperature(1.5, "openai"), 1.5)

    def test_no_provider_passthrough(self):
        self.assertEqual(clamp_temperature(1.5, None), 1.5)

    def test_unknown_provider_passthrough(self):
        self.assertEqual(clamp_temperature(2.5, "unknown"), 2.5)


class TestGetProviderConfig(unittest.TestCase):
    """Tests for get_provider_config() configuration resolution."""

    @patch.dict(os.environ, {}, clear=True)
    def test_no_provider_defaults(self):
        cfg = get_provider_config(None)
        self.assertEqual(cfg["model_name"], "deepseek-chat")
        self.assertIsNone(cfg["base_url"])

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mk"}, clear=True)
    def test_minimax_provider_config(self):
        cfg = get_provider_config("minimax")
        self.assertEqual(cfg["base_url"], "https://api.minimax.io/v1")
        self.assertEqual(cfg["api_key"], "mk")
        self.assertEqual(cfg["model_name"], "MiniMax-M2.7")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mk", "MODEL_NAME": "MiniMax-M2.5"}, clear=True)
    def test_model_name_env_overrides_preset(self):
        cfg = get_provider_config("minimax")
        self.assertEqual(cfg["model_name"], "MiniMax-M2.5")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mk", "OPENAI_BASE_URL": "https://custom.example.com/v1"}, clear=True)
    def test_base_url_env_overrides_preset(self):
        cfg = get_provider_config("minimax")
        self.assertEqual(cfg["base_url"], "https://custom.example.com/v1")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "ok", "OPENAI_BASE_URL": "https://api.deepseek.com/v1"}, clear=True)
    def test_generic_openai_env_vars(self):
        cfg = get_provider_config(None)
        self.assertEqual(cfg["api_key"], "ok")
        self.assertEqual(cfg["base_url"], "https://api.deepseek.com/v1")

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "dk"}, clear=True)
    def test_deepseek_provider_config(self):
        cfg = get_provider_config("deepseek")
        self.assertEqual(cfg["base_url"], "https://api.deepseek.com/v1")
        self.assertEqual(cfg["api_key"], "dk")
        self.assertEqual(cfg["model_name"], "deepseek-chat")


if __name__ == "__main__":
    unittest.main()
