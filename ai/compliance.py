"""Small, testable adapter for the external compliance decision service."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

class SensitiveCheckUnavailable(RuntimeError):
    """Raised when the compliance service cannot make a trustworthy decision."""


def _default_post(*args: Any, **kwargs: Any) -> Any:
    import requests

    return requests.post(*args, **kwargs)


def check_sensitive(
    content: str,
    post: Callable[..., Any] | None = None,
    url: str | None = None,
) -> bool:
    """Return the service decision and fail closed on transport/protocol errors."""

    try:
        response = (post or _default_post)(
            url or os.environ.get("SENSITIVE_CHECK_URL", "https://spam.dw-dengwei.workers.dev"),
            json={"text": content},
            timeout=5,
        )
    except Exception as error:
        raise SensitiveCheckUnavailable("sensitive check request failed") from error

    if response.status_code != 200:
        raise SensitiveCheckUnavailable(
            f"sensitive check returned HTTP {response.status_code}"
        )

    try:
        result = response.json()
    except ValueError as error:
        raise SensitiveCheckUnavailable("sensitive check returned invalid JSON") from error

    if not isinstance(result, dict) or "sensitive" not in result:
        raise SensitiveCheckUnavailable("sensitive check omitted the decision")
    if not isinstance(result["sensitive"], bool):
        raise SensitiveCheckUnavailable("sensitive check returned a non-boolean decision")
    return result["sensitive"]
