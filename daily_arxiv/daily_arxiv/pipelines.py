# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


class DailyArxivPipeline:
    def process_item(self, item: dict, spider):
        item["pdf"] = f"https://arxiv.org/pdf/{item['id']}"
        item["abs"] = f"https://arxiv.org/abs/{item['id']}"
        item.setdefault("authors", [])
        item.setdefault("title", "")
        item.setdefault("categories", [])
        item.setdefault("comment", "")
        item.setdefault("summary", "")
        return item