#!/usr/bin/env python3
"""
检查Scrapy爬取统计信息的脚本 / Script to check Scrapy crawling statistics
用于获取去重检查的状态结果 / Used to get deduplication check status results

功能说明 / Features:
- 检查当日与昨日论文数据的重复情况 / Check duplication between today's and yesterday's paper data
- 删除重复论文条目，保留新内容 / Remove duplicate papers, keep new content
- 根据去重后的结果决定工作流是否继续 / Decide workflow continuation based on deduplication results
"""
import json
import sys
import os
from datetime import datetime, timedelta

def load_papers_data(file_path):
    """
    从jsonl文件中加载完整的论文数据
    Load complete paper data from jsonl file
    
    Args:
        file_path (str): JSONL文件路径 / JSONL file path
        
    Returns:
        list: 论文数据列表 / List of paper data
        set: 论文ID集合 / Set of paper IDs
    """
    if not os.path.exists(file_path):
        return [], set()
    
    papers = []
    ids = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    papers.append(data)
                    ids.add(data.get('id', ''))
        return papers, ids
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return [], set()

def save_papers_data(papers, file_path):
    """
    保存论文数据到jsonl文件
    Save paper data to jsonl file
    
    Args:
        papers (list): 论文数据列表 / List of paper data
        file_path (str): 文件路径 / File path
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for paper in papers:
                f.write(json.dumps(paper, ensure_ascii=False) + '\n')
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}", file=sys.stderr)
        return False

def perform_deduplication():
    """
    执行去重：删除重复论文条目，保留新内容
    Perform intelligent deduplication: remove duplicate papers, keep new content
    
    Returns:
        str: 去重状态 / Deduplication status
             - "has_new_content": 有新内容 / Has new content
             - "no_new_content": 无新内容 / No new content  
             - "no_data": 无数据 / No data
             - "error": 处理错误 / Processing error
    """
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_file = f"../data/{yesterday}.jsonl"
    today_file = f"../data/{today}.jsonl"
    
    # 检查今日文件是否存在 / Check if today's file exists
    if not os.path.exists(today_file):
        print("今日数据文件不存在 / Today's data file does not exist", file=sys.stderr)
        return "no_data"
    
    try:
        # 加载今日和昨日的数据 / Load today's and yesterday's data
        today_papers, today_ids = load_papers_data(today_file)
        yesterday_papers, yesterday_ids = load_papers_data(yesterday_file)
        
        print(f"今日论文总数: {len(today_papers)} / Total papers today: {len(today_papers)}", file=sys.stderr)
        print(f"昨日论文总数: {len(yesterday_papers)} / Total papers yesterday: {len(yesterday_papers)}", file=sys.stderr)
        
        if not today_papers:
            print("今日无论文数据 / No paper data today", file=sys.stderr)
            return "no_data"
        
        # 找出重复的论文ID / Find duplicate paper IDs
        duplicate_ids = today_ids & yesterday_ids
        
        if duplicate_ids:
            print(f"发现 {len(duplicate_ids)} 篇重复论文 / Found {len(duplicate_ids)} duplicate papers", file=sys.stderr)
            
            # 从今日数据中移除重复论文 / Remove duplicate papers from today's data
            new_papers = [paper for paper in today_papers if paper.get('id', '') not in duplicate_ids]
            
            print(f"去重后剩余论文数: {len(new_papers)} / Papers remaining after deduplication: {len(new_papers)}", file=sys.stderr)
            
            if new_papers:
                # 保存去重后的数据 / Save deduplicated data
                if save_papers_data(new_papers, today_file):
                    print(f"已更新今日文件，移除 {len(duplicate_ids)} 篇重复论文 / Updated today's file, removed {len(duplicate_ids)} duplicate papers", file=sys.stderr)
                    return "has_new_content"
                else:
                    print("保存去重后的数据失败 / Failed to save deduplicated data", file=sys.stderr)
                    return "error"
            else:
                # 没有新内容，删除今日文件 / No new content, delete today's file
                try:
                    os.remove(today_file)
                    print(f"所有论文均为重复内容，已删除今日文件 / All papers are duplicates, deleted today's file", file=sys.stderr)
                except Exception as e:
                    print(f"删除文件失败 / Failed to delete file: {e}", file=sys.stderr)
                return "no_new_content"
        else:
            # 没有重复论文 / No duplicate papers
            print("未发现重复论文，所有内容均为新内容 / No duplicate papers found, all content is new", file=sys.stderr)
            return "has_new_content"
            
    except Exception as e:
        print(f"去重处理失败 / Deduplication processing failed: {e}", file=sys.stderr)
        return "error"

def main():
    """
    检查去重状态并返回相应的退出码
    Check deduplication status and return corresponding exit code
    
    退出码含义 / Exit code meanings:
    0: 有新内容，继续处理 / Has new content, continue processing
    1: 无新内容，停止工作流 / No new content, stop workflow
    2: 处理错误 / Processing error
    """
    
    print("正在执行去重检查... / Performing intelligent deduplication check...", file=sys.stderr)
    
    # 执行去重处理 / Perform deduplication processing
    dedup_status = perform_deduplication()
    
    if dedup_status == "has_new_content":
        print("✅ 去重完成，发现新内容，继续工作流 / Deduplication completed, new content found, continue workflow", file=sys.stderr)
        sys.exit(0)
    elif dedup_status == "no_new_content":
        print("⏹️ 去重完成，无新内容，停止工作流 / Deduplication completed, no new content, stop workflow", file=sys.stderr)
        sys.exit(1)
    elif dedup_status == "no_data":
        print("⏹️ 今日无数据，停止工作流 / No data today, stop workflow", file=sys.stderr)
        sys.exit(1)
    elif dedup_status == "error":
        print("❌ 去重处理出错，停止工作流 / Deduplication processing error, stop workflow", file=sys.stderr)
        sys.exit(2)
    else:
        # 意外情况：未知状态 / Unexpected case: unknown status
        print("❌ 未知去重状态，停止工作流 / Unknown deduplication status, stop workflow", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main() 