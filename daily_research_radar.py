#!/usr/bin/env python3
"""Personalised Daily Research Radar for arXiv papers."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import arxiv
import dotenv
import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


DEFAULT_CATEGORIES = [
    "cs.LG",
    "stat.ML",
    "cs.AI",
    "cs.CL",
    "cs.CV",
    "q-bio.GN",
    "q-bio.QM",
    "stat.AP",
    "stat.ME",
    "cs.IR",
]

REPORT_TEMPLATE_PATH = Path("templates/daily_research_radar.md")
PROMPT_PATH = Path("prompts/research_radar_prompt.md")


for env_path in (Path(".env"), Path("ai/.env")):
    if env_path.exists():
        dotenv.load_dotenv(env_path, override=False)


class RadarScores(BaseModel):
    topic_match_score: int = 0
    personal_relevance_score: int = 0
    novelty_score: int = 0
    translational_potential_score: int = 0
    idea_generation_score: int = 0
    final_priority_score: int = 0

    @field_validator("*", mode="before")
    @classmethod
    def clamp_score(cls, value: Any) -> int:
        try:
            score = int(round(float(value)))
        except (TypeError, ValueError):
            score = 0
        return max(0, min(10, score))


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        normalized = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized
    if isinstance(value, tuple | set):
        return normalize_string_list(list(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                decoded = None
            if isinstance(decoded, list):
                return normalize_string_list(decoded)
        return [part.strip() for part in text.split(",") if part.strip()]
    text = str(value).strip()
    return [text] if text else []


class RadarSummary(BaseModel):
    plain_english_summary: str = ""
    technical_summary: str = ""
    key_methods: list[str] = Field(default_factory=list)
    data_or_benchmark: str = ""
    main_contribution: str = ""
    limitations: str = ""
    relevance_to_weijie: str = ""
    possible_use_in_my_research: str = ""
    possible_research_idea: str = ""
    priority: str = "Optional"
    estimated_reading_time: str = "20 min"
    topic_tags: list[str] = Field(default_factory=list)
    scores: RadarScores = Field(default_factory=RadarScores)

    @field_validator("key_methods", "topic_tags", mode="before")
    @classmethod
    def normalize_list_fields(cls, value: Any) -> list[str]:
        return normalize_string_list(value)


@dataclass(frozen=True)
class TopicContext:
    index: int
    topic: dict[str, Any]
    previous_topic: dict[str, Any]
    next_topic: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a personalised Daily Research Radar report.")
    parser.add_argument("--date", help="Report date as YYYY-MM-DD or 'today'. Defaults to today.")
    parser.add_argument("--start-date", help="Start date for inclusive backfill range as YYYY-MM-DD.")
    parser.add_argument("--end-date", help="End date for inclusive backfill range as YYYY-MM-DD or 'today'.")
    parser.add_argument("--days-back", type=int, help="Generate an inclusive rolling window ending today.")
    parser.add_argument("--data", help="Input JSONL file. Defaults to data/YYYY-MM-DD.jsonl.")
    parser.add_argument("--profile", default=os.environ.get("RESEARCH_PROFILE_PATH", "research_profile.yaml"))
    parser.add_argument("--schedule", default=os.environ.get("DAILY_TOPIC_SCHEDULE_PATH", "daily_topic_schedule.yaml"))
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--history", default="data/research_radar_history.json")
    parser.add_argument("--max-key", type=int, default=int(os.environ.get("MAX_KEY_PAPERS_PER_DAY", "3") or 3))
    parser.add_argument("--max-other", type=int, default=int(os.environ.get("MAX_OTHER_PAPERS_PER_DAY", "8") or 8))
    parser.add_argument("--serendipity-ratio", type=float, default=float(os.environ.get("SERENDIPITY_RATIO", "0.25") or 0.25))
    parser.add_argument("--max-workers", type=int, default=int(os.environ.get("RADAR_MAX_WORKERS", "4") or 4))
    parser.add_argument("--llm-timeout-seconds", type=float, default=float(os.environ.get("LLM_TIMEOUT_SECONDS", "60") or 60))
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM summaries even when OPENAI_API_KEY is set.")
    parser.add_argument("--no-fetch", action="store_true", help="Do not fetch arXiv papers if the input file is missing.")
    parser.add_argument("--max-fetch-results", type=int, default=int(os.environ.get("MAX_FETCH_RESULTS", "250") or 250))
    parser.add_argument("--skip-existing", action="store_true", help="Skip dates that already have enhanced JSONL, Markdown, and HTML outputs.")
    return parser.parse_args()


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return loaded


def parse_report_date(value: str) -> date:
    if str(value).strip().lower() == "today":
        return datetime.now(timezone.utc).date()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"Invalid --date value {value!r}; expected YYYY-MM-DD") from exc


def date_range(start: date, end: date) -> list[date]:
    if start > end:
        raise SystemExit(f"Start date {start.isoformat()} is after end date {end.isoformat()}")
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def resolve_report_dates(args: argparse.Namespace, today: date | None = None) -> list[date]:
    today = today or datetime.now(timezone.utc).date()
    modes = sum(
        bool(value)
        for value in (
            args.date,
            args.start_date or args.end_date,
            args.days_back is not None,
        )
    )
    if modes > 1:
        raise SystemExit("Use only one of --date, --start-date/--end-date, or --days-back.")

    if args.days_back is not None:
        if args.days_back < 1:
            raise SystemExit("--days-back must be at least 1")
        return date_range(today - timedelta(days=args.days_back - 1), today)

    if args.start_date or args.end_date:
        if not args.start_date or not args.end_date:
            raise SystemExit("Both --start-date and --end-date are required for range generation.")
        return date_range(parse_report_date(args.start_date), parse_report_date(args.end_date))

    return [parse_report_date(args.date) if args.date else today]


def expected_output_paths(output_dir: Path, report_date: date) -> dict[str, Path]:
    date_prefix = report_date.isoformat()
    return {
        "enhanced": output_dir / f"{date_prefix}_research_radar_enhanced.jsonl",
        "markdown": output_dir / f"{date_prefix}_research_radar.md",
        "html": output_dir / f"{date_prefix}_research_radar.html",
    }


def has_expected_outputs(output_dir: Path, report_date: date) -> bool:
    return all(path.exists() and path.stat().st_size > 0 for path in expected_output_paths(output_dir, report_date).values())


def configured_categories(profile: dict[str, Any]) -> list[str]:
    env_categories = os.environ.get("CATEGORIES", "").strip()
    if env_categories:
        return [category.strip() for category in env_categories.split(",") if category.strip()]
    categories = profile.get("arxiv_categories") or DEFAULT_CATEGORIES
    return [str(category).strip() for category in categories if str(category).strip()]


def get_topic_context(schedule: dict[str, Any], report_date: date) -> TopicContext:
    cycle = schedule.get("cycle", {})
    topics = cycle.get("topics") or []
    if not topics:
        raise ValueError("daily_topic_schedule.yaml must define cycle.topics")

    mode = os.environ.get("DAILY_TOPIC_MODE", "rotate").strip().lower()
    fixed_id = os.environ.get("DAILY_TOPIC_ID", "").strip()
    if mode == "fixed" and fixed_id:
        for idx, topic in enumerate(topics):
            if topic.get("id") == fixed_id:
                return TopicContext(idx, topic, topics[(idx - 1) % len(topics)], topics[(idx + 1) % len(topics)])
        raise ValueError(f"DAILY_TOPIC_ID={fixed_id!r} is not present in the topic schedule")

    if mode == "exploratory":
        for idx, topic in enumerate(topics):
            if topic.get("id") == "exploratory_frontier":
                return TopicContext(idx, topic, topics[(idx - 1) % len(topics)], topics[(idx + 1) % len(topics)])

    anchor = parse_report_date(str(cycle.get("anchor_date", report_date.isoformat())))
    idx = (report_date - anchor).days % len(topics)
    return TopicContext(idx, topics[idx], topics[(idx - 1) % len(topics)], topics[(idx + 1) % len(topics)])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    papers: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                papers.append(json.loads(line))
    return deduplicate_by_id(papers)


def write_jsonl(path: Path, papers: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for paper in papers:
            handle.write(json.dumps(paper, ensure_ascii=False) + "\n")


def deduplicate_by_id(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for paper in papers:
        paper_id = str(paper.get("id", "")).strip()
        if not paper_id or paper_id in seen:
            continue
        seen.add(paper_id)
        unique.append(paper)
    return unique


def fetch_arxiv_papers(report_date: date, categories: list[str], max_results: int) -> list[dict[str, Any]]:
    category_query = " OR ".join(f"cat:{category}" for category in categories)
    date_query = f"submittedDate:[{report_date:%Y%m%d}000000 TO {report_date:%Y%m%d}235959]"
    query = f"({category_query}) AND {date_query}" if category_query else date_query
    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=3)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    fetched: list[dict[str, Any]] = []
    for paper in client.results(search):
        published = paper.published.date() if paper.published else report_date
        if published > report_date:
            continue
        if published != report_date:
            continue
        paper_categories = list(paper.categories or [])
        if categories and not set(paper_categories).intersection(categories):
            continue
        fetched.append(
            {
                "id": paper.entry_id.rsplit("/", 1)[-1],
                "pdf": paper.pdf_url,
                "abs": paper.entry_id,
                "authors": [author.name for author in paper.authors],
                "title": paper.title,
                "categories": paper_categories,
                "comment": paper.comment,
                "summary": paper.summary,
                "published": paper.published.isoformat() if paper.published else "",
                "updated": paper.updated.isoformat() if paper.updated else "",
            }
        )
    return deduplicate_by_id(fetched)


def load_or_fetch_papers(args: argparse.Namespace, report_date: date, categories: list[str]) -> tuple[Path, list[dict[str, Any]]]:
    data_path = Path(args.data) if args.data else Path(args.output_dir) / f"{report_date.isoformat()}.jsonl"
    if data_path.exists():
        return data_path, read_jsonl(data_path)

    if args.no_fetch:
        raise FileNotFoundError(f"Input data file not found: {data_path}")

    print(f"Input file {data_path} not found; fetching arXiv papers for {report_date.isoformat()}.", file=sys.stderr)
    papers = fetch_arxiv_papers(report_date, categories, args.max_fetch_results)
    write_jsonl(data_path, papers)
    return data_path, papers


def normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("-", " ")).lower()


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    haystack = normalise_text(text)
    hits = []
    for keyword in keywords:
        needle = normalise_text(str(keyword))
        if needle and needle in haystack:
            hits.append(str(keyword))
    return hits


def score_from_hits(title: str, summary: str, keywords: list[str], weight: float = 1.0) -> tuple[int, list[str]]:
    title_hits = keyword_hits(title, keywords)
    summary_hits = keyword_hits(summary, keywords)
    unique_hits = sorted(set(title_hits + summary_hits), key=str.lower)
    weighted = (2.0 * len(set(title_hits)) + len(set(summary_hits))) * weight
    return max(0, min(10, int(round(weighted)))), unique_hits


def score_paper(paper: dict[str, Any], profile: dict[str, Any], topic: dict[str, Any], report_date: date) -> dict[str, Any]:
    title = str(paper.get("title", ""))
    summary = str(paper.get("summary", ""))
    topics = profile.get("topics", {})
    linked_topic_id = topic.get("linked_profile_topic")
    linked_topic = topics.get(linked_topic_id, {}) if linked_topic_id else {}

    topic_keywords = list(linked_topic.get("keywords", []))
    if topic.get("id") == "exploratory_frontier":
        topic_keywords = [
            keyword
            for topic_data in topics.values()
            for keyword in topic_data.get("keywords", [])
        ]
    topic_score, topic_hits = score_from_hits(title, summary, topic_keywords, float(linked_topic.get("weight", 1.0)))

    all_topic_hits: list[str] = []
    personal_raw_score = 0
    topic_tags: list[str] = []
    for topic_id, topic_data in topics.items():
        score, hits = score_from_hits(title, summary, list(topic_data.get("keywords", [])), float(topic_data.get("weight", 1.0)))
        if hits:
            topic_tags.append(str(topic_data.get("name", topic_id)))
            all_topic_hits.extend(hits)
        personal_raw_score += score
    personal_score = max(topic_score, min(10, personal_raw_score))

    scoring_cfg = profile.get("scoring", {})
    novelty_score, novelty_hits = score_from_hits(title, summary, list(scoring_cfg.get("novelty_keywords", [])))
    translational_score, translational_hits = score_from_hits(title, summary, list(scoring_cfg.get("biomedical_relevance_keywords", [])))

    method_terms = ["model", "method", "framework", "inference", "prediction", "causal", "multi-omics", "transformer"]
    method_score, method_hits = score_from_hits(title, summary, method_terms)
    idea_score = min(10, int(round((personal_score + novelty_score + method_score) / 3)))

    published_raw = str(paper.get("published") or paper.get("updated") or "")
    recency_score = 5
    if published_raw:
        try:
            published_date = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).date()
            recency_score = max(0, min(10, 10 - max(0, (report_date - published_date).days)))
        except ValueError:
            pass

    generic_llm_hits = keyword_hits(f"{title} {summary}", list(scoring_cfg.get("generic_llm_keywords", [])))
    biomedical_hits = topic_hits + translational_hits
    generic_llm_penalty = 1.5 if generic_llm_hits and not biomedical_hits else 0.0

    final_score = (
        0.30 * topic_score
        + 0.25 * personal_score
        + 0.15 * novelty_score
        + 0.15 * translational_score
        + 0.10 * idea_score
        + 0.05 * recency_score
        - generic_llm_penalty
    )
    final_score = max(0, min(10, final_score))

    scores = {
        "topic_match_score": topic_score,
        "personal_relevance_score": personal_score,
        "novelty_score": novelty_score,
        "translational_potential_score": translational_score,
        "idea_generation_score": idea_score,
        "final_priority_score": int(round(final_score)),
    }
    return {
        "scores": scores,
        "topic_tags": sorted(set(topic_tags), key=str.lower),
        "keyword_hits": sorted(set(topic_hits + all_topic_hits + novelty_hits + translational_hits + method_hits), key=str.lower),
        "generic_llm_penalty": generic_llm_penalty,
    }


def first_sentence(text: str, max_chars: int = 240) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "No abstract was available."
    match = re.search(r"(?<=[.!?])\s+", cleaned)
    sentence = cleaned[: match.start()].strip() if match else cleaned
    if len(sentence) > max_chars:
        return sentence[: max_chars - 3].rstrip() + "..."
    return sentence


def fallback_summary(paper: dict[str, Any], scoring: dict[str, Any], topic: dict[str, Any]) -> RadarSummary:
    title = str(paper.get("title", ""))
    summary = str(paper.get("summary", ""))
    scores = RadarScores(**scoring["scores"])
    priority = priority_from_score(scores.final_priority_score)
    reading_time = reading_time_from_score(scores.final_priority_score, len(summary.split()))
    tags = scoring.get("topic_tags") or [topic.get("name", "Research radar")]
    hits = scoring.get("keyword_hits") or []
    methods = [hit for hit in hits if hit.lower() in normalise_text(summary)][:5]
    return RadarSummary(
        plain_english_summary=first_sentence(summary),
        technical_summary=(
            f"This paper appears relevant through {', '.join(hits[:5])}."
            if hits
            else first_sentence(summary, 320)
        ),
        key_methods=methods,
        data_or_benchmark="Not clear from the abstract.",
        main_contribution=first_sentence(summary, 260),
        limitations="Limitations are not clear from the abstract and should be checked in the full paper.",
        relevance_to_weijie=(
            f"Relevant to {topic.get('name', 'today')} because it matches {', '.join(hits[:4])}."
            if hits
            else "Potentially relevant as a recent paper in the monitored arXiv categories."
        ),
        possible_use_in_my_research=(
            "Use it to compare methods, datasets, or assumptions against ongoing genetic epidemiology and prediction work."
        ),
        possible_research_idea=make_paper_idea(title, topic.get("name", "today's topic")),
        priority=priority,
        estimated_reading_time=reading_time,
        topic_tags=tags,
        scores=scores,
    )


def priority_from_score(score: int) -> str:
    if score >= 8:
        return "Must read"
    if score >= 6:
        return "Strongly recommended"
    if score >= 3:
        return "Optional"
    return "Skip"


def reading_time_from_score(score: int, word_count: int) -> str:
    if score >= 8 or word_count > 250:
        return "deep read"
    if score >= 6:
        return "45 min"
    return "20 min"


def make_paper_idea(title: str, main_topic: str) -> str:
    return f"Test whether the approach in '{title}' can be adapted to {main_topic.lower()} using a well-phenotyped cohort."


def get_llm_chain(model_name: str, request_timeout: float):
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        from langchain_openai import ChatOpenAI
    except Exception as exc:
        print(f"LLM unavailable because langchain_openai could not be imported: {exc}", file=sys.stderr)
        return None

    kwargs: dict[str, Any] = {
        "model": model_name,
        "temperature": 0,
        "request_timeout": request_timeout,
    }
    if os.environ.get("OPENAI_BASE_URL"):
        kwargs["base_url"] = os.environ["OPENAI_BASE_URL"]
    try:
        return ChatOpenAI(**kwargs).with_structured_output(RadarSummary, method="function_calling")
    except Exception as exc:
        print(f"LLM unavailable for model {model_name}: {exc}", file=sys.stderr)
        return None


def enhance_paper(
    paper: dict[str, Any],
    profile: dict[str, Any],
    topic: dict[str, Any],
    report_date: date,
    chain: Any,
) -> dict[str, Any]:
    scoring = score_paper(paper, profile, topic, report_date)
    fallback = fallback_summary(paper, scoring, topic)
    summary = enhance_with_llm(paper, chain, topic, fallback)
    enhanced_paper = dict(paper)
    enhanced_paper["research_radar"] = {
        "date": report_date.isoformat(),
        "main_topic": topic.get("name", ""),
        "main_topic_id": topic.get("id", ""),
        "scores": summary.scores.model_dump(),
        "topic_tags": summary.topic_tags,
        "keyword_hits": scoring.get("keyword_hits", []),
        "generic_llm_penalty": scoring.get("generic_llm_penalty", 0),
        "summary": summary.model_dump(),
    }
    return enhanced_paper


def enhance_with_llm(paper: dict[str, Any], chain: Any, topic: dict[str, Any], fallback: RadarSummary) -> RadarSummary:
    if chain is None:
        return fallback
    try:
        prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
        replacements = {
            "{main_topic}": str(topic.get("name", "")),
            "{title}": str(paper.get("title", "")),
            "{authors}": ", ".join(paper.get("authors", [])),
            "{categories}": ", ".join(paper.get("categories", [])),
            "{summary}": str(paper.get("summary", "")),
        }
        prompt = prompt_template
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)
        response = chain.invoke(prompt)
        if isinstance(response, RadarSummary):
            merged_scores = fallback.scores.model_dump()
            merged_scores.update({k: v for k, v in response.scores.model_dump().items() if v is not None})
            response.scores = RadarScores(**merged_scores)
            if not response.topic_tags:
                response.topic_tags = fallback.topic_tags
            if not response.priority or response.priority == "Skip":
                response.priority = fallback.priority
            if not response.estimated_reading_time:
                response.estimated_reading_time = fallback.estimated_reading_time
            return response
        return RadarSummary.model_validate(response)
    except (ValidationError, Exception) as exc:
        print(f"LLM summary failed for {paper.get('id', 'unknown')}: {exc}", file=sys.stderr)
        return fallback


def load_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def recent_appearances(history_entry: dict[str, Any], report_date: date, days: int = 30) -> list[dict[str, Any]]:
    recent = []
    for appearance in history_entry.get("appearances", []):
        try:
            seen_date = parse_report_date(str(appearance.get("date", "")))
        except SystemExit:
            continue
        if 0 < (report_date - seen_date).days <= days:
            recent.append(appearance)
    return recent


def eligible_for_section(paper: dict[str, Any], history: dict[str, Any], report_date: date, section: str) -> bool:
    paper_id = str(paper.get("id", ""))
    recent = recent_appearances(history.get(paper_id, {}), report_date)
    if not recent:
        return True
    if section == "key":
        had_key = any(item.get("section") == "key" for item in recent)
        if had_key:
            return False
        scores = paper["research_radar"]["scores"]
        return scores["final_priority_score"] >= 8 and scores["topic_match_score"] >= 6
    return False


def select_papers(
    papers: list[dict[str, Any]],
    history: dict[str, Any],
    report_date: date,
    max_key: int,
    max_other: int,
    serendipity_ratio: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ranked = sorted(
        papers,
        key=lambda paper: (
            paper["research_radar"]["scores"]["final_priority_score"],
            paper["research_radar"]["scores"]["topic_match_score"],
            paper["research_radar"]["scores"]["personal_relevance_score"],
        ),
        reverse=True,
    )
    key_candidates = [
        paper
        for paper in ranked
        if paper["research_radar"]["scores"]["final_priority_score"] >= 5
        and eligible_for_section(paper, history, report_date, "key")
    ]
    if not key_candidates:
        key_candidates = ranked
    key_papers = key_candidates[: max(1, max_key)]

    key_ids = {paper["id"] for paper in key_papers}
    other_candidates = [
        paper
        for paper in ranked
        if paper["id"] not in key_ids
        and paper["research_radar"]["scores"]["final_priority_score"] >= 3
        and eligible_for_section(paper, history, report_date, "other")
    ]
    serendipity_slots = max(0, min(max_other, int(round(max_other * serendipity_ratio))))
    topic_slots = max_other - serendipity_slots
    topic_pool = [paper for paper in other_candidates if paper["research_radar"]["scores"]["topic_match_score"] >= 3]
    serendipity_pool = [paper for paper in other_candidates if paper["research_radar"]["scores"]["topic_match_score"] < 3]

    other_papers: list[dict[str, Any]] = []
    other_papers.extend(topic_pool[:topic_slots])
    other_papers.extend(serendipity_pool[:serendipity_slots])

    if len(other_papers) < max_other:
        used = {paper["id"] for paper in other_papers}
        for paper in other_candidates:
            if paper["id"] not in used:
                other_papers.append(paper)
                used.add(paper["id"])
            if len(other_papers) >= max_other:
                break
    return key_papers, other_papers[:max_other]


def update_history(path: Path, report_date: date, key_papers: list[dict[str, Any]], other_papers: list[dict[str, Any]]) -> None:
    history = load_history(path)
    for section, papers in (("key", key_papers), ("other", other_papers)):
        for paper in papers:
            paper_id = str(paper.get("id", ""))
            entry = history.setdefault(
                paper_id,
                {
                    "title": paper.get("title", ""),
                    "first_seen": report_date.isoformat(),
                    "appearances": [],
                },
            )
            entry["title"] = paper.get("title", entry.get("title", ""))
            entry["last_recommended"] = report_date.isoformat()
            entry.setdefault("appearances", []).append(
                {
                    "date": report_date.isoformat(),
                    "section": section,
                    "score": paper["research_radar"]["scores"]["final_priority_score"],
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(history, handle, ensure_ascii=False, indent=2, sort_keys=True)


def authors_text(authors: list[str], limit: int = 8) -> str:
    if len(authors) <= limit:
        return ", ".join(authors)
    return ", ".join(authors[:limit]) + ", et al."


def h(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def paper_url(paper: dict[str, Any]) -> str:
    return str(paper.get("abs") or f"https://arxiv.org/abs/{paper.get('id', '')}")


def paper_badges(paper: dict[str, Any], radar: RadarSummary) -> str:
    badges = []
    for category in paper.get("categories", [])[:3]:
        badges.append(f"<span class=\"badge category\">{h(category)}</span>")
    for tag in radar.topic_tags[:5]:
        badges.append(f"<span class=\"badge topic\">{h(tag)}</span>")
    if radar.priority:
        priority_class = "must" if radar.priority == "Must read" else "priority"
        badges.append(f"<span class=\"badge {priority_class}\">{h(radar.priority)}</span>")
    return "\n".join(badges)


def score_meter(label: str, score: int) -> str:
    width = max(0, min(10, score)) * 10
    return (
        "<div class=\"score-row\">"
        f"<span>{h(label)}</span>"
        "<div class=\"score-track\" aria-hidden=\"true\">"
        f"<div class=\"score-fill\" style=\"width:{width}%\"></div>"
        "</div>"
        f"<strong>{score}/10</strong>"
        "</div>"
    )


def format_dashboard_paper(paper: dict[str, Any], featured: bool = False) -> str:
    radar = RadarSummary.model_validate(paper["research_radar"]["summary"])
    scores = radar.scores
    is_must = radar.priority == "Must read" or scores.final_priority_score >= 8
    card_classes = ["paper-card"]
    if featured:
        card_classes.append("featured")
    if is_must:
        card_classes.append("must-read")
    methods = "".join(f"<span class=\"method-chip\">{h(method)}</span>" for method in radar.key_methods[:8])
    methods_block = f"<div class=\"method-row\">{methods}</div>" if methods else ""
    return f"""
