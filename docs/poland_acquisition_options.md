# Polish transcript acquisition: archive versus statement API

The [official Sejm API](https://api.sejm.gov.pl/sejm.html) exposes three
different resources for each sitting day: a JSON statement list, individually
numbered HTML statement bodies, and one complete stenographic PDF at
`/sejm/term{term}/proceedings/{number}/{date}/transcripts/pdf`.
The [Sejm stenographic archive](https://sejm.gov.pl/sejm10.nsf/stenogramy.xsp)
also links the whole-day records. There is **an archive**; the study has not
mistaken the per-statement endpoint for the only available transcript source.

## Why this build uses the HTML statements

The JSON list contains numbered statements with speaker metadata. Fetching
the matching HTML gives a direct source URL, a stable statement ID, and a
reproducible speech boundary. The PDF has all turns in fewer requests but
contains page headers, layout line breaks and hyphenation, and several
speakers within a page. A PDF parser would need a new speaker-boundary and
attribution audit before replacing the already collected HTML corpus.
`/transcripts/0` is a long procedural account, **not** a bulk replacement for
all numbered statement bodies.

On 2026-09-25, two official sample PDFs were retrieved read-only for
inspection: term 10, proceeding 1, 2023-11-13 (36 pages, 731,749 bytes) and
term 9, proceeding 75, 2023-05-09 (118 pages, 1,983,612 bytes). They are not
part of the tracked corpus or a validated PDF-parser fallback. A third-party
Hugging Face Sejm corpus is available, but it changes the speech unit and
minimum length and has no September 2026 records in its current data viewer;
it cannot be substituted for verified official source records without a
full reconciliation.

## Network cost and tested small-file change

The general downloader probes byte ranges to protect large archives. The
Sejm statement files are small: most replies were HTTP 206, so each statement
cost a probe **and** a full-range request. The Sejm adapter now selects a
single, plain GET for its indexes, metadata and HTML bodies. The same
downloader still checks `Content-Length`, writes atomically, retries on
failure, and appends SHA-256/URL metadata only after success. Other archive
adapters retain verified range downloads. A single previously cached
statement matched byte-for-byte through both routes; the range route took
0.79 s and the plain route 0.59 s in one local sample. This is a diagnostic,
**not** a demonstrated corpus-wide speedup. The existing writer must stop
before a new process can use this change; never run two writers concurrently.

The first resumed writer (`--workers 4`) stopped on a transient DNS failure
after 67,433 speeches had been saved. Its prefix was preserved. A new 4-worker
writer validated the prefix, resumed, and was stopped cleanly for a further
network change; the partial file still ended in a complete JSONL line.
The current single writer uses `--resume-partial --through-date 2026-09-25
--workers 12` and logs to `/tmp/opencode/poland-resume-pooled-12.log`.
The Sejm adapter now reuses at most 12 HTTP/1.1 keep-alive connections across
statement and day requests, while keeping plain GETs, per-file atomic writes,
response-length checks, retries, SHA-256 hashes, and append-only provenance.
Transient request errors now have up to eight bounded attempts (previously
three); no verification or reuse term is bypassed. A six-request sequential
comparison against *previously cached official statement URLs* took 4.72 s
with fresh `urllib` connections versus 2.55 s with a pooled HTTP client.
This small diagnostic does **not** establish a 10× sustained rate, and 12
workers increase load on the official API; watch for throttling or failures.
The PDF route still has no validated speaker-boundary parser.

Do not represent a cached day or a fetched PDF as a completed, validated
speech corpus. The Polish gap report and human source-boundary check remain
required before any paid inference.
