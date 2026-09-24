# Economist study: reconstruction and replication ledger

## Scope and source access

A story metadata mirror lists *The Economist* headline “AI-written speeches are taking over politics,” describes the subtitle as “British MPs are avid users. But they have nothing on Australians or Canadians,” and says it appeared on economist.com on 23 September 2026 at 18:20:26.[1] This is metadata, not the article body or a methodology note. Direct extraction of the Economist URL returned no article text; attempts to locate a Wayback snapshot were rate-limited/unavailable. No Economist source note, code repository, data download, or detector configuration was recovered in this pass. The user's brief states that the inspiration used Pangram; that statement is retained as a project premise to verify, not upgraded here into an independently confirmed article fact.

## CONFIRMED

- The contemporaneous story metadata exists and reports that headline, subtitle, and timestamp.[1]
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
