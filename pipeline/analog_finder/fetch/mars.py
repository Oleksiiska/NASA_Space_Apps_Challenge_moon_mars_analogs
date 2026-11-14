"""Mars: MGS MOLA gridded topography and Mars Odyssey GRS element maps (NASA PDS)."""
from __future__ import annotations

from .pds import fetch_world


def fetch(dry_run: bool = False, ids=None, log=print):
    return fetch_world("mars", ids=ids, dry_run=dry_run, log=log)
