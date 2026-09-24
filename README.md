# European Parliamentary AI-Writing Study

This repository is the engineering workspace for a comparative study of AI-classified text in six European lower chambers: the German Bundestag, French Assemblée nationale, Dutch Tweede Kamer, Italian Camera dei deputati, Spanish Congreso de los Diputados, and Polish Sejm.

Research question: How has the prevalence of AI-generated or AI-assisted text in parliamentary interventions changed since widespread generative AI, and how does it compare across major European legislatures?

The project is motivated by The Economist's September 2026 article, “AI-written speeches are taking over politics.” The article's public page confirms its headline and topic, but the article body, source notes, detector configuration, and calculation methods have not been recovered. This is therefore a comparative extension, not an exact replication. See [the reconstruction ledger](docs/economist_replication.md).

## Current status — be precise

- RESEARCH RECONNAISSANCE: partial; primary Economist method disclosure is still inaccessible
- FRANCE ARCHIVE COLLECTION: downloaded the official 15th, 16th, and 17th-legislature Syceron XML archives
- FRANCE PARSING/NORMALIZATION: 1,243,388 intervention records and 75,364,490 words processed for 2018–2026 material through 2026-07-21; raw/processed archives remain local and Git-ignored
- FRANCE QA: 0 duplicate speech IDs, 0 empty records, and 0 missing provenance fields in the streamed check; one official webpage sample was manually compared; full manual sampling, text-boundary audit, duplicate-text review, and review of an over-10,000-word record remain outstanding
- POLAND: official API enumeration and per-statement HTML downloader/parser implemented; one 2023-11-13 sitting sample yielded 43 interventions and 19,291 words; the full historical corpus and country QA have not been run
- NETHERLANDS: OData final-report adapter/parser implemented; one corrected 2025-03-19 plenary report yielded 308 interventions and 55,561 words; full historical acquisition and country QA have not been run ([sample QA](docs/netherlands_sample_qa.md))
- ITALY: explicit-sitting HTML downloader/parser implemented; one 2026-09-18 sitting yielded 47 interventions and 1,808 words; full session index and historical corpus are not ready ([sample QA](docs/italy_sample_qa.md))
- GERMANY, SPAIN: no complete acquisition/parser adapter yet
- PANGRAM CLIENT: async task client, request fingerprint cache, resume state, opt-in paid-run guard, and mocked tests implemented; no live request made
- COST CONTROL: configurable estimator implemented; default Pangram 4 price is an estimate from the current public developer page, not an account quote
- ANALYSIS: aggregation, tables, SVG figures, and report generation implemented; exercised on synthetic smoke data only
- FULL INFERENCE: NOT RUN; no paid API call was made

The API key is not the only blocker: five country corpora, cross-country acquisition and parsing, complete validation, and manual review remain unfinished. Do not cite mock outputs as research findings. Detailed French counts, coverage, and known anomalies are in [docs/corpus_qa.md](docs/corpus_qa.md).

## Run the verified smoke workflow

Python 3.11 or later; no third-party runtime packages are required.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
./run_experiment.sh --dry-run
```

The dry run is deterministic and never contacts Pangram. With no corpus present, it creates an explicitly synthetic six-country test fixture and exercises QA, cost estimation, aggregation, CSV tables, SVG figures, machine-readable mock results, and a report under `results/`. The generated test corpus is not parliamentary data and must not be treated as detector evidence.

Run tests with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Cost estimate and paid-run guard

The Pangram 4 public developer page currently advertises $0.05 per 100 words (equivalent to $0.50 per 1,000 words); Pangram 3 is advertised at a different rate. The code's default rate is a planning assumption for Pangram 4 and is configurable. Confirm the current plan, model access, and billing terms with Pangram before a paid run. The public page also advertises bulk pricing; this repository does not assume eligibility for it.[3]

After a normalized JSONL corpus exists, estimate cost without inference:

```bash
./run_experiment.sh --estimate-only --corpus data/processed/speeches.jsonl
./run_experiment.sh --estimate-only --corpus data/processed/speeches.jsonl --country Germany --year 2024
```

To configure access, copy `.env.example` to `.env` and set `PANGRAM_API_KEY`; `.env` is ignored by Git. The real pipeline refuses to submit without the explicit `--confirm-paid-run` flag:

```bash
./run_experiment.sh --corpus data/processed/speeches.jsonl --confirm-paid-run
```

This command currently requires a corpus prepared by acquisition code; the six-country automatic corpus build is not complete. Never use the paid flag until corpus QA and the estimate are reviewed. Completed responses are cached under a text-plus-configuration SHA-256 key. Ambiguous POST outcomes are marked and not automatically resubmitted, to reduce duplicate billing risk.

## Method and data

The observation is intended to be an individually attributed substantive plenary intervention, preserving source-language text. Do not translate before detection. AI-generated and AI-assisted classifications are distinct; the primary word share uses Pangram segment word counts where returned, falling back to the returned text fractions only if segment word counts are absent. Historical texts (2018–2021) are calibration controls, not ground truth. A detector label does not establish that a named member personally used AI; staff may draft speeches. Method choices and uncertainties are recorded in [docs/methodology.md](docs/methodology.md), [docs/data_sources.md](docs/data_sources.md), and [docs/limitations.md](docs/limitations.md).

## Output and data policy

Source licenses and terms must be reviewed before redistribution or paid processing. French raw archives and four processed JSONL files exist locally, are excluded from Git, and are inventoried by checksums in `data/manifests/source_manifest.jsonl`; their counts and integrity caveats are in `docs/corpus_qa.md`. France-only corpus statistics are not six-country research results.

## Repository status

This is an active research-engineering project, not a completed empirical study. The French source-corpus size is documented, but there is no six-country corpus and no detector-based evidence about AI adoption rates in any of the six chambers. The research-credit status summary is in [docs/pangram_research_request.md](docs/pangram_research_request.md) and intentionally documents the unfinished corpus work rather than claiming the six-country study is ready.
