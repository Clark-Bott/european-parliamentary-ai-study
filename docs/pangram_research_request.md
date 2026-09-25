# Pangram research-credit request summary

## Research question

How has the prevalence of AI-generated or AI-assisted text in parliamentary interventions changed since widespread generative AI, and how does it compare across major European legislatures?

The project was inspired by The Economist's September 2026 article “AI-written speeches are taking over politics.” A syndicated reprint of the article body confirms that The Economist used Pangram and reported a word-weighted AI share for UK debates, but the Pangram model selector, thresholds, date range, speech definition, and any source note remain unrecovered. This project is a transparent comparative extension, not an exact replication; knowing The Economist's configuration would let us report comparable figures.[25][17]

## Countries and work completed

The target chambers are the Bundestag (Germany), Assemblée nationale (France), Tweede Kamer (Netherlands), Camera dei deputati (Italy), Congreso de los Diputados (Spain), and Sejm (Poland).

The official French Syceron archives for legislatures 15–17 were acquired and ZIP-tested again locally. A current parser run for 2018-01-16 through 2026-07-21 emitted **1,243,606 records / 75,392,623 words**; a disk-backed audit found zero duplicate IDs, empty/mismatched records, missing provenance, or invalid dates, but 389,687 repeated text hashes (mostly formulaic short turns). A controlled pre-role parser rebuild produced exactly the same IDs and text; only 419,188 `speaker_role` values changed. The earlier reported 1,243,388 / 75,364,490 run is therefore an unresolved historical execution discrepancy, not a reproducible parser difference. One >10,000-word intervention remains under review; only one official-page boundary comparison is documented. Raw and processed corpora are excluded from Git.[6][7][8]

Official source adapters exist for all six chambers. Local full-file integrity audits now pass for Germany, France, Italy, the Netherlands, and Spain; these are parser outputs, not source-coverage sign-offs. Germany's verified CC0 CPP-BT 2026-09-19 baseline contains 64,796 speeches (latest sitting 11 September). Earlier official XML retrieval met Enodia verification; ordinary requests to the 23 and 24 September XML succeeded on 25 September, but those records are not yet incorporated and the 24 September listing is marked partial. The corrected Dutch build contains 344,220 records from 903 reports, exactly matching the active corrected/rectified final-report set. Spain's two PDF-only journals are included through a separate pypdf parser with page-boundary regression coverage. Poland is still downloading. Corrected full-file automated source-boundary screening sampled ten records per built country: 38 verbatim, eight after punctuation folding, three partial, and one Spanish automatic mismatch whose turn was located manually in the official source. This small screen is not human country-level QA sign-off; manual review is still needed.[9][15][16][18][19][20][22][23]

The repository includes a canonical multilingual speech schema, source downloader with SHA-256 manifests, general integrity checks, a deterministic historical-control sampler (with local German, French, Italian, Dutch, and Spanish samples), a Pangram asynchronous task client, content/configuration-addressed caching, retry/poll handling, ambiguous-submission protection, cost estimation, an explicit paid-run authorization flag, and analysis/output generation. The test suite and one-command synthetic dry run pass. No Pangram inference has been run.[2]

## Proposed inference scope and estimated cost

The transparent eligibility threshold is 40 words; it is a study choice, not an Economist filter. In the current local French rebuild, **393,565 records / 66,401,901 words** pass that threshold. Pangram lists Pangram 4 at $0.05 per **started 100-word block per speech**. The code counts **847,941 units**, projecting **$42,397.05 France-only list price** at the stated rate. The older $33,187.54 unrounded figure was a lower bound, not a payable estimate. Actual API cost also depends on redundant identical-text cache hits, model entitlement, contract, and discounts. This is not a six-country quote.[3]

