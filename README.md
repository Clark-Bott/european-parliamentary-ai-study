# European Parliamentary AI-Writing Study

This repository is the engineering workspace for a comparative study of AI-classified text in six European lower chambers: the German Bundestag, French Assemblée nationale, Dutch Tweede Kamer, Italian Camera dei deputati, Spanish Congreso de los Diputados, and Polish Sejm.

Research question: How has the prevalence of AI-generated or AI-assisted text in parliamentary interventions changed since widespread generative AI, and how does it compare across major European legislatures?

The project is motivated by The Economist's September 2026 article, “AI-written speeches are taking over politics.” The article's public page confirms its headline and topic, but the article body, source notes, detector configuration, and calculation methods have not been recovered. This is therefore a comparative extension, not an exact replication. See [the reconstruction ledger](docs/economist_replication.md).

## Current status — be precise

```text
DATA COLLECTION:        IN PROGRESS — five official corpora collected and built locally; Poland acquisition running; post-2026-09-19 German XML blocked by Enodia verification
PARSING:                COMPLETE for Germany, France, Netherlands, Italy, Spain; Poland parser implemented, full build pending
NORMALIZATION:          COMPLETE for the five built corpora; common schema, source URLs, and source-language text retained
VALIDATION:             PARTIAL — automated full-file integrity QA passed for all five built corpora, and automated source-boundary screening found 0 mismatches in 10 sampled records per country; human sample reading still outstanding
PANGRAM INTEGRATION:    COMPLETE — client, fingerprint cache, resume, duplicate-billing and paid-run guards, mocked tests
ANALYSIS PIPELINE:      COMPLETE — tables, figures, sensitivity and control analyses implemented and exercised on mocked detector output
FULL PANGRAM INFERENCE: NOT RUN — blocked by API key, recorded source gaps, coverage completion, and rights/approval review
```

