import scrapy
import os
import re


class ArxivSpider(scrapy.Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = os.environ.get("CATEGORIES", "cs.CV")
        categories = categories.split(",")
        # 保存目标分类列表，用于后续验证
        self.target_categories = set(map(str.strip, categories))
        self.start_urls = [
            f"https://arxiv.org/list/{cat}/new" for cat in self.target_categories
        ]  # 起始URL（计算机科学领域的最新论文）

    name = "arxiv"  # 爬虫名称
    allowed_domains = ["arxiv.org"]  # 允许爬取的域名

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def _extract_categories(self, paper_dd):
        subjects_text = " ".join(paper_dd.css(".list-subjects *::text").getall())
        subjects_text = self._normalize_text(subjects_text)
        # Example: Computer Vision and Pattern Recognition (cs.CV); Robotics (cs.RO)
        codes = re.findall(r"\(([a-z]+\.[A-Za-z0-9\-]+)\)", subjects_text)
        return sorted(set(codes))

    def parse(self, response):
        # 提取每篇论文的信息
        anchors = []
        current_list_category = ""
        m = re.search(r"/list/([^/]+)/new", response.url)
        if m:
            current_list_category = m.group(1)

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
                
            arxiv_id = abstract_link.split("/")[-1]
            
            # 获取对应的论文描述部分 (dd元素)
            paper_dd = paper.xpath("following-sibling::dd[1]")
            if not paper_dd:
                continue

            paper_categories = self._extract_categories(paper_dd)
            if not paper_categories and current_list_category:
                # Fallback: keep the listing category for robust filtering.
                paper_categories = [current_list_category]

            # 检查论文分类是否与目标分类有交集
            if set(paper_categories).intersection(self.target_categories):
                title_raw = " ".join(paper_dd.css(".list-title *::text").getall())
                title = self._normalize_text(re.sub(r"^Title:\s*", "", title_raw))

                authors = [self._normalize_text(a) for a in paper_dd.css(".list-authors a::text").getall()]
                authors = [a for a in authors if a]

                comment_raw = " ".join(paper_dd.css(".list-comments *::text").getall())
                comment = self._normalize_text(re.sub(r"^Comments:\s*", "", comment_raw))

                summary = self._normalize_text(" ".join(paper_dd.css(".mathjax::text").getall()))

                yield {
                    "id": arxiv_id,
                    "categories": paper_categories,
                    "authors": authors,
                    "title": title,
                    "comment": comment,
                    "summary": summary,
                }
                self.logger.info(f"Found paper {arxiv_id} with categories {paper_categories}")
            else:
                self.logger.debug(
                    f"Skipped paper {arxiv_id} with categories {paper_categories} "
                    f"(not in target {self.target_categories})"
                )
