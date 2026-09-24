from collections import Counter
from io import BytesIO
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

from parliament_ai_study.analysis import aggregate_results, is_chair_role, is_minister_role
from parliament_ai_study.cost import estimate_cost
from parliament_ai_study.io import iter_jsonl, write_jsonl
from parliament_ai_study.models import Speech, word_count
from parliament_ai_study.pangram import PangramClient, ResponseCache, request_fingerprint
from parliament_ai_study.pipeline import run_pipeline, validate_processing_approval
from parliament_ai_study.positive_controls import (
    evaluate_positive_controls,
    import_controls,
    load_controls,
    normalize_record,
)
from parliament_ai_study.provenance import reconcile_source_manifest
from parliament_ai_study.qa import audit_corpus_file
from parliament_ai_study.review import (
    containment_status,
    normalize,
    sample_records,
)
from parliament_ai_study.sampling import sample_historical_controls
from parliament_ai_study.sources.build import build_six_country_corpus


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


class JsonLinesTests(unittest.TestCase):
    def test_disk_backed_audit_reports_duplicate_text_and_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"
            write_jsonl(path, [{"country": "France", "date": "2024-01-01", "speech_id": "a",
                                "speech_text": "Bonjour", "word_count": 1, "source_url": "https://example.test/a",
                                "source_identifier": "a"},
                               {"country": "France", "date": "2024-01-01", "speech_id": "b",
                                "speech_text": "Bonjour", "word_count": 1, "source_url": "https://example.test/b",
                                "source_identifier": "b"}])
            report = audit_corpus_file(path)
            self.assertTrue(report["valid"])
            self.assertEqual(report["duplicate_text_count"], 1)

    def test_stream_reader_round_trips_json_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"
            expected = [{"id": 1}, {"id": 2, "text": "grüße"}]
            write_jsonl(path, expected)
            self.assertEqual(list(iter_jsonl(path)), expected)


class ProvenanceTests(unittest.TestCase):
    def test_reconcile_hashes_current_files_and_marks_unknown_source_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw"
            files = {
                "spain/term-12/DSCD-12-PL-162.html": b"html",
                "spain/pdf-fallback/DSCD-12-PL-162.PDF": b"%PDF",
                "italy/leg18/sitting-0001.xml": b"<seduta/>",
                "netherlands/verslag/abc-123.xml": b"<verslag/>",
                "poland/term-8/proceeding-1/2018-01-01/statement-2.html": b"<p>text</p>",
                "germany/term-19/19001.xml": b"<xml/>",
            }
            for relative, content in files.items():
                path = raw / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            manifest = Path(directory) / "source_manifest.jsonl"
            report = reconcile_source_manifest(raw, manifest, Path(directory) / "report.json")
            self.assertEqual(report["current_raw_files"], len(files))
            self.assertEqual(report["unresolved_source_urls"][0]["local_path"].split("/")[-1], "19001.xml")
            entries = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
            by_name = {Path(entry["local_path"]).name: entry for entry in entries}
            self.assertIn("DSCD-12-PL-162.html", by_name)
            self.assertIn("statement-2.html", by_name)
            self.assertTrue(by_name["19001.xml"]["source_url"] == "")


