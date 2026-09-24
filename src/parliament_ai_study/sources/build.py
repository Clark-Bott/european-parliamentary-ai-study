"""Build a reproducible, concatenated six-country corpus from official sources."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from ..io import iter_jsonl, write_jsonl
from ..sampling import sample_historical_controls
from .france import build_france_corpus, download_france_archives
from .germany import build_bundestag_corpus
from .italy import build_camera_corpus
from .netherlands import build_tweede_kamer_corpus
from .sejm import build_sejm_corpus
from .spain import build_congreso_corpus

BUILDERS = {"Germany": build_bundestag_corpus, "Netherlands": build_tweede_kamer_corpus,
            "Italy": build_camera_corpus, "Spain": build_congreso_corpus, "Poland": build_sejm_corpus}


def build_six_country_corpus(corpus: str | Path = "data/processed/speeches.jsonl", *,
                             start_year: int = 2018, end_year: int = 2026,
                             raw_dir: str | Path = "data/raw",
                             manifest_path: str | Path = "data/manifests/source_manifest.jsonl",
                             sample_size: int = 1000) -> dict:
    """Download missing sources, normalize and combine; do not submit to Pangram.

    Per-country outputs are atomic. A completed country's output can be reused
    on restart; remove it explicitly to rebuild against updated source data.
    """
    target = Path(corpus)
    target.parent.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for country in ("Germany", "France", "Netherlands", "Italy", "Spain", "Poland"):
        path = target.parent / f"{country.lower()}_speeches.jsonl"
        paths[country] = path
        if path.is_file():
            print(f"Using existing {country} normalized corpus: {path}", flush=True)
            continue
        print(f"Acquiring {country} official plenary archive: {path}", flush=True)
        if country == "France":
            archives = download_france_archives(raw_dir=raw_dir, manifest_path=manifest_path)
            result = build_france_corpus(archives, path, start_year=start_year, end_year=end_year)
        else:
            result = BUILDERS[country](path, start_year=start_year, end_year=end_year,
                                       raw_dir=raw_dir, manifest_path=manifest_path)
        print(f"{country}: {result}", flush=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("wb") as out:
        for path in paths.values():
            with path.open("rb") as stream:
                shutil.copyfileobj(stream, out)
    temporary.replace(target)
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    # Controls are separate from the full historical archive. The sampler is
    # deterministic and works country-by-country, avoiding combined-corpus RAM.
    controls: list[dict] = []
    for path in paths.values():
        controls.extend(sample_historical_controls(iter_jsonl(path),
                                                   sample_size_per_country=sample_size))
    control_path = target.parent.parent / "controls" / "historical_sample.jsonl"
    write_jsonl(control_path, controls)
    report = {"corpus": str(target), "sha256": digest.hexdigest(), "bytes": target.stat().st_size,
              "country_files": {key: str(value) for key, value in paths.items()},
              "control_sample": str(control_path), "sample_records": len(controls),
              "start_year": start_year, "end_year": end_year}
    manifest = target.parent.parent / "manifests" / "combined_corpus.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Build the complete corpus without Pangram inference")
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/speeches.jsonl"))
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2026)
    args = parser.parse_args()
    print(json.dumps(build_six_country_corpus(args.corpus, start_year=args.start_year,
                                              end_year=args.end_year), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
