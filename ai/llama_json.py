import json
import re


AI_FIELD_NAMES = ("tldr", "motivation", "method", "result", "conclusion")


def _strip_invalid_control_chars(s: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)


def _repair_common_json_issues(s: str) -> str:
    s = _strip_invalid_control_chars(s)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s


def parse_llm_json(text: str) -> dict:
    if not isinstance(text, str):
        raise TypeError("text must be str")

    text = text.strip()
    if not text:
        raise ValueError("empty text")

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no json object found")

    candidate = text[start : end + 1]
    candidate = _repair_common_json_issues(candidate)
    obj = json.loads(candidate)
    if not isinstance(obj, dict):
        raise ValueError("json is not object")
    return obj


def ensure_ai_fields(obj: dict) -> dict:
    if obj is None:
        obj = {}
    if not isinstance(obj, dict):
        raise TypeError("obj must be dict")

    out = {}
    for k in AI_FIELD_NAMES:
        v = obj.get(k, "")
        if v is None:
            v = ""
        if not isinstance(v, str):
            v = str(v)
        out[k] = v
    return out