<article class="{' '.join(card_classes)}">
  <div class="paper-card-topline">
    <div class="badge-row">{paper_badges(paper, radar)}</div>
    <a class="arxiv-link" href="{h(paper_url(paper))}" target="_blank" rel="noopener">arXiv {h(paper.get('id', ''))}</a>
  </div>
  <h3>{h(paper.get('title', 'Untitled'))}</h3>
  <p class="authors">{h(authors_text(paper.get('authors', [])))}</p>
  <p class="plain-summary">{h(radar.plain_english_summary)}</p>
  {methods_block}
  <details class="paper-details" {'open' if featured else ''}>
    <summary>Why this matters</summary>
    <div class="detail-grid">
      <section>
        <h4>Technical summary</h4>
        <p>{h(radar.technical_summary)}</p>
      </section>
      <section>
        <h4>Why read it</h4>
        <p>{h(radar.relevance_to_weijie)}</p>
      </section>
      <section>
        <h4>Connection to my work</h4>
        <p>{h(radar.possible_use_in_my_research)}</p>
      </section>
      <section>
        <h4>Research idea</h4>
        <p>{h(radar.possible_research_idea)}</p>
      </section>
    </div>
  </details>
  <details class="paper-details compact">
    <summary>Scores and reading plan</summary>
    <div class="score-grid">
      {score_meter("Topic", scores.topic_match_score)}
      {score_meter("Personal", scores.personal_relevance_score)}
      {score_meter("Novelty", scores.novelty_score)}
      {score_meter("Translational", scores.translational_potential_score)}
      {score_meter("Ideas", scores.idea_generation_score)}
      {score_meter("Final", scores.final_priority_score)}
    </div>
    <p class="reading-time">Estimated reading time: <strong>{h(radar.estimated_reading_time)}</strong></p>
  </details>
