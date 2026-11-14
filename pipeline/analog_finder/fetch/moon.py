"""Moon: LRO LOLA polar terrain and LRO Diviner polar resource product (NASA PDS)."""
from __future__ import annotations

from .pds import fetch_world


def fetch(dry_run: bool = False, ids=None, log=print):
    return fetch_world("moon", ids=ids, dry_run=dry_run, log=log)
