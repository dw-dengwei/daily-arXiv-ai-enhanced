#!/usr/bin/env python3
"""Generate daily keyword report and author-focused per-paper source summaries."""

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Set, Tuple

import requests


TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "autonomous exploration": [
        "autonomous exploration",
        "robot exploration",
        "active exploration",
        "frontier exploration",
    ],
    "reinforcement learning": [
        "reinforcement learning",
        "deep reinforcement learning",
        "policy gradient",
        "q-learning",
        "rl",
    ],
    "path planning": [
        "path planning",
        "motion planning",
        "trajectory planning",
        "route planning",
    ],
    "VLM": [
        "vlm",
        "vision-language model",
        "vision language model",
        "vision-language models",
        "multimodal model",
    ],
}

TARGET_AUTHORS: Dict[str, List[str]] = {
    "Gao Fei": ["gao fei", "fei gao"],
    "Zhou Boyu": ["zhou boyu", "boyu zhou"],
    "Cao Yuhong": ["cao yuhong", "yuhong cao"],
    "Daniele Nardi": ["daniele nardi"],
    "Vincenzo Suriani": ["vincenzo suriani"],
    "Guillaume Sartoretti": ["guillaume sartoretti"],
}


def get_bjt_date() -> str:
    bjt = timezone(timedelta(hours=8))
    return datetime.now(bjt).strftime("%Y-%m-%d")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily focused arXiv report")
    parser.add_argument("--input", type=str, default="", help="Input jsonl file path")
    parser.add_argument("--date", type=str, default="", help="Report date, e.g. 2026-03-09")
    parser.add_argument("--output-dir", type=str, default="report", help="Output report dir")
    parser.add_argument(
        "--generate-source-guide",
        action="store_true",
        help="Generate per-paper source summaries for author-matched papers",
    )
    parser.add_argument(
        "--source-guide-dir",
        type=str,
        default="report/author_source_guides",
        help="Directory for source summary markdown output",
    )
    parser.add_argument(
        "--max-source-papers",
        type=int,
        default=20,
        help="Max number of author-matched papers to summarize",
    )
    return parser.parse_args()


def load_papers(input_file: str) -> List[dict]:
    papers: List[dict] = []
    if not input_file or not os.path.exists(input_file):
        return papers
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                papers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return papers


def normalize_author_tokens(name: str) -> Set[str]:
    return set(re.findall(r"[a-z]+", name.lower()))


def build_alias_token_map() -> Dict[str, List[Set[str]]]:
    alias_map: Dict[str, List[Set[str]]] = {}
    for target, aliases in TARGET_AUTHORS.items():
        alias_map[target] = [normalize_author_tokens(alias) for alias in aliases]
    return alias_map


def match_target_authors(authors: Iterable[str], alias_token_map: Dict[str, List[Set[str]]]) -> List[str]:
    matched: List[str] = []
    for target, alias_sets in alias_token_map.items():
        for author in authors:
            author_tokens = normalize_author_tokens(str(author))
            if not author_tokens:
                continue
            if any(alias_tokens.issubset(author_tokens) for alias_tokens in alias_sets):
                matched.append(target)
                break
    return matched


def collect_search_text(item: dict) -> str:
    text_fields = [
        item.get("title", ""),
        item.get("summary", ""),
        item.get("comment", ""),
        " ".join(item.get("categories", [])) if isinstance(item.get("categories"), list) else "",
    ]
    ai = item.get("AI", {})
    if isinstance(ai, dict):
        text_fields.extend(str(v) for v in ai.values())
    return "\n".join(str(x) for x in text_fields if x).lower()


def match_topics(text: str) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text]
        if hits:
            result[topic] = sorted(set(hits))
    return result


def short_summary(item: dict, limit: int = 220) -> str:
    ai = item.get("AI", {})
    candidate = ""
    if isinstance(ai, dict):
        candidate = str(ai.get("tldr", "")).strip()
    if not candidate:
        candidate = str(item.get("summary", "")).strip().replace("\n", " ")
    if len(candidate) > limit:
        return candidate[: limit - 3] + "..."
    return candidate


def split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[\.\!\?。！？;；])\s+", text) if s.strip()]


def pick_sentence(sentences: List[str], cues: Iterable[str], default: str) -> str:
    for sent in sentences:
        lower = sent.lower()
        if any(cue in lower for cue in cues):
            return sent
    return default


