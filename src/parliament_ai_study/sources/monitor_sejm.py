"""Read-only live progress display for a Sejm acquisition already in progress.

The bar measures cached *sitting-day metadata*, not the number of transcript
bodies parsed or coverage approved. This command never modifies the corpus,
the raw-source cache, or the append-only provenance manifest.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import json
import os
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .sejm import API, TERMS


_SPEECH_ID = re.compile(
    r"sejm-term(?P<term>\d+)-proceeding(?P<proceeding>\d+)-(?P<day>\d{4}-\d{2}-\d{2})-statement\d+"
)


def target_days(index: list[dict], cutoff: date) -> list[tuple[int, str]]:
    """Only historical, real-numbered sitting days can have transcripts."""
    return [(int(sitting["number"]), day)
            for sitting in index for day in sitting.get("dates", [])
            if int(sitting["number"]) > 0
            and 2018 <= date.fromisoformat(day).year <= 2026
            and date.fromisoformat(day) <= cutoff]


def _read_index(root: Path, term: int, *, offline: bool) -> list[dict] | None:
    cached = root / f"term-{term}" / "proceedings.json"
    if cached.is_file():
        return json.loads(cached.read_text(encoding="utf-8"))
    if offline:
        return None
    # Read the missing denominator once from the public API; never write it to
    # data/raw or the source manifest while the acquisition writer is active.
    url = f"{API}/term{term}/proceedings"
    try:
        with urlopen(Request(url, headers={"User-Agent": "EuropeanParliamentaryAIStudy/0.1"}),
                     timeout=12) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


@dataclass
class CorpusTail:
    """Count only newly appended bytes after the first scan."""

    inode: int | None = None
    offset: int = 0
    records: int = 0
    last_id: str = "—"
    _carry: bytes = b""

    def update(self, path: Path) -> None:
        if not path.is_file():
            return
        stat = path.stat()
        if stat.st_ino != self.inode or stat.st_size < self.offset:
            self.inode, self.offset, self.records, self.last_id, self._carry = (
                stat.st_ino, 0, 0, "—", b"")
        with path.open("rb") as stream:
            stream.seek(self.offset)
            while block := stream.read(1024 * 1024):
                self.offset += len(block)
                parts = (self._carry + block).split(b"\n")
                self._carry = parts.pop()
                self.records += len(parts)
                if parts:
                    # The speech ID is ASCII; no full JSON parse is needed for
                    # a record that can be written concurrently with this read.
                    match = _SPEECH_ID.search(parts[-1].decode("utf-8", errors="replace"))
                    if match:
                        self.last_id = match.group()


def _running_pids() -> list[int]:
    pids = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "-m parliament_ai_study.sources.sejm" in command and entry.name != str(os.getpid()):
            pids.append(int(entry.name))
    return pids


def _last_log_line(path: Path) -> str:
    if not path.is_file():
        return "No acquisition log found"
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - 4096))
        lines = stream.read().decode("utf-8", errors="replace").splitlines()
    return lines[-1] if lines else "Acquisition log is empty"


def _last_day_bodies(raw_dir: Path, speech_id: str) -> str:
    match = _SPEECH_ID.fullmatch(speech_id)
    if not match:
        return "Unknown"
    day = (raw_dir / f"term-{match['term']}" / f"proceeding-{match['proceeding']}" /
           match["day"])
    try:
        statements = json.loads((day / "statements.json").read_text(encoding="utf-8"))["statements"]
    except (OSError, ValueError, KeyError):
        return f"{match['day']}: no valid cached statement list"
    if not isinstance(statements, list) or any(not isinstance(item, dict) for item in statements):
        return f"{match['day']}: invalid cached statement list"
    spoken = [item for item in statements if not item.get("unspoken")]
    cached = sum((day / f"statement-{item.get('num')}.html").is_file() for item in spoken)
    return f"{match['day']} (term {match['term']}): {cached}/{len(spoken)} bodies cached"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch Sejm acquisition (read-only)")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/poland"))
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/poland_speeches.jsonl"))
    parser.add_argument("--log", type=Path, default=Path("/tmp/opencode/poland-resume.log"))
    parser.add_argument("--through-date", type=date.fromisoformat, default=date.today(),
                        help="latest sitting day to count; defaults to today")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between refreshes")
    parser.add_argument("--offline", action="store_true", help="do not read a missing index from the public API")
    parser.add_argument("--once", action="store_true", help="print one snapshot and exit")
    args = parser.parse_args(argv)
    if args.interval <= 0 or args.through_date > date.today():
        parser.error("interval must be positive and the date must not be in the future")

    indexes = {term: _read_index(args.raw_dir, term, offline=args.offline) for term in TERMS}
    tail = CorpusTail()
    progress = Progress(TextColumn("{task.description:<13}"), BarColumn(bar_width=35),
                        TaskProgressColumn(), TextColumn("{task.fields[days]}"), expand=True)
    tasks = {term: progress.add_task(f"Term {term}", total=None, days="index unavailable")
             for term in TERMS}
    total_task = progress.add_task("All terms", total=None, days="index incomplete")
    last_poll: float | None = None
    previous_records = 0

    def render() -> tuple[Panel, bool, bool]:
        nonlocal last_poll, previous_records
        totals = cached_counts = 0
        all_indexed = True
        for term in TERMS:
            # The writer can create term 10's index while this monitor runs.
            if indexes[term] is None:
                indexes[term] = _read_index(args.raw_dir, term, offline=True)
            index = indexes[term]
            if index is None:
                all_indexed = False
                progress.update(tasks[term], completed=0, total=None, days="index unavailable")
                continue
            days = target_days(index, args.through_date)
            cached = sum((args.raw_dir / f"term-{term}" / f"proceeding-{number}" /
                          day / "statements.json").is_file() for number, day in days)
            totals += len(days)
            cached_counts += cached
            progress.update(tasks[term], completed=cached, total=max(1, len(days)),
                            days=f"{cached}/{len(days)} metadata days")
        progress.update(total_task, completed=cached_counts,
                        total=max(1, totals) if all_indexed else None,
                        days=f"{cached_counts}/{totals} metadata days" if all_indexed else
                             "denominator incomplete")

        complete = args.corpus.is_file()
        tail.update(args.corpus if complete else args.corpus.with_suffix(args.corpus.suffix + ".tmp"))
        now = time.monotonic()
        recent = (f"+{tail.records - previous_records:,} records in {now - last_poll:.0f}s"
                  if last_poll is not None and tail.records >= previous_records else "Awaiting next refresh")
        last_poll, previous_records = now, tail.records
        pids = _running_pids()
        coverage = args.raw_dir.parent.parent / "manifests" / "poland_coverage_audit.json"
        status = ("Corpus promoted; coverage report present" if complete and coverage.is_file() else
                  "Corpus promoted; awaiting coverage report" if complete else
                  f"Acquisition running (PIDs: {', '.join(map(str, pids))})" if pids else
                  "No acquisition process found; partial output remains")
        info = Table.grid(padding=(0, 2))
        info.add_column(style="bold cyan")
        info.add_column()
        info.add_row("Status", status)
        info.add_row("Flushed speeches", f"{tail.records:,} (final record count is not known yet)")
        info.add_row("Recent flush", recent)
        info.add_row("Last record", tail.last_id)
        info.add_row("Last parsed day", _last_day_bodies(args.raw_dir, tail.last_id))
        info.add_row("Last log line", _last_log_line(args.log))
        warning = Text("Bars measure cached day metadata, NOT downloaded bodies, parser QA or paid-run readiness.",
                       style="yellow")
        if not all_indexed:
            warning.append(" The total is incomplete until all term indexes are available.")
        return Panel(Group(progress, info, warning),
                     title=f"Polish Sejm acquisition through {args.through_date}"), (
                         complete and coverage.is_file()), not pids and not complete

    with Live(refresh_per_second=4, transient=False) as live:
        while True:
            panel, finished, stopped = render()
            live.update(panel, refresh=True)
            if args.once or finished or stopped:
                break
            time.sleep(args.interval)
    return 1 if stopped and not args.once else 0


if __name__ == "__main__":
    raise SystemExit(main())
