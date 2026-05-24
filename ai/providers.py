"""
LLM provider presets for daily-arXiv-ai-enhanced.

Provides auto-detection and configuration for multiple OpenAI-compatible
LLM providers, including DeepSeek, MiniMax, and OpenAI.
"""

import os
from typing import Dict, Optional

# Provider preset configurations
PROVIDER_PRESETS: Dict[str, Dict] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "temperature_range": (0.0, 2.0),
    },
    "minimax": {
        "base_url": "https://api.minimax.io/v1",
        "api_key_env": "MINIMAX_API_KEY",
        "default_model": "MiniMax-M2.7",
        "temperature_range": (0.0, 1.0),
        "models": [
            "MiniMax-M2.7",
            "MiniMax-M2.5",
            "MiniMax-M2.5-highspeed",
        ],
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "temperature_range": (0.0, 2.0),
    },
}


def detect_provider() -> Optional[str]:
    """Auto-detect LLM provider from environment variables.

    Checks provider-specific API key env vars in order:
    MINIMAX_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY.

    Returns the provider name or None if only generic OPENAI_* vars are set
    (which means the user configured a custom provider manually).
    """
    if os.environ.get("LLM_PROVIDER"):
        provider = os.environ["LLM_PROVIDER"].lower()
        if provider in PROVIDER_PRESETS:
            return provider

    if os.environ.get("MINIMAX_API_KEY"):
        return "minimax"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"

    return None


def clamp_temperature(temperature: float, provider: Optional[str] = None) -> float:
    """Clamp temperature to the valid range for the given provider."""
    if provider and provider in PROVIDER_PRESETS:
        lo, hi = PROVIDER_PRESETS[provider]["temperature_range"]
        return max(lo, min(hi, temperature))
    return temperature


def get_provider_config(provider: Optional[str] = None) -> Dict:
    """Get LLM configuration from provider preset or environment variables.

    If a provider is specified (or auto-detected), applies its preset
    configuration as defaults. Environment variables OPENAI_API_KEY,
    OPENAI_BASE_URL, and MODEL_NAME always take precedence when set.

    Returns a dict with keys: base_url, api_key, model_name.
    """
    config = {}

    if provider and provider in PROVIDER_PRESETS:
        preset = PROVIDER_PRESETS[provider]

        # Use provider-specific API key, fall back to OPENAI_API_KEY
        api_key = os.environ.get(preset["api_key_env"]) or os.environ.get("OPENAI_API_KEY", "")
        config["api_key"] = api_key
        config["base_url"] = preset["base_url"]
        config["model_name"] = preset["default_model"]
    else:
        config["api_key"] = os.environ.get("OPENAI_API_KEY", "")
        config["base_url"] = None
        config["model_name"] = "deepseek-chat"

    # Environment variables always override preset defaults
    if os.environ.get("OPENAI_BASE_URL"):
        config["base_url"] = os.environ["OPENAI_BASE_URL"]
    if os.environ.get("OPENAI_API_KEY") and not provider:
        config["api_key"] = os.environ["OPENAI_API_KEY"]
    if os.environ.get("MODEL_NAME"):
        config["model_name"] = os.environ["MODEL_NAME"]

    return config
