# Local llama-server (Qwen3.5-9B GGUF) Offline Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the full pipeline locally (crawl → dedup → local llama-server AI enhance → convert → local file-list) and serve a local static website that only reads local files.

**Architecture:** Replace the current LangChain function-calling path with a llama-server OpenAI-compatible client that enforces JSON-only output and parses it with robust fallbacks. Frontend data loading switches to local paths automatically on localhost.

**Tech Stack:** Python 3.12+, Scrapy, requests, llama-server (llama.cpp OpenAI-compatible API), vanilla JS frontend, local static file server.

---

## File/Change Map

**Modify**
- `ai/enhance.py` (add llama-server backend, remove sensitive check, robust JSON parsing)
- `js/data-config.js` (local mode uses local relative/origin URLs)
- `README.md` (add local usage instructions)

**Create**
- `ai/llama_server.py` (small HTTP client + prompt builder + JSON extract/parse helpers)
- `scripts/local_pipeline.py` (non-interactive local pipeline runner)

---

### Task 1: Add llama-server client + JSON parsing utilities

**Files:**
- Create: `ai/llama_server.py`
- Test: `ai/tests/test_llama_server_json.py` (unittest)

- [ ] **Step 1: Create `ai/llama_server.py` with a minimal client**

Include:
- `LlamaServerConfig` (base_url, model, temperature, max_tokens, timeout_s)
- `build_prompt(language: str, abstract: str) -> list[dict]` that returns OpenAI chat messages
- `call_chat_completions(config, messages) -> str` that returns raw assistant text
- `extract_first_json_object(text: str) -> str | None`
- `parse_ai_json(text: str) -> dict` that returns dict with required keys or raises
- `ensure_ai_fields(obj: dict) -> dict` that fills missing keys with defaults

```python
# ai/llama_server.py
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any, Dict, List, Optional

import requests

REQUIRED_AI_FIELDS = ["tldr", "motivation", "method", "result", "conclusion"]


@dataclass(frozen=True)
class LlamaServerConfig:
    base_url: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 1000
    timeout_s: int = 120


def build_messages(language: str, abstract: str) -> List[Dict[str, str]]:
    system = (
        "You are a professional paper analyst.\n"
        "Output must be STRICT JSON only. Do not output Markdown, code fences, or extra text.\n"
        f"Language: {language}\n"
        "Return exactly one JSON object with keys: "
        "tldr, motivation, method, result, conclusion.\n"
        "Only use information from the provided abstract.\n"
    )
    user = (
        "Analyze the following paper abstract and return the required JSON.\n\n"
        f"Abstract:\n{abstract}\n"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def call_chat_completions(config: LlamaServerConfig, messages: List[Dict[str, str]]) -> str:
    url = f"{config.base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    resp = requests.post(url, json=payload, timeout=config.timeout_s)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def extract_first_json_object(text: str) -> Optional[str]:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _light_json_fix(s: str) -> str:
    s = s.strip()
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    return s


def parse_ai_json(text: str) -> Dict[str, Any]:
    raw = text.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass

    candidate = extract_first_json_object(raw)
    if not candidate:
        raise ValueError("No JSON object found in model output")

    candidate = _light_json_fix(candidate)
    return json.loads(candidate)


def ensure_ai_fields(obj: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k in REQUIRED_AI_FIELDS:
        v = obj.get(k, "")
        out[k] = "" if v is None else str(v)
    return out
```

- [ ] **Step 2: Add a unittest for JSON extraction + parsing**

Create `ai/tests/test_llama_server_json.py` (no extra dependencies).

