"""Official-source download helpers with a structured provenance manifest."""
from __future__ import annotations

from datetime import datetime, timezone
from http.client import IncompleteRead
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any

USER_AGENT = "EuropeanParliamentaryAIStudy/0.1 (reproducible research; contact via repository)"


def fetch_bytes(url: str, *, timeout: float = 60, headers: dict[str, str] | None = None,
                retries: int = 3, opener=urlopen) -> tuple[bytes, dict[str, Any]]:
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with opener(Request(url, headers=request_headers), timeout=timeout) as response:
                body = response.read()
                meta = {"status": response.status, "content_type": response.headers.get("Content-Type", "")}
                return body, meta
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if isinstance(exc, HTTPError) and exc.code < 500 and exc.code != 429:
                raise
            if attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
    assert last_error is not None
    raise last_error


def file_manifest_entry(path: str | Path, source_url: str, *, content_type: str = "",
                        http_status: int = 200, retrieved_at_utc: str | None = None) -> dict[str, Any]:
    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    parts = urlsplit(source_url)
    sensitive = {"apikey", "api_key", "access_token", "token", "key", "authorization", "secret"}
    safe_query = urlencode([(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                            if key.casefold() not in sensitive])
    safe_url = urlunsplit((parts.scheme, parts.netloc, parts.path, safe_query, ""))
    timestamp = retrieved_at_utc or datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat()
    return {"source_url": safe_url, "retrieved_at_utc": timestamp, "local_path": str(target),
            "bytes": target.stat().st_size, "sha256": digest.hexdigest(),
            "content_type": content_type, "http_status": http_status}


def _parse_content_range(value: str | None) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"bytes\s+(\d+)-(\d+)/(\d+)", value or "", re.I)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else None


def download_file(url: str, destination: str | Path, *, manifest_path: str | Path,
                   headers: dict[str, str] | None = None, timeout: float = 180,
                   retries: int = 3, chunk_size: int = 1024 * 1024,
                   range_chunk_size: int = 4 * 1024 * 1024,
                   opener=urlopen, sleep=time.sleep,
                   use_range: bool = True) -> dict[str, Any]:
    """Stream to disk; skip a redundant range probe for known small files."""
    if retries < 1 or chunk_size < 1 or range_chunk_size < 1:
        raise ValueError("retries and chunk sizes must be positive")
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    last_error: Exception | None = None
    metadata: dict[str, Any] = {}

    def stream_full(response) -> None:
        nonlocal metadata
        if response.status != 200:
            raise IncompleteRead(b"", 1)
        metadata = {"status": response.status,
                    "content_type": response.headers.get("Content-Type", "")}
        expected = response.headers.get("Content-Length")
        written = 0
        with temp.open("wb") as stream:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                stream.write(chunk)
                written += len(chunk)
        if expected is not None and written != int(expected):
            raise IncompleteRead(b"", int(expected) - written)
        if written == 0:
            raise IncompleteRead(b"", 1)
        os.replace(temp, target)

    def fetch_range(start: int, end: int, total: int) -> dict[str, Any]:
        range_error: Exception | None = None
        for chunk_attempt in range(retries):
            range_headers = {**request_headers, "Range": f"bytes={start}-{end}"}
            try:
                with opener(Request(url, headers=range_headers), timeout=timeout) as response:
                    info = _parse_content_range(response.headers.get("Content-Range"))
                    if response.status != 206 or info != (start, end, total):
                        raise IncompleteRead(b"", end - start + 1)
                    chunk_meta = {"status": response.status,
                                  "content_type": response.headers.get("Content-Type", "")}
                    written = 0
                    with temp.open("wb" if start == 0 else "ab") as stream:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            stream.write(chunk)
                            written += len(chunk)
                    expected = end - start + 1
                    if written != expected:
                        raise IncompleteRead(b"", expected - written)
                    return chunk_meta
            except (HTTPError, URLError, TimeoutError, OSError, IncompleteRead) as exc:
                range_error = exc
                if temp.exists():
                    with temp.open("r+b") as stream:
                        stream.truncate(start)
                if isinstance(exc, HTTPError) and exc.code < 500 and exc.code != 429:
                    raise
                if chunk_attempt + 1 < retries:
                    sleep(min(2 ** chunk_attempt, 8))
        assert range_error is not None
        raise range_error

    for attempt in range(retries):
        try:
            if not use_range:
                with opener(Request(url, headers=request_headers), timeout=timeout) as response:
                    stream_full(response)
                break
            probe_headers = {**request_headers, "Range": "bytes=0-0"}
            with opener(Request(url, headers=probe_headers), timeout=timeout) as response:
                metadata = {"status": response.status,
                            "content_type": response.headers.get("Content-Type", "")}
                info = _parse_content_range(response.headers.get("Content-Range"))
                if response.status == 206 and info is not None and info[0] == 0:
                    total = info[2]
                elif response.status == 200:
                    stream_full(response)
                    break
                elif response.status == 206 and response.headers.get("Content-Range", "").endswith("/*"):
                    # Some official/CDN endpoints respond to a range probe
                    # with bytes 0-0/* even though a plain GET is complete.
                    # Do not treat one probed byte as an entire download.
                    with opener(Request(url, headers=request_headers), timeout=timeout) as full_response:
                        stream_full(full_response)
                    break
                else:
                    raise IncompleteRead(b"", 1)
            offset = 0
            while offset < total:
                end = min(offset + range_chunk_size - 1, total - 1)
                metadata = fetch_range(offset, end, total)
                offset = end + 1
            if temp.stat().st_size != total:
                raise IncompleteRead(b"", total - temp.stat().st_size)
            os.replace(temp, target)
            break
        except (HTTPError, URLError, TimeoutError, OSError, IncompleteRead) as exc:
            last_error = exc
            if temp.exists():
                temp.unlink()
            if isinstance(exc, HTTPError) and exc.code < 500 and exc.code != 429:
                raise
            if attempt + 1 < retries:
                sleep(min(2 ** attempt, 8))
    else:
        assert last_error is not None
        raise last_error
    entry = file_manifest_entry(target, url, content_type=metadata["content_type"],
                                http_status=metadata["status"],
                                retrieved_at_utc=datetime.now(timezone.utc).isoformat())
    manifest = Path(manifest_path)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    # Several bounded workers may append provenance entries concurrently.
    with manifest.open("a", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            stream.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    return entry