class CostTests(unittest.TestCase):
    def test_rounds_each_speech_up_to_a_started_billable_block(self):
        rows = [{"country": "Italy", "date": "2024-01-01", "word_count": 101},
                {"country": "Italy", "date": "2024-01-02", "word_count": 101}]
        cost = estimate_cost(rows, price_per_1000_words=0.5)
        self.assertEqual(cost["estimated_api_units"], 4)
        self.assertAlmostEqual(cost["estimated_cost"], 0.20)

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
    def test_window_counts_use_detector_denominator_after_text_normalization(self):
        rows = [{"country": "Poland", "date": "2025-01-01", "word_count": 100, "speech_id": "p"}]
        results = {"p": {"fraction_ai": 0.0, "fraction_ai_assisted": 0.0,
                          "windows": [{"label": "AI-Generated", "word_count": 30},
                                      {"label": "Human Written", "word_count": 80}]}}
        summary = aggregate_results(rows, results)[0]
        self.assertAlmostEqual(summary["ai_word_share"], 30 / 110)
        self.assertAlmostEqual(summary["ai_words_estimate"], 100 * 30 / 110)

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

    def test_analysis_accepts_a_lazy_response_resolver(self):
        speeches = [{"country": "Germany", "date": "2024-01-01", "word_count": 40, "speech_id": "p"}]
        calls = []
        def resolve(speech):
            calls.append(speech["speech_id"])
            return {"fraction_ai": 0.25, "fraction_ai_assisted": 0.0}
        result = aggregate_results(iter(speeches), resolve)
        self.assertEqual(calls, ["p"])
        self.assertAlmostEqual(result[0]["ai_word_share"], 0.25)

    def test_lazy_resolver_is_not_called_for_filtered_speeches(self):
        speeches = [{"country": "Germany", "date": "2024-01-01", "word_count": 39, "speech_id": "short"}]
        def resolve(speech):
            raise AssertionError("response resolver was called")
        self.assertEqual(aggregate_results(speeches, resolve), [])

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

    def test_window_labels_with_spaces_and_slashes_are_recognized(self):
        speeches = [{"country": "France", "date": "2024-01-01", "word_count": 100, "speech_id": "f"}]
        responses = {"f": {"fraction_ai": 0.0, "fraction_ai_assisted": 0.0,
                           "windows": [{"label": "AI Generated", "word_count": 25},
                                       {"label": "AI-Assisted / Mixed", "word_count": 15},
                                       {"label": "Human Written", "word_count": 60}]}}
        result = aggregate_results(speeches, responses, period="year", min_words=0)[0]
        self.assertAlmostEqual(result["ai_word_share"], 0.25)
        self.assertAlmostEqual(result["mixed_word_share"], 0.15)

    def test_unknown_window_vocabulary_keeps_response_fractions_instead_of_zeroing(self):
        speeches = [{"country": "Italy", "date": "2024-01-01", "word_count": 100, "speech_id": "i"}]
        responses = {"i": {"fraction_ai": 0.4, "fraction_ai_assisted": 0.1,
                           "windows": [{"label": "AI Generated Text (v5)", "word_count": 50},
                                       {"label": "Written By A Human", "word_count": 50}]}}
        result = aggregate_results(speeches, responses, period="year", min_words=0)[0]
        self.assertAlmostEqual(result["ai_word_share"], 0.4)
        self.assertAlmostEqual(result["mixed_word_share"], 0.1)

    def test_minister_filter_matches_every_source_language(self):
        minister_roles = [
            "Bundesminister der Finanzen", "Bundeskanzlerin",          # Germany
            "ministre déléguée", "Premier ministre", "garde des sceaux",  # France
            "minister-president, minister van Algemene Zaken",         # Netherlands
            "staatssecretaris van Infrastructuur en Waterstaat",
            "minister",                                                # Italy, Spain
            "Prezes Rady Ministrów",                                   # Poland
        ]
        for role in minister_roles:
            self.assertTrue(is_minister_role(role), role)
        ordinary_roles = ["", "lid Tweede Kamer", "rapporteur", "floor_speaker",
                          "Sekretarz Poseł", "Presidentschaft"]
        for role in ordinary_roles:
            self.assertFalse(is_minister_role(role), role)
        rows = [{"country": "Germany", "date": "2024-01-01", "word_count": 50,
                 "speech_id": "m", "speaker_role": "Bundesministerin des Innern"}]
        response = {"m": {"fraction_ai": 0.5, "fraction_ai_assisted": 0.0}}
        self.assertEqual(aggregate_results(rows, response, exclude_ministers=True), [])
        self.assertEqual(len(aggregate_results(rows, response)), 1)

    def test_chair_filter_matches_plenary_chairs_but_not_committee_chairs(self):
        chair_roles = ["presiding_officer", "Präsident", "Präsidentin",
                       "Präsident Dr. Wolfgang Schäuble", "Vizepräsidentin",
                       "Wicemarszałek"]
        for role in chair_roles:
            self.assertTrue(is_chair_role(role), role)
        self.assertTrue(is_chair_role("", "Marszałek"))
        # German state premiers are cabinet roles, French and Dutch committee
        # presidents are not the plenary chair: none belongs in the chair
        # exclusion.
        for role in ["Ministerpräsident (Bayern)",
                     "président de la commission des finances",
                     "voorzitter van de commissie"]:
            self.assertFalse(is_chair_role(role), role)


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