```python
# ai/tests/test_llama_server_json.py
import unittest

from ai.llama_server import extract_first_json_object, parse_ai_json, ensure_ai_fields


class TestLlamaServerJson(unittest.TestCase):
    def test_extract_json_plain(self):
        s = '{"tldr":"a","motivation":"b","method":"c","result":"d","conclusion":"e"}'
        self.assertEqual(extract_first_json_object(s), s)

    def test_extract_json_wrapped_text(self):
        s = 'Here is the JSON:\\n{"tldr":"a","motivation":"b","method":"c","result":"d","conclusion":"e"}\\nThanks'
        self.assertTrue(extract_first_json_object(s).startswith("{"))

    def test_parse_ai_json_with_trailing_comma(self):
        s = '{"tldr":"a","motivation":"b","method":"c","result":"d","conclusion":"e",}'
        obj = parse_ai_json(s)
        self.assertEqual(obj["tldr"], "a")

    def test_ensure_ai_fields_fills_missing(self):
        obj = {"tldr": "a"}
        fixed = ensure_ai_fields(obj)
        self.assertEqual(set(fixed.keys()), {"tldr","motivation","method","result","conclusion"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the unittest**

Run:
```bash
python -m unittest ai.tests.test_llama_server_json -v
```

Expected:
- PASS all tests

- [ ] **Step 4: Commit**

```bash
git add ai/llama_server.py ai/tests/test_llama_server_json.py
git commit -m "feat: add llama-server client and JSON parsing helpers"
```

---

### Task 2: Refactor `ai/enhance.py` to use llama-server backend (offline)

**Files:**
- Modify: `ai/enhance.py`
- Modify: `ai/system.txt` and `ai/template.txt` (optional; can be deprecated for llama backend)
- Test: `python -m unittest ai.tests.test_llama_server_json -v`

- [ ] **Step 1: Add backend selection via env**

In `main()` read:
- `LLM_BACKEND` default to `llama_server`
- `LLAMA_BASE_URL` default `http://127.0.0.1:8080/v1`
- `LLAMA_MODEL` default from `/v1/models` or fallback to env

Implementation approach:
- For llama-server path, bypass LangChain entirely.

- [ ] **Step 2: Remove sensitive check network calls**

Delete:
- `import re` usage only for github link detection can stay, but remove:
  - `requests.post("https://spam.dw-dengwei.workers.dev", ...)`
  - any early returns based on sensitive

Keep (optional):
- github URL extraction (local only) and GitHub API enrichment can remain behind `TOKEN_GITHUB` if you still want it.

- [ ] **Step 3: Implement per-item processing using llama-server**

Pseudocode:
- Build messages via `build_messages(language, item["summary"])`
- Call `call_chat_completions(...)` to get text
- Parse `parse_ai_json(text)` then `ensure_ai_fields(...)`
- Set `item["AI"] = parsed`
- Write output jsonl as before

Ensure:
- Default values on any exception (same 5 keys)
- Keep existing `--max_workers` but default to 1 and document that llama-server is best run serially.

- [ ] **Step 4: Run a dry-run on a small jsonl sample**

Create a tiny sample file (2 items) under a temp path (do not commit):

```bash
python -c "import json;print(json.dumps({'id':'x','summary':'This paper proposes ...'}));print(json.dumps({'id':'y','summary':'We study ...'}))" > /tmp/sample.jsonl
LLM_BACKEND=llama_server LLAMA_BASE_URL=http://127.0.0.1:8080/v1 LLAMA_MODEL=Qwen3.5-9B-Q4_K_M.gguf LANGUAGE=Chinese python ai/enhance.py --data /tmp/sample.jsonl --max_workers 1
```

Expected:
- Generates `/tmp/sample_AI_enhanced_Chinese.jsonl`
- Each line has an `AI` object with 5 string fields

- [ ] **Step 5: Commit**

```bash
git add ai/enhance.py
git commit -m "feat: run AI enhancement via local llama-server"
```

---

### Task 3: Make frontend load local files on localhost

**Files:**
- Modify: `js/data-config.js`

- [ ] **Step 1: Add local host detection**

Logic:
- `const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);`

- [ ] **Step 2: Update `getDataBaseUrl`**

When local:
- return `window.location.origin`

Else:
- keep current GitHub raw base

- [ ] **Step 3: Verify in browser**

Run:
```bash
python -m http.server 8000
```
Open:
- `http://127.0.0.1:8000/`

Expected:
- file-list loads from `http://127.0.0.1:8000/assets/file-list.txt`
- data loads from `http://127.0.0.1:8000/data/...`

