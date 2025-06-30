#!/usr/bin/env python3
"""
检查Scrapy爬取统计信息的脚本 / Script to check Scrapy crawling statistics
用于获取去重检查的状态结果 / Used to get deduplication check status results

功能说明 / Features:
- 检查当日与昨日论文数据的重复情况 / Check duplication between today's and yesterday's paper data
- 提供多种检查方式：直接文件检查和日志解析 / Provide multiple check methods: direct file check and log parsing
- 根据检查结果返回相应的退出状态码 / Return corresponding exit status codes based on check results
"""
import json
import sys
import os
import re
import glob
from datetime import datetime, timedelta

def load_paper_ids(file_path):
    """
    从jsonl文件中提取论文ID列表
    Extract paper ID list from jsonl file
    
    Args:
        file_path (str): JSONL文件路径 / JSONL file path
        
    Returns:
        set: 论文ID集合 / Paper ID set
    """
    if not os.path.exists(file_path):
        return set()
    
    ids = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    ids.add(data.get('id', ''))
        return ids
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return set()

def get_latest_log_file():
    """
    获取最新的爬取日志文件
    Get the latest crawling log file
    
    Returns:
        str: 最新日志文件路径 / Latest log file path
    """
    # 查找最新的日志文件 / Search for the latest log file
    log_pattern = "logs/daily_arxiv.log*"
    log_files = glob.glob(log_pattern)
    
    if not log_files:
        return None
    
    # 返回最新修改的日志文件 / Return the most recently modified log file
    return max(log_files, key=os.path.getmtime)

def check_scrapy_logs():
    """
    通过检查最新的爬取日志获取去重状态
    Get deduplication status by checking the latest crawling logs
    
    Returns:
        str: 去重状态 / Deduplication status
             - "duplicate": 内容重复 / Content duplicated
             - "new_content": 发现新内容 / New content found
             - "no_new": 无新内容 / No new content
             - "unknown": 状态未知 / Status unknown
    """
    log_file = get_latest_log_file()
    
    if not log_file or not os.path.exists(log_file):
        print("未找到Scrapy日志文件 / Scrapy log file not found", file=sys.stderr)
        return "unknown"

    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # 检查去重相关的日志信息 / Check deduplication-related log information
        if "今日论文ID列表与昨日完全相同，内容重复" in content:
            print("从日志检测到：内容重复 / Detected from logs: content duplicated", file=sys.stderr)
            return "duplicate"
        elif re.search(r"发现 \d+ 篇新论文", content):
            print("从日志检测到：发现新论文 / Detected from logs: new papers found", file=sys.stderr)
            return "new_content"
        elif "没有新论文，但ID列表不同" in content:
            print("从日志检测到：没有新论文 / Detected from logs: no new papers", file=sys.stderr)
            return "no_new"
        elif "开始去重检查" in content:
            # 如果有去重检查开始的日志，但没有结果，可能是检查过程中出错
            # If there's a log for dedup check start but no results, might be an error during check
            print("检测到去重检查已启动，但未找到结果 / Detected dedup check started but no results found", file=sys.stderr)
            return "unknown"
            
    except Exception as e:
        print(f"读取日志文件失败 / Failed to read log file: {e}", file=sys.stderr)
    
    return "unknown"

def check_scrapy_output():
    """
    检查Scrapy的标准输出，寻找去重信息
    Check Scrapy's standard output for deduplication information
    
    通过直接比较今日和昨日的数据文件进行去重检查
    Perform deduplication check by directly comparing today's and yesterday's data files
    
    Returns:
        str: 去重状态 / Deduplication status
    """
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_file = f"../../data/{yesterday}.jsonl"
    today_file = f"../../data/{today}.jsonl"
    
    # 如果今日文件不存在，说明可能爬取失败 / If today's file doesn't exist, crawling might have failed
    if not os.path.exists(today_file):
        print("今日数据文件不存在 / Today's data file does not exist", file=sys.stderr)
        return "no_data"
    
    # 简单的去重检查逻辑 / Simple deduplication check logic
    try:
        today_ids = load_paper_ids(today_file)
        yesterday_ids = load_paper_ids(yesterday_file)
        
        if not today_ids:
            print("今日无论文数据 / No paper data today", file=sys.stderr)
            return "no_data"
        
        if today_ids == yesterday_ids:
            print("直接检查发现：内容重复 / Direct check found: content duplicated", file=sys.stderr)
            return "duplicate"
        elif today_ids - yesterday_ids:
            new_count = len(today_ids - yesterday_ids)
            print(f"直接检查发现：{new_count} 篇新论文 / Direct check found: {new_count} new papers", file=sys.stderr)
            return "new_content"
        else:
            print("直接检查发现：没有新论文 / Direct check found: no new papers", file=sys.stderr)
            return "no_new"
            
    except Exception as e:
        print(f"直接去重检查失败 / Direct dedup check failed: {e}", file=sys.stderr)
        return "unknown"

def main():
    """
    检查去重状态并返回相应的退出码
    Check deduplication status and return corresponding exit code
    
    退出码含义 / Exit code meanings:
    0: 发现新内容，继续处理 / New content found, continue processing
    1: 今日无新论文 / No new papers today
    2: 内容重复 / Content duplicated
    """
    
    print("正在检查Scrapy去重结果... / Checking Scrapy deduplication results...", file=sys.stderr)
    
    # 方案1: 直接检查数据文件（最可靠）/ Method 1: Direct data file check (most reliable)
    direct_status = check_scrapy_output()
    if direct_status != "unknown":
        if direct_status == "duplicate":
            # 删除重复文件 / Delete duplicate file
            today = datetime.now().strftime("%Y-%m-%d")
            today_file = f"../../data/{today}.jsonl"
            try:
                os.remove(today_file)
                print(f"已删除重复文件: {today_file} / Deleted duplicate file: {today_file}", file=sys.stderr)
            except Exception as e:
                print(f"删除重复文件失败 / Failed to delete duplicate file: {e}", file=sys.stderr)
            sys.exit(2)
        elif direct_status == "new_content":
            sys.exit(0)
        elif direct_status == "no_new":
            sys.exit(1)
        elif direct_status == "no_data":
            sys.exit(1)
    
    # 方案2: 检查日志文件（备用）/ Method 2: Check log files (backup)
    log_status = check_scrapy_logs()
    if log_status == "duplicate":
        sys.exit(2)
    elif log_status == "new_content":
        sys.exit(0)
    elif log_status == "no_new":
        sys.exit(1)
    
    # 默认：如果无法确定状态，继续处理 / Default: if status cannot be determined, continue processing
    print("无法确定去重状态，继续处理 / Cannot determine dedup status, continue processing", file=sys.stderr)
    sys.exit(0)

if __name__ == "__main__":
    main() 