</article>
"""


def format_key_paper(paper: dict[str, Any]) -> str:
    radar = RadarSummary.model_validate(paper["research_radar"]["summary"])
    category = paper.get("categories", [""])[0] if paper.get("categories") else ""
    return (
        f"### {paper.get('title', 'Untitled')}\n\n"
        f"- **Authors:** {authors_text(paper.get('authors', []))}\n"
        f"- **arXiv:** [{paper.get('id', '')}]({paper.get('abs', '')})\n"
        f"- **Category:** {category}\n"
        f"- **Plain-English summary:** {radar.plain_english_summary}\n"
        f"- **Technical summary:** {radar.technical_summary}\n"
        f"- **Why I should read this paper:** {radar.relevance_to_weijie}\n"
        f"- **Connection to my work:** {radar.possible_use_in_my_research}\n"
        f"- **Possible research idea:** {radar.possible_research_idea}\n"
        f"- **Priority:** {radar.priority}\n"
        f"- **Estimated reading time:** {radar.estimated_reading_time}\n"
        f"- **Scores:** topic {radar.scores.topic_match_score}/10; personal {radar.scores.personal_relevance_score}/10; "
        f"novelty {radar.scores.novelty_score}/10; translational {radar.scores.translational_potential_score}/10; "
        f"idea {radar.scores.idea_generation_score}/10; final {radar.scores.final_priority_score}/10"
    )


def format_other_paper(paper: dict[str, Any]) -> str:
    radar = RadarSummary.model_validate(paper["research_radar"]["summary"])
    category = paper.get("categories", [""])[0] if paper.get("categories") else ""
    return (
        f"- **[{paper.get('title', 'Untitled')}]({paper.get('abs', '')})** ({category}, "
        f"{radar.scores.final_priority_score}/10): {radar.plain_english_summary}"
    )


def generate_research_ideas(topic: dict[str, Any], key_papers: list[dict[str, Any]]) -> list[dict[str, str]]:
    titles = [paper.get("title", "today's papers") for paper in key_papers] or ["today's papers"]
    topic_name = str(topic.get("name", "today's topic"))
    topic_id = str(topic.get("id", ""))
    if "prs" in topic_id:
        return [
            {
                "question": "Can cross-ancestry PRS calibration improve osteoarthritis or cardiometabolic risk prediction beyond ancestry-specific baseline models?",
                "data": "UK Biobank, All of Us, public GWAS, ancestry-matched LD references",
                "method": "SBayesR/SBayesRC, PRS-CSx, Coxnet, calibration and time-dependent AUC",
                "publishable": "It addresses portability, clinical validity, and equity in a disease area with available large-scale cohorts.",
                "difficulty": "medium",
            },
            {
                "question": f"Can the method from '{titles[0]}' improve PRS transfer across ancestries or phenotype definitions?",
                "data": "UK Biobank, All of Us, FinnGen summary statistics",
                "method": "Bayesian PRS, external validation, genetic correlation, subgroup calibration",
                "publishable": "A careful benchmark with transparent validation would be useful for applied genetic epidemiology.",
                "difficulty": "medium",
            },
            {
                "question": "Do protein-informed PRS models identify subgroups with different osteoarthritis progression risk?",
                "data": "UKB-PPP, OAI, public pQTL resources",
                "method": "PRS, pQTL colocalisation, survival models, mediation analysis",
                "publishable": "It connects prediction to mechanism and may generate clinically interpretable subtypes.",
                "difficulty": "ambitious",
            },
        ]
    if "causal" in topic_id or "mr" in topic_id:
        return [
            {
                "question": "Which circulating proteins are likely causal mediators between cardiometabolic traits and osteoarthritis outcomes?",
                "data": "UKB-PPP, deCODE/Fenland pQTL, public GWAS, OAI",
                "method": "MR, colocalisation, HyPrColoc, mediation",
                "publishable": "It can produce target-prioritisation evidence with clear sensitivity analyses.",
                "difficulty": "medium",
            },
            {
                "question": f"Can the causal framework in '{titles[0]}' be adapted to separate pleiotropy from mediation in OA-related traits?",
                "data": "OpenGWAS, UK Biobank, public pQTL and eQTL resources",
                "method": "Genomic SEM, multivariable MR, LDSC, genetic correlation",
                "publishable": "The method comparison would clarify interpretation for multi-trait genetic epidemiology.",
                "difficulty": "ambitious",
            },
            {
                "question": "Are druggable protein targets for inflammation also genetically linked to joint replacement risk?",
                "data": "Drug target databases, pQTL resources, UK Biobank joint replacement endpoints",
                "method": "Drug-target MR, colocalisation, phenome-wide sensitivity analyses",
                "publishable": "It has translational relevance and a direct therapeutic framing.",
                "difficulty": "easy",
            },
        ]
    if "prediction" in topic_id or "survival" in topic_id:
        return [
            {
                "question": "Can PRS, proteins, and EHR features improve time-to-joint-replacement prediction beyond clinical risk factors?",
                "data": "UK Biobank, OAI, UKB-PPP, linked hospital records",
                "method": "Coxnet, competing risks, calibration, C-index, time-dependent AUC",
                "publishable": "It targets a concrete clinical endpoint and emphasises transportable prediction performance.",
                "difficulty": "medium",
            },
            {
                "question": f"Can the evaluation strategy in '{titles[0]}' strengthen reporting of survival prediction in genetic epidemiology?",
                "data": "UK Biobank or OAI",
                "method": "External validation, decision curves, recalibration, missing-data sensitivity analysis",
                "publishable": "A rigorous evaluation paper can be useful even when model novelty is modest.",
                "difficulty": "easy",
            },
            {
                "question": "Do wearable-derived activity trajectories add incremental value to cardiometabolic survival prediction?",
                "data": "UK Biobank accelerometry, EHR-linked outcomes",
                "method": "Longitudinal feature extraction, Cox model, MLP, transformer, calibration",
                "publishable": "It integrates digital epidemiology with clinically measurable risk improvement.",
                "difficulty": "ambitious",
            },
        ]
    return [
        {
            "question": f"Can ideas from '{titles[0]}' improve multimodal prediction for osteoarthritis or cardiometabolic outcomes?",
            "data": "UK Biobank, All of Us, OAI, UKB-PPP, public GWAS and pQTL resources",
            "method": "Multimodal deep learning, cross-attention, Coxnet or transformer baselines",
            "publishable": "A strong paper is possible if the method is benchmarked against simpler clinical and genetic models.",
            "difficulty": "ambitious",
        },
        {
            "question": "Which representation-learning features are stable enough for epidemiological interpretation rather than only benchmark performance?",
            "data": "UK Biobank tabular/EHR data, wearable accelerometry, proteomics",
            "method": "Representation learning, external validation, calibration, subgroup analysis",
            "publishable": "It links modern AI methods to reproducibility and clinical utility.",
            "difficulty": "medium",
        },
        {
            "question": f"Can today's {topic_name.lower()} papers suggest a small, publishable methods note for genetic epidemiology workflows?",
            "data": "Public GWAS, pQTL, UK Biobank example phenotypes",
            "method": "Benchmarking, sensitivity analysis, transparent reporting checklist",
            "publishable": "A focused methods note could be fast to execute and valuable for applied researchers.",
            "difficulty": "easy",
        },
    ]


def format_research_ideas(ideas: list[dict[str, str]]) -> str:
    blocks = []
    for idx, idea in enumerate(ideas, 1):
        blocks.append(
            f"{idx}. **Research question:** {idea['question']}\n"
            f"   - **Possible data source:** {idea['data']}\n"
            f"   - **Possible method:** {idea['method']}\n"
            f"   - **Why it could be publishable:** {idea['publishable']}\n"
            f"   - **Difficulty level:** {idea['difficulty']}"
        )
    return "\n\n".join(blocks)


def render_report(
    report_date: date,
    topic_context: TopicContext,
    key_papers: list[dict[str, Any]],
    other_papers: list[dict[str, Any]],
) -> str:
    topic = topic_context.topic
    learning_points = "\n".join(f"- {point}" for point in topic.get("learning_points", []))
    key_block = "\n\n".join(format_key_paper(paper) for paper in key_papers) or "No strong matches were found today."
    other_block = "\n".join(format_other_paper(paper) for paper in other_papers) or "No additional relevant papers after deduplication."
    ideas_block = format_research_ideas(generate_research_ideas(topic, key_papers))
    trajectory = (
        f"Yesterday's cycle topic was **{topic_context.previous_topic.get('name')}**. "
        f"Today's focus on **{topic.get('name')}** prepares the next step, "
        f"**{topic_context.next_topic.get('name')}**, by connecting methods, datasets, and disease questions across the week."
    )
    template = REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.format(
        date=report_date.isoformat(),
        main_topic=topic.get("name", ""),
        why_it_matters=topic.get("why_it_matters", ""),
        learning_points=learning_points,
        key_papers=key_block,
        other_papers=other_block,
        research_ideas=ideas_block,
        trajectory=trajectory,
    )


def topic_cycle(schedule: dict[str, Any]) -> list[dict[str, Any]]:
    return list(schedule.get("cycle", {}).get("topics") or [])


def previous_topic_items(schedule: dict[str, Any], report_date: date, days: int = 3) -> list[dict[str, Any]]:
    return [get_topic_context(schedule, report_date.fromordinal(report_date.toordinal() - offset)).topic for offset in range(1, days + 1)]


def format_sidebar(topic_context: TopicContext, schedule: dict[str, Any], report_date: date) -> str:
    previous_items = "\n".join(
        f"<li>{h(topic.get('name'))}</li>" for topic in previous_topic_items(schedule, report_date)
    )
    rotation_items = []
    for idx, topic in enumerate(topic_cycle(schedule), 1):
        active = " class=\"active\"" if topic.get("id") == topic_context.topic.get("id") else ""
        rotation_items.append(f"<li{active}><span>Day {idx}</span>{h(topic.get('name'))}</li>")
    return f"""