def analyze_matches(papers: List[dict]) -> Tuple[List[dict], List[dict], Counter, Counter]:
    alias_map = build_alias_token_map()
    matched_records: List[dict] = []
    topic_counter: Counter = Counter()
    author_counter: Counter = Counter()

    for item in papers:
        topics = match_topics(collect_search_text(item))
        authors = item.get("authors", [])
        authors = authors if isinstance(authors, list) else []
        matched_authors = match_target_authors(authors, alias_map)
        if topics or matched_authors:
            matched_records.append({"item": item, "topics": topics, "authors": matched_authors})
            topic_counter.update(topics.keys())
            author_counter.update(matched_authors)

    author_focus_records = merge_author_matched_records(matched_records)
    return matched_records, author_focus_records, topic_counter, author_counter


def merge_author_matched_records(matched_records: List[dict]) -> List[dict]:
    merged: Dict[str, dict] = {}
    order: List[str] = []
    for record in matched_records:
        if not record["authors"]:
            continue
        item = record["item"]
        item_id = str(item.get("id") or item.get("abs") or item.get("title") or len(order))
        if item_id not in merged:
            merged[item_id] = {"item": item, "topics": dict(record["topics"]), "authors": list(record["authors"])}
            order.append(item_id)
        else:
            prev = merged[item_id]
            prev["authors"] = sorted(set(prev["authors"]) | set(record["authors"]), key=author_rank)
            for topic, kws in record["topics"].items():
                old = set(prev["topics"].get(topic, []))
                prev["topics"][topic] = sorted(old | set(kws))
    return [merged[item_id] for item_id in order]


def author_rank(author_name: str) -> int:
    names = list(TARGET_AUTHORS.keys())
    return names.index(author_name) if author_name in names else len(names)


def build_model_candidates() -> List[str]:
    primary = os.environ.get("NOTEBOOKLM_MODEL", "").strip() or "gemini-2.0-flash"
    raw_fallbacks = os.environ.get("NOTEBOOKLM_FALLBACK_MODELS", "").strip()
    if raw_fallbacks:
        fallback_models = [m.strip() for m in raw_fallbacks.split(",") if m.strip()]
    else:
        fallback_models = ["gemini-2.0-flash", "gemini-1.5-flash"]

    models: List[str] = []
    for model in [primary, *fallback_models]:
        if model and model not in models:
            models.append(model)
    return models


def invoke_gemini(prompt: str, model_name: str, api_key: str) -> Tuple[int, str]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600},
    }
    response = requests.post(url, json=payload, timeout=80)
    status_code = response.status_code
    if status_code != 200:
        return status_code, ""
    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return 200, ""
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "\n".join(part.get("text", "").strip() for part in parts if part.get("text"))
    return 200, text.strip()


def generate_gemini_summary(
    item: dict,
    matched_authors: List[str],
    models: List[str],
    api_key: str,
    runtime_state: Dict[str, int],
) -> Tuple[str, str, str]:
    ai_tldr = item.get("AI", {}).get("tldr", "") if isinstance(item.get("AI", {}), dict) else ""
    prompt = (
        "请基于下面这篇论文信息，输出“来源总结”。\n"
        "输出格式固定为 5 行（每行 1 句，精炼，不超过 35 个字）：\n"
        "- 介绍：\n- 提出：\n- 方法：\n- 实验效果：\n- 结论：\n"
        "不要编造，不要输出多余说明。\n\n"
        f"标题：{item.get('title', 'N/A')}\n"
        f"作者：{', '.join(item.get('authors', [])) if isinstance(item.get('authors'), list) else 'N/A'}\n"
        f"命中关注作者：{', '.join(matched_authors)}\n"
        f"分类：{', '.join(item.get('categories', [])) if isinstance(item.get('categories'), list) else 'N/A'}\n"
        f"链接：{item.get('abs', 'N/A')}\n"
        f"一句话摘要：{ai_tldr}\n"
        f"原始摘要：{item.get('summary', '')}\n"
    )

    start_idx = runtime_state.get("model_idx", 0)
    attempt_order = models[start_idx:] + models[:start_idx]
    for model in attempt_order:
        try:
            code, text = invoke_gemini(prompt=prompt, model_name=model, api_key=api_key)
            if code == 200 and text:
                runtime_state["model_idx"] = models.index(model)
                return text, model, "gemini"
            if code == 404:
                continue
            if code == 429:
                continue
        except Exception:
            continue

    return build_local_paper_source_summary(item), "", "local_fallback"


