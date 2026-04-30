import os
import json
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Optional

try:
    import dotenv
except ModuleNotFoundError:
    dotenv = None

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    def tqdm(it, **kwargs):
        return it

try:
    from ai.llama_json import parse_llm_json, ensure_ai_fields
except ModuleNotFoundError:
    from llama_json import parse_llm_json, ensure_ai_fields

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

_AI_DIR = Path(__file__).resolve().parent

if dotenv and os.path.exists(".env"):
    dotenv.load_dotenv()

template = (_AI_DIR / "template.txt").read_text()
system = (_AI_DIR / "system.txt").read_text()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    parser.add_argument("--max_workers", type=int, default=1, help="Maximum number of parallel workers")
    return parser.parse_args()

def _default_ai_fields() -> Dict[str, str]:
    return {
        "tldr": "",
        "motivation": "",
        "method": "",
        "result": "",
        "conclusion": "",
    }


def _get_llama_config():
    base_url = os.environ.get("LLAMA_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/")
    model = os.environ.get("LLAMA_MODEL", "").strip()
    if not model:
        raise RuntimeError("LLAMA_MODEL is required")

    language = os.environ.get("LANGUAGE", "Chinese")
    temperature = float(os.environ.get("TEMPERATURE", "0.2"))
    max_tokens = int(os.environ.get("MAX_TOKENS", "1000"))
    return base_url, model, language, temperature, max_tokens


def _list_models(base_url: str) -> List[str]:
    data = _http_request_json("GET", f"{base_url}/models", timeout=10)
    models = []
    for m in data.get("data", []):
        mid = m.get("id")
        if isinstance(mid, str) and mid:
            models.append(mid)
    return models


def _check_model_available(base_url: str, model: str) -> None:
    models = _list_models(base_url)
    if model not in models:
        raise RuntimeError(f"LLAMA_MODEL not found in /v1/models: {model}")


def _build_messages(language: str, content: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system.replace("{language}", language)},
        {"role": "user", "content": template.replace("{content}", content)},
    ]


def _chat_completions(
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    data = _http_request_json("POST", f"{base_url}/chat/completions", payload=payload, timeout=120)
    return data["choices"][0]["message"]["content"]


def _http_request_json(method: str, url: str, payload: Optional[dict] = None, timeout: int = 30) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} for {url}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"Request failed for {url}: {e}") from e

    return json.loads(body)


def process_single_item(base_url: str, model: str, item: Dict, language: str, temperature: float, max_tokens: int) -> Dict:
    try:
        messages = _build_messages(language=language, content=item.get("summary", ""))
        content = _chat_completions(
            base_url=base_url,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        parsed = parse_llm_json(content)
        item["AI"] = ensure_ai_fields(parsed)
    except Exception as e:
        print(f"AI enhance failed for {item.get('id', 'unknown')}: {e}", file=sys.stderr)
        item["AI"] = _default_ai_fields()
    return item


def process_all_items(
    data: List[Dict],
    base_url: str,
    model: str,
    language: str,
    temperature: float,
    max_tokens: int,
    max_workers: int,
) -> List[Dict]:
    processed_data: List[Optional[Dict]] = [None] * len(data)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(process_single_item, base_url, model, item, language, temperature, max_tokens): idx
            for idx, item in enumerate(data)
        }

        for future in tqdm(as_completed(future_to_idx), total=len(data), desc="Processing items"):
            idx = future_to_idx[future]
            try:
                processed_data[idx] = future.result()
            except Exception as e:
                print(f"Item at index {idx} generated an exception: {e}", file=sys.stderr)
                processed_data[idx] = data[idx]
                processed_data[idx]["AI"] = _default_ai_fields()

    return [x for x in processed_data if x is not None]

def main():
    args = parse_args()
    base_url, model, language, temperature, max_tokens = _get_llama_config()
    _check_model_available(base_url, model)

    target_file = args.data.replace(".jsonl", f"_AI_enhanced_{language}.jsonl")
    if os.path.exists(target_file):
        os.remove(target_file)
        print(f"Removed existing file: {target_file}", file=sys.stderr)

    data = []
    with open(args.data, "r") as f:
        for line in f:
            data.append(json.loads(line))

    seen_ids = set()
    unique_data = []
    for item in data:
        iid = item.get("id")
        if iid not in seen_ids:
            seen_ids.add(iid)
            unique_data.append(item)

    data = unique_data
    print("Open:", args.data, file=sys.stderr)

    processed_data = process_all_items(
        data,
        base_url,
        model,
        language,
        temperature,
        max_tokens,
        args.max_workers
    )

    with open(target_file, "w") as f:
        for item in processed_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
