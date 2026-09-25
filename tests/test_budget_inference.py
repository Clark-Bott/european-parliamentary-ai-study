"""Sampling and paid smoke tests use only synthetic text and fake API clients."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from parliament_ai_study.analysis import aggregate_results
from parliament_ai_study.budget_sample import plan_sample, write_sample
from parliament_ai_study.cost import estimate_cost
from parliament_ai_study.io import iter_jsonl, write_jsonl
from parliament_ai_study.pangram import request_fingerprint
from parliament_ai_study.pipeline import run_api_test, run_pipeline
from parliament_ai_study.run_experiment import main


def fixture():
    return [{"country": country, "date": f"{year}-{month:02d}-15",
             "speech_id": f"{country}-{year}-{month}-{i}", "speaker_id": f"speaker-{i}",
             "speaker_name": "Synthetic", "speaker_role": "member", "party": "A",
             "speech_text": ("synthetic " * words),
             "word_count": words, "source_identifier": f"{country}-{year}-{month}-{i}",
             "source_url": "https://example.invalid/synthetic"}
            for country in ("Germany", "France", "Netherlands", "Italy", "Spain", "Poland")
            for year in range(2018, 2026) for month in (2, 9)
            for i, words in enumerate((50, 75, 120, 200, 300))]


class SampleTests(unittest.TestCase):
    def test_stratified_sample_is_bounded_reproducible_and_weighted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "all.jsonl"
            write_jsonl(source, fixture())
            plan = plan_sample(source, budget=25, price_per_1000_words=0.5, seed=7)
            first = root / "first.jsonl"
            write_sample(source, first, plan)
            rows = list(iter_jsonl(first))
            self.assertEqual(len(plan["strata"]), 96)
            self.assertLess(len(rows), len(fixture()))
            self.assertEqual(sum(s["eligible"] for s in plan["strata"].values()), len(fixture()))
            self.assertEqual(len(rows), sum(s["selected"] for s in plan["strata"].values()))
            self.assertLessEqual(estimate_cost(rows, price_per_1000_words=0.5)["estimated_cost"], 25)
            self.assertTrue(all(s["selected"] > 0 for s in plan["strata"].values()))
            second = root / "second.jsonl"
            write_sample(source, second, plan)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            results = aggregate_results(rows, lambda _: {"fraction_ai": 0.3, "fraction_ai_assisted": 0.2})
            self.assertEqual(len(results), 96)
            for result in results:
                self.assertAlmostEqual(result["ai_word_share"], 0.3)
                self.assertAlmostEqual(result["mixed_word_share"], 0.2)
                self.assertAlmostEqual(result["speeches"], 5)
            self.assertRaisesRegex(ValueError, "conservative minimum", plan_sample,
                                   source, budget=1, price_per_1000_words=0.5)

    def test_changed_corpus_blocks_sample_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "all.jsonl"
            write_jsonl(source, fixture()[:5])
            plan = plan_sample(source, budget=5, price_per_1000_words=0.5)
            source.write_text(source.read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "corpus changed"):
                write_sample(source, root / "subset.jsonl", plan)

    def test_dry_budgeted_pipeline_labels_output_and_stays_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "all.jsonl"
            write_jsonl(source, fixture())
            with patch("parliament_ai_study.pipeline.PangramClient", side_effect=AssertionError("network")):
                result = run_pipeline(corpus=source, results_dir=root / "out", dry_run=True,
                                      price_per_1000_words=0.5, model="pangram-4",
                                      positive_controls=None, sample_budget=25)
            self.assertTrue(result["sampled"])
            report = (root / "out/reports/dry_run_report.md").read_text()
            self.assertIn("MOCKED", report)
            self.assertIn("inverse-inclusion", report)
            self.assertIn("SAMPLED", (root / "out/figures/all_countries.svg").read_text())
            self.assertEqual(json.loads((root / "out/reports/sampling_plan.json").read_text())
                             ["sampled_speeches"], result["speeches"])

    def test_paid_sample_still_checks_source_gaps_before_client(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "all.jsonl"
            write_jsonl(source, fixture())
            gap = root / "gaps.json"
            gap.write_text('[{"missing": true}]')
            with patch("parliament_ai_study.pipeline.PangramClient", side_effect=AssertionError("network")):
                with self.assertRaisesRegex(ValueError, "unresolved official source gaps"):
                    run_pipeline(corpus=source, results_dir=root / "out", dry_run=False,
                                 price_per_1000_words=0.5, model="pangram-4",
                                 confirm_paid_run=True, api_key="fake", gap_reports=gap,
                                 sample_budget=25, positive_controls=None)
            self.assertFalse((root / "out/raw_pangram").exists())

    def test_paid_sample_with_fake_api_produces_weighted_tables_under_cap(self):
        class FakeClient:
            def __init__(self, api_key, *, model):
                self.model = model
            def available_models(self):
                return [self.model]
            def analyze(self, text, cache, *, allow_paid):
                if not allow_paid:
                    raise AssertionError("explicit paid authorization missing")
                response = {"stage": "STAGE_SUCCESS", "fraction_ai": 0.25,
                            "fraction_ai_assisted": 0.10, "fraction_human": 0.65}
                cache.store(request_fingerprint(text, {"model": self.model,
                                                       "public_dashboard_link": False}), response)
                return response

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "all.jsonl"
            write_jsonl(source, fixture())
            gap = root / "gaps.json"
            gap.write_text("[]\n")
            with patch("parliament_ai_study.pipeline.PangramClient", FakeClient):
                with self.assertRaisesRegex(ValueError, "conservative minimum"):
                    run_pipeline(corpus=source, results_dir=root / "paid", dry_run=False,
                                 price_per_1000_words=0.5, model="pangram-4",
                                 confirm_paid_run=True, api_key="fake", gap_reports=gap,
                                 positive_controls=None,
                                 sample_budget=1, max_cost=1)
                result = run_pipeline(corpus=source, results_dir=root / "paid", dry_run=False,
                                      price_per_1000_words=0.5, model="pangram-4",
                                      confirm_paid_run=True, api_key="fake", gap_reports=gap,
                                      positive_controls=None,
                                      sample_budget=25, max_cost=25)
            self.assertTrue(result["sampled"])
            self.assertFalse(result["mocked"])
            self.assertLessEqual(result["estimated_cost"], 25)
            monthly = (root / "paid/tables/monthly_results.csv").read_text()
            self.assertIn("sampled_speeches", monthly)
            self.assertIn("0.25", monthly)
            self.assertIn("SAMPLED ESTIMATE", (root / "paid/figures/all_countries.svg").read_text())
            self.assertIn("AI-assisted", (root / "paid/figures/all_countries_mixed_word_share.svg").read_text())
            self.assertEqual((root / "paid/tables/speaker_breakdown.csv").read_text(), "\n")


class PaidSmokeTests(unittest.TestCase):
    def test_real_corpus_selection_and_fake_client_report(self):
        calls = []
        source_texts = {record["speech_text"] for record in fixture()}

        class FakeClient:
            def __init__(self, api_key, *, model):
                calls.append(("init", model))
                self.model = model
            def available_models(self):
                calls.append(("models",))
                return ["pangram-4"]
            def analyze(self, text, cache, *, allow_paid):
                calls.append(("task", len(text.split()), allow_paid))
                self_test.assertTrue(40 <= len(text.split()) <= 100)
                self_test.assertIn(text, source_texts)
                fingerprint = request_fingerprint(text, {"model": self.model,
                                                        "public_dashboard_link": False})
                if cache.load(fingerprint) is not None:
                    return cache.load(fingerprint)
                result = {"stage": "STAGE_SUCCESS", "fraction_ai": 0.3,
                          "fraction_ai_assisted": 0.2, "fraction_human": 0.5}
                cache.store(fingerprint, result)
                return result

        self_test = self
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "all.jsonl"
            write_jsonl(corpus, fixture())
            gap = root / "gaps.json"
            gap.write_text("[]\n")
            options = dict(corpus=corpus, results_dir=root, model="pangram-4",
                           api_key="fake", confirm_paid_run=True,
                           price_per_1000_words=0.5, gap_reports=gap)
            with patch("parliament_ai_study.pipeline.PangramClient", FakeClient):
                with self.assertRaisesRegex(PermissionError, "confirm-paid-run"):
                    run_api_test(**{**options, "confirm_paid_run": False})
                with self.assertRaisesRegex(PermissionError, "exceed the test cap"):
                    run_api_test(**options, max_cost=0.01)
                with self.assertRaisesRegex(PermissionError, "exceed the test cap"):
                    run_api_test(**options, test_count=2)
                self.assertEqual(calls, [])
                summary = run_api_test(**options)
                two = run_api_test(**{**options, "results_dir": root / "two"},
                                   test_count=2, max_cost=0.10)
            self.assertEqual(summary["billing_units"], 1)
            self.assertEqual(two["billing_units"], 2)
            self.assertEqual(len(two["completed_speeches"]), 2)
            self.assertEqual(len({row["speech_id"] for row in two["completed_speeches"]}), 2)
            self.assertEqual([c[0] for c in calls], ["init", "models", "task", "init", "models", "task", "task"])
            self.assertEqual((root / "api_test/test_result.json").exists(), True)
            self.assertEqual(summary["completed_speeches"][0]["ai_only_share"], 0.3)
            self.assertEqual(summary["completed_speeches"][0]["ai_assisted_share"], 0.2)
            self.assertEqual(summary["completed_speeches"][0]["country"] in
                             ("Germany", "France", "Netherlands", "Italy", "Spain", "Poland"), True)
            self.assertNotIn("speech_text", (root / "api_test/test_result.json").read_text())
            self.assertFalse((root / "tables").exists())
            changed = root / "changed.jsonl"
            write_jsonl(changed, list(iter_jsonl(corpus)) + [{"country": "Germany", "date": "2024-01-01",
                         "speech_id": "new", "speech_text": "something " * 50,
                         "word_count": 50, "source_identifier": "new",
                         "source_url": "https://example.invalid/new"}])
            with self.assertRaisesRegex(ValueError, "existing API test selection differs"):
                run_api_test(**{**options, "corpus": changed})

    def test_paid_api_test_keeps_full_coverage_and_polish_spanish_gap_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "single.jsonl"
            write_jsonl(corpus, fixture()[:1])
            options = dict(corpus=corpus, results_dir=root, model="pangram-4", api_key="fake",
                           confirm_paid_run=True, price_per_1000_words=0.5,
                           gap_reports=root / "gaps.json")
            with patch("parliament_ai_study.pipeline.PangramClient", side_effect=AssertionError("network")):
                with self.assertRaisesRegex(ValueError, "country/year coverage"):
                    run_api_test(**options)
                write_jsonl(corpus, fixture())
                with self.assertRaisesRegex(ValueError, "source-gap report is missing"):
                    run_api_test(**options)
                (root / "gaps.json").write_text('[{"missing": true}]')
                with self.assertRaisesRegex(ValueError, "unresolved official source gaps"):
                    run_api_test(**options)
                (root / "gaps.json").write_text("[]\n")
                german = root / "germany_unavailable_protocols.json"
                german.write_text('[{"number":95},{"number":96}]\n')
                with self.assertRaisesRegex(PermissionError, "exceed the test cap"):
                    run_api_test(**{**options, "gap_reports": (german, root / "gaps.json")},
                                 max_cost=0)
            self.assertFalse((root / "api_test").exists())

    def test_cli_test_does_not_build_missing_corpus(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("parliament_ai_study.run_experiment.build_six_country_corpus", side_effect=AssertionError("build")):
                with patch("parliament_ai_study.run_experiment.load_dotenv", return_value=None):
                    with self.assertRaisesRegex(FileNotFoundError, "test corpus not found"):
                        main(["--test-api", "--confirm-paid-run", "--corpus",
                              str(Path(directory) / "missing.jsonl")])

    def test_cli_forwards_country_count_and_full_guard_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "fixture.jsonl"
            summary = {"completed_speeches": [{"country": "France", "date": "2024-01-01",
                        "speech_id": "example", "ai_only_share": 0.3, "ai_assisted_share": 0.1}],
                       "estimated_max_cost_usd": 0.10}
            with patch("parliament_ai_study.run_experiment.load_dotenv", return_value=None):
                with patch("parliament_ai_study.run_experiment.build_six_country_corpus",
                           side_effect=AssertionError("build")):
                    with patch("parliament_ai_study.run_experiment.run_api_test",
                               return_value=summary) as test:
                        self.assertEqual(main(["--test-api", "--confirm-paid-run", "--corpus",
                                               str(corpus), "--test-count", "2", "--test-country",
                                               "France", "--max-cost", "0.10"]), 0)
                        self.assertEqual(test.call_args.kwargs["corpus"], corpus)
                        self.assertEqual(test.call_args.kwargs["test_count"], 2)
                        self.assertEqual(test.call_args.kwargs["test_country"], "France")
                        self.assertEqual(test.call_args.kwargs["max_cost"], 0.10)


if __name__ == "__main__":
    unittest.main()
