# Economist study: reconstruction and replication ledger

## Scope and source access

The official Economist article page resolves at the URL shown below and confirms the headline “AI-written speeches are taking over politics,” but page extraction returned only a short section label rather than the story body. A third-party metadata mirror reports the subtitle “British MPs are avid users. But they have nothing on Australians or Canadians” and says it appeared on economist.com on 23 September 2026 at 18:20:26.[1][17] The metadata mirror is not the article or a methodology note. No source note, code repository, downloadable data, or detector configuration was recovered. The project brief identifies Pangram as the study's inspiration; accessible primary text does not yet independently confirm which Pangram configuration was used.

## CONFIRMED

- The official Economist article page is live and titled “AI-written speeches are taking over politics”; the available extraction did not expose its body or methodological notes.[17]
- A third-party story metadata mirror reports a comparative subtitle and publication timestamp.[1]
- The user's project brief defines cross-country extension to six non-English chambers and a 2018–2026 period. This is the project's requested scope, not a confirmed description of The Economist's sample or method.

## INFERRED WITH EVIDENCE

- The story likely compares temporal prevalence across legislatures, because its headline concerns AI-written speeches and its subtitle compares countries. The inference is limited to the headline and subtitle metadata.[1]
- A comparable extension should analyze original-language speech text, preserve speech-level provenance, measure both AI-generated and mixed/assisted text, and report historical controls. This is a design recommendation, not a reconstruction of the article's exact choices.

## UNKNOWN (not silently imputed)

The accessible evidence does not establish: legislatures analyzed; complete date range; speech/intervention definition; exclusion rules; minimum text length; detector model/version or settings; whether Pangram was used in the article itself; whether texts were sent individually or in batches; how detector segments were mapped to words; whether mixed text counted as AI; denominator and aggregation weighting; historical controls; validation or sensitivity analyses; or temporal smoothing/uncertainty procedure.

## Replication policy

Until primary methods become available, the study will label its design as a *comparative extension*, not an exact replication. It will keep separate outputs for word-weighted AI-only share, AI-plus-mixed share, and speech-weighted classification; vary minimum lengths; expose exclusions; report year-specific historical baselines by language; and treat baseline subtraction as a sensitivity analysis only. Any later evidence that changes a design choice must be added to this ledger with a source and date, and the code/configuration must version that choice.

## Sources

[1] https://biztoc.com/x/d5f103685ea36fdb — Economist story metadata mirror