def build_local_paper_source_summary(item: dict) -> str:
    sentences = split_sentences(item.get("summary", ""))
    intro = sentences[0] if sentences else "摘要信息不足。"
    proposal = pick_sentence(
        sentences,
        cues=("propose", "present", "introduce", "novel", "new", "提出", "提出了"),
        default=intro,
    )
    method = pick_sentence(
        sentences,
        cues=("method", "framework", "approach", "algorithm", "policy", "planner", "methodology", "方法"),
        default="方法细节在摘要中描述有限。",
    )
    result = pick_sentence(
        sentences,
        cues=("experiment", "result", "outperform", "improve", "achieve", "%", "实验", "效果"),
        default="摘要未给出明确实验效果。",
    )
    conclusion = sentences[-1] if sentences else "结论信息不足。"

    lines = [
        f"- 介绍：{intro}",
        f"- 提出：{proposal}",
        f"- 方法：{method}",
        f"- 实验效果：{result}",
        f"- 结论：{conclusion}",
    ]
    return "\n".join(lines)


def save_author_source_guide(
    date_str: str,
    author_focus_records: List[dict],
    source_guide_dir: str,
    max_source_papers: int,
) -> str:
    os.makedirs(source_guide_dir, exist_ok=True)
    output_path = os.path.join(source_guide_dir, f"{date_str}.md")

    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    models = build_model_candidates()
    runtime_state = {"model_idx": 0}

    lines = [
        f"# 关注作者论文来源总结（{date_str}）",
        "",
        "> 仅针对“关注作者命中”的论文生成来源总结。",
        "> 总结结构：介绍 / 提出 / 方法 / 实验效果 / 结论",
        "",
    ]

    if not author_focus_records:
        lines.append("今日没有命中关注作者的论文。")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return output_path

    if api_key:
        lines.append(f"> 生成引擎：Gemini API（模型候选：{', '.join(models)}）")
    else:
        lines.append("> 生成引擎：本地回退（未配置 GOOGLE_API_KEY）")
    lines.append("")

    gemini_count = 0
    picked_records = author_focus_records[: max(1, max_source_papers)]
    for idx, record in enumerate(picked_records, start=1):
        item = record["item"]
        matched_authors = record["authors"]
        if api_key:
            summary_text, model_used, mode = generate_gemini_summary(
                item=item,
                matched_authors=matched_authors,
                models=models,
                api_key=api_key,
                runtime_state=runtime_state,
            )
        else:
            summary_text, model_used, mode = build_local_paper_source_summary(item), "", "local_fallback"

        if mode == "gemini":
            gemini_count += 1

        lines.append(f"## [{idx}] {item.get('title', 'Untitled')}")
        if item.get("abs"):
            lines.append(f"- 链接：{item.get('abs')}")
        lines.append(f"- 命中作者：{', '.join(matched_authors) if matched_authors else '无'}")
        topic_tags = ", ".join(record["topics"].keys()) if record["topics"] else "无"
        lines.append(f"- 相关主题：{topic_tags}")
        if mode == "gemini" and model_used:
            lines.append(f"- 生成模型：{model_used}")
        elif api_key:
            lines.append("- 生成模型：Gemini 调用失败，已回退本地总结")
        lines.append("")
        lines.append(summary_text)
        lines.append("")

    lines.insert(
        4,
        f"> 今日命中关注作者论文数：{len(author_focus_records)}，生成总结论文数：{len(picked_records)}，Gemini 成功数：{gemini_count}",
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return output_path


def render_report(
    date_str: str,
    input_file: str,
    papers: List[dict],
    matched_records: List[dict],
    author_focus_records: List[dict],
    topic_counter: Counter,
    author_counter: Counter,
    source_guide_rel_path: str = "",
) -> str:
    lines: List[str] = []
    lines.append(f"# arXiv 关键词日报（{date_str}）")
    lines.append("")
    lines.append("> 时区：北京时间（UTC+8）")
    lines.append("> 关注主题关键词：autonomous exploration, reinforcement learning, path planning, VLM")
    lines.append("> 关注作者关键词：Gao Fei, Zhou Boyu, Cao Yuhong, Daniele Nardi, Vincenzo Suriani, Guillaume Sartoretti")
    lines.append("")

    if not papers:
        lines.append("## 今日概览")
        lines.append("")
        if input_file:
            lines.append(f"- 数据文件：`{input_file}` 不存在或为空。")
        else:
            lines.append("- 今日无可用数据文件（可能是去重后无新内容）。")
        if source_guide_rel_path:
            lines.append(f"- 关注作者来源总结：[{source_guide_rel_path}]({source_guide_rel_path})")
        lines.append("- 本日报已自动生成，占位说明。")
        return "\n".join(lines) + "\n"

    lines.append("## 今日概览")
    lines.append("")
    lines.append(f"- 扫描论文总数：**{len(papers)}**")
    lines.append(f"- 命中（主题/作者）论文数：**{len(matched_records)}**")
    lines.append(f"- 命中关注作者论文数：**{len(author_focus_records)}**")
    if source_guide_rel_path:
        lines.append(f"- 关注作者来源总结：[{source_guide_rel_path}]({source_guide_rel_path})")
    lines.append("")

    lines.append("### 主题命中统计")
    lines.append("")
    for topic in TOPIC_KEYWORDS:
        lines.append(f"- {topic}: {topic_counter.get(topic, 0)}")
    lines.append("")

    lines.append("### 作者命中统计")
    lines.append("")
    for author in TARGET_AUTHORS:
        lines.append(f"- {author}: {author_counter.get(author, 0)}")
    lines.append("")

    if not matched_records:
        lines.append("## 结论")
        lines.append("")
        lines.append("- 今日未发现与关注主题或作者关键词直接相关的论文。")
        return "\n".join(lines) + "\n"

    lines.append("## 按主题分类")
    lines.append("")
    for topic in TOPIC_KEYWORDS:
        topic_records = [r for r in matched_records if topic in r["topics"]]
        lines.append(f"### {topic}（{len(topic_records)}）")
        lines.append("")
        if not topic_records:
            lines.append("- 无")
            lines.append("")
            continue
        for idx, record in enumerate(topic_records, start=1):
            item = record["item"]
            lines.append(f"{idx}. **{item.get('title', 'Untitled')}**")
            if item.get("abs"):
                lines.append(f"   - 链接：{item.get('abs')}")
            authors = ", ".join(item.get("authors", [])) if isinstance(item.get("authors"), list) else "未知"
            categories = ", ".join(item.get("categories", [])) if isinstance(item.get("categories"), list) else "未知"
            lines.append(f"   - 作者：{authors}")
            lines.append(f"   - 分类：{categories}")
            lines.append(f"   - 主题命中词：{', '.join(record['topics'].get(topic, []))}")
            lines.append(f"   - 作者关键词命中：{', '.join(record['authors']) if record['authors'] else '无'}")
            lines.append(f"   - 摘要：{short_summary(item)}")
            lines.append("")

    lines.append("## 按关注作者聚类")
    lines.append("")
    for author in TARGET_AUTHORS:
        author_records = [r for r in author_focus_records if author in r["authors"]]
        lines.append(f"### {author}（{len(author_records)}）")
        lines.append("")
        if not author_records:
            lines.append("- 无")
            lines.append("")
            continue
        for idx, record in enumerate(author_records, start=1):
            item = record["item"]
            lines.append(f"{idx}. **{item.get('title', 'Untitled')}**")
            if item.get("abs"):
                lines.append(f"   - 链接：{item.get('abs')}")
            topic_tags = ", ".join(record["topics"].keys()) if record["topics"] else "仅作者命中"
            lines.append(f"   - 主题关联：{topic_tags}")
            lines.append("")

    lines.append("## 备注")
    lines.append("")
    lines.append("- 命中规则基于关键词字符串匹配与作者名 token 匹配，可能存在少量误报/漏报。")
    lines.append("- 来源总结只针对“关注作者命中”论文生成。")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    date_str = args.date.strip() if args.date else get_bjt_date()
    papers = load_papers(args.input)

    matched_records, author_focus_records, topic_counter, author_counter = analyze_matches(papers)

    source_guide_rel_path = ""
    if args.generate_source_guide:
        source_guide_path = save_author_source_guide(
            date_str=date_str,
            author_focus_records=author_focus_records,
            source_guide_dir=args.source_guide_dir,
            max_source_papers=args.max_source_papers,
        )
        source_guide_rel_path = os.path.relpath(
            os.path.abspath(source_guide_path), start=os.path.abspath(args.output_dir)
        ).replace(os.sep, "/")

    report_text = render_report(
        date_str=date_str,
        input_file=args.input,
        papers=papers,
        matched_records=matched_records,
        author_focus_records=author_focus_records,
        topic_counter=topic_counter,
        author_counter=author_counter,
        source_guide_rel_path=source_guide_rel_path,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    output_file = os.path.join(args.output_dir, f"{date_str}.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Generated report: {output_file}")
    if source_guide_rel_path:
        print(f"Generated source guide: {source_guide_rel_path}")


if __name__ == "__main__":
    main()
