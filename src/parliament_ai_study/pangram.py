"""Pangram async API client and durable content-addressed response cache.

Paid requests are deliberately opt-in. A submission whose POST outcome is ambiguous
is not automatically retried: doing so could cause duplicate inference charges.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://text.external-api.pangram.com"


def request_fingerprint(text: str, configuration: dict[str, Any]) -> str:
    payload = json.dumps({"text": text, "configuration": configuration}, ensure_ascii=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ResponseCache:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def lock(self, fingerprint: str) -> Iterator[None]:
        """Serialize cache check-and-submit across threads and processes."""
        self._path(fingerprint)  # validate before constructing a lock path
        lock_path = self.directory / f"{fingerprint}.lock"
        with lock_path.open("a+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def _path(self, fingerprint: str) -> Path:
        if len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint):
            raise ValueError("fingerprint must be a lowercase SHA-256 hex digest")
        return self.directory / f"{fingerprint}.json"

    def load(self, fingerprint: str) -> dict[str, Any] | None:
        path = self._path(fingerprint)
        if not path.exists():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") != "complete":
            return None
        return record["response"]

    def store(self, fingerprint: str, response: dict[str, Any]) -> None:
        if response.get("stage") not in ("STAGE_SUCCESS", "success", "complete"):
            raise ValueError("only completed Pangram responses may be cached")
        self._write(fingerprint, {"status": "complete", "response": response})

    def state(self, fingerprint: str) -> dict[str, Any] | None:
        path = self._path(fingerprint)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def pending(self, fingerprint: str) -> dict[str, Any] | None:
        record = self.state(fingerprint)
        return record if record and record.get("status") == "pending" else None

    def save_pending(self, fingerprint: str, task_id: str) -> None:
        self._write(fingerprint, {"status": "pending", "task_id": task_id})

    def mark_unknown(self, fingerprint: str, message: str) -> None:
        self._write(fingerprint, {"status": "submission_unknown", "error": message})

    def _write(self, fingerprint: str, record: dict[str, Any]) -> None:
        path = self._path(fingerprint)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)


class PangramClient:
    def __init__(self, api_key: str, *, model: str, timeout: float = 30,
                 max_poll_attempts: int = 120, poll_interval: float = 2,
                 max_backoff: float = 30, opener: Callable[..., Any] | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        if not api_key:
            raise ValueError("PANGRAM_API_KEY is required")
        if not model:
            raise ValueError("an explicit Pangram model selector is required")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_poll_attempts = max_poll_attempts
        self.poll_interval = poll_interval
        self.max_backoff = max_backoff
        self.opener = opener or urlopen
        self.sleep = sleep

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(API_BASE + path, data=data, method=method, headers={
            "x-api-key": self.api_key, "Content-Type": "application/json", "Accept": "application/json"})
        with self.opener(request, timeout=self.timeout) as response:
            body = response.read()
        parsed = json.loads(body.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Pangram response must be a JSON object")
        return parsed

    def available_models(self) -> list[str]:
        """Read-only entitlement check before any billable task submission."""
        response = self._request("GET", "/models")
        models = response.get("models")
        if not isinstance(models, list) or not all(isinstance(item, str) for item in models):
            raise ValueError("Pangram model catalog has invalid format")
        return models

    def analyze(self, text: str, cache: ResponseCache, *, allow_paid: bool = False) -> dict[str, Any]:
        configuration = {"model": self.model, "public_dashboard_link": False}
        fingerprint = request_fingerprint(text, configuration)
        with cache.lock(fingerprint):
            return self._analyze_locked(text, cache, fingerprint, allow_paid=allow_paid)

    def _analyze_locked(self, text: str, cache: ResponseCache, fingerprint: str,
                        *, allow_paid: bool) -> dict[str, Any]:
        cached = cache.load(fingerprint)
        if cached is not None:
            return cached
        state = cache.state(fingerprint)
        if state and state.get("status") == "submission_unknown":
            raise RuntimeError("previous POST outcome is ambiguous; inspect Pangram before resetting this cache entry")
        pending = cache.pending(fingerprint)
        if pending is None:
            if not allow_paid:
                raise PermissionError("paid Pangram inference requires explicit authorization")
            for attempt in range(8):
                try:
                    created = self._request("POST", "/task", {
                        "text": text, "model": self.model, "public_dashboard_link": False})
                    break
                except HTTPError as exc:
                    # The server rejected a rate-limited request. Only this
                    # explicit non-acceptance is safe to retry automatically.
                    if exc.code == 429 and attempt < 7:
                        retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                        wait = float(retry_after) if retry_after.isdigit() else min(2 ** attempt, self.max_backoff)
                        self.sleep(min(wait, self.max_backoff))
                        continue
                    if exc.code == 429 or exc.code in (400, 401, 402, 403, 413, 422):
                        raise
                    cache.mark_unknown(fingerprint, f"POST HTTP status {exc.code}; billing outcome unknown")
                    raise RuntimeError("submission outcome unknown; refusing automatic resubmission") from exc
                except (URLError, TimeoutError, OSError) as exc:
                    cache.mark_unknown(fingerprint, f"POST outcome may be ambiguous: {type(exc).__name__}")
                    raise RuntimeError("submission outcome unknown; refusing automatic resubmission") from exc
            task_id = created.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                cache.mark_unknown(fingerprint, "POST response did not include task_id")
                raise ValueError("Pangram POST response missing task_id; refusing resubmission")
            cache.save_pending(fingerprint, task_id)
            pending = {"task_id": task_id}
        task_id = pending["task_id"]
        for attempt in range(self.max_poll_attempts):
            try:
                result = self._request("GET", f"/task/{task_id}")
            except (HTTPError, URLError, TimeoutError, OSError):
                if attempt + 1 >= self.max_poll_attempts:
                    raise
                self.sleep(min(self.poll_interval * (2 ** min(attempt, 8)), self.max_backoff))
                continue
            stage = result.get("stage")
            if stage == "STAGE_SUCCESS":
                self._validate_result(result)
                cache.store(fingerprint, result)
                return result
            if stage == "STAGE_FAILED":
                raise RuntimeError(f"Pangram task {task_id} failed: {result.get('error', 'unspecified error')}")
            if stage is not None and not str(stage).startswith("STAGE_"):
                raise ValueError(f"unexpected Pangram task stage: {stage!r}")
            if attempt + 1 < self.max_poll_attempts:
                self.sleep(min(self.poll_interval * (2 ** min(attempt, 8)), self.max_backoff))
        raise TimeoutError(f"Pangram task {task_id} did not complete within the polling limit")

    @staticmethod
    def _validate_result(result: dict[str, Any]) -> None:
        for key in ("fraction_ai", "fraction_ai_assisted", "fraction_human"):
            value = result.get(key)
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"successful Pangram response has invalid {key}")
        if result["fraction_ai"] + result["fraction_ai_assisted"] + result["fraction_human"] > 1.00001:
            raise ValueError("Pangram fractions sum to more than 1")
