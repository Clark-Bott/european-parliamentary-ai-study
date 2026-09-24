import json
import tempfile
import unittest
from pathlib import Path

from parliament_ai_study.analysis import aggregate_results
from parliament_ai_study.cost import estimate_cost
from parliament_ai_study.models import Speech, word_count
from parliament_ai_study.pangram import PangramClient, ResponseCache, request_fingerprint
from parliament_ai_study.pipeline import run_pipeline


class SpeechSchemaTests(unittest.TestCase):
    def test_unicode_word_count_and_normalized_speech_round_trip(self):
        self.assertEqual(word_count("L’intelligence artificielle — Grüße, Polska!"), 4)
        speech = Speech(
            country="Netherlands",
            parliament="Tweede Kamer",
            chamber="Lower",
            date="2024-03-12",
            session_id="session-1",
            speech_id="speech-1",
            speaker_id="member-1",
            speaker_name="Zoë",
            speech_text="Goedemorgen, collega’s.",
            source_url="https://example.test/record/1",
        )
        serialized = speech.to_dict()
        restored = Speech.from_dict(json.loads(json.dumps(serialized)))
        self.assertEqual(restored.speech_text, "Goedemorgen, collega’s.")
        self.assertEqual(restored.word_count, 2)
        self.assertEqual(restored.source_identifier, "speech-1")


class CostTests(unittest.TestCase):
    def test_estimate_cost_filters_country_and_year_and_groups(self):
        speeches = [
            {"country": "Germany", "date": "2019-01-01", "word_count": 1000},
            {"country": "Germany", "date": "2024-01-01", "word_count": 500},
            {"country": "France", "date": "2024-01-01", "word_count": 2000},
        ]
        result = estimate_cost(speeches, price_per_1000_words=0.5, country="Germany", years={2019})
        self.assertEqual(result["speeches"], 1)
        self.assertEqual(result["words"], 1000)
        self.assertAlmostEqual(result["estimated_cost"], 0.5)
        self.assertEqual(result["estimated_api_units"], 10)

    def test_default_cost_filter_excludes_interventions_below_forty_words(self):
        records = [{"country": "Poland", "date": "2020-01-01", "word_count": 39},
                   {"country": "Poland", "date": "2020-01-02", "word_count": 40}]
        result = estimate_cost(records, price_per_1000_words=0.5)
        self.assertEqual(result["speeches"], 1)
        self.assertEqual(result["words"], 40)


class AnalysisTests(unittest.TestCase):
    def test_aggregates_ai_and_mixed_word_shares_by_period(self):
        speeches = [
            {"country": "France", "date": "2024-02-01", "word_count": 100, "speech_id": "a"},
            {"country": "France", "date": "2024-02-02", "word_count": 300, "speech_id": "b"},
        ]
        responses = {
            "a": {"fraction_ai": 0.5, "fraction_ai_assisted": 0.2},
            "b": {"fraction_ai": 0.0, "fraction_ai_assisted": 0.1},
        }
        result = aggregate_results(speeches, responses, period="month")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["period"], "2024-02")
        self.assertEqual(result[0]["speeches"], 2)
        self.assertAlmostEqual(result[0]["ai_word_share"], 0.125)
        self.assertAlmostEqual(result[0]["mixed_word_share"], 0.125)
        self.assertAlmostEqual(result[0]["ai_plus_mixed_word_share"], 0.25)

    def test_default_analysis_excludes_interventions_below_forty_words(self):
        speeches = [{"country": "Germany", "date": "2024-01-01", "word_count": 39, "speech_id": "short"}]
        result = aggregate_results(speeches, {"short": {"fraction_ai": 0.5, "fraction_ai_assisted": 0.0}})
        self.assertEqual(result, [])

    def test_uses_pangram_window_word_counts_when_available(self):
        speeches = [{"country": "Poland", "date": "2024-01-01", "word_count": 10, "speech_id": "p1"}]
        responses = {"p1": {"fraction_ai": 0.9, "fraction_ai_assisted": 0.0,
                            "windows": [{"label": "AI-Generated", "word_count": 3},
                                        {"label": "AI-Assisted", "word_count": 2},
                                        {"label": "Human Written", "word_count": 5}]}}
        result = aggregate_results(speeches, responses, period="year", min_words=0)[0]
        self.assertEqual(result["ai_words_estimate"], 3)
        self.assertEqual(result["mixed_words_estimate"], 2)
        self.assertAlmostEqual(result["ai_word_share"], 0.3)
        self.assertAlmostEqual(result["mixed_word_share"], 0.2)