- [ ] **Step 4: Commit**

```bash
git add js/data-config.js
git commit -m "feat: load data from local paths on localhost"
```

---

### Task 4: Add a non-interactive local pipeline runner

**Files:**
- Create: `scripts/local_pipeline.py`
- Modify: `README.md`

- [ ] **Step 1: Create `scripts/local_pipeline.py`**

Responsibilities:
- Determine `today` (UTC) or accept `--date YYYY-MM-DD`
- Run commands in order (use `subprocess.run(..., check=True)`)
  1) `scrapy crawl arxiv -o data/<date>.jsonl` (cwd: repo root, but run inside `daily_arxiv` directory like workflow does)
  2) `python daily_arxiv/check_stats.py` (cwd: `daily_arxiv`)
  3) `python ai/enhance.py --data data/<date>.jsonl` (cwd: repo root)
  4) `python to_md/convert.py --data data/<date>_AI_enhanced_<LANG>.jsonl` (cwd: repo root)
  5) write `assets/file-list.txt` listing `data/*.jsonl` (repo root)

Minimal code skeleton:

```python
from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    date = args.date or utc_today()

    data_dir = root / "data"
    assets_dir = root / "assets"
    data_dir.mkdir(exist_ok=True)
    assets_dir.mkdir(exist_ok=True)

    daily_arxiv_dir = root / "daily_arxiv"

    run(["scrapy", "crawl", "arxiv", "-o", f"../data/{date}.jsonl"], cwd=daily_arxiv_dir)
    run(["python", "daily_arxiv/check_stats.py"], cwd=daily_arxiv_dir)

    run(["python", "ai/enhance.py", "--data", f"data/{date}.jsonl", "--max_workers", "1"], cwd=root)

    lang = os.environ.get("LANGUAGE", "Chinese")
    enhanced = f"data/{date}_AI_enhanced_{lang}.jsonl"
    run(["python", "to_md/convert.py", "--data", enhanced], cwd=root)

    files = sorted(data_dir.glob("*.jsonl"))
    (assets_dir / "file-list.txt").write_text("\n".join([f.name for f in files]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Update README with local usage**

Add a new section “Local offline mode”:
- start llama-server command (user provided)
- set env vars:
  - `LLM_BACKEND=llama_server`
  - `LLAMA_BASE_URL=http://127.0.0.1:8080/v1`
  - `LLAMA_MODEL=Qwen3.5-9B-Q4_K_M.gguf`
  - `LANGUAGE=Chinese`
  - `CATEGORIES=...`
- run pipeline:
  - `python scripts/local_pipeline.py`
- serve:
  - `python -m http.server 8000`

- [ ] **Step 3: Verify end-to-end**

1) Ensure llama-server running
2) Run:
```bash
export LLM_BACKEND=llama_server
export LLAMA_BASE_URL=http://127.0.0.1:8080/v1
export LLAMA_MODEL=Qwen3.5-9B-Q4_K_M.gguf
export LANGUAGE=Chinese
export CATEGORIES="cs.CV,cs.CL"
python scripts/local_pipeline.py
python -m http.server 8000
```

Expected:
- `assets/file-list.txt` exists and lists `*_AI_enhanced_Chinese.jsonl`
- `http://127.0.0.1:8000/` loads and shows papers

- [ ] **Step 4: Commit**

```bash
git add scripts/local_pipeline.py README.md
git commit -m "feat: local offline pipeline runner"
```

---

## Plan Self-Review

- Spec coverage:
  - AI backend llama-server + JSON-only: Task 1 + Task 2
  - Remove sensitive check: Task 2
  - Frontend local data source: Task 3
  - Full local pipeline: Task 4
- Placeholder scan:
  - All steps include concrete file paths, code, and commands
  - No TODO/TBD
- Type consistency:
  - `AI` dict keys are consistent across utilities and enhance integration

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-04-30-llama-server-local-qwen35-9b.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks
2. **Inline Execution** — execute tasks in this session with checkpoints

Which approach?

