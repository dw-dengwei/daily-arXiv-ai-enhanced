import scrapy
import os
import re

from ..record_utils import normalize_arxiv_id


class ArxivSpider(scrapy.Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = os.environ.get("CATEGORIES", "cs.CV")
        categories = [category.strip() for category in categories.split(",") if category.strip()]
        # 保存目标分类列表，用于后续验证
        self.target_categories = tuple(dict.fromkeys(categories))
        self.start_urls = [
            f"https://arxiv.org/list/{cat}/new" for cat in self.target_categories
        ]  # 起始URL（计算机科学领域的最新论文）
        self.seen_ids: set[str] = set()

    name = "arxiv"  # 爬虫名称
    allowed_domains = ["arxiv.org"]  # 允许爬取的域名

    def parse(self, response):
        requested_category = response.url.rstrip("/").split("/")[-2]
        # 提取每篇论文的信息
        anchors = []
        for li in response.css("div[id=dlpage] ul li"):
            href = li.css("a::attr(href)").get()
            if href and "item" in href:
                anchors.append(int(href.split("item")[-1]))

        # 遍历每篇论文的详细信息
        for paper in response.css("dl dt"):
            paper_anchor = paper.css("a[name^='item']::attr(name)").get()
            if not paper_anchor:
                continue
                
            paper_id = int(paper_anchor.split("item")[-1])
            if anchors and paper_id >= anchors[-1]:
                continue

            # 获取论文ID
            abstract_link = paper.css("a[title='Abstract']::attr(href)").get()
            if not abstract_link:
                continue
                
            arxiv_id = normalize_arxiv_id(abstract_link)
            if arxiv_id in self.seen_ids:
                continue
            self.seen_ids.add(arxiv_id)
            
            # 获取对应的论文描述部分 (dd元素)
            paper_dd = paper.xpath("following-sibling::dd[1]")
            if not paper_dd:
                continue
            
            # 提取论文分类信息 - 在subjects部分
            subjects_text = " ".join(paper_dd.css(".list-subjects *::text").getall())
            if not subjects_text:
                subjects_text = " ".join(paper_dd.css(".list-subjects::text").getall())
            
            if subjects_text:
                # 解析分类信息，通常格式如 "Computer Vision and Pattern Recognition (cs.CV)"
                # 提取括号中的分类代码
                categories_in_paper = re.findall(r'\(([^)]+)\)', subjects_text)
                
                paper_categories = set(categories_in_paper)
                # The paper came from this requested category's /new page, so
                # retain that category even when it is only a cross-list and is
                # not exposed as the HTML primary subject.
                yield {
                    "id": arxiv_id,
                    "categories": sorted(paper_categories),
                    "matched_category": requested_category,
                    "matched_categories": [requested_category],
                }
                self.logger.info(f"Found paper {arxiv_id} for {requested_category}")
            else:
                # 如果无法获取分类信息，记录警告但仍然返回论文（保持向后兼容）
                self.logger.warning(f"Could not extract categories for paper {arxiv_id}, including anyway")
                yield {
                    "id": arxiv_id,
                    "categories": [],
                    "matched_category": requested_category,
                    "matched_categories": [requested_category],
                }
