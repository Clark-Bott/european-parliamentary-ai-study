# Positive controls (Phase 8)

Positive controls test whether the detector flags clearly machine-written
parliamentary prose in each target language. They are optional. The main
study does not depend on them, and no paid execution is required to design,
import, or validate them.

## What they are

Short fictional plenary passages (150–400 words) written entirely by a
contemporary LLM, in German, French, Dutch, Italian, Spanish, and Polish.
They are labelled synthetic at every stage and are never appended to a real
corpus file.

## Separation rules

- `source_type` is always `synthetic_positive_control`.
- `speech_id` always starts with `positive-control-`.
- `source_url`, `source_identifier`, `speaker_id`, and `party` must be empty.
  `src/parliament_ai_study/positive_controls.py` rejects any record that
  carries them, so a synthetic passage cannot impersonate an official record.
- Controls live in `data/controls/positive_controls.jsonl`, which is
  Git-ignored like other generated data.

## Workflow

1. Print the per-language specification:

   ```bash
   uv run --python 3.12 python -m parliament_ai_study.positive_controls --brief Spain
   ```

2. Generate the passages with any contemporary LLM. Store one JSON object per
   passage with `country`, `text_language`, `generator` (model and version),
   `prompt_id`, and `text`.

3. Validate and store them:

   ```bash
   uv run --python 3.12 python -m parliament_ai_study.positive_controls \
     --import-from my_drafts.jsonl
   ```

4. Run the experiment. When `data/controls/positive_controls.jsonl` exists,
   the pipeline submits the passages through the same fingerprint cache as the
   real corpus (so a restart never pays twice) and writes
   `results/tables/positive_controls.csv` and
   `results/reports/positive_controls.json`.

## Interpretation

The per-language detection rate is calibration evidence, not a research
finding. A low detection rate on known-AI text warns that the historical
2018–2021 baseline for that language may also be understated. Report it next
to the historical baseline table, and do not treat it as a correction factor.

## Cost

Positive controls add a few thousand words in total, under $2 at the default
rate. They are not included in the corpus cost tables.
