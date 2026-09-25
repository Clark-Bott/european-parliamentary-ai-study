# Rights and third-party processing review

Evidence collected 2026-09-24. This is a source/processor reference, not legal advice or a runtime approval checklist. The researcher reported on 2026-09-25 that they checked processing readiness and directed removal of the approval-file step. This report is a user decision, not independent verification of account-specific terms. One 73-word Dutch corpus speech was submitted as a paid API diagnostic on 2026-09-25; full study inference has not run.

## Source materials

| Country | Verified public evidence | Engineering status before paid processing |
|---|---|---|
| Germany | CPP-BT version 2026-09-19 is published under CC0 1.0 and states that the underlying plenary protocols are official works. The official Bundestag remains the primary source. | **Conditionally cleared for the verified CPP-BT baseline.** Cite the CPP-BT DOI and Bundestag source. Post-2026-09-19 XML remains a coverage gap. |
| France | The Assemblée nationale open-data portal applies the Licence Ouverte / Open Licence. It allows reproduction, redistribution, adaptation, and commercial use, with mandatory source attribution. | **Conditionally cleared.** Preserve source attribution and archive version/date. |
| Netherlands | The Tweede Kamer Open Data Portal disclaimer applies CC0 1.0 to API data unless otherwise indicated. It permits sharing and modification, including commercial use. | **Conditionally cleared.** Check for record-specific markings or restrictions before redistribution. |
| Italy | The Camera RDF dataset for sittings and stenographic reports is marked CC BY-SA 4.0. The project reads a separate `documenti.camera.it` rendered XML endpoint. | **Unresolved.** The RDF license has not been shown to govern the separate XML endpoint and the Pangram processing purpose. Obtain written confirmation or use a clearly covered source. |
| Spain | The Congreso legal notice permits website-information reuse if content is not altered or distorted, the source and last-update date are cited, and use is diligent. It does not grant a general CC-style license for redistributed transcript extracts. | **Unresolved for third-party commercial processing and redistribution.** Confirm that the intended research use and Pangram submission are permitted. |
| Poland | The [Sejm information-system reuse notice for term 10](https://www.sejm.gov.pl/sejm10.nsf/page.xsp/copyright) and [term 9](https://www.sejm.gov.pl/sejm9.nsf/page.xsp/copyright) permit free use of Sejm information-system materials, require source attribution for text taken from `www.sejm.gov.pl`, and prohibit Sejm materials (in particular iTV broadcasts and archives) from forming part of a commercial offer. The [official API](https://api.sejm.gov.pl/sejm.html) separately documents transcript endpoints; the notice does not expressly resolve third-party US API processing of those transcripts. The [2021 public-sector reuse statute](https://api.sejm.gov.pl/eli/acts/DU/2021/1641/text.html) supplies a general framework, not an account-specific processing agreement. | **Unresolved for Pangram submission.** Preserve Sejm attribution and obtain a review of whether the notice covers API text and the intended third-party processing. Do not read the commercial-offer restriction as permission for it. |

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
- Paid execution requires an explicit flag, complete 2018–2025 country/year coverage, and present and empty Spanish and Polish source-gap reports. The recorded German 2026 cutoff is informational, not a paid gate; no processing-approval file is required.

These safeguards reduce exposure; they do not establish account-specific contractual terms.

## Researcher decision

The researcher confirmed readiness to submit an explicitly authorized, low-cost corpus test and removed the approval-record workflow. The source and processor observations above remain useful context but are not machine-enforced. The 2018–2025 coverage and Spanish/Polish source-gap checks remain separate data-integrity gates.

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