Separate local German, Italian, Dutch, and Spanish corpora have 63,834, 120,839, 193,384, and 50,204 length-eligible records, respectively; their list-price estimates are **$17,802.00**, **$26,924.80**, **$26,680.00**, and **$14,862.70**. Their full-file integrity checks passed, but source-boundary and rights review remain. Germany lacks an incorporated, verified final post-archive XML supplement; Spain's PDF fallback is parsed but still needs human boundary and reuse review. The Dutch 903 local report IDs exactly match all active corrected/rectified final reports; no historical transcript is missing. The **five locally built corpora alone** comprise **2,573,331 started 100-word billing units / $128,666.55** at public Pangram 4 list price. This is **not** a complete six-country estimate, an approved submission scope, or an account quote: Poland is incomplete and Germany has a recorded source gap. The repository's estimator will recalculate the actual reviewed scope before any paid run.

## Research-credit application: scope and timing

The [current Pangram research page](https://www.pangram.com/contact-us/research) lists a typical grant of **200,000 credits**, with one credit per 100-word billing unit, extra credits at **$0.025 each**, and expiry after **three months** unless extended. The [API page](https://www.pangram.com/solutions/api) says noncommercial academic projects *may* qualify; applicants should state their true affiliation and intended noncommercial use, not imply automatic eligibility. At list price, 200,000 credits are equivalent to $10,000 and cover only **about 7.8% of the five-country units already measured**, before Poland. Confirm the actual grant's model access, billing, unit rounding, bulk pricing, and start/expiry terms with Pangram; this public-page arithmetic is not a funding offer.

Apply **before** the Polish build finishes if desired. Request either a scoped, cross-language pilot (historical controls plus reviewed contemporary samples) within the standard grant, or discuss a larger allocation and negotiated pricing for the full study. Ask whether the three-month window can begin when validated data and legal approvals are ready, or be extended. The application should disclose the pending Polish acquisition, German post-cutoff gap, human QA, and source/processor rights review. It should **not** claim that an API key alone permits immediate inference. No parliamentary text needs to be uploaded with the inquiry, and no Pangram request has been made.

## What Pangram access would enable

Once the remaining corpora and country QA are complete, research credits/API access would enable original-language, per-intervention detection without translation; caching/resumable inference; AI-only and AI-assisted word-share estimation; language-specific 2018–2021 historical detector baselines; sensitivity analyses; and reproducible country/time-series tables and figures. Outputs will describe detector classifications, not assert that individual politicians personally used AI. Parliamentary staff may draft speeches, and a detector result is not proof of authorship.[2]

## Current blockers

This is **not yet** a claim that “the dataset, methodology, API integration, and analysis pipeline are all built.” Germany, France, Italy, the Netherlands, and Spain have local parsed corpora and disk-backed integrity audits, not complete human source-boundary sign-offs. Germany has an unresolved post-cutoff interval, Spain's PDF fallback is parsed but still needs human boundary and reuse review, and Poland is still downloading. Dutch corrected-final coverage is reconciled. The [rights and processing review](rights_and_processing_review.md) leaves Italy, Spain, Poland, Pangram API retention, and international-transfer terms unresolved; no paid processing approval file exists. Full cross-country acquisition and human quality review remain necessary **before submitting transcripts**, not before requesting credits. Pangram API access was intentionally not used; the default dry run uses clearly labeled synthetic fixtures only.

## Sources

[1] https://biztoc.com/x/d5f103685ea36fdb — Economist story metadata mirror
[2] https://docs.pangram.com/api-reference/ai-detection — Pangram AI Detection API
[3] https://www.pangram.com/pricing?category=developers — Pangram developer pricing
[4] https://www.pangram.com/contact-us/research — research grant terms and inquiry form
[5] https://www.pangram.com/solutions/api — API research-credit eligibility and published rate
[17] https://www.economist.com/britain/2026/09/23/ai-written-speeches-are-taking-over-politics — official article page
[25] https://www.hindustantimes.com/world-news/aiwritten-speeches-are-taking-over-politics-101790241476569.html — syndicated full-text reprint of the article
