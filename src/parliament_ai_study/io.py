"""JSON Lines input/output helpers."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Iterator


def iter_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield JSON object records one line at a time, with line-numbered validation."""
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_number}: each JSONL line must be an object")
                yield value


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(temporary, target)