<aside class="sidebar">
  <div class="sidebar-card today-card">
    <span class="eyebrow">Today's Topic</span>
    <h2>{h(topic_context.topic.get('name'))}</h2>
    <p>{h(topic_context.topic.get('why_it_matters'))}</p>
  </div>
  <div class="sidebar-card">
    <h3>Previous topics</h3>
    <ul class="plain-list">{previous_items}</ul>
  </div>
  <div class="sidebar-card">
    <h3>Weekly rotation</h3>
    <ol class="rotation-list">{''.join(rotation_items)}</ol>
  </div>
</aside>
"""


def format_learning_points(topic: dict[str, Any]) -> str:
    return "\n".join(f"<li>{h(point)}</li>" for point in topic.get("learning_points", []))


def format_idea_bank(ideas: list[dict[str, str]]) -> str:
    cards = []
    for idx, idea in enumerate(ideas, 1):
        difficulty = idea.get("difficulty", "medium")
        cards.append(
            f"""
<article class="idea-card difficulty-{h(difficulty)}">
  <div class="idea-number">{idx}</div>
  <div>
    <h3>{h(idea['question'])}</h3>
    <dl>
      <dt>Data</dt><dd>{h(idea['data'])}</dd>
      <dt>Method</dt><dd>{h(idea['method'])}</dd>
      <dt>Publishable because</dt><dd>{h(idea['publishable'])}</dd>
      <dt>Difficulty</dt><dd><span class="difficulty-pill">{h(difficulty)}</span></dd>
    </dl>
  </div>
