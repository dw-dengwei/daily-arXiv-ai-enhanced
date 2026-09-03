"""Best-effort content filtering for generated paper summaries."""

import sys

import requests


FILTER_URL = "https://spam.dw-dengwei.workers.dev"


def is_sensitive(content: str) -> bool:
    """Return True only when the filtering service positively flags content.

    Filtering is intentionally fail-open: a rate limit or outage must not make
    an otherwise successful daily crawl publish an empty data set.
    """
    try:
        response = requests.post(FILTER_URL, json={"text": content}, timeout=5)
        if response.status_code == 200:
            return bool(response.json().get("sensitive", False))
        print(
            f"Sensitive check unavailable (HTTP {response.status_code}); allowing content",
            file=sys.stderr,
        )
    except requests.RequestException as error:
        print(f"Sensitive check error; allowing content: {error}", file=sys.stderr)
    return False