class CacheTests(unittest.TestCase):
    def test_cache_fingerprint_depends_on_exact_text_and_configuration(self):
        base = request_fingerprint("exact text", {"model": "pangram-4"})
        self.assertEqual(base, request_fingerprint("exact text", {"model": "pangram-4"}))
        self.assertNotEqual(base, request_fingerprint("Exact text", {"model": "pangram-4"}))
        self.assertNotEqual(base, request_fingerprint("exact text", {"model": "pangram-3"}))

    def test_cache_persists_completed_response(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = ResponseCache(Path(directory))
            fingerprint = request_fingerprint("text", {"model": "pangram-4"})
            cache.store(fingerprint, {"stage": "STAGE_SUCCESS", "fraction_ai": 0.2})
            self.assertEqual(cache.load(fingerprint)["fraction_ai"], 0.2)


class PangramClientTests(unittest.TestCase):
    def test_concurrent_inference_for_same_text_submits_only_once(self):
        import json
        import threading
        import time

        calls = []
        call_lock = threading.Lock()
        post_started = threading.Event()
        release_post = threading.Event()
        errors = []

        class FakeResponse:
            def __init__(self, value): self.data = json.dumps(value).encode()
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return self.data

        def opener(request, timeout):
            with call_lock:
                calls.append(request.method)
            if request.method == "POST":
                post_started.set()
                release_post.wait(timeout=2)
                return FakeResponse({"task_id": "shared-task"})
            return FakeResponse({"stage": "STAGE_SUCCESS", "fraction_ai": 0.1,
                                 "fraction_ai_assisted": 0.1, "fraction_human": 0.8})

        with tempfile.TemporaryDirectory() as directory:
            client = PangramClient("test-key", model="pangram-4", opener=opener,
                                   sleep=lambda _: None, max_poll_attempts=1)
            cache = ResponseCache(Path(directory))
            outputs = []
            def run():
                try: outputs.append(client.analyze("same text", cache, allow_paid=True))
                except Exception as exc: errors.append(exc)
            first = threading.Thread(target=run)
            second = threading.Thread(target=run)
            first.start()
            self.assertTrue(post_started.wait(timeout=1))
            second.start()
            time.sleep(0.05)
            release_post.set()
            first.join(timeout=2)
            second.join(timeout=2)
            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(len(outputs), 2)
            self.assertEqual(calls.count("POST"), 1)

    def test_unknown_post_outcome_blocks_automatic_resubmission(self):
        fingerprint = request_fingerprint("text", {"model": "pangram-4", "public_dashboard_link": False})
        with tempfile.TemporaryDirectory() as directory:
            cache = ResponseCache(Path(directory))
            cache.mark_unknown(fingerprint, "simulated lost response")
            calls = []
            client = PangramClient("test-key", model="pangram-4",
                                   opener=lambda *args, **kwargs: calls.append(args))
            with self.assertRaises(RuntimeError):
                client.analyze("text", cache, allow_paid=True)
            self.assertEqual(calls, [])

    def test_requires_authorization_then_caches_without_resubmission(self):
        import json

        calls = []
        payloads = [
            {"task_id": "task-1"},
            {"stage": "STAGE_SUCCESS", "fraction_ai": 0.1,
             "fraction_ai_assisted": 0.2, "fraction_human": 0.7},
        ]

        class FakeResponse:
            def __init__(self, payload):
                self.payload = json.dumps(payload).encode()
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return self.payload

        def opener(request, timeout):
            calls.append(request.method)
            return FakeResponse(payloads.pop(0))

        with tempfile.TemporaryDirectory() as directory:
            cache = ResponseCache(Path(directory))
            client = PangramClient("test-key", model="pangram-4", opener=opener,
                                   sleep=lambda _: None, max_poll_attempts=2)
            with self.assertRaises(PermissionError):
                client.analyze("text", cache)
            self.assertEqual(calls, [])
            result = client.analyze("text", cache, allow_paid=True)
            self.assertEqual(result["fraction_ai"], 0.1)
            self.assertEqual(calls, ["POST", "GET"])
            self.assertEqual(client.analyze("text", cache)["fraction_ai"], 0.1)
            self.assertEqual(calls, ["POST", "GET"])


class PipelineTests(unittest.TestCase):
    def test_mock_dry_run_creates_outputs_for_all_six_countries(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = run_pipeline(
                corpus=None, results_dir=Path(directory), dry_run=True,
                price_per_1000_words=0.5, model="pangram-4")
            self.assertTrue(summary["synthetic_smoke_test"])
            self.assertEqual(len(summary["countries"]), 6)
            for relative in (
                "tables/corpus_size.csv", "tables/annual_results.csv",
                "tables/cost_estimate.csv", "figures/all_countries.svg",
                "reports/dry_run_report.md", "processed/mock_results.jsonl",
            ):
                self.assertTrue((Path(directory) / relative).is_file(), relative)

    def test_real_corpus_dry_run_is_labeled_mocked_not_as_research_result(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            corpus = base / "corpus.jsonl"
            corpus.write_text(json.dumps({
                "country": "Germany", "parliament": "Bundestag", "chamber": "lower",
                "date": "2024-01-01", "session_id": "1", "speech_id": "s1",
                "speaker_id": "m1", "speaker_name": "Test", "speech_text": "Hallo Welt",
                "word_count": 2, "source_identifier": "s1", "source_url": "https://example.test/s1"
            }) + "\n", encoding="utf-8")
            run_pipeline(corpus=corpus, results_dir=base / "out", dry_run=True,
                         price_per_1000_words=0.5, model="pangram-4")
            report = (base / "out/reports/dry_run_report.md").read_text(encoding="utf-8")
            self.assertIn("MOCKED PIPELINE", report)
            self.assertNotIn("Pangram inference outputs", report)
            self.assertTrue((base / "out/processed/mock_results.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