- RESEARCH RECONNAISSANCE: substantially advanced 2026-09-24; the article body was recovered through a syndicated reprint, which confirms Pangram as the detector and a word-weighted UK headline metric; the Pangram model, thresholds, date range, speech definition, and any source note, code, or data release remain unavailable, so this stays a comparative extension, not a replication ([ledger](docs/economist_replication.md))
- FRANCE ARCHIVE COLLECTION: official 15th–17th legislature Syceron ZIPs were downloaded and checksum-verified locally; they are not in Git and must be downloaded in a fresh clone
- FRANCE PARSING/NORMALIZATION: current local rebuild emitted 1,243,606 intervention records / 75,392,623 words through 2026-07-21; disk-backed full-file audit passed, but found 389,687 repeated text hashes, mostly formulaic short turns. Random source-boundary QA remains outstanding.
- FRANCE QA: 0 duplicate speech IDs, 0 empty records, and 0 missing provenance fields in the streamed check; one official webpage sample was manually compared; full manual sampling, text-boundary audit, duplicate-text review, and review of an over-10,000-word record remain outstanding
- HISTORICAL CONTROL: deterministic 2018–2021 samples now exist locally for Germany, France, Italy, Spain, and the Netherlands. The Dutch sample contains 658 rather than 1,000 records because the strict speaker cap could not fill the quota. No Poland sample exists yet ([method and QA](docs/historical_controls.md))
- POLAND: official API enumeration and per-statement HTML downloader/parser implemented; one 2023-11-13 sitting sample yielded 43 interventions and 19,291 words; the full historical corpus and country QA have not been run
- NETHERLANDS: the corrected-pagination build emitted 344,220 records / 46,237,076 words from 903 reports; disk-backed integrity QA passed. A live coverage audit exactly matches all 903 active corrected/rectified final reports. The other 16 OData rows are one verified 2020 duplicate plus 15 post-2026-06-25 provisional-only meetings, not missing historical transcripts ([build QA](docs/netherlands_corpus_qa.md); [sample QA](docs/netherlands_sample_qa.md)).
- ITALY: official XML adapter across terms 17–19; a local full-builder run emitted 262,716 records / 49,946,554 words from 1,457 sittings. Disk-backed integrity QA passed, but official enumeration, random boundary review, role/short-turn cleaning, and XML reuse terms have not been signed off ([build QA](docs/italy_corpus_qa.md); [sample QA](docs/italy_sample_qa.md)).
- GERMANY: verified CC0 CPP-BT 2026-09-19 baseline emitted 64,796 records / 32,514,063 words, including 5,607 records through 2026-09-19; disk-backed integrity QA passed. The official XML supplement after the archive cutoff is blocked by Enodia verification and remains a recorded paid-run gap. Random source-boundary review is outstanding ([build QA](docs/germany_corpus_qa.md); [sample QA](docs/germany_sample_qa.md)).
- SPAIN: official Diario build emitted 101,069 records / 28,139,144 words from 583 journals, including 252 and 148 turns recovered from two official PDF-only journals with the pypdf fallback; page-boundary regression and disk-backed integrity QA passed. Speaker/party enrichment and random source-boundary review remain outstanding ([build QA](docs/spain_corpus_qa.md); [sample QA](docs/spain_sample_qa.md)).
- SIX-COUNTRY BUILD: acquisition adapters and a combined-corpus builder exist; the full 2018–2026 acquisition and random manual QA have **not** been completed. An earlier Dutch 90,706-record build was incomplete because the OData server omitted a pagination link; explicit skip pagination is implemented, but that file must not be used as complete. Spanish numbered-journal gaps are recorded and block paid submission.
- SOURCE-BOUNDARY SCREENING: a deterministic 10-record sample per built country was checked against its official source (live URL for Italy, the Netherlands, and Spain; the local official archives for Germany and France). All 50 records were located: 39 verbatim, 8 after punctuation folding, 3 partial because cleaning had removed inline cues or page markers, **0 mismatches**, 0 skipped. Method, statuses, and limits: [docs/source_boundary_verification.md](docs/source_boundary_verification.md). This is a screening sample, not the human Phase 4 sign-off; 25-record review packets per country are generated under `data/interim/review_packets/` (Git-ignored).
- PANGRAM CLIENT: client for Pangram's asynchronous task API (synchronous POST plus polling), request fingerprint cache, resume state, opt-in paid-run guard, and mocked tests implemented; no live request made
- COST CONTROL: per-item rounded estimator implemented; local length-eligible estimates are **$42,397.05** for France, **$17,802.00** for Germany, **$26,924.80** for Italy, **$26,680.00** for the reconciled Dutch corpus, and **$14,862.70** for the Spanish corpus including PDF fallbacks. None is an account quote or a validated six-country total.
- POSITIVE CONTROLS: optional Phase 8 design implemented — per-language generation briefs, validation that keeps synthetic text out of real corpora, cached submission, and a per-language detection table. No passages generated yet ([method](docs/positive_controls.md))
- ANALYSIS: aggregation, tables, SVG figures, and report generation implemented; exercised on synthetic smoke data only
- FULL INFERENCE: NOT RUN; no paid API call was made

The API key is **not** the only blocker: post-cutoff German XML, the full Polish acquisition, full six-country coverage validation, licensing/third-party processing review, and random manual boundary audits remain unfinished. A guard prevents paid submission when any country/year is missing, a recorded German source gap remains, or processing approval is absent. Spain's two PDF-only journals are now covered, but its source terms still require review. Do not cite mock outputs as research findings. Detailed earlier French counts and anomalies are in [docs/corpus_qa.md](docs/corpus_qa.md).

## Run the verified smoke workflow

