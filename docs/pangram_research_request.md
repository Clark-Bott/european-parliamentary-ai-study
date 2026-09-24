# Pangram research-credit request summary

## Research question

How has the prevalence of AI-generated or AI-assisted text in parliamentary interventions changed since widespread generative AI, and how does it compare across major European legislatures?

The project was inspired by The Economist's September 2026 article “AI-written speeches are taking over politics.” Its public page and accessible metadata establish the topic, but its detailed methodology, source notes, and detector configuration have not been recovered. This project is a transparent comparative extension, not an exact replication.[1][17]

## Countries and work completed

The target chambers are the Bundestag (Germany), Assemblée nationale (France), Tweede Kamer (Netherlands), Camera dei deputati (Italy), Congreso de los Diputados (Spain), and Sejm (Poland).

The French official Syceron archives for legislatures 15–17 have been acquired, ZIP-tested, parsed, and normalized locally for 2018-01-16 through 2026-07-21: 1,243,388 records and 75,364,490 words. A streaming integrity check found no duplicate speech IDs, empty text, or missing provenance fields. One record over 10,000 words remains under review; only one official-page speaker/date/text-boundary spot check has been completed. The raw and processed corpora are not committed to Git; checksums, counts, parser details, and caveats are documented in the repository.[6][7][8]

Official API ingestion/parser code also exists for Sejm statement bodies and Tweede Kamer final corrected plenary reports; an explicit-sitting Camera HTML parser is also implemented. Live sample retrievals produced 43 Polish interventions / 19,291 words from one sitting day, 308 Dutch interventions / 55,561 words from one corrected sitting report, and 47 Italian interventions / 1,808 words from one sitting. These are samples, not full national corpora. Germany and Spain remain reconnaissance-only; Italy's session index and full historical corpus are not yet ready.[9][15][16][18][19][20][22][23]

The repository includes a canonical multilingual speech schema, source downloader with SHA-256 manifests, general integrity checks, a deterministic historical-control sampler (with a French 1,000-record sample generated locally), a Pangram asynchronous task client, content/configuration-addressed caching, retry/poll handling, ambiguous-submission protection, cost estimation, an explicit paid-run authorization flag, and analysis/output generation. The test suite and one-command synthetic dry run pass. No Pangram inference has been run.[2]

## Proposed inference scope and estimated cost

The current transparent baseline eligibility threshold is 40 words; it is a study design choice, not a reconstructed Economist filter. Of the collected French records, 393,480 pass that length threshold, containing 66,375,086 words. Pangram's public developer page lists Pangram 4 at $0.05 per 100 words (equivalent to $0.50 per 1,000 words), yielding a preliminary France-only list-price estimate of $33,187.54. Pricing, billing granularity, model availability, account terms, and discounts must be reconfirmed before submission.[3]

A defensible six-country total cannot yet be quoted: full collections for the remaining chambers are not complete. Credits sufficient for the French corpus would enable a first language-specific pilot; access for the planned cross-country experiment would require estimating all six corpora after acquisition and validation. The repository's estimator is configurable and will calculate the actual selected corpus once prepared.

## What Pangram access would enable

Once the remaining corpora and country QA are complete, research credits/API access would enable original-language, per-intervention detection without translation; caching/resumable inference; AI-only and AI-assisted word-share estimation; language-specific 2018–2021 historical detector baselines; sensitivity analyses; and reproducible country/time-series tables and figures. Outputs will describe detector classifications, not assert that individual politicians personally used AI. Parliamentary staff may draft speeches, and a detector result is not proof of authorship.[2]

## Current blockers

This is not yet a claim that “the dataset, methodology, API integration, and analysis pipeline are all built.” France is the only chamber with a full parsed corpus; two more have sample adapters, and three do not yet have complete source pipelines. Full cross-country QA, licensing/reuse review, and random source-boundary validation remain necessary in every country. Pangram API access is intentionally not used during development; the dry-run uses clearly labeled synthetic fixtures only.
