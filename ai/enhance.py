import os
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from queue import Queue
from threading import Lock
import time # 导入 time 模块


import dotenv
import argparse
from tqdm import tqdm

import langchain_core.exceptions
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()
# 1. 读取延迟时间的环境变量，并提供默认值
# 默认延迟 5 秒，如果未设置 API_DELAY_SECONDS 环境变量，则使用此默认值
API_DELAY_SECONDS = int(os.environ.get("API_DELAY_SECONDS", 5)) 

# 确保延迟时间是正整数，如果用户输入了非法的，使用默认值
if not isinstance(API_DELAY_SECONDS, int) or API_DELAY_SECONDS < 0:
    print(f"Warning: Invalid API_DELAY_SECONDS value '{API_DELAY_SECONDS}'. Using default of 5 seconds.", file=sys.stderr)
    API_DELAY_SECONDS = 5

template = open("template.txt", "r").read()
system = open("system.txt", "r").read()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    parser.add_argument("--max_workers", type=int, default=1, help="Maximum number of parallel workers")
    # 可以选择性地在这里也添加一个命令行参数来覆盖环境变量，如果需要的话
    # parser.add_argument("--delay", type=int, default=API_DELAY_SECONDS, help="Delay in seconds between API calls")
    
    return parser.parse_args()

def process_single_item(chain, item: Dict, language: str) -> Dict:
    """处理单个数据项"""
    try:
        response: Structure = chain.invoke({
            "language": language,
            "content": item['summary']
        })
        item['AI'] = response.model_dump()
        
        # !!! 在这里添加延迟 !!!
        time.sleep(API_DELAY_SECONDS) 
    except langchain_core.exceptions.OutputParserException as e:
        # 尝试从错误信息中提取 JSON 字符串并修复
        error_msg = str(e)
        if "Function Structure arguments:" in error_msg:
            try:
                # 提取 JSON 字符串
                json_str = error_msg.split("Function Structure arguments:", 1)[1].strip().split('are not valid JSON')[0].strip()
                # 预处理 LaTeX 数学符号 - 使用四个反斜杠来确保正确转义
                json_str = json_str.replace('\\', '\\\\')
                # 尝试解析修复后的 JSON
                fixed_data = json.loads(json_str)
                item['AI'] = fixed_data
                
                # !!! 在这里添加延迟 !!!
                time.sleep(API_DELAY_SECONDS) 
                return item
            except Exception as json_e:
                print(f"Failed to fix JSON for {item['id']}: {json_e} {json_str}", file=sys.stderr)
        
        # 如果修复失败，返回错误状态
        item['AI'] = {
            "tldr": "Error",
            "motivation": "Error",
            "method": "Error",
            "result": "Error",
            "conclusion": "Error"
        }
        # !!! 即使是错误，也添加延迟，以保护 API !!!
        time.sleep(API_DELAY_SECONDS)
    except Exception as e: # 捕获其他可能的异常，比如 API 请求本身的错误
        print(f"An unexpected error occurred for item {item.get('id', 'unknown')}: {e}", file=sys.stderr)
        item['AI'] = {
            "tldr": "Unexpected Error",
            "motivation": str(e),
            "method": "N/A",
            "result": "N/A",
            "conclusion": "N/A"
        }
        # 即使是其他错误，也添加延迟
        time.sleep(API_DELAY_SECONDS) # 使用变量

    # !!! 在所有成功的处理（包括没有异常）之后，也添加延迟 !!!
    # 确保每次 invoke() 之后都有延迟。
    # 如果是在 except 块中已经 sleep 了，这里就不会再 sleep 了（因为代码流从那里跳过）
    # 但如果 try 块成功执行，需要确保这里也 sleep。
    # 所以，最稳妥的方式是把 sleep 放在最后，或者在每个分支都加。
    # 为了简洁且确保生效，我们把 sleep 放在 try 块成功执行后，以及所有 except 块中。
    # 让我们把 sleep 统一放在最后，确保不论成功还是出错，都会有延迟。
    # （但这样会导致即使抛出异常，如果 except 块没有 sleep，也会漏掉）
    # 最好的方法是在每个可能的 exit point 都加 sleep.
    # 既然我们已经在每个 except 块中加了，这里只为 try 块成功时添加。
    else: # else 块与 try 对应，在 try 块没有异常时执行
        time.sleep(API_DELAY_SECONDS) # 使用变量

    return item

def process_all_items(data: List[Dict], model_name: str, language: str, max_workers: int) -> List[Dict]:
    """并行处理所有数据项"""
    llm = ChatOpenAI(model=model_name).with_structured_output(Structure, method="function_calling")
    print('Connect to:', model_name, file=sys.stderr)
    
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])

    chain = prompt_template | llm
    
    # 使用线程池并行处理
    processed_data = [None] * len(data)  # 预分配结果列表
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
            except Exception as e:
                print(f"Item at index {idx} generated an exception: {e}", file=sys.stderr)
                # 保持原始数据
                processed_data[idx] = data[idx]
    
    return processed_data

def main():
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'deepseek-chat')
    language = os.environ.get("LANGUAGE", 'Chinese')

    # 检查并删除目标文件
    target_file = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    if os.path.exists(target_file):
        os.remove(target_file)
        print(f'Removed existing file: {target_file}', file=sys.stderr)

    # 读取数据
    data = []
    with open(args.data, "r") as f:
        for line in f:
            data.append(json.loads(line))

    # 去重
    seen_ids = set()
    unique_data = []
    for item in data:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)

    data = unique_data
    print('Open:', args.data, file=sys.stderr)
    
    # 并行处理所有数据
    processed_data = process_all_items(
        data,
        model_name,
        language,
        args.max_workers
    )
    
    # 保存结果
    with open(target_file, "w") as f:
        for item in processed_data:
            f.write(json.dumps(item) + "\n")

if __name__ == "__main__":
    main()
