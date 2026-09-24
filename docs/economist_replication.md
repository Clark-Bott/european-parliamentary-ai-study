# Economist study: reconstruction and replication ledger

## Scope and source access

The official Economist page (economist.com/britain/2026/09/23/ai-written-speeches-are-taking-over-politics)
rejects automated extraction with HTTP 403.[17] On 2026-09-24 the full article body was recovered
from a syndicated reprint carried by Hindustan Times, dated 2026-09-24.[25] The reprint reproduces
the complete narrative text and describes all four charts in words. It is a reprint of the article,
not the publisher's own page: it carries no source note, footnote list, code link, or data link, and
chart contents are described rather than shown. A third-party metadata mirror fixes the publication
timestamp as 2026-09-23 18:20:26.[1]

What is now known comes from the article body.[25] What remains unknown comes from the absence of
any methodology note, data release, or configuration disclosure. Nothing below is imputed silently.

## CONFIRMED

- The analysis used **Pangram**: "Our analysis, using Pangram, finds that one in ten of the words
  spoken in Britain's parliamentary debates are drafted by AI."[25]
- The **primary headline metric is word-weighted**: one in ten words spoken in UK parliamentary
  debates, rising "from near-zero in 2024."[25]
- The comparison set is **English-speaking chambers**: Australia and Canada at "triple the rate of
  British ones," US House close behind, House of Lords above Commons, New Zealand House and US Senate
  lowest.[25]
- The article states a **pre-ChatGPT baseline expectation**: Pangram "flags vanishingly few speeches
  from before the release of ChatGPT in November 2022."[25]
- The article quotes Pangram's public accuracy claim of **one false positive in 24,000**, and a
  University of Chicago result of "near-zero" error rate on longer text.[25]
- **Per-MP figures cover "the past year"** and are speech-count weighted at member level: the most
  flagged member had "three-quarters of his parliamentary contributions" flagged.[25]
- The article reports that **ministers' and party leaders' speeches "rarely seem to be
  AI-written"** and names six leaders with none flagged.[25] It reports this as an observation, not
  as a stated exclusion rule.
- A **party pattern** is reported among backbenchers (Liberal Democrats highest of the major
  parties), and a commissioned **Public First voter poll** forms chart 4.[25]
- Four charts are referenced: (1) upper — UK word share over time; (1) lower — cross-country
  comparison; (2) per-MP concentration; (3) party rates; (4) polling.[25]
- The headline, subtitle, and publication timestamp match the metadata mirror.[1][17]

## INFERRED WITH EVIDENCE

- The same Pangram configuration was applied across the compared chambers, because one chart ranks
  countries on a common flagged-rate scale.[25] The configuration itself is not stated.
- The time series likely starts in or near 2024 for the UK, because the share is described as rising
  "from near-zero in 2024," while the false-positive discussion refers to pre-November-2022
  material.[25] Exact endpoints are unconfirmed.
- Per-member results appear to count flagged speeches rather than flagged words, because members are
  ranked on "contributions … flagged as AI-written."[25]
- Speech-level claims ("flagged as entirely AI-written," "any material AI input") imply a speech-level
  threshold exists, but its value is not stated.[25]

## UNKNOWN (not silently imputed)

The recovered body does not establish: the Pangram model/selector or API version; any threshold that
converts fractions into "AI-written"; the exact date range; the definition of a speech or intervention;
the transcript source and its revision policy; inclusion or minimum-length rules; how AI-assisted/mixed
text is counted in the headline number; denominators and aggregation weighting details; whether texts
were sent individually or in batches; historical controls; validation, sensitivity, or uncertainty
procedures; the false-positive rate measured on their own pre-ChatGPT parliamentary data; or any
code, data, or source-note release.

## Related literature recovered on 2026-09-24

Useful for comparison and for calibrating claims; none is a substitute for The Economist's method.

- Suvanto, McGlinchey, Barclay and Wahde, "Detecting undisclosed LLM-generated content in
  parliamentary texts" (arXiv preprint 2606.14209): a glass-box n-gram classifier trained on
  2014–2020 UK and Swedish motions with LLM-rewritten positives; reports F1 0.940 (UK) / 0.969 (SE),
  whole-text detection of 2.1% UK and 6.5% SE by 2026, and 15.5% / 9.4% when any long paragraph is
  flagged.[26][27] It measures a different unit (motions and statements, not spoken interventions)
  and a different detector from Pangram.
- The Economist's own "How to spot AI writing" (Off the Charts, 2026-08-08) describes Pangram's
  99.98% accuracy claim and a separate study in which LLMs rewrote Economist articles.[28]
- Originality.AI's Congressional Record study applies a different commercial detector with an
  explicit 15% allowance threshold, producing much higher rates (22.2% of sampled floor turns in
  2026 YTD).[29] It shows how strongly detector and threshold choice moves the headline number.
- Dutch journalism used Pangram on cabinet speeches and on the prime minister's social posts, with
  public denials from the ministries involved.[30] Relevant context for the Netherlands analysis and
  for this project's rule against individual-use allegations.
- Pimlico Journal's phrase-frequency study of Hansard is a detector-free alternative design based on
  AI-associated phrase counts.[31]

## Replication policy

The study remains a **comparative extension**, not an exact replication. Two facts now anchor that
choice: the article used Pangram, so this project's detector choice matches, and the article's
headline metric is word-weighted AI share, which is this project's primary estimand. Everything
between those anchors — model selector, thresholds, speech definition, date range, mixed-text
handling — is still undisclosed, so the extension keeps separate outputs for word-weighted AI-only
share, AI-plus-mixed share, and speech-weighted classification; varies minimum lengths; exposes
exclusions; reports year-specific historical baselines by language; and treats baseline subtraction as
a sensitivity analysis only. Any later evidence that changes a design choice must be added to this
ledger with a source and date, and the code must version that choice.

## Sources

[1] https://biztoc.com/x/d5f103685ea36fdb — Economist story metadata mirror
[17] https://www.economist.com/britain/2026/09/23/ai-written-speeches-are-taking-over-politics — official article page (HTTP 403 to automated extraction)
[25] https://www.hindustantimes.com/world-news/aiwritten-speeches-are-taking-over-politics-101790241476569.html — syndicated full-text reprint of the article
[26] https://arxiv.org/abs/2606.14209 — Suvanto et al., detecting undisclosed LLM-generated content in parliamentary texts
[27] https://www.chalmers.se/en/current/news/me-mps-are-using-ai-to-help-write-parliamentary-motions-without-disclosing-it/ — Chalmers press release with per-year figures
[28] https://theeconomistoffthecharts.substack.com/p/how-to-spot-ai-writing — The Economist, Off the Charts, 2026-08-08
[29] https://originality.ai/blog/likely-ai-language-congressional-record — Originality.AI Congressional Record study
[30] https://nltimes.nl/2026/09/12/key-defense-speeches-year-appear-fully-ai-generated-analysis — Dutch cabinet speech Pangram reporting
[31] https://www.pimlicojournal.co.uk/p/mps-are-almost-certainly-using-chatgpt — phrase-frequency alternative design
