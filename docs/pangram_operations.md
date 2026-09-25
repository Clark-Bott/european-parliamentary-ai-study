# Pangram run operations

How a paid run behaves at runtime, and what to do when it stops.

## Sequence of guards

A paid run refuses to start unless all of these hold:

1. `--confirm-paid-run` is passed (and `--dry-run` is not).
2. `PANGRAM_API_KEY` is set, and Pangram's read-only `GET /models` reports the
   configured model for that key.
3. The combined corpus passes disk-backed QA with no errors.
4. Every `country:year` from 2018 to 2025 has records.
5. Every required source-gap report exists and contains an empty JSON list:
   `germany_unavailable_protocols.json`, `spain_unavailable_journals.json`,
   and `poland_unavailable_statements.json` by default. An absent report
   blocks the paid run; it is not treated as evidence of no gaps.
6. `data/manifests/paid_processing_approval.json` exists and records human
   review of source terms, processor terms, and international transfers.
7. If `--max-cost X` is given, the estimate is at most $X.

The estimate is printed before the first request in every mode.

## Resume and duplicate-billing protection

Each request fingerprint is SHA-256 over the exact submitted text plus the
configuration (`model`, `public_dashboard_link: false`). Results live under
`results/raw_pangram/<fingerprint>.json`.

- **Completed response present** → reused, never resubmitted.
- **`pending` with a task ID** → the run resumes polling the existing task;
  it does not submit again.
- **`submission_unknown`** → the POST outcome is ambiguous (timeout, 5xx,
  connection failure after the request may have reached Pangram). The client
  refuses to submit that fingerprint again.

A per-fingerprint `flock` prevents two concurrent workers from paying twice
for the same text.

## Ambiguous submissions

Before doing anything else, check the Pangram dashboard for the speech IDs in
`results/reports/pangram_errors.jsonl` (`error_type` and `message` per line).

- If Pangram has **no** task for that text: delete the stale
  `results/raw_pangram/<fingerprint>.json` entry and rerun. The fingerprint is
  printed in the error message; if it is not, recompute it from the same text
  and configuration with `pangram.request_fingerprint`.
- If Pangram **has** the task: keep the entry and let polling finish, or
  record the response manually in the same file shape as a completed entry.

Do not delete an entry to "retry" a request you have not checked: that is how
a paid text gets billed twice.

## Errors and restart

Every failure is appended to `results/reports/pangram_errors.jsonl` with a UTC
timestamp, speech ID, error type, and message, then the run stops with a
non-zero exit status. Rerun the same command after fixing the cause; completed
responses are loaded from cache, so only unfinished items are billed.

## Cost cap

`--max-cost 500` aborts before any request when the estimate for the corpus
**plus optional positive controls** exceeds $500. Use it as a second, independent limit alongside
`--confirm-paid-run`.