</article>
"""
        )
    return "\n".join(cards)


def render_dashboard_html(
    report_date: date,
    topic_context: TopicContext,
    schedule: dict[str, Any],
    key_papers: list[dict[str, Any]],
    other_papers: list[dict[str, Any]],
) -> str:
    topic = topic_context.topic
    ideas = generate_research_ideas(topic, key_papers)
    key_cards = "\n".join(format_dashboard_paper(paper, featured=True) for paper in key_papers)
    other_cards = "\n".join(format_dashboard_paper(paper) for paper in other_papers)
    if not key_cards:
        key_cards = "<div class=\"empty-state\">No high-priority papers were selected today.</div>"
    if not other_cards:
        other_cards = "<div class=\"empty-state\">No secondary papers passed the relevance threshold today.</div>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Research Radar - {h(report_date.isoformat())}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f7fb;
      --surface: #ffffff;
      --surface-soft: #eef4f8;
      --text: #1f2937;
      --muted: #64748b;
      --line: #d8e0e8;
      --accent: #0f766e;
      --accent-soft: #d9f3ee;
      --must: #b42318;
      --must-bg: #fff1f0;
      --idea: #744210;
      --idea-bg: #fff7df;
      --shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
    }}
    body.dark {{
      color-scheme: dark;
      --bg: #111827;
      --surface: #182232;
      --surface-soft: #223044;
      --text: #e5e7eb;
      --muted: #a8b3c3;
      --line: #334155;
      --accent: #5eead4;
      --accent-soft: #123d3a;
      --must: #fca5a5;
      --must-bg: #3f1d22;
      --idea: #fde68a;
      --idea-bg: #3d2f12;
      --shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
      letter-spacing: 0;
    }}
    a {{ color: inherit; }}
    .dashboard-shell {{
      display: grid;
      grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
      min-height: 100vh;
    }}
    .sidebar {{
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
      padding: 24px;
      background: var(--surface);
      border-right: 1px solid var(--line);
    }}
    .sidebar-card {{
      background: var(--surface-soft);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }}
    .today-card {{ background: var(--accent-soft); }}
    .eyebrow {{
      display: block;
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 800;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .sidebar h2, .sidebar h3 {{ margin: 0 0 10px; line-height: 1.25; }}
    .sidebar p {{ margin: 0; color: var(--muted); }}
    .plain-list, .rotation-list {{ margin: 0; padding-left: 18px; color: var(--muted); }}
    .plain-list li, .rotation-list li {{ margin: 8px 0; }}
    .rotation-list li.active {{
      color: var(--text);
      font-weight: 700;
    }}
    .rotation-list span {{
      display: block;
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 700;
    }}
    .content {{
      padding: 28px;
      max-width: 1220px;
      width: 100%;
      margin: 0 auto;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
      margin-bottom: 24px;
    }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: clamp(2rem, 4vw, 3.2rem);
      line-height: 1.05;
    }}
    .hero p {{ max-width: 820px; color: var(--muted); margin: 0; }}
    .toolbar {{
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: flex-end;
    }}
    .toggle {{
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--text);
      border-radius: 8px;
      padding: 10px 12px;
      font-weight: 700;
      cursor: pointer;
    }}
    .section-card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      margin-bottom: 18px;
      overflow: hidden;
    }}
    details.section-card > summary {{
      cursor: pointer;
      list-style: none;
      padding: 20px 22px;
      font-size: 1.2rem;
      font-weight: 800;
      border-bottom: 1px solid var(--line);
    }}
    details.section-card > summary::-webkit-details-marker {{ display: none; }}
    .section-body {{ padding: 22px; }}
    .learning-list {{ margin: 0; padding-left: 20px; }}
    .paper-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 16px;
    }}
    .paper-card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      min-width: 0;
    }}
    .paper-card.featured {{ border-color: color-mix(in srgb, var(--accent), var(--line) 45%); }}
    .paper-card.must-read {{
      border-color: var(--must);
      background: linear-gradient(180deg, var(--must-bg), var(--surface) 34%);
    }}
    .paper-card h3 {{
      margin: 12px 0 6px;
      font-size: 1.1rem;
      line-height: 1.25;
    }}
    .paper-card-topline {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }}
    .badge-row, .method-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .badge, .method-chip, .difficulty-pill {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      padding: 3px 9px;
      font-size: 0.78rem;
      font-weight: 700;
      background: var(--surface-soft);
      color: var(--muted);
      border: 1px solid var(--line);
    }}
    .badge.topic {{ color: var(--accent); background: var(--accent-soft); }}
    .badge.must {{ color: var(--must); background: var(--must-bg); border-color: var(--must); }}
    .arxiv-link {{
      flex: 0 0 auto;
      color: var(--accent);
      font-weight: 800;
      text-decoration: none;
    }}
    .authors, .plain-summary, .paper-details p, .reading-time {{
      color: var(--muted);
    }}
    .paper-details {{
      margin-top: 14px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }}
    .paper-details summary {{
      cursor: pointer;
      font-weight: 800;
      color: var(--text);
    }}
    .detail-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px 18px;
      margin-top: 12px;
    }}
    .detail-grid h4 {{ margin: 0 0 4px; }}
    .detail-grid p {{ margin: 0; }}
    .score-grid {{
      display: grid;
      gap: 8px;
      margin-top: 12px;
    }}
    .score-row {{
      display: grid;
      grid-template-columns: 110px 1fr 48px;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .score-track {{
      height: 8px;
      border-radius: 999px;
      background: var(--surface-soft);
      overflow: hidden;
    }}
    .score-fill {{
      height: 100%;
      background: var(--accent);
      border-radius: inherit;
    }}
    .idea-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }}
    .idea-card {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 14px;
      padding: 18px;
      border-radius: 8px;
      border: 1px solid color-mix(in srgb, var(--idea), var(--line) 55%);
      background: var(--idea-bg);
    }}
    .idea-number {{
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: var(--idea);
      color: var(--surface);
      font-weight: 900;
    }}
    .idea-card h3 {{
      margin: 0 0 12px;
      line-height: 1.25;
    }}
    .idea-card dl {{
      display: grid;
      grid-template-columns: 110px 1fr;
      gap: 8px 12px;
      margin: 0;
    }}
    .idea-card dt {{ font-weight: 800; }}
    .idea-card dd {{ margin: 0; color: var(--muted); }}
    .empty-state {{
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 20px;
      color: var(--muted);
      background: var(--surface-soft);
    }}
    @media (max-width: 900px) {{
      .dashboard-shell {{ grid-template-columns: 1fr; }}
      .sidebar {{
        position: relative;
        height: auto;
        border-right: none;
        border-bottom: 1px solid var(--line);
      }}
      .hero {{ grid-template-columns: 1fr; }}
      .toolbar {{ justify-content: flex-start; }}
    }}
    @media (max-width: 560px) {{
      .content, .sidebar {{ padding: 16px; }}
      .paper-card-topline {{ flex-direction: column; }}
      .score-row {{ grid-template-columns: 88px 1fr 42px; }}
      .idea-card dl {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="dashboard-shell">
    {format_sidebar(topic_context, schedule, report_date)}
    <main class="content">
      <header class="hero">
        <div>
          <span class="eyebrow">Daily Research Radar - {h(report_date.isoformat())}</span>
          <h1>{h(topic.get('name'))}</h1>
          <p>{h(topic.get('why_it_matters'))}</p>
        </div>
        <div class="toolbar">
          <button id="darkModeToggle" class="toggle" type="button">Dark mode</button>
        </div>
      </header>

      <details class="section-card" open>
        <summary>Today's learning focus</summary>
        <div class="section-body">
          <ul class="learning-list">{format_learning_points(topic)}</ul>
        </div>
      </details>

      <details class="section-card" open>
        <summary>Read these first</summary>
        <div class="section-body paper-grid">{key_cards}</div>
      </details>

      <details class="section-card">
        <summary>Other relevant papers</summary>
        <div class="section-body paper-grid">{other_cards}</div>
      </details>

      <details class="section-card" open>
        <summary>Idea Bank</summary>
        <div class="section-body idea-grid">{format_idea_bank(ideas)}</div>
      </details>

      <details class="section-card">
        <summary>Weekly learning trajectory</summary>
        <div class="section-body">
          <p>Yesterday's cycle topic was <strong>{h(topic_context.previous_topic.get('name'))}</strong>. Today's focus prepares the next step, <strong>{h(topic_context.next_topic.get('name'))}</strong>, by connecting methods, datasets, and disease questions across the week.</p>
        </div>
      </details>
    </main>
  </div>
  <script>
    const storedTheme = localStorage.getItem('researchRadarTheme');
    if (storedTheme === 'dark') document.body.classList.add('dark');
    const toggle = document.getElementById('darkModeToggle');
    function syncToggleLabel() {{
      toggle.textContent = document.body.classList.contains('dark') ? 'Light mode' : 'Dark mode';
    }}
    toggle.addEventListener('click', () => {{
      document.body.classList.toggle('dark');
      localStorage.setItem('researchRadarTheme', document.body.classList.contains('dark') ? 'dark' : 'light');
      syncToggleLabel();
    }});
    syncToggleLabel();
  </script>
</body>
</html>
"""