class HistoricalSamplingTests(unittest.TestCase):
    def test_sampling_is_seeded_balanced_and_limits_speaker_reuse(self):
        records = []
        for year in range(2018, 2022):
            for party in ("A", "B"):
                for length in (80, 180):
                    sid = f"{year}-{party}-{length}"
                    records.append({"country": "France", "date": f"{year}-04-01",
                                   "speech_id": sid, "speaker_id": sid,
                                   "party": party, "word_count": length})
        records.append({"country": "France", "date": "2022-01-01", "speech_id": "transition",
                        "speaker_id": "transition", "party": "C", "word_count": 180})
        first = sample_historical_controls(records, sample_size_per_country=8, seed=17, max_per_speaker=1)
        second = sample_historical_controls(records, sample_size_per_country=8, seed=17, max_per_speaker=1)
        self.assertEqual([r["speech_id"] for r in first], [r["speech_id"] for r in second])
        self.assertEqual(len(first), 8)
        self.assertEqual(len({r["speaker_id"] for r in first}), 8)
        self.assertTrue(all(2018 <= int(r["date"][:4]) <= 2021 for r in first))
        self.assertGreaterEqual(len({r["date"][:4] for r in first}), 3)
    def test_zero_speaker_id_is_treated_as_missing_not_one_shared_person(self):
        records = [
            {"country": "France", "date": "2018-02-01", "speech_id": "one", "speaker_id": "0",
             "party": "A", "word_count": 60},
            {"country": "France", "date": "2018-02-02", "speech_id": "two", "speaker_id": "0",
             "party": "B", "word_count": 60},
        ]
        sample = sample_historical_controls(records, sample_size_per_country=2, max_per_speaker=1)
        self.assertEqual(len(sample), 2)

    def test_year_balance_is_not_swamped_by_many_parties_in_one_year(self):
        records = []
        for year in (2018, 2019, 2020):
            for person in range(30):
                sid = f"{year}-small-{person}"
                records.append({"country": "France", "date": f"{year}-05-01", "speech_id": sid,
                                "speaker_id": sid, "party": "single", "word_count": 120})
        for party_index in range(20):
            for person in range(30):
                sid = f"2021-party{party_index}-{person}"
                records.append({"country": "France", "date": "2021-05-01", "speech_id": sid,
                                "speaker_id": sid, "party": f"party{party_index}", "word_count": 120})
        sample = sample_historical_controls(records, sample_size_per_country=40, seed=4,
                                            max_per_speaker=1)
        counts = Counter(row["date"][:4] for row in sample)
        self.assertEqual(len(sample), 40)
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)


