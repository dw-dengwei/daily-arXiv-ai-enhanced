# Local llama-server (Qwen3.5-9B GGUF) Offline Pipeline Implementation Plan

**Goal:** Run the full pipeline locally (crawl → dedup → local llama-server AI enhance → convert → local file-list) and serve a local static website that only reads local files.

**Architecture:** Replace the current LangChain function-calling path with a llama-server OpenAI-compatible client that enforces JSON-only output and parses it with robust fallbacks. Frontend data loading always uses local origin + relative paths (no GitHub raw mode).

**Tech Stack:** Python 3.12+, Scrapy, llama-server (llama.cpp OpenAI-compatible API), vanilla JS frontend, local static file server. HTTP calls use Python standard library (urllib) to avoid extra runtime dependencies.

---

## File/Change Map

**Modify**
- `ai/enhance.py` (llama-server backend, JSON-only output, robust JSON parsing, remove sensitive check + GitHub API)
- `ai/system.txt` and `ai/template.txt` (prompt enforces JSON-only output)
- `js/data-config.js` (always use local origin + relative paths)

**Create**
- `ai/llama_json.py` (JSON parse/extract/repair helpers + ensure required fields)
- `local_arxiv/__main__.py` (CLI: `python -m local_arxiv run|serve`)
- `local_arxiv/__init__.py`
- `tests/test_llama_json.py` (unittest)
- `tests/test_local_integration.py` (unittest; fake llama-server)

---

## Status

This plan has been implemented in the repository. The steps below document what was built and how to verify it.

---

## Implementation Summary (as-built)

- `ai/enhance.py` now calls llama-server directly via `urllib`:
  - Checks `GET {LLAMA_BASE_URL}/models` and fails fast if `LLAMA_MODEL` is missing
  - Calls `POST {LLAMA_BASE_URL}/chat/completions`
  - Enforces JSON-only output via prompt and parses with robust fallbacks
- Sensitive-check network calls and GitHub API enrichment have been removed.
- Parsing utilities are in `ai/llama_json.py`.

---

## Frontend Data Source (as-built)

- `js/data-config.js` always uses local origin + relative paths:
  - `assets/file-list.txt`
  - `data/*.jsonl`

---

## Local CLI (as-built)

`python -m local_arxiv run` performs:

1) Crawl: `scrapy crawl arxiv -o data/<date>.jsonl` (runs inside `daily_arxiv/`)
2) Dedup: `python daily_arxiv/check_stats.py` (runs inside `daily_arxiv/`)
3) Enhance: `python -m ai.enhance --data data/<date>.jsonl --max_workers <N>`
4) Optional convert: `--convert-md`
5) Index: write `assets/file-list.txt` listing `data/*.jsonl`

`python -m local_arxiv serve` starts a local static server (defaults to `127.0.0.1:8000`).

---

## Verification

Run unit tests:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Run the local pipeline (requires a running llama-server):

```bash
export LLAMA_BASE_URL="http://127.0.0.1:8080/v1"
export LLAMA_MODEL="Qwen3.5-9B-Q4_K_M.gguf"
export LANGUAGE="Chinese"
export CATEGORIES="cs.CV,cs.CL"
python -m local_arxiv run
python -m local_arxiv serve
```
