import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from daily_research_radar import (  # noqa: E402
    RadarSummary,
    eligible_for_section,
    generate_daily_report,
    get_topic_context,
    has_expected_outputs,
    load_yaml,
    render_dashboard_html,
    resolve_report_dates,
    score_paper,
    update_file_list,
)


class ResearchRadarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = load_yaml(ROOT / "research_profile.yaml")
        cls.schedule = load_yaml(ROOT / "daily_topic_schedule.yaml")

    def test_topic_rotation_uses_anchor_date(self):
        first = get_topic_context(self.schedule, date(2026, 6, 15))
        second = get_topic_context(self.schedule, date(2026, 6, 16))
        wrapped = get_topic_context(self.schedule, date(2026, 6, 22))

        self.assertEqual(first.topic["id"], "prs_cross_ancestry_prediction")
        self.assertEqual(second.topic["id"], "genomic_sem_mr_causal_inference")
        self.assertEqual(wrapped.topic["id"], "prs_cross_ancestry_prediction")

    def test_topic_rotation_across_multiple_dates(self):
        dates = [date(2026, 6, 15), date(2026, 6, 16), date(2026, 6, 17), date(2026, 6, 18)]
        topic_ids = [get_topic_context(self.schedule, current_date).topic["id"] for current_date in dates]

        self.assertEqual(
            topic_ids,
            [
                "prs_cross_ancestry_prediction",
                "genomic_sem_mr_causal_inference",
                "proteomics_pqtl_multiomics_oa",
                "clinical_prediction_survival_risk",
            ],
        )

    def test_resolve_date_range_generation(self):
        args = Namespace(date=None, start_date="2026-06-01", end_date="2026-06-03", days_back=None)

        self.assertEqual(
            resolve_report_dates(args, today=date(2026, 6, 17)),
            [date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)],
        )

    def test_resolve_days_back_generation(self):
        args = Namespace(date=None, start_date=None, end_date=None, days_back=3)

        self.assertEqual(
            resolve_report_dates(args, today=date(2026, 6, 17)),
            [date(2026, 6, 15), date(2026, 6, 16), date(2026, 6, 17)],
        )

    def test_personalised_scoring_prioritises_relevant_genetic_epidemiology(self):
        topic = get_topic_context(self.schedule, date(2026, 6, 15)).topic
        relevant = {
            "title": "Cross-ancestry PRS-CSx improves osteoarthritis survival prediction",
            "summary": (
                "We combine polygenic risk score methods, UK Biobank, OAI, Coxnet, "
                "calibration, pQTL colocalization, and cardiometabolic phenotypes."
            ),
            "published": "2026-06-15T00:00:00+00:00",
        }
        generic_llm = {
            "title": "Instruction tuning for large language model reasoning",
            "summary": "A generic LLM benchmark improves chatgpt instruction tuning without biomedical data.",
            "published": "2026-06-15T00:00:00+00:00",
        }

        relevant_score = score_paper(relevant, self.profile, topic, date(2026, 6, 15))
        generic_score = score_paper(generic_llm, self.profile, topic, date(2026, 6, 15))

        self.assertGreater(relevant_score["scores"]["final_priority_score"], generic_score["scores"]["final_priority_score"])
        self.assertEqual(generic_score["generic_llm_penalty"], 1.5)
        self.assertIn("PRS and statistical genetics", relevant_score["topic_tags"])

    def test_recent_history_allows_only_high_relevance_upgrade_from_other(self):
        paper = {
            "id": "2606.00001",
            "research_radar": {
                "scores": {
                    "final_priority_score": 8,
                    "topic_match_score": 7,
                    "personal_relevance_score": 8,
                }
            },
        }
        history = {
            "2606.00001": {
                "appearances": [
                    {"date": "2026-06-01", "section": "other", "score": 5},
                ]
            }
        }

        self.assertTrue(eligible_for_section(paper, history, date(2026, 6, 17), "key"))
        self.assertFalse(eligible_for_section(paper, history, date(2026, 6, 17), "other"))

        history["2606.00001"]["appearances"].append({"date": "2026-06-10", "section": "key", "score": 8})
        self.assertFalse(eligible_for_section(paper, history, date(2026, 6, 17), "key"))

    def test_same_date_history_does_not_block_reruns(self):
        paper = {
            "id": "2606.00001",
            "research_radar": {
                "scores": {
                    "final_priority_score": 8,
                    "topic_match_score": 7,
                    "personal_relevance_score": 8,
                }
            },
        }
        history = {
            "2606.00001": {
                "appearances": [
                    {"date": "2026-06-17", "section": "key", "score": 8},
                ]
            }
        }

        self.assertTrue(eligible_for_section(paper, history, date(2026, 6, 17), "key"))

    def test_summary_accepts_real_list_fields(self):
        summary = RadarSummary.model_validate(
            {
                "key_methods": ["MR", "PRS"],
                "topic_tags": ["Causal inference", "Statistical genetics"],
            }
        )

        self.assertEqual(summary.key_methods, ["MR", "PRS"])
        self.assertEqual(summary.topic_tags, ["Causal inference", "Statistical genetics"])

    def test_summary_accepts_json_string_list_fields(self):
        summary = RadarSummary.model_validate(
            {
                "key_methods": '["MR", "PRS"]',
                "topic_tags": '["Causal inference", "Statistical genetics"]',
            }
        )

        self.assertEqual(summary.key_methods, ["MR", "PRS"])
        self.assertEqual(summary.topic_tags, ["Causal inference", "Statistical genetics"])

    def test_summary_accepts_comma_separated_list_fields(self):
        summary = RadarSummary.model_validate(
            {
                "key_methods": "MR, PRS, Cox model",
                "topic_tags": "Causal inference, Statistical genetics",
            }
        )

        self.assertEqual(summary.key_methods, ["MR", "PRS", "Cox model"])
        self.assertEqual(summary.topic_tags, ["Causal inference", "Statistical genetics"])

    def test_summary_accepts_empty_or_missing_list_fields(self):
        missing = RadarSummary.model_validate({})
        empty = RadarSummary.model_validate({"key_methods": "", "topic_tags": None})

        self.assertEqual(missing.key_methods, [])
        self.assertEqual(missing.topic_tags, [])
        self.assertEqual(empty.key_methods, [])
        self.assertEqual(empty.topic_tags, [])

    def test_dashboard_html_contains_reading_features(self):
        topic_context = get_topic_context(self.schedule, date(2026, 6, 15))
        paper = {
            "id": "2606.00001",
            "abs": "https://arxiv.org/abs/2606.00001",
            "authors": ["A. Researcher", "B. Statistician"],
            "title": "Cross-ancestry PRS-CSx improves osteoarthritis survival prediction",
            "categories": ["stat.ML", "q-bio.GN"],
            "research_radar": {
                "summary": RadarSummary(
                    plain_english_summary="Plain summary.",
                    technical_summary="Technical summary.",
                    key_methods=["PRS", "Cox model"],
                    relevance_to_weijie="Relevant.",
                    possible_use_in_my_research="Use it.",
                    possible_research_idea="New idea.",
                    priority="Must read",
                    estimated_reading_time="45 min",
                    topic_tags=["PRS and statistical genetics"],
                    scores={
                        "topic_match_score": 9,
                        "personal_relevance_score": 9,
                        "novelty_score": 7,
                        "translational_potential_score": 6,
                        "idea_generation_score": 8,
                        "final_priority_score": 9,
                    },
                ).model_dump()
            },
        }

        html = render_dashboard_html(date(2026, 6, 15), topic_context, self.schedule, [paper], [])

        self.assertIn("dashboard-shell", html)
        self.assertIn("Dark mode", html)
        self.assertIn("Idea Bank", html)
        self.assertIn("Weekly rotation", html)
        self.assertIn("Must read", html)
        self.assertIn("https://arxiv.org/abs/2606.00001", html)
        self.assertIn("PRS and statistical genetics", html)

    def test_multi_date_generation_and_skip_existing(self):
        fixture = ROOT / "tests/fixtures/sample_papers.jsonl"
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "data"
            output_dir.mkdir()
            for current_date in (date(2026, 6, 15), date(2026, 6, 16)):
                (output_dir / f"{current_date.isoformat()}.jsonl").write_text(fixture.read_text(), encoding="utf-8")

            args = Namespace(
                data=None,
                output_dir=str(output_dir),
                history=str(output_dir / "history.json"),
                max_key=2,
                max_other=1,
                serendipity_ratio=0.25,
                no_llm=True,
                no_fetch=True,
                max_fetch_results=250,
                max_workers=1,
                llm_timeout_seconds=60,
                skip_existing=False,
            )

            generated = [
                generate_daily_report(args, current_date, self.profile, self.schedule, self.profile["arxiv_categories"])
                for current_date in (date(2026, 6, 15), date(2026, 6, 16))
            ]
            update_file_list(output_dir, Path(tmp) / "assets/file-list.txt")

            self.assertEqual(generated, [True, True])
            for current_date in (date(2026, 6, 15), date(2026, 6, 16)):
                self.assertTrue(has_expected_outputs(output_dir, current_date))
            file_list = (Path(tmp) / "assets/file-list.txt").read_text()
            self.assertIn("2026-06-15_research_radar.html", file_list)
            self.assertIn("2026-06-16_research_radar.html", file_list)

            args.skip_existing = True
            self.assertFalse(generate_daily_report(args, date(2026, 6, 15), self.profile, self.schedule, self.profile["arxiv_categories"]))


if __name__ == "__main__":
    unittest.main()
