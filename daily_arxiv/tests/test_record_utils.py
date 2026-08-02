import unittest

from daily_arxiv.record_utils import deduplicate_records, filter_new_records


class RecordUtilsTest(unittest.TestCase):
    def test_deduplicates_versions_and_preserves_categories(self):
        records = [
            {
                "id": "https://arxiv.org/abs/2607.12345v1",
                "categories": ["cond-mat.dis-nn"],
                "matched_category": "cond-mat.dis-nn",
            },
            {
                "id": "2607.12345v2",
                "categories": ["cond-mat.stat-mech"],
                "matched_category": "cond-mat.stat-mech",
            },
        ]

        result = deduplicate_records(records)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "2607.12345")
        self.assertEqual(
            result[0]["categories"],
            ["cond-mat.dis-nn", "cond-mat.stat-mech"],
        )
        self.assertEqual(
            result[0]["matched_categories"],
            ["cond-mat.dis-nn", "cond-mat.stat-mech"],
        )

    def test_filters_records_seen_in_history(self):
        records = [
            {"id": "2607.12345", "title": "old"},
            {"id": "2607.12345v2", "title": "old duplicate"},
            {"id": "2607.67890", "title": "new"},
        ]

        result = filter_new_records(records, {"2607.12345v1"})

        self.assertEqual([record["id"] for record in result], ["2607.67890"])


if __name__ == "__main__":
    unittest.main()
