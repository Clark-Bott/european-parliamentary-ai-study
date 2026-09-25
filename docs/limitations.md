# Limitations and interpretation

1. **Primary article methods are only partly recovered.** The article body is available through a syndicated reprint, so the detector (Pangram) and the headline metric (word-weighted AI share) are confirmed. The Pangram model and thresholds, the date range, the speech definition, the mixed-text treatment, and any source note, code, or data release are still unavailable.[25][17] This project must not market itself as an exact replication.
2. **Detector uncertainty.** Pangram classifications are probabilistic outputs, not proof of authorship, deliberate AI use, or a named member's personal behavior. Staff, researchers, party offices, human editing, and mixed workflows may contribute to a speech.
3. **Language comparability.** Six languages and institutional transcription conventions differ. A single commercial detector may have different calibration and error rates by language, register, and historical period. Language-specific historical controls and manual validation are essential, but cannot establish ground truth.
4. **Selection and coverage.** Full official archives can omit committee speech, informal exchange, or periods with different recording practices; daily files can change after correction. Country/year comparisons are only defensible after coverage is measured.
5. **Procedural text above the length cutoff.** In the Spanish corpus, 3,830 eligible chair turns (256,449 words) include an explicit vote total. The 40-word cutoff does not remove all non-speech material. The chair-exclusion sensitivity provides a bound, not a validated substitute for manual coding and a precise inclusion rule.
6. **Corpus unit and cleaning.** Parliamentary interventions are not identical to prepared speeches. Short procedural turns, interruptions, quoted text, staff-drafted remarks, and floor transcripts can distort speech-level estimates.
7. **Pricing and API behavior change.** Pangram's public price page currently lists different rates for Pangram 3 and 4; rates and account-specific billing can change.[3] A live cost estimate and explicit confirmation must precede any paid request.
8. **Privacy, rights, and attribution.** Public parliamentary text can still contain personally identifying information, quotations, and sensitive matter. The client submits only speech text, but source permissions and Pangram's processor terms remain separate questions. The unresolved evidence and required approval are recorded in [`rights_and_processing_review.md`](rights_and_processing_review.md). Do not publish individual rankings or detector labels as factual claims.

## Interpretation rule

Use phrasing such as “Pangram classified an estimated share of these words as AI-generated/assisted,” not “member X used AI.” Report corpus coverage, model and date, detector version, language, uncertainty, excluded text, and control results alongside every headline estimate.

## Sources

[1] https://biztoc.com/x/d5f103685ea36fdb — Economist story metadata mirror
[3] https://www.pangram.com/pricing?category=developers — Pangram developer pricing
[17] https://www.economist.com/britain/2026/09/23/ai-written-speeches-are-taking-over-politics — official article page
[25] https://www.hindustantimes.com/world-news/aiwritten-speeches-are-taking-over-politics-101790241476569.html — syndicated full-text reprint of the article
