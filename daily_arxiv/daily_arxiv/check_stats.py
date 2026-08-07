#!/usr/bin/env python3
"""Check whether today's arXiv records contain unseen papers."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

try:
    from .record_utils import deduplicate_records, filter_new_records
except ImportError:  # pragma: no cover - compatibility for direct execution
    from record_utils import deduplicate_records, filter_new_records


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def load_papers_data(file_path: str | Path) -> tuple[list[dict], set[str]]:
    """Load JSONL records and canonical IDs, failing on malformed data."""

    path = Path(file_path)
    if not path.exists():
        return [], set()

    papers: list[dict] = []
    ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON in {path}:{line_number}") from error
            if not isinstance(data, dict):
                raise ValueError(f"record in {path}:{line_number} is not an object")
            papers.append(data)

    for record in deduplicate_records(papers):
        ids.add(record["id"])
    return papers, ids


def save_papers_data(papers: Iterable[dict], file_path: str | Path) -> bool:
    """Atomically save JSONL records so interrupted runs cannot publish partial data."""

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            for paper in papers:
                handle.write(json.dumps(paper, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        return True
    except Exception as error:
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)
        print(f"Error saving {path}: {error}", file=sys.stderr)
        return False


def _resolve_date(value: date | str | None) -> date:
    if value is None:
        value = os.environ.get("ARXIV_DATE")
    if value is None:
        return datetime.now(timezone.utc).date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def perform_deduplication(
    today: date | str | None = None,
    data_dir: str | Path | None = None,
    history_days: int = 7,
) -> str:
    """Remove historical duplicates and report whether new records remain."""

    today_date = _resolve_date(today)
    root = Path(data_dir or os.environ.get("DATA_DIR") or REPOSITORY_ROOT / "data")
    today_file = root / f"{today_date.isoformat()}.jsonl"

    if not today_file.exists():
        print("今日数据文件不存在 / Today's data file does not exist", file=sys.stderr)
        return "no_data"

    try:
        today_papers, _ = load_papers_data(today_file)
        print(
            f"今日论文总数: {len(today_papers)} / Today's total papers: {len(today_papers)}",
            file=sys.stderr,
        )
        if not today_papers:
            return "no_data"

        history_ids: set[str] = set()
        for offset in range(1, history_days + 1):
            history_file = root / f"{today_date - timedelta(days=offset)}.jsonl"
            _, past_ids = load_papers_data(history_file)
            history_ids.update(past_ids)

        print(
            f"历史{history_days}日去重库大小: {len(history_ids)} / "
            f"History {history_days} days deduplication library size: {len(history_ids)}",
            file=sys.stderr,
        )

        new_papers = filter_new_records(today_papers, history_ids)
        removed_count = len(today_papers) - len(new_papers)
        print(
            f"去重后剩余论文数: {len(new_papers)} / Remaining papers after deduplication: {len(new_papers)}",
            file=sys.stderr,
        )

        if not new_papers:
            today_file.unlink()
            print(
                f"所有论文均为重复内容，已删除今日文件 / All papers are duplicate content, today's file deleted "
                f"(removed {removed_count})",
                file=sys.stderr,
            )
            return "no_new_content"

        if not save_papers_data(new_papers, today_file):
            return "error"
        if removed_count:
            print(
                f"已移除 {removed_count} 条重复记录 / Removed {removed_count} duplicate records",
                file=sys.stderr,
            )
        return "has_new_content"
    except Exception as error:
        print(f"去重处理失败: {error} / Deduplication processing failed: {error}", file=sys.stderr)
        return "error"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="UTC date in YYYY-MM-DD format")
    parser.add_argument("--data-dir", help="Directory containing daily JSONL files")
    parser.add_argument("--history-days", type=int, default=7)
    args = parser.parse_args(argv)

    print("正在执行去重检查... / Performing intelligent deduplication check...", file=sys.stderr)
    status = perform_deduplication(
        today=args.date,
        data_dir=args.data_dir,
        history_days=args.history_days,
    )
    if status == "has_new_content":
        print("✅ 去重完成，发现新内容，继续工作流 / Deduplication completed, new content found, continue workflow", file=sys.stderr)
        raise SystemExit(0)
    if status == "no_new_content":
        print("⏹️ 去重完成，无新内容，停止工作流 / Deduplication completed, no new content, stop workflow", file=sys.stderr)
        raise SystemExit(1)
    if status == "no_data":
        print("⏹️ 今日无数据，停止工作流 / No data today, stop workflow", file=sys.stderr)
        raise SystemExit(1)
    print("❌ 去重处理出错，停止工作流 / Deduplication processing error, stop workflow", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
