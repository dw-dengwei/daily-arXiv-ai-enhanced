"""Pure helpers for canonicalising and de-duplicating arXiv records."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


_VERSION_SUFFIX = re.compile(r"v\d+$", re.IGNORECASE)


def normalize_arxiv_id(value: Any) -> str:
    """Return the canonical arXiv identifier without an optional version."""

    if value is None:
        raise ValueError("arXiv record is missing an id")

    identifier = str(value).strip()
    if not identifier:
        raise ValueError("arXiv record has an empty id")

    identifier = identifier.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    if "/" in identifier:
        identifier = identifier.rsplit("/", 1)[-1]
    if identifier.lower().startswith("arxiv:"):
        identifier = identifier.split(":", 1)[1]

    identifier = _VERSION_SUFFIX.sub("", identifier)
    if not identifier:
        raise ValueError(f"invalid arXiv id: {value!r}")
    return identifier


def _stable_unique(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _matched_categories(record: Mapping[str, Any]) -> list[Any]:
    values = _as_list(record.get("matched_categories"))
    if not values:
        values = _as_list(record.get("matched_category"))
    return _stable_unique(values)


def deduplicate_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate records by canonical arXiv ID while merging category metadata."""

    unique: list[dict[str, Any]] = []
    positions: dict[str, int] = {}

    for source in records:
        if not isinstance(source, Mapping):
            raise ValueError("arXiv record must be a mapping")

        record = dict(source)
        identifier = normalize_arxiv_id(record.get("id"))
        record["id"] = identifier
        record["categories"] = _stable_unique(_as_list(record.get("categories")))
        matched_categories = _matched_categories(record)
        record["matched_categories"] = matched_categories
        if matched_categories:
            record["matched_category"] = matched_categories[0]

        if identifier not in positions:
            positions[identifier] = len(unique)
            unique.append(record)
            continue

        existing = unique[positions[identifier]]
        existing["categories"] = _stable_unique(
            [*existing.get("categories", []), *record["categories"]]
        )
        existing["matched_categories"] = _stable_unique(
            [
                *existing.get("matched_categories", []),
                *record.get("matched_categories", []),
            ]
        )
        if existing["matched_categories"]:
            existing["matched_category"] = existing["matched_categories"][0]

    return unique


def filter_new_records(
    records: Iterable[Mapping[str, Any]],
    historical_ids: Iterable[Any],
) -> list[dict[str, Any]]:
    """Return one copy of each record whose canonical ID is not historical."""

    history = {normalize_arxiv_id(identifier) for identifier in historical_ids}
    return [
        record
        for record in deduplicate_records(records)
        if record["id"] not in history
    ]
