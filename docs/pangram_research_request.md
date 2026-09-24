# Pangram research-credit request summary

## Research question

How has the prevalence of AI-generated or AI-assisted text in parliamentary interventions changed since widespread generative AI, and how does it compare across major European legislatures?

The project was inspired by The Economist's September 2026 article “AI-written speeches are taking over politics.” Its public page and accessible metadata establish the topic, but its detailed methodology, source notes, and detector configuration have not been recovered. This project is a transparent comparative extension, not an exact replication.[1][17]

## Countries and work completed

The target chambers are the Bundestag (Germany), Assemblée nationale (France), Tweede Kamer (Netherlands), Camera dei deputati (Italy), Congreso de los Diputados (Spain), and Sejm (Poland).

The official French Syceron archives for legislatures 15–17 were acquired and ZIP-tested again locally. A current parser run for 2018-01-16 through 2026-07-21 emitted **1,243,606 records / 75,392,623 words**; a disk-backed audit found zero duplicate IDs, empty/mismatched records, missing provenance, or invalid dates, but 389,687 repeated text hashes (mostly formulaic short turns). A controlled pre-role parser rebuild produced exactly the same IDs and text; only 419,188 `speaker_role` values changed. The earlier reported 1,243,388 / 75,364,490 run is therefore an unresolved historical execution discrepancy, not a reproducible parser difference. One >10,000-word intervention remains under review; only one official-page boundary comparison is documented. Raw and processed corpora are excluded from Git.[6][7][8]

Official source adapters exist for all six chambers. Local full-file integrity audits now pass for Germany, France, Italy, the Netherlands, and Spain; these are parser outputs, not source-coverage sign-offs. Germany's verified CC0 CPP-BT 2026-09-19 baseline contains 64,796 speeches through 2026-09-19, but official XML after that cutoff remains blocked by verification. The corrected Dutch build contains 344,220 records from 903 reports, exactly matching the active corrected/rectified final-report set. Spain's two PDF-only journals are now included through a separate pypdf parser. Poland is still downloading. Randomized source-boundary validation has not been performed.[9][15][16][18][19][20][22][23]

The repository includes a canonical multilingual speech schema, source downloader with SHA-256 manifests, general integrity checks, a deterministic historical-control sampler (with local German, French, Italian, Dutch, and Spanish samples), a Pangram asynchronous task client, content/configuration-addressed caching, retry/poll handling, ambiguous-submission protection, cost estimation, an explicit paid-run authorization flag, and analysis/output generation. The test suite and one-command synthetic dry run pass. No Pangram inference has been run.[2]

## Proposed inference scope and estimated cost

The transparent eligibility threshold is 40 words; it is a study choice, not an Economist filter. In the current local French rebuild, **393,565 records / 66,401,901 words** pass that threshold. Pangram lists Pangram 4 at $0.05 per **started 100-word block per speech**. The code counts **847,941 units**, projecting **$42,397.05 France-only list price** at the stated rate. The older $33,187.54 unrounded figure was a lower bound, not a payable estimate. Actual API cost also depends on redundant identical-text cache hits, model entitlement, contract, and discounts. This is not a six-country quote.[3]

Separate local German, Italian, Dutch, and Spanish corpora have 63,834, 120,839, 193,384, and 50,197 length-eligible records, respectively; their list-price estimates are **$17,802.00**, **$26,924.80**, **$26,680.00**, and **$14,838.45**. Their full-file integrity checks passed, but source-boundary and rights review remain. Germany lacks a verified post-2026-09-19 XML supplement; Spain's PDF fallback is parsed but still needs random boundary and reuse review. The Dutch 903 local report IDs exactly match all active corrected/rectified final reports; no historical transcript is missing. A defensible six-country total cannot yet be quoted because Germany has a recorded gap, Spain's rights review is unresolved, and Poland is incomplete. Credits sufficient for one reviewed language-specific pilot would not fund the planned cross-country experiment. The repository's estimator is configurable and will calculate the selected corpus once prepared.

## What Pangram access would enable

Once the remaining corpora and country QA are complete, research credits/API access would enable original-language, per-intervention detection without translation; caching/resumable inference; AI-only and AI-assisted word-share estimation; language-specific 2018–2021 historical detector baselines; sensitivity analyses; and reproducible country/time-series tables and figures. Outputs will describe detector classifications, not assert that individual politicians personally used AI. Parliamentary staff may draft speeches, and a detector result is not proof of authorship.[2]

## Current blockers

This is **not yet** a claim that “the dataset, methodology, API integration, and analysis pipeline are all built.” Germany, France, Italy, the Netherlands, and Spain have local parsed corpora and disk-backed integrity audits, not complete random source-boundary sign-offs. Germany has an unresolved post-cutoff interval, Spain has a resolved PDF fallback but still needs random boundary and reuse review, and Poland is still downloading. Dutch corrected-final coverage is reconciled. The [rights and processing review](rights_and_processing_review.md) leaves Italy, Spain, Poland, Pangram API retention, and international-transfer terms unresolved; no paid processing approval file exists. Full cross-country acquisition, quality review, and random source-boundary validation remain necessary. Pangram API access was intentionally not used; the default dry run uses clearly labeled synthetic fixtures only.
