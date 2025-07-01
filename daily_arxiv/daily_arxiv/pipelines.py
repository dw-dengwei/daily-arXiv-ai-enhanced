# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import arxiv
import json
import os
import sys
from datetime import datetime, timedelta


class DailyArxivPipeline:
    def __init__(self):
        self.page_size = 100
        self.client = arxiv.Client(self.page_size)

    def process_item(self, item: dict, spider):
        item["pdf"] = f"https://arxiv.org/pdf/{item['id']}"
        item["abs"] = f"https://arxiv.org/abs/{item['id']}"
        search = arxiv.Search(
            id_list=[item["id"]],
        )
        paper = next(self.client.results(search))
        item["authors"] = [a.name for a in paper.authors]
        item["title"] = paper.title
        item["categories"] = paper.categories
        item["comment"] = paper.comment
        item["summary"] = paper.summary
        print(item)
        return item


# 注意：DedupCheckPipeline已弃用 / Note: DedupCheckPipeline is deprecated
# 去重检查功能已迁移到外部脚本 check_stats.py / Dedup check functionality migrated to external script check_stats.py
# 该脚本提供更完整的去重处理和工作流决策机制 / The script provides more complete dedup processing and workflow decision mechanism

# class DedupCheckPipeline:
#     """
#     去重检查管道 - 在爬取结束后检查重复内容 [已弃用]
#     Deduplication Check Pipeline - Check for duplicate content after crawling is complete [DEPRECATED]
#     
#     功能说明 / Features:
#     - 收集爬取过程中的所有论文ID / Collect all paper IDs during crawling process
#     - 在爬取结束时与昨日数据进行比较 / Compare with yesterday's data when crawling ends
#     - 设置去重状态供外部脚本判断 / Set dedup status for external script judgment
#     
#     弃用原因 / Deprecation reason:
#     - 功能已被 check_stats.py 完全替代 / Functionality completely replaced by check_stats.py
#     - 避免双重去重机制的逻辑冲突 / Avoid logical conflicts from dual dedup mechanisms
#     - 简化工作流程，提高可维护性 / Simplify workflow and improve maintainability
#     """
#     
#     def __init__(self):
#         # 收集当前爬取的论文ID集合 / Collect current crawled paper ID set
#         self.collected_ids = set()
#         # 获取今日和昨日的日期字符串 / Get today's and yesterday's date strings
#         self.today = datetime.now().strftime("%Y-%m-%d")
#         self.yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
#         
#     def process_item(self, item, spider):
#         """
#         处理每个爬取的条目，收集论文ID
#         Process each crawled item and collect paper IDs
#         """
#         # 收集所有爬取的论文ID / Collect all crawled paper IDs
#         if 'id' in item:
#             self.collected_ids.add(item['id'])
#         return item
#     
#     def close_spider(self, spider):
#         """
#         在spider关闭时执行去重检查
#         Perform deduplication check when spider closes
#         """
#         spider.logger.info(f"开始去重检查，今日爬取论文数量: {len(self.collected_ids)} / Starting dedup check, today's crawled papers: {len(self.collected_ids)}")
#         
#         # 加载昨日的论文ID / Load yesterday's paper IDs
#         yesterday_file = os.path.join("../../data", f"{self.yesterday}.jsonl")
#         yesterday_ids = self._load_paper_ids(yesterday_file)
#         
#         spider.logger.info(f"昨日论文数量: {len(yesterday_ids)} / Yesterday's papers: {len(yesterday_ids)}")
#         
#         # 比较ID集合进行去重判断 / Compare ID sets for deduplication judgment
#         if self.collected_ids == yesterday_ids:
#             spider.logger.warning("今日论文ID列表与昨日完全相同，内容重复 / Today's paper ID list is identical to yesterday's, content duplicated")
#             # 设置重复状态标记 / Set duplicate status flag
#             spider.crawler.stats.set_value('dedup_status', 'duplicate')
#         elif self.collected_ids - yesterday_ids:
#             # 计算新增论文数量 / Calculate number of new papers
#             new_count = len(self.collected_ids - yesterday_ids)
#             spider.logger.info(f"发现 {new_count} 篇新论文 / Found {new_count} new papers")
#             spider.crawler.stats.set_value('dedup_status', 'new_content')
#         else:
#             spider.logger.info("没有新论文，但ID列表不同 / No new papers, but ID list is different")
#             spider.crawler.stats.set_value('dedup_status', 'no_new')
#     
#     def _load_paper_ids(self, file_path):
#         """
#         从jsonl文件中提取论文ID列表
#         Extract paper ID list from jsonl file
#         
#         Args:
#             file_path (str): JSONL文件路径 / JSONL file path
#             
#         Returns:
#             set: 论文ID集合 / Paper ID set
#         """
#         if not os.path.exists(file_path):
#             return set()
#         
#         ids = set()
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 for line in f:
#                     if line.strip():
#                         data = json.loads(line)
#                         ids.add(data.get('id', ''))
#         except Exception as e:
#             print(f"Error reading {file_path}: {e}", file=sys.stderr)
#         return ids
