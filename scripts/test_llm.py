#!/usr/bin/env python3
"""Quickly test the configured OpenAI-compatible LLM endpoint."""

import argparse
import os
import sys

import dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class TestResponse(BaseModel):
    tldr: str = Field(description="A one sentence summary")
    ok: bool = Field(description="Whether the request succeeded")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test OPENAI_API_KEY, OPENAI_BASE_URL, and MODEL_NAME without running the arXiv workflow."
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("MODEL_NAME", "gpt-4o-mini"),
        help="Override MODEL_NAME for this test.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        help="Override OPENAI_BASE_URL for this test.",
    )
    parser.add_argument(
        "--prompt",
        default="用中文用一句话概括：arXiv daily digest checks new papers and asks an LLM to summarize them.",
        help="Prompt sent to the model.",
    )
    return parser.parse_args()


def main() -> int:
    dotenv.load_dotenv()
    args = parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 2

    os.environ["OPENAI_BASE_URL"] = args.base_url

    print("Testing LLM configuration:")
    print(f"  OPENAI_BASE_URL: {args.base_url}")
    print(f"  MODEL_NAME: {args.model}")
    print("  OPENAI_API_KEY: set", flush=True)

    if "api.kimi.com/coding" in args.base_url:
        print(
            "WARNING: This is the Kimi For Coding endpoint. It is restricted to supported coding agents.",
            file=sys.stderr,
        )

    try:
        llm = ChatOpenAI(model=args.model, temperature=0).with_structured_output(
            TestResponse,
            method="function_calling",
        )
        result = llm.invoke(args.prompt)
    except Exception as exc:
        print(f"ERROR: LLM request failed: {exc}", file=sys.stderr)
        error_text = str(exc)
        if "Invalid Authentication" in error_text and "moonshot" in args.base_url:
            print(
                "HINT: The base URL is now a normal Moonshot/Kimi API endpoint, "
                "but this key is not accepted there. Kimi Code keys are separate "
                "from regular Moonshot API keys.",
                file=sys.stderr,
            )
        elif "Kimi For Coding" in error_text or "access_terminated_error" in error_text:
            print(
                "HINT: You are still using the Kimi For Coding endpoint. "
                "Use https://api.moonshot.cn/v1 or https://api.moonshot.ai/v1 for normal API calls.",
                file=sys.stderr,
            )
        return 1

    print("SUCCESS: LLM request completed.")
    print(f"  tldr: {result.tldr}")
    print(f"  ok: {result.ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
