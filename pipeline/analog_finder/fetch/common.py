"""Resumable HTTP download with a size check.

A download goes to ``<name>.part`` and is renamed only when complete, so an
interrupted run never leaves a truncated file under the final name.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests

CHUNK = 1 << 20  # 1 MiB
USER_AGENT = "analog-finder/0.1 (NASA Space Apps 2026 team project)"


@dataclass
class Result:
    name: str
    status: str  # present | downloaded | resumed | failed | planned
    bytes: int = 0
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status != "failed"


def _mb(n: float) -> str:
    return f"{n / 1e6:.1f} MB"


def download(
    url: str,
    dest: Path,
    expected_bytes: Optional[int] = None,
    retries: int = 5,
    timeout: tuple[float, float] = (20, 120),
    session: Optional[requests.Session] = None,
    log: Callable[[str], None] = print,
    backoff: float = 2.0,
) -> Result:
    """Download ``url`` to ``dest``; resume a partial file when the server allows it."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")

    if dest.exists():
        size = dest.stat().st_size
        if expected_bytes is None or size == expected_bytes:
            return Result(dest.name, "present", size)
        if size < expected_bytes and not part.exists():
            os.replace(dest, part)  # treat a short file as a partial download
        else:
            dest.unlink()

    own_session = session is None
    s = session or requests.Session()
    resumed = False
    last_error = ""
    try:
        for attempt in range(1, retries + 1):
            have = part.stat().st_size if part.exists() else 0
            if expected_bytes is not None:
                if have == expected_bytes:
                    break
                if have > expected_bytes:
                    part.unlink()
                    have = 0
            headers = {"User-Agent": USER_AGENT}
            if have:
                headers["Range"] = f"bytes={have}-"
            try:
                with s.get(url, headers=headers, stream=True, timeout=timeout) as r:
                    if r.status_code == 416:  # our partial file does not match the server's
                        part.unlink(missing_ok=True)
                        last_error = "HTTP 416, restarting from zero"
                        continue
                    if r.status_code in (401, 403, 404):
                        return Result(dest.name, "failed", have, f"HTTP {r.status_code} for {url}")
                    r.raise_for_status()
                    if have and r.status_code == 200:
                        have = 0  # server ignored Range: start over
                    mode = "ab" if have else "wb"
                    resumed = resumed or bool(have)
                    total = expected_bytes
                    if total is None and r.headers.get("Content-Length"):
                        total = have + int(r.headers["Content-Length"])
                    done, shown, t0 = have, time.monotonic(), time.monotonic()
                    with open(part, mode) as f:
                        for chunk in r.iter_content(CHUNK):
                            if not chunk:
                                continue
                            f.write(chunk)
                            done += len(chunk)
                            now = time.monotonic()
                            if now - shown >= 5:
                                shown = now
                                pct = f"{100 * done / total:5.1f}%" if total else ""
                                speed = (done - have) / max(now - t0, 1e-6)
                                log(f"    {dest.name}: {pct} {_mb(done)} ({_mb(speed)}/s)")
                size = part.stat().st_size
                if expected_bytes is None or size == expected_bytes:
                    break
                last_error = f"got {size} of {expected_bytes} bytes"
            except (requests.RequestException, OSError) as e:
                last_error = f"{type(e).__name__}: {e}"
            if attempt < retries:
                time.sleep(min(backoff * attempt, 30))
        size = part.stat().st_size if part.exists() else 0
        if size == 0 or (expected_bytes is not None and size != expected_bytes):
            return Result(dest.name, "failed", size, last_error or "incomplete download")
        os.replace(part, dest)
        return Result(dest.name, "resumed" if resumed else "downloaded", size)
    finally:
        if own_session:
            s.close()
