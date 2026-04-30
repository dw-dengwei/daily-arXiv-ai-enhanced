import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def _utc_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _http_get_json(url: str, timeout: int = 10) -> dict:
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} for {url}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"Request failed for {url}: {e}") from e
    return json.loads(body)


def _check_llama_server(base_url: str, model: str) -> None:
    base_url = base_url.rstrip("/")
    data = _http_get_json(f"{base_url}/models", timeout=10)
    models = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
    if model not in models:
        raise RuntimeError(f"LLAMA_MODEL not found in /v1/models: {model}")


def _run_cmd(cmd: list[str], cwd: Optional[str] = None, env: Optional[dict] = None) -> None:
    p = subprocess.run(cmd, cwd=cwd, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)} (exit {p.returncode})")


def _write_file_list() -> None:
    data_dir = Path("data")
    assets_dir = Path("assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    files = sorted([p.name for p in data_dir.glob("*.jsonl")])
    (assets_dir / "file-list.txt").write_text("\n".join(files) + ("\n" if files else ""))


def cmd_run(args: argparse.Namespace) -> None:
    date = args.date or _utc_today()
    language = args.language or os.environ.get("LANGUAGE", "Chinese")
    categories = args.categories or os.environ.get("CATEGORIES", "cs.CV")

    base_url = args.llama_base_url or os.environ.get("LLAMA_BASE_URL", "http://127.0.0.1:8080/v1")
    model = args.llama_model or os.environ.get("LLAMA_MODEL", "")
    if not model:
        raise RuntimeError("LLAMA_MODEL is required (or pass --llama-model)")

    _check_llama_server(base_url, model)

    Path("data").mkdir(parents=True, exist_ok=True)
    out_file = Path("data") / f"{date}.jsonl"
    if out_file.exists():
        out_file.unlink()

    env = os.environ.copy()
    env["CATEGORIES"] = categories
    env["LANGUAGE"] = language
    env["LLAMA_BASE_URL"] = base_url
    env["LLAMA_MODEL"] = model
    if args.temperature is not None:
        env["TEMPERATURE"] = str(args.temperature)
    if args.max_tokens is not None:
        env["MAX_TOKENS"] = str(args.max_tokens)

    _run_cmd(
        ["scrapy", "crawl", "arxiv", "-o", f"../data/{date}.jsonl"],
        cwd="daily_arxiv",
        env=env,
    )

    if not out_file.exists():
        raise RuntimeError(f"crawl did not produce {out_file}")

    p = subprocess.run([sys.executable, "daily_arxiv/check_stats.py"], cwd="daily_arxiv", env=env)
    if p.returncode != 0:
        raise SystemExit(p.returncode)

    _run_cmd(
        [
            sys.executable,
            "-m",
            "ai.enhance",
            "--data",
            str(out_file),
            "--max_workers",
            str(args.max_workers),
        ],
        env=env,
    )

    if args.convert_md:
        enhanced = out_file.with_name(f"{out_file.stem}_AI_enhanced_{language}.jsonl")
        _run_cmd([sys.executable, "to_md/convert.py", "--data", str(enhanced)], env=env)

    _write_file_list()


def _check_port_available(host: str, port: int) -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
    finally:
        s.close()


def cmd_serve(args: argparse.Namespace) -> None:
    host = args.host
    port = args.port
    _check_port_available(host, port)
    httpd = ThreadingHTTPServer((host, port), SimpleHTTPRequestHandler)
    httpd.serve_forever()


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m local_arxiv")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run")
    run_p.add_argument("--date", type=str, default=None)
    run_p.add_argument("--categories", type=str, default=None)
    run_p.add_argument("--language", type=str, default=None)
    run_p.add_argument("--max-workers", type=int, default=1)
    run_p.add_argument("--llama-base-url", type=str, default=None)
    run_p.add_argument("--llama-model", type=str, default=None)
    run_p.add_argument("--temperature", type=float, default=None)
    run_p.add_argument("--max-tokens", type=int, default=None)
    run_p.add_argument("--convert-md", action="store_true")
    run_p.set_defaults(func=cmd_run)

    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--host", type=str, default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

