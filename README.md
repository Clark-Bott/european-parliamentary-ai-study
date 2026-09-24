# European Parliamentary AI-Writing Study

A reproducible research pipeline to measure changes in detected AI-written and AI-assisted text across six European chambers: the German Bundestag, French Assemblée nationale, Dutch Tweede Kamer, Italian Camera dei deputati, Spanish Congreso de los Diputados, and Polish Sejm.

## Research question

How has the prevalence of AI-generated or AI-assisted text in parliamentary speeches changed since the widespread introduction of generative AI, and how does it compare across major European legislatures?

The project is motivated by *The Economist*'s September 2026 coverage of AI-written parliamentary speeches. A metadata mirror identifies the story as “AI-written speeches are taking over politics” and describes British MPs as avid users, with Australia and Canada above them; this repository does not treat that brief metadata as a complete methods disclosure.[1] The replication evidence and unresolved methodological questions are in [`docs/economist_replication.md`](docs/economist_replication.md).

## Status

**Research reconnaissance and repository scaffolding only.** No six-country corpus has yet been fully downloaded, parsed, or validated, and no Pangram inference has been run. Country-level acquisition adapters, tests, analysis, and executable workflows are under construction. See [`docs/data_sources.md`](docs/data_sources.md) for what has been verified versus what remains open.

| Workstream | Current status |
|---|---|
| Article/method reconstruction | Partial; source-method details not independently available yet |
| Official source discovery | Initial reconnaissance completed; coverage and reuse terms vary |
| Six-country acquisition and parsing | Not complete |
| Normalized corpus and QA | Not complete |
| Pangram client and cost control | Not implemented |
| Analysis and outputs | Not implemented |
| Full inference | Intentionally not run; no paid calls authorized |

## Method and cautions

The unit of analysis is intended to be a substantive speaker intervention in the source language. Text will not be translated before detection. A Pangram classification is detector evidence, not proof that a named member personally used AI; speechwriting may involve staff, editors, or collaboration. We will report AI-generated and mixed/assisted classifications separately unless a sourced replication method requires another treatment. Historical texts are calibration controls, not an unquestioned ground truth.

See [`docs/data_sources.md`](docs/data_sources.md), [`docs/methodology.md`](docs/methodology.md), and [`docs/limitations.md`](docs/limitations.md). This README's article description is based only on a third-party story metadata mirror, not the inaccessible primary story text.[1]

## Sources

[1] https://biztoc.com/x/d5f103685ea36fdb — Economist story metadata mirror
