import unittest

from scrapy.http import HtmlResponse, Request

from daily_arxiv.spiders.arxiv import ArxivSpider


class ArxivSpiderTest(unittest.TestCase):
    def test_keeps_requested_category_for_cross_listed_paper(self):
        html = b"""
        <html><body><div id="dlpage"><dl>
          <dt><a name="item1"></a><a title="Abstract" href="/abs/2607.12345">abs</a></dt>
          <dd><div class="list-subjects">
            Subjects: <span class="primary-subject">Machine Learning (cs.LG)</span>;
            Computer Vision and Pattern Recognition (cs.CV)
          </div></dd>
        </dl></div></body></html>
        """
        request = Request("https://arxiv.org/list/cs.CV/new")
        response = HtmlResponse(request.url, request=request, body=html, encoding="utf-8")

        items = list(ArxivSpider().parse(response))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "2607.12345")
        self.assertEqual(items[0]["matched_category"], "cs.CV")
        self.assertEqual(items[0]["categories"], ["cs.CV", "cs.LG"])


if __name__ == "__main__":
    unittest.main()
