import unittest

from to_md.convert import main_category


class ConverterTest(unittest.TestCase):
    def test_uses_matched_category_for_cross_listed_paper(self):
        self.assertEqual(
            main_category(
                {
                    "categories": ["quant-ph", "cond-mat.dis-nn"],
                    "matched_categories": ["cond-mat.dis-nn"],
                }
            ),
            "cond-mat.dis-nn",
        )

    def test_uses_matched_category_when_categories_are_empty(self):
        self.assertEqual(
            main_category(
                {
                    "categories": [],
                    "matched_category": "cs.CV",
                }
            ),
            "cs.CV",
        )


if __name__ == "__main__":
    unittest.main()