def update_file_list(output_dir: Path, file_list_path: Path = Path("assets/file-list.txt")) -> None:
    file_list_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(path.name for path in output_dir.glob("*") if path.is_file())
    file_list_path.write_text("\n".join(files) + ("\n" if files else ""), encoding="utf-8")


def generate_daily_report(
    args: argparse.Namespace,
    report_date: date,
    profile: dict[str, Any],
    schedule: dict[str, Any],
    categories: list[str],
) -> bool:
    output_dir = Path(args.output_dir)
    if args.skip_existing and has_expected_outputs(output_dir, report_date):
        print(f"Skipping {report_date.isoformat()} because expected outputs already exist.")
        return False

    topic_context = get_topic_context(schedule, report_date)
    data_path, papers = load_or_fetch_papers(args, report_date, categories)
    if not papers:
        raise SystemExit(f"No papers available in {data_path}")

    model_name = os.environ.get("MODEL_NAME", "gpt-4o-mini")
    chain = None if args.no_llm else get_llm_chain(model_name, args.llm_timeout_seconds)

    enhanced: list[dict[str, Any]]
    if all("research_radar" in paper for paper in papers):
        print(f"Using pre-enhanced research radar data from {data_path}.", file=sys.stderr)
        enhanced = papers
    elif chain is not None and args.max_workers > 1:
        enhanced_slots: list[dict[str, Any] | None] = [None] * len(papers)
        workers = max(1, args.max_workers)
        print(f"Enhancing {len(papers)} papers with {workers} LLM workers.", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {
                executor.submit(enhance_paper, paper, profile, topic_context.topic, report_date, chain): idx
                for idx, paper in enumerate(papers)
            }
            for completed, future in enumerate(as_completed(future_to_idx), 1):
                idx = future_to_idx[future]
                try:
                    enhanced_slots[idx] = future.result()
                except Exception as exc:
                    print(f"Unexpected paper enhancement failure at index {idx}: {exc}", file=sys.stderr)
                    enhanced_slots[idx] = enhance_paper(
                        papers[idx],
                        profile,
                        topic_context.topic,
                        report_date,
                        None,
                    )
                if completed == len(papers) or completed % 10 == 0:
                    print(f"Enhanced {completed}/{len(papers)} papers.", file=sys.stderr)
        enhanced = [paper for paper in enhanced_slots if paper is not None]
    else:
        enhanced = []
        for idx, paper in enumerate(papers, 1):
            enhanced.append(enhance_paper(paper, profile, topic_context.topic, report_date, chain))
            if idx == len(papers) or idx % 25 == 0:
                print(f"Enhanced {idx}/{len(papers)} papers.", file=sys.stderr)

    history_path = Path(args.history)
    history = load_history(history_path)
    key_papers, other_papers = select_papers(
        enhanced,
        history,
        report_date,
        max_key=max(1, args.max_key),
        max_other=max(0, args.max_other),
        serendipity_ratio=max(0.0, min(1.0, args.serendipity_ratio)),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = expected_output_paths(output_dir, report_date)
    enhanced_path = paths["enhanced"]
    report_path = paths["markdown"]
    dashboard_path = paths["html"]

    ranked_enhanced = sorted(
        enhanced,
        key=lambda paper: paper["research_radar"]["scores"]["final_priority_score"],
        reverse=True,
    )
    write_jsonl(enhanced_path, ranked_enhanced)
    report_path.write_text(render_report(report_date, topic_context, key_papers, other_papers), encoding="utf-8")
    dashboard_path.write_text(
        render_dashboard_html(report_date, topic_context, schedule, key_papers, other_papers),
        encoding="utf-8",
    )
    update_history(history_path, report_date, key_papers, other_papers)

    print(f"Wrote enhanced radar data: {enhanced_path}")
    print(f"Wrote Markdown report: {report_path}")
    print(f"Wrote HTML dashboard: {dashboard_path}")
    print(f"Main topic: {topic_context.topic.get('name')}")
    print(f"Selected {len(key_papers)} key papers and {len(other_papers)} other papers.")
    return True


def main() -> None:
    args = parse_args()
    report_dates = resolve_report_dates(args)
    if args.data and len(report_dates) != 1:
        raise SystemExit("--data can only be used with a single --date run.")

    profile = load_yaml(args.profile)
    schedule = load_yaml(args.schedule)
    categories = configured_categories(profile)

    generated = 0
    for report_date in report_dates:
        print(f"=== Daily Research Radar: {report_date.isoformat()} ===")
        if generate_daily_report(args, report_date, profile, schedule, categories):
            generated += 1

    update_file_list(Path(args.output_dir))
    print(f"Updated assets/file-list.txt")
    print(f"Processed {len(report_dates)} date(s); generated {generated}, skipped {len(report_dates) - generated}.")


if __name__ == "__main__":
    main()
