# Pangram research-credit request summary

## Research question

How has the prevalence of AI-generated or AI-assisted text in parliamentary interventions changed since widespread generative AI, and how does it compare across major European legislatures?

The project was inspired by The Economist's September 2026 article “AI-written speeches are taking over politics.” Its public page and accessible metadata establish the topic, but its detailed methodology, source notes, and detector configuration have not been recovered. This project is a transparent comparative extension, not an exact replication.[1][17]

## Countries and work completed

The target chambers are the Bundestag (Germany), Assemblée nationale (France), Tweede Kamer (Netherlands), Camera dei deputati (Italy), Congreso de los Diputados (Spain), and Sejm (Poland).

The official French Syceron archives for legislatures 15–17 were acquired and ZIP-tested again locally. A current parser run for 2018-01-16 through 2026-07-21 emitted **1,243,606 records / 75,392,623 words**; a disk-backed audit found zero duplicate IDs, empty/mismatched records, missing provenance, or invalid dates, but 389,687 repeated text hashes (mostly formulaic short turns). These archives have the same SHA-256 hashes as the earlier run, which reported 1,243,388 / 75,364,490; the discrepancy remains under investigation. One >10,000-word intervention remains under review; only one official-page boundary comparison is documented. Raw and processed corpora are excluded from Git.[6][7][8]

Official source adapters now exist for all six chambers. Live sample retrievals produced 43 Polish interventions / 19,291 words from one day; 308 Dutch turns / 55,561 words from one corrected report; 47 Italian XML interventions / 15,203 words from one sitting; 190 German XML turns / 43,805 words from one sitting; and 134 Spanish Diario turns / 53,459 words from one journal. The earlier Italian HTML-only extraction of 1,808 words was incomplete and has been replaced. These are source/parser samples, not complete 2018–2026 national corpora. Full acquisition attempts are underway for four chambers; the German attempt stopped at an official verification challenge, and Spanish numbered-journal gaps need review. The earlier 90,706-record Dutch build used incomplete OData pagination and is being replaced. Randomized validation has not been performed.[9][15][16][18][19][20][22][23]

The repository includes a canonical multilingual speech schema, source downloader with SHA-256 manifests, general integrity checks, a deterministic historical-control sampler (with a French 1,000-record sample generated locally), a Pangram asynchronous task client, content/configuration-addressed caching, retry/poll handling, ambiguous-submission protection, cost estimation, an explicit paid-run authorization flag, and analysis/output generation. The test suite and one-command synthetic dry run pass. No Pangram inference has been run.[2]

## Proposed inference scope and estimated cost

The transparent eligibility threshold is 40 words; it is a study choice, not an Economist filter. In the current local French rebuild, **393,565 records / 66,401,901 words** pass that threshold. Pangram lists Pangram 4 at $0.05 per **started 100-word block per speech**. The code counts **847,941 units**, projecting **$42,397.05 France-only list price** at the stated rate. The older $33,187.54 unrounded figure was a lower bound, not a payable estimate. Actual API cost also depends on redundant identical-text cache hits, model entitlement, contract, and discounts. This is not a six-country quote.[3]

Separate local Italian, Dutch, and Spanish corpora have 120,839, 193,384, and 50,021 length-eligible records, respectively; their list-price estimates are **$26,924.80**, **$26,680.00**, and **$14,813.10**. Their full-file integrity checks passed, but source-boundary and rights review remain. The Dutch 919-meeting listing versus 903 parsed reports is unresolved, and two Spanish journals have PDF records but no usable HTML. A defensible six-country total cannot yet be quoted: Germany, Spain, and Poland are not yet complete or gap-free. Credits sufficient for one reviewed language-specific pilot would not fund the planned cross-country experiment. The repository's estimator is configurable and will calculate the selected corpus once prepared.

## What Pangram access would enable

Once the remaining corpora and country QA are complete, research credits/API access would enable original-language, per-intervention detection without translation; caching/resumable inference; AI-only and AI-assisted word-share estimation; language-specific 2018–2021 historical detector baselines; sensitivity analyses; and reproducible country/time-series tables and figures. Outputs will describe detector classifications, not assert that individual politicians personally used AI. Parliamentary staff may draft speeches, and a detector result is not proof of authorship.[2]

## Current blockers

This is **not yet** a claim that “the dataset, methodology, API integration, and analysis pipeline are all built.” France, Italy, and the Netherlands have local parsed corpora and disk-backed integrity audits, not source-coverage sign-offs. Germany is blocked by an official verification challenge; Spain has numbered-journal gaps; Poland is still downloading. Full cross-country acquisition, quality review, licensing/third-party processing review, and random source-boundary validation remain necessary. Pangram API access was intentionally not used; the default dry run uses clearly labeled synthetic fixtures only.
