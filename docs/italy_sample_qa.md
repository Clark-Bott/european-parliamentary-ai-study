# Camera dei deputati sample QA — one sitting only

The official Camera stenographic HTML page for legislature 19, sitting 711 (Friday 18 September 2026) was downloaded from `https://www.camera.it/leg19/410?idSeduta=0711&tipo=stenografico` and parsed for paragraphs with the official `intervento` class.[18] Speaker labels link to official deputy pages; the parser retains paragraph IDs, speaker profile IDs where available, source URLs, and both the raw paragraph text and cleaned text without the linked speaker-label prefix.

| Check | Result |
|---|---:|
| Sitting date | 2026-09-18 |
| Raw HTML bytes | 178,670 |
| Parsed interventions | 47 |
| Unique normalized IDs | 47 |
| Words | 1,808 |
| Under 40 words | 33 |
| Empty text / missing provenance | 0 / 0 |

Normalized output is local at `data/processed/italy_sample_2026-09-18.jsonl`; downloaded HTML is under ignored `data/raw/italy/`. Raw URL and checksum are in `data/manifests/source_manifest.jsonl`.

This checks a single live page and verifies one chair label plus paragraph extraction; it is not a random manual sample audit. The full sitting index, historical 2018–2026 acquisition, party/role enrichment, and reuse terms have not been established. The source page is public, but no broad redistribution or third-party processing license is asserted here. No Pangram inference was run.