class PangramClientTests(unittest.TestCase):
    def test_model_discovery_and_safe_rate_limit_retry(self):
        calls = []

        class FakeResponse:
            def __init__(self, data): self.data = json.dumps(data).encode()
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return self.data

        def opener(request, timeout):
            calls.append((request.method, request.full_url))
            if request.full_url.endswith("/models"):
                return FakeResponse({"models": ["default", "pangram-4"]})
            if request.method == "POST" and sum(method == "POST" for method, _ in calls) == 1:
                raise HTTPError(request.full_url, 429, "rate limit", {"Retry-After": "1"}, BytesIO())
            if request.method == "POST":
                return FakeResponse({"task_id": "task-safe"})
            return FakeResponse({"stage": "STAGE_SUCCESS", "fraction_ai": 0.0,
                                 "fraction_ai_assisted": 0.0, "fraction_human": 1.0})

        with tempfile.TemporaryDirectory() as directory:
            waits = []
            client = PangramClient("not-real", model="pangram-4", opener=opener, sleep=waits.append)
            self.assertIn("pangram-4", client.available_models())
            client.analyze("Test words", ResponseCache(directory), allow_paid=True)
            self.assertEqual(sum(method == "POST" for method, _ in calls), 2)
            self.assertEqual(waits, [1.0])

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
    def test_build_combines_six_existing_country_corpora_and_writes_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "data/processed"
            for country in ("germany", "france", "netherlands", "italy", "spain", "poland"):
                write_jsonl(root / f"{country}_speeches.jsonl", [{
                    "country": country.title(), "date": "2019-03-01",
                    "speech_id": country, "speaker_id": country, "word_count": 100,
                    "speech_text": "historical synthetic fixture"}])
            result = build_six_country_corpus(root / "speeches.jsonl", sample_size=1)
            self.assertEqual(len(list(iter_jsonl(root / "speeches.jsonl"))), 6)
            self.assertEqual(result["sample_records"], 6)
            self.assertEqual(set(result["country_sha256"]), {
                "Germany", "France", "Netherlands", "Italy", "Spain", "Poland"})
            self.assertTrue(result["source_gap_free"])
            self.assertFalse(result["paid_inference_ready"])
            self.assertIn("paid processing approval is absent", result["paid_inference_blockers"])
            self.assertTrue((root.parent / "manifests/combined_corpus.json").is_file())
            gap = root.parent / "manifests/spain_unavailable_journals.json"
            write_jsonl(gap, [{"term": 14, "number": 59}])
            blocked = build_six_country_corpus(root / "speeches.jsonl", sample_size=1)
            self.assertFalse(blocked["paid_inference_ready"])
            self.assertIn("Spain", blocked["unresolved_source_gaps"])

    def test_processing_approval_requires_source_processor_and_transfer_review(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "approval.json"
            path.write_text(json.dumps({"approved": True}), encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "source_terms_reviewed"):
                validate_processing_approval(path)
            approval = {
                "approved": True,
                "approved_by": "Research owner",
                "approved_at_utc": "2026-09-24T12:00:00+00:00",
                "scope": "Pangram API processing for the six-country corpus",
                "source_terms_reviewed": True,
                "processor_terms_reviewed": True,
                "international_transfer_reviewed": True,
            }
            path.write_text(json.dumps(approval), encoding="utf-8")
            self.assertEqual(validate_processing_approval(path), approval)

    def test_paid_mode_requires_processing_approval_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            corpus = base / "covered.jsonl"
            records = [{"country": country, "date": f"{year}-01-01",
                        "word_count": 40, "speech_id": f"{country}-{year}",
                        "speech_text": "text " * 40, "source_identifier": "s",
                        "source_url": "https://example.test/s"}
                       for country in ("Germany", "France", "Netherlands", "Italy", "Spain", "Poland")
                       for year in range(2018, 2026)]
            write_jsonl(corpus, records)
            (base / "gaps.json").write_text("[]\n", encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "requires an approval record"):
                run_pipeline(corpus=corpus, results_dir=base / "out", dry_run=False,
                             confirm_paid_run=True, api_key="fake-key", model="pangram-4",
                             price_per_1000_words=0.5, gap_reports=base / "gaps.json",
                             processing_approval=base / "missing-approval.json")
            self.assertFalse((base / "out/raw_pangram").exists())

    def test_paid_mode_refuses_incomplete_corpus_before_any_network_call(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            corpus = base / "only-one-country.jsonl"
            write_jsonl(corpus, [{"country": "France", "date": "2024-01-01", "word_count": 40,
                                 "speech_id": "one", "speech_text": "Bonjour " * 40,
                                 "source_identifier": "one", "source_url": "https://example.test/one"}])
            with self.assertRaisesRegex(ValueError, "country/year coverage"):
                run_pipeline(corpus=corpus, results_dir=base / "out", dry_run=False,
                             confirm_paid_run=True, api_key="fake-key", model="pangram-4",
                             price_per_1000_words=0.5,
                             gap_reports=base / "missing-gaps.json")
            self.assertFalse((base / "out/raw_pangram").exists())

    def test_paid_mode_rejects_recorded_source_gaps_after_coverage_check(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            corpus = base / "covered.jsonl"
            records = [{"country": country, "date": f"{year}-01-01",
                        "word_count": 40, "speech_id": f"{country}-{year}",
                        "speech_text": "text " * 40, "source_identifier": "s",
                        "source_url": "https://example.test/s"}
                       for country in ("Germany", "France", "Netherlands", "Italy", "Spain", "Poland")
                       for year in range(2018, 2026)]
            write_jsonl(corpus, records)
            gaps = base / "gaps.json"
            write_jsonl(gaps, [{"term": 12, "number": 162}])
            with self.assertRaisesRegex(ValueError, "unresolved official source gaps"):
                run_pipeline(corpus=corpus, results_dir=base / "out", dry_run=False,
                             confirm_paid_run=True, api_key="fake-key", model="pangram-4",
                             price_per_1000_words=0.5, gap_reports=gaps)
            self.assertFalse((base / "out/raw_pangram").exists())

    def test_mock_dry_run_creates_outputs_for_all_six_countries(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = run_pipeline(
                corpus=None, results_dir=Path(directory), dry_run=True,
                price_per_1000_words=0.5, model="pangram-4")
            self.assertTrue(summary["synthetic_smoke_test"])
            self.assertEqual(len(summary["countries"]), 6)
            for relative in (
                "tables/corpus_size.csv", "tables/annual_results.csv",
                "tables/cost_estimate.csv", "tables/sensitivity.csv", "figures/all_countries.svg",
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


class PositiveControlTests(unittest.TestCase):
    def _record(self, **overrides):
        record = {"country": "Spain", "text_language": "es", "generator": "test-llm",
                  "prompt_id": "p1", "text": "Señor Presidente, esta enmienda mejora el texto."}
        record.update(overrides)
        return record

    def test_normalization_labels_a_passage_as_synthetic_and_strips_source_fields(self):
        record = normalize_record(self._record(), 0)
        self.assertTrue(record["synthetic_control"])
        self.assertEqual(record["source_type"], "synthetic_positive_control")
        self.assertTrue(record["speech_id"].startswith("positive-control-es-"))
        self.assertEqual(record["parliament"], "Congreso de los Diputados")

    def test_validation_rejects_missing_fields_and_official_looking_records(self):
        with self.assertRaises(ValueError):
            normalize_record(self._record(generator=""), 0)
        with self.assertRaises(ValueError):
            normalize_record(self._record(text_language="fr"), 0)
        with self.assertRaises(ValueError):
            normalize_record(self._record(source_url="https://example.test/official"), 0)
        with self.assertRaises(ValueError):
            normalize_record(self._record(country="Belgium"), 0)

    def test_import_writes_every_supplied_passage_and_load_revalidates(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "raw.jsonl", Path(directory) / "controls.jsonl"
            write_jsonl(source, [self._record(), self._record(prompt_id="p2")])
            records = import_controls(source, output)
            self.assertEqual(len(records), 2)
            self.assertEqual(len(load_controls(output)), 2)

    def test_evaluation_reports_detection_rate_per_language(self):
        controls = [normalize_record(self._record(prompt_id="p1"), 0),
                    normalize_record(self._record(prompt_id="p2", country="Poland",
                                                   text_language="pl"), 1)]
        responses = {control["speech_id"]: {"fraction_ai": 0.9, "fraction_ai_assisted": 0.05}
                     for control in controls}
        rows, summary = evaluate_positive_controls(
            controls, lambda control: responses[control["speech_id"]])
        self.assertEqual(len(rows), 2)
        self.assertEqual([group["country"] for group in summary], ["Poland", "Spain"])
        for group in summary:
            self.assertEqual(group["detection_rate"], 1.0)
            self.assertAlmostEqual(group["mean_ai_fraction"], 0.9)

    def test_dry_run_writes_a_positive_control_table_when_controls_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            controls = base / "positive_controls.jsonl"
            write_jsonl(controls, [self._record()])
            corpus = base / "corpus.jsonl"
            write_jsonl(corpus, [{
                "country": "Germany", "parliament": "Bundestag", "chamber": "lower",
                "date": "2024-01-01", "session_id": "1", "speech_id": "s1",
                "speaker_id": "m1", "speaker_name": "Test", "speech_text": "Hallo Welt",
                "word_count": 2, "source_identifier": "s1",
                "source_url": "https://example.test/s1"}])
            summary = run_pipeline(corpus=corpus, results_dir=base / "out", dry_run=True,
                                   price_per_1000_words=0.5, model="pangram-4",
                                   positive_controls=controls)
            self.assertTrue(summary["positive_controls"]["prepared"])
            self.assertTrue((base / "out/tables/positive_controls.csv").is_file())
            self.assertTrue((base / "out/reports/positive_controls.json").is_file())


class SourceBoundaryReviewTests(unittest.TestCase):
    def test_normalize_handles_punctuation_spacing_from_inline_markup(self):
        self.assertEqual(normalize("De  voorzitter : Geen steun."),
                         normalize("De voorzitter: Geen steun."))

    def test_containment_statuses_distinguish_cleaning_from_boundary_errors(self):
        source = ("La señora presidenta: señorías, por favor, guarden silencio. "
                  "(rumores). respeten a quien tiene la palabra y que los "
                  "diputados guarden el orden.")
        # The parser removes the inline "(rumores)" cue, so strict containment
        # fails even though every segment of the record is present.
        record = ("señorías, por favor, guarden silencio. respeten a quien "
                  "tiene la palabra y que los diputados guarden el orden.")
        self.assertEqual(containment_status("guarden silencio.", source), "verified")
        self.assertEqual(containment_status(record, source), "partial")
        self.assertEqual(containment_status("Je n’ai pas souvenir.", "Je n'ai pas souvenir."),
                         "normalized")
        self.assertEqual(containment_status(
            "una frase que no aparece en ninguna parte de la fuente oficial",
            source), "mismatch")

    def test_sampling_is_deterministic_balanced_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "c.jsonl"
            rows = []
            for year in (2018, 2021, 2024):
                for index in range(8):
                    rows.append({"country": "Germany", "date": f"{year}-05-{index + 1:02d}",
                                 "speech_id": f"de-{year}-{index}", "speech_text": "x" * 90,
                                 "word_count": 90})
            write_jsonl(corpus, rows)
            first = sample_records(corpus, "Germany", 6, 2026)
            second = sample_records(corpus, "Germany", 6, 2026)
            self.assertEqual([row["speech_id"] for row in first],
                             [row["speech_id"] for row in second])
            self.assertEqual(len(first), 6)
            self.assertEqual({row["date"][:4] for row in first}, {"2018", "2021", "2024"})
            self.assertEqual(sample_records(corpus, "France", 5, 2026), [])


if __name__ == "__main__":
    unittest.main()
