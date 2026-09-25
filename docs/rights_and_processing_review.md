# Rights and third-party processing review

Review date: 2026-09-24. This is an engineering evidence record, not legal advice. It distinguishes public source terms from unresolved permission. No Pangram text has been submitted.

## Source materials

| Country | Verified public evidence | Engineering status before paid processing |
|---|---|---|
| Germany | CPP-BT version 2026-09-19 is published under CC0 1.0 and states that the underlying plenary protocols are official works. The official Bundestag remains the primary source. | **Conditionally cleared for the verified CPP-BT baseline.** Cite the CPP-BT DOI and Bundestag source. Post-2026-09-19 XML remains a coverage gap. |
| France | The Assemblée nationale open-data portal applies the Licence Ouverte / Open Licence. It allows reproduction, redistribution, adaptation, and commercial use, with mandatory source attribution. | **Conditionally cleared.** Preserve source attribution and archive version/date. |
| Netherlands | The Tweede Kamer Open Data Portal disclaimer applies CC0 1.0 to API data unless otherwise indicated. It permits sharing and modification, including commercial use. | **Conditionally cleared.** Check for record-specific markings or restrictions before redistribution. |
| Italy | The Camera RDF dataset for sittings and stenographic reports is marked CC BY-SA 4.0. The project reads a separate `documenti.camera.it` rendered XML endpoint. | **Unresolved.** The RDF license has not been shown to govern the separate XML endpoint and the Pangram processing purpose. Obtain written confirmation or use a clearly covered source. |
| Spain | The Congreso legal notice permits website-information reuse if content is not altered or distorted, the source and last-update date are cited, and use is diligent. It does not grant a general CC-style license for redistributed transcript extracts. | **Unresolved for third-party commercial processing and redistribution.** Confirm that the intended research use and Pangram submission are permitted. |
| Poland | The API is official and public. Polish public-sector reuse law provides a general framework, but the API documentation does not state a license and a Sejm-specific reuse notice was not located in this review. | **Unresolved.** Obtain Sejm-specific terms or written confirmation. |

The source terms do not by themselves resolve privacy, data-protection, or third-party processing questions. Public office and speech context reduces some privacy risk but does not automatically authorize every downstream use.

## Pangram processing evidence

The public Pangram materials last updated 14 August 2025 state that:

- users retain rights in submitted content, while Pangram processes it under its terms;
- registered-account submissions and associated metadata are collected;
- submissions are not used to train, develop, refine, sell, or market Pangram models or products;
- data is hosted in the United States and processed by contracted infrastructure providers;
- Pangram says it supports GDPR rights, DPIA/RoPA, and Standard Contractual Clauses when needed; and
- registered content is retained as long as needed to serve the customer, with account-history deletion after account closure under the stated policy.

A separate Pangram enterprise page says API content is processed transiently and discarded. This conflicts with the broader registered-account privacy-policy language. The exact API plan, contractual retention period, subprocessors, deletion method, international-transfer mechanism, and research-use permission are not established by the public pages for this project.

## Code-level safeguards

- The client sends only `speech_text`; it does not send speaker name, party, ID, date, or source URL.
- Public dashboard sharing is disabled in the API configuration.
- Responses are cached locally by a SHA-256 fingerprint of exact text and model configuration.
- API keys are read from the environment and are not stored in source files.
- Paid execution requires an explicit flag, complete country/year coverage, present and empty German, Spanish, and Polish source-gap reports, and a recorded human approval.

These safeguards reduce exposure but do not replace a processor agreement or legal approval.

## Required approval before inference

Obtain and archive:

1. Pangram enterprise/API terms covering this research corpus and the selected plan.
2. A written API-content retention and deletion schedule that resolves the public-policy conflict.
3. The current subprocessor list and applicable data-processing agreement.
4. Confirmation of SCCs or another valid transfer mechanism for EU-origin data.
5. Source permission for Italy, Spain, and Poland, or a documented legal basis and counsel approval.
6. An attribution file, retention schedule, and deletion owner for local raw responses and controls.

Until those items exist, the repository must not submit text. The machine-readable `data/manifests/paid_processing_approval.json` guard is intentionally absent until a responsible reviewer completes the review. After review, the file must have this shape; the values are assertions by the reviewer, not defaults supplied by the software:

```json
{
  "approved": true,
  "approved_by": "name or accountable role",
  "approved_at_utc": "2026-09-24T12:00:00+00:00",
  "scope": "Pangram API processing for the reviewed six-country corpus",
  "source_terms_reviewed": true,
  "processor_terms_reviewed": true,
  "international_transfer_reviewed": true
}
```

## Public evidence

- Germany CPP-BT: https://doi.org/10.5281/zenodo.22844952
- France open licence: https://data.assemblee-nationale.fr/licence-ouverte-open-licence
- Netherlands disclaimer: https://opendata.tweedekamer.nl/disclaimer
- Italy dataset record: https://dati.camera.it/dataset/sedute-e-resoconti-stenografici-delle-legislature-precedenti
- Spain legal notice: https://www.congreso.es/es/cem/aviso-legal
- Poland API: https://api.sejm.gov.pl/sejm.html
- Pangram terms: https://www.pangram.com/terms-of-service
- Pangram privacy policy: https://www.pangram.com/privacy-policy
- Pangram API privacy statement: https://www.pangram.com/use-cases/trust-and-safety
- Pangram GDPR statement: https://www.pangram.com/knowledge-hub/is-pangram-gdpr-compliant