Python 3.11 or later. The only runtime dependency is `pypdf==6.1.1`, used for the two Spain PDF fallback journals. The launcher uses the project environment through `uv` when available, then falls back to an explicit `.venv`.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e .
./run_experiment.sh --dry-run
```

The default dry run is deterministic and never contacts Pangram. With no combined corpus present, it creates an explicitly synthetic six-country test fixture and exercises QA, cost estimation, aggregation, CSV tables, SVG figures, machine-readable mock results, and a report under `results/`. **This is a software smoke test, not an end-to-end run on six real corpora.** To acquire every official corpus before a real-corpus dry run, use `./run_experiment.sh --build-corpus --dry-run`. This can download many files and may take a long time. To acquire without analysis, use `uv run --python 3.12 python -m parliament_ai_study.sources.build` after installation. Individual adapters: `uv run --python 3.12 python -m parliament_ai_study.sources.cli Germany` (also France, Netherlands, Italy, Spain, Poland). After all acquisition processes stop, reconcile checksums and inferred source URLs with `uv run --python 3.12 python -m parliament_ai_study.provenance --resolve-germany`; unresolved URLs are reported rather than guessed.

Run tests with:

```bash
uv run --python 3.12 python -m unittest discover -s tests -v
```

## Cost estimate and paid-run guard

The Pangram 4 developer page advertises $0.05 per **started 100-word block per item**, with a minimum one block per eligible speech. Two 101-word speeches cost four blocks, not 2.02 blocks. The default $0.50 / 1,000 words is configurable. Confirm current plan, model access, and billing terms before a paid run. The public page advertises bulk discounts; this task-based client does not assume them.[3]

After a normalized JSONL corpus exists, estimate cost without inference:

```bash
./run_experiment.sh --estimate-only --corpus data/processed/speeches.jsonl
./run_experiment.sh --estimate-only --corpus data/processed/speeches.jsonl --country Germany --year 2024
```

To configure access, copy `.env.example` to `.env` and set `PANGRAM_API_KEY`; `.env` is ignored by Git. The real pipeline refuses to submit without the explicit `--confirm-paid-run` flag:

```bash
./run_experiment.sh --corpus data/processed/speeches.jsonl --confirm-paid-run
```

If the combined corpus is missing, this command attempts to acquire and normalize all six chambers first. It rejects missing country/year coverage, non-empty German or Spanish source-gap reports, and a missing/incomplete `data/manifests/paid_processing_approval.json`. That approval must record human review of source terms, Pangram's processor terms, and international transfers. `--max-cost 500` adds an independent ceiling: the run aborts before the first request if the estimate exceeds it. The command then checks model access through Pangram's read-only `/models` endpoint. **Do not create the approval or use the paid flag until the items in [the rights and processing review](docs/rights_and_processing_review.md) are complete.** Completed responses are cached under a text-plus-configuration SHA-256 key. Ambiguous POST outcomes are marked and not automatically resubmitted; [docs/pangram_operations.md](docs/pangram_operations.md) documents resume, error logs, and the reset procedure. An inaccessible source or unresolved format change still requires engineering; the key alone is not sufficient today. For a real corpus, the pipeline replays the JSONL file for QA, costing, analysis, and output instead of loading every record into memory; paid responses are reloaded from the cache for analysis.

## Method and data

The observation is intended to be an individually attributed substantive plenary intervention, preserving source-language text. Do not translate before detection. AI-generated and AI-assisted classifications are distinct; the primary word share uses Pangram segment word proportions where returned, scaled to the source Unicode word denominator to accommodate Pangram normalization. Historical texts (2018–2021) are calibration controls, not ground truth. A detector label does not establish that a named member personally used AI; staff may draft speeches. Method choices and uncertainties are recorded in [docs/methodology.md](docs/methodology.md), [docs/data_sources.md](docs/data_sources.md), and [docs/limitations.md](docs/limitations.md).

## Output and data policy

Source licenses and terms must be reviewed before redistribution or paid processing. Raw archives and derived JSONL are excluded from Git. The manifests document verified local French, German, Italian, Dutch, and Spanish builds; a new clone must reacquire them. Country-level historical corpus statistics are not six-country research results.

## Repository status

This is an active research-engineering project, not a completed empirical study. Five country-level corpora have local builds, but the combined corpus is not validated, Germany retains a post-cutoff source gap, Spain still needs source-boundary and rights review, and Poland is still acquiring. There is no detector-based evidence about AI adoption rates in any chamber. The research-credit status summary is in [docs/pangram_research_request.md](docs/pangram_research_request.md) and intentionally documents the unfinished corpus work rather than claiming the six-country study is ready.
