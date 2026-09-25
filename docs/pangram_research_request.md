# Pangram research-credit request summary

For the current three-step inquiry form and ready-to-adapt field entries, see
[the field-by-field application draft](pangram_research_application_form.md).

## Research question

How has the prevalence of AI-generated or AI-assisted text in parliamentary interventions changed since widespread generative AI, and how does it compare across major European legislatures?

The project was inspired by The Economist's September 2026 article “AI-written speeches are taking over politics.” A syndicated reprint of the article body confirms that The Economist used Pangram and reported a word-weighted AI share for UK debates, but the Pangram model selector, thresholds, date range, speech definition, and any source note remain unrecovered. This project is a transparent comparative extension, not an exact replication; knowing The Economist's configuration would let us report comparable figures.[25][17]

## Countries and work completed

The target chambers are the Bundestag (Germany), Assemblée nationale (France), Tweede Kamer (Netherlands), Camera dei deputati (Italy), Congreso de los Diputados (Spain), and Sejm (Poland).

The official French Syceron archives for legislatures 15–17 were acquired and ZIP-tested again locally. A current parser run for 2018-01-16 through 2026-07-21 emitted **1,243,606 records / 75,392,623 words**; a disk-backed audit found zero duplicate IDs, empty/mismatched records, missing provenance, or invalid dates, but 389,687 repeated text hashes (mostly formulaic short turns). A controlled pre-role parser rebuild produced exactly the same IDs and text; only 419,188 `speaker_role` values changed. The earlier reported 1,243,388 / 75,364,490 run is therefore an unresolved historical execution discrepancy, not a reproducible parser difference. One >10,000-word intervention remains under review; only one official-page boundary comparison is documented. Raw and processed corpora are excluded from Git.[6][7][8]

Official source adapters and local disk-backed integrity audits exist for all six chambers. The combined corpus contains **2,113,920 interventions**. Germany's verified CC0 CPP-BT baseline contains 64,796 speeches (latest sitting 11 September 2026); accessible 23 and 24 September XML is not incorporated, and the latter is labeled partial. The corrected Dutch build contains 344,220 records from 903 reports, matching the active corrected/rectified final-report set. Spain includes two PDF-only journals. Poland has 97,513 records through 25 September 2026; live proceedings indexes match all 480 target cached days, but 2,458 cached statement bodies lack source-manifest entries. Small 10-record automated source-boundary screens exist for each country, including a Polish partial match and a Spanish automatic mismatch located manually in its source. These do not constitute human country-level QA sign-off.[9][15][16][18][19][20][22][23]

The repository includes a canonical multilingual speech schema, source downloader with SHA-256 manifests, general integrity checks, a deterministic historical-control sampler (local samples for all six countries), a Pangram asynchronous task client, content/configuration-addressed caching, retry/poll handling, ambiguous-submission protection, cost estimation, an explicit paid-run authorization flag, and analysis/output generation. The offline test suite passes. One tiny real-corpus API diagnostic completed; full inference has not run.[2]

The pipeline also supports a conservative, [budgeted country-month sample](budgeted_inference.md) with inverse-inclusion-weighted plots and a separately authorized **one-block real-corpus API diagnostic**. A 73-word Dutch intervention was submitted once at a $0.05 local cost estimate; Pangram returned 0.0% AI-only and 0.0% AI-assisted on that single short text. The full study is not funded or run. Small samples produce exploratory diagnostics, not precise population rates. The German late-September gap and a processing-approval record are not paid-run gates.

## Proposed inference scope and estimated cost

The transparent eligibility threshold is 40 words; it is a study choice, not an Economist filter. In the current local French rebuild, **393,565 records / 66,401,901 words** pass that threshold. Pangram lists Pangram 4 at $0.05 per **started 100-word block per speech**. The code counts **847,941 units**, projecting **$42,397.05 France-only list price** at the stated rate. The older $33,187.54 unrounded figure was a lower bound, not a payable estimate. Actual API cost also depends on redundant identical-text cache hits, model entitlement, contract, and discounts. This is not a six-country quote.[3]

Separate local German, Italian, Dutch, Spanish, and Polish corpora have 63,834, 120,839, 193,384, 50,204, and 96,528 length-eligible records; their respective list-price estimates are **$17,802.00**, **$26,924.80**, **$26,680.00**, **$14,862.70**, and **$18,546.15**. The six-country total is **2,944,254 started 100-word units / $147,212.70** at public Pangram 4 list price. This is a local estimate, **not** an account quote or approval for full inference. Human source-boundary work remains; Germany's post-archive XML is not incorporated, and Polish cached-file provenance has documented gaps.

## Research-credit application: scope and timing

The [current Pangram research page](https://www.pangram.com/contact-us/research) lists a typical grant of **200,000 credits**, with one credit per 100-word billing unit, extra credits at **$0.025 each**, and expiry after **three months** unless extended. The [API page](https://www.pangram.com/solutions/api) says noncommercial academic projects *may* qualify; applicants should state their true affiliation and intended noncommercial use, not imply automatic eligibility. At list price, 200,000 credits are equivalent to $10,000 and cover only **about 6.8% of the six-country units measured**. Confirm the actual grant's model access, billing, unit rounding, bulk pricing, and start/expiry terms with Pangram; this public-page arithmetic is not a funding offer.

Request either a scoped, cross-language pilot (historical controls plus reviewed contemporary samples) within the standard grant, or discuss a larger allocation and negotiated pricing for the full study. Ask whether the three-month window can begin when the pilot is ready, or be extended. The application should disclose the accepted German 11 September cutoff, Polish cached-file provenance gaps, human QA limits, and the one prior short-text paid API diagnostic. No parliamentary text needs to be uploaded with the inquiry.

## What Pangram access would enable

After additional human QA and a scoped spending decision, research credits could enable original-language, per-intervention detection without translation; caching/resumable inference; AI-only and AI-assisted word-share estimation; language-specific 2018–2021 historical detector baselines; sensitivity analyses; and reproducible country/time-series tables and figures. Outputs will describe detector classifications, not assert that individual politicians personally used AI. Parliamentary staff may draft speeches, and a detector result is not proof of authorship.[2]

## Current blockers

All six local country corpora and the combined file are built and pass integrity QA. This does **not** certify every boundary, attribution, or retrieval history. Germany's post-cutoff interval is accepted as an informational limit; Polish cached-file provenance and human reviews remain open. The [public evidence ledger](rights_and_processing_review.md) does not independently establish account-specific Pangram terms; the researcher reports they checked processing readiness and removed the approval-file gate. Only the one tiny paid diagnostic has run; no substantive prevalence result has been produced.

## Sources

[1] https://biztoc.com/x/d5f103685ea36fdb — Economist story metadata mirror
[2] https://docs.pangram.com/api-reference/ai-detection — Pangram AI Detection API
[3] https://www.pangram.com/pricing?category=developers — Pangram developer pricing
[4] https://www.pangram.com/contact-us/research — research grant terms and inquiry form
[5] https://www.pangram.com/solutions/api — API research-credit eligibility and published rate
[17] https://www.economist.com/britain/2026/09/23/ai-written-speeches-are-taking-over-politics — official article page
[25] https://www.hindustantimes.com/world-news/aiwritten-speeches-are-taking-over-politics-101790241476569.html — syndicated full-text reprint of the article
