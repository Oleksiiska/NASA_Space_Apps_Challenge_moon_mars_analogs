"""Download the Moon and Mars files listed in config/sources.yaml from NASA PDS.

No login is needed. Every data file is checked against the byte size recorded
in the manifest (sizes were read from the PDS directory listings).
"""
from __future__ import annotations

from typing import Callable, Iterable, Optional

from .. import config
from .common import Result, download


def planned_files(ds: dict) -> list[dict]:
    """Expand one dataset into the list of files to fetch (data files and labels)."""
    base = ds.get("base_url", "").rstrip("/") + "/"
    out = []
    for f in ds.get("files", []):
        out.append({"name": f["name"], "url": f.get("url") or base + f["name"], "bytes": f.get("bytes")})
        if f.get("label"):
            out.append({"name": f["label"], "url": base + f["label"], "bytes": None})
    return out


def total_bytes(datasets: Iterable[dict]) -> int:
    return sum(f.get("bytes") or 0 for ds in datasets for f in ds.get("files", []))


def fetch_datasets(
    datasets: list[dict],
    dry_run: bool = False,
    log: Callable[[str], None] = print,
    session=None,
) -> list[Result]:
    results: list[Result] = []
    log(f"{len(datasets)} dataset(s), {total_bytes(datasets) / 1e9:.2f} GB of data files")
    for ds in datasets:
        dest_dir = config.resolve(ds["dest"])
        log(f"\n[{ds['id']}] {ds['title']}\n  -> {dest_dir}")
        for f in planned_files(ds):
            dest = dest_dir / f["name"]
            if dry_run:
                state = "present" if dest.exists() else "planned"
                size = f"{f['bytes'] / 1e6:8.1f} MB" if f["bytes"] else "   label   "
                log(f"  {state:8s} {size}  {f['url']}")
                results.append(Result(f["name"], state, f["bytes"] or 0))
                continue
            r = download(f["url"], dest, expected_bytes=f["bytes"], log=log, session=session)
            mark = "ok " if r.ok else "ERR"
            log(f"  {mark} {r.status:10s} {r.bytes / 1e6:8.1f} MB  {f['name']}  {r.message}")
            results.append(r)
    failed = [r for r in results if not r.ok]
    log(f"\nDone: {len(results) - len(failed)} ok, {len(failed)} failed")
    for r in failed:
        log(f"  failed: {r.name}: {r.message}")
    return results


def fetch_world(world: Optional[str], ids: Optional[list[str]] = None,
                dry_run: bool = False, log: Callable[[str], None] = print) -> list[Result]:
    """Fetch every open-access PDS dataset of one world ("moon", "mars") or of both (None)."""
    datasets = [d for d in config.datasets(world=world, access="open", ids=ids)
                if d.get("provider") == "pds"]
    return fetch_datasets(datasets, dry_run=dry_run, log=log)


def check(log: Callable[[str], None] = print) -> bool:
    """Compare local file sizes with the manifest. Returns True when all files are complete."""
    ok = True
    for ds in config.datasets(access="open"):
        if ds.get("provider") != "pds":
            continue
        dest_dir = config.resolve(ds["dest"])
        for f in ds.get("files", []):
            p = dest_dir / f["name"]
            if not p.exists():
                log(f"  missing  {ds['id']}/{f['name']}")
                ok = False
            elif f.get("bytes") and p.stat().st_size != f["bytes"]:
                log(f"  bad size {ds['id']}/{f['name']}: {p.stat().st_size} != {f['bytes']}")
                ok = False
            else:
                log(f"  ok       {ds['id']}/{f['name']}")
            lbl = f.get("label")
            if lbl and not (dest_dir / lbl).exists():
                log(f"  missing  {ds['id']}/{lbl}")
                ok = False
    return ok
