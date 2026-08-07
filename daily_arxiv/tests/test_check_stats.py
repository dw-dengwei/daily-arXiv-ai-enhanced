import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from daily_arxiv.check_stats import perform_deduplication


class CheckStatsTest(unittest.TestCase):
    def test_history_only_duplicates_stop_processing(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / "2026-08-01.jsonl").write_text(
                json.dumps({"id": "2607.12345v1"}) + "\n",
                encoding="utf-8",
            )
            today_file = data_dir / "2026-08-02.jsonl"
            today_file.write_text(
                json.dumps({"id": "2607.12345v2"}) + "\n",
                encoding="utf-8",
            )

            status = perform_deduplication(
                today=date(2026, 8, 2),
                data_dir=data_dir,
            )

            self.assertEqual(status, "no_new_content")
            self.assertFalse(today_file.exists())

    def test_keeps_only_new_records_and_normalizes_the_saved_file(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / "2026-08-01.jsonl").write_text(
                json.dumps({"id": "2607.12345"}) + "\n",
                encoding="utf-8",
            )
            today_file = data_dir / "2026-08-02.jsonl"
            today_file.write_text(
                "\n".join(
                    [
                        json.dumps({"id": "2607.12345v2"}),
                        json.dumps({"id": "2607.67890v1"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            status = perform_deduplication(
                today=date(2026, 8, 2),
                data_dir=data_dir,
            )

            self.assertEqual(status, "has_new_content")
            self.assertEqual(
                [json.loads(line)["id"] for line in today_file.read_text(encoding="utf-8").splitlines()],
                ["2607.67890"],
            )


if __name__ == "__main__":
    unittest.main()
