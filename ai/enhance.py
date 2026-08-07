import os
import json
import sys
import re
from functools import lru_cache
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tempfile import NamedTemporaryFile
from typing import List, Dict
# INSERT_YOUR_CODE
import requests

import dotenv
import argparse
from tqdm import tqdm

from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
try:
    from .structure import Structure
except ImportError:  # pragma: no cover - compatibility for direct execution
    from structure import Structure

try:
    from daily_arxiv.daily_arxiv.record_utils import deduplicate_records
except ImportError:  # pragma: no cover - compatibility for direct execution
    from daily_arxiv.record_utils import deduplicate_records
try:
    from .compliance import check_sensitive
except ImportError:  # pragma: no cover - compatibility for direct execution
    from compliance import check_sensitive

module_dir = Path(__file__).resolve().parent
if (module_dir / ".env").exists():
    dotenv.load_dotenv(module_dir / ".env")
template = (module_dir / "template.txt").read_text(encoding="utf-8")
system = (module_dir / "system.txt").read_text(encoding="utf-8")


@lru_cache(maxsize=512)
def github_repo_metadata(owner: str, repo: str, token: str) -> dict:
    """Cache optional GitHub metadata so repeated papers do not repeat requests."""

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
            timeout=5,
        )
        if response.status_code != 200:
            return {}
        data = response.json()
        return {
            "code_stars": data.get("stargazers_count", 0),
            "code_last_update": data.get("pushed_at", "")[:10],
        }
    except Exception:
        return {}


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    parser.add_argument("--max_workers", type=int, default=1, help="Maximum number of parallel workers")
    return parser.parse_args()

def process_single_item(chain, item: Dict, language: str) -> Dict:
    def check_github_code(content: str) -> Dict:
        """提取并验证 GitHub 链接"""
        code_info = {}

        # 1. 优先匹配 github.com/owner/repo 格式
        github_pattern = r"https?://github\.com/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_\.]+)"
        match = re.search(github_pattern, content)
        
        if match:
            owner, repo = match.groups()
            # 清理 repo 名称，去掉可能的 .git 后缀或末尾的标点
            repo = re.sub(r"\.git$", "", repo, flags=re.IGNORECASE).rstrip(".,)")
            
            full_url = f"https://github.com/{owner}/{repo}"
            code_info["code_url"] = full_url
            
            metadata = github_repo_metadata(owner, repo, os.environ.get("TOKEN_GITHUB", ""))
            code_info.update(metadata)
            return code_info

        # 2. 如果没有 github.com，尝试匹配 github.io
        github_io_pattern = r"https?://[a-zA-Z0-9-_]+\.github\.io(?:/[a-zA-Z0-9-_\.]+)*"
        match_io = re.search(github_io_pattern, content)
        
        if match_io:
            url = match_io.group(0)
            # 清理末尾标点
            url = url.rstrip(".,)")
            code_info["code_url"] = url
            # github.io 不进行 star 和 update 判断
                
        return code_info

    # 检查 summary 字段
    if check_sensitive(item.get("summary", "")):
        return None

    # 检测代码可用性
    code_info = check_github_code(item.get("summary", ""))
    if code_info:
        item.update(code_info)

    """Process one paper, returning None only for an explicit rejection."""

    try:
        response: Structure = chain.invoke({
            "language": language,
            "content": item["summary"],
        })
    except Exception as error:
        raise RuntimeError(f"AI generation failed for {item.get('id', 'unknown')}") from error

    item["AI"] = response.model_dump()
    generated_text = "\n".join(str(value) for value in item["AI"].values())
    if check_sensitive(generated_text):
        return None
    return item

def process_all_items(data: List[Dict], model_name: str, language: str, max_workers: int) -> List[Dict]:
    """并行处理所有数据项"""
    llm = ChatOpenAI(
            model=model_name,
            timeout=60,
            max_retries=2,
            model_kwargs={"extra_body": {"thinking": {"type": "disabled"}}}
        ).with_structured_output(Structure, method="function_calling")

    print('Connect to:', model_name, file=sys.stderr)
    
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])

    chain = prompt_template | llm
    
    # 使用线程池并行处理
    processed_data = [None] * len(data)  # 预分配结果列表
    failures = []
    rejected = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_idx = {
            executor.submit(process_single_item, chain, item, language): idx
            for idx, item in enumerate(data)
        }
        
        # 使用tqdm显示进度
        for future in tqdm(
            as_completed(future_to_idx),
            total=len(data),
            desc="Processing items"
        ):
            idx = future_to_idx[future]
            try:
                result = future.result()
                processed_data[idx] = result
                if result is None:
                    rejected += 1
            except Exception as e:
                print(f"Item at index {idx} generated an exception: {e}", file=sys.stderr)
                failures.append((data[idx].get("id", "unknown"), e))

    if failures:
        ids = ", ".join(identifier for identifier, _ in failures[:5])
        raise RuntimeError(f"AI processing failed for {len(failures)} papers: {ids}")
    print(f"Rejected by compliance check: {rejected}", file=sys.stderr)
    return processed_data

def main():
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'deepseek-chat')
    language = os.environ.get("LANGUAGE", 'Chinese')

    # Validate the language before constructing the output path.
    if not re.fullmatch(r"[A-Za-z0-9-]+", language):
        raise ValueError("LANGUAGE must contain only letters, numbers, and hyphens")
    data_path = Path(args.data)
    target_file = str(data_path.with_name(f"{data_path.stem}_AI_enhanced_{language}.jsonl"))
    # 读取数据
    data = []
    with open(args.data, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    data = deduplicate_records(data)
    print('Open:', args.data, file=sys.stderr)

    if not data:
        raise RuntimeError("no valid papers to enhance")
    
    # 并行处理所有数据
    processed_data = process_all_items(
        data,
        model_name,
        language,
        args.max_workers
    )
    
    # 原子保存结果，只有完整处理成功后才替换旧文件。
    target_path = Path(target_file)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=target_path.parent or Path("."),
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary_path = Path(handle.name)
        for item in processed_data:
            if item is not None:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, target_path)

if __name__ == "__main__":
    main()
