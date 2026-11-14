"""ASCII tables from NASA PDS: Diviner Polar Resource Product and GRS element maps."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import numpy as np

# 1-based byte offsets from the PDS4 label dlre_prp_south.xml (Table_Character, 210-byte records)
DIVINER_PRP_LAYOUT = {
    "tri_clon": (127, 15),
    "tri_clat": (144, 15),
    "tri_calt": (161, 15),
    "temp_avg": (178, 8),
    "temp_max": (188, 8),
    "ice_depth": (198, 11),
}
ICE_DEPTH_TOO_DEEP = -999.0     # ice stable only deeper than 2.87 m (limit of the model)


def _record_length(path: Path) -> int:
    with open(path, "rb") as f:
        head = f.read(4096)
    nl = head.find(b"\n")
    if nl < 0:
        raise ValueError(f"{path.name}: no line break in the first 4096 bytes")
    return nl + 1


def read_diviner_prp(path: str | Path, fields: Iterable[str] = ("tri_clon", "tri_clat", "temp_avg", "temp_max", "ice_depth"),
                     layout: Optional[dict] = None, max_rows: Optional[int] = None) -> dict[str, np.ndarray]:
    """Read selected columns of the Diviner PRP table (2.88 million rows) into float arrays.

    Fast path: fixed-width columns straight from a memory map. If the header does
    not match the expected layout, the columns are located by header name instead.
    """
    path = Path(path)
    layout = layout or DIVINER_PRP_LAYOUT
    fields = list(fields)
    rec = _record_length(path)
    size = path.stat().st_size
    if size <= rec:
        raise ValueError(f"{path.name}: no data rows")
    with open(path, "rb") as f:
        header = f.read(rec).decode("ascii", errors="replace")

    def header_ok(name: str) -> bool:
        start, length = layout[name]
        return name in header[max(start - 2, 0): start - 1 + length + 1]

    fixed_width = size % rec == 0 and all(name in layout and header_ok(name) for name in fields)
    if fixed_width:
        n = size // rec - 1
        if max_rows:
            n = min(n, max_rows)
        mm = np.memmap(path, dtype=np.uint8, mode="r", offset=rec, shape=(n, rec))
        out = {}
        for name in fields:
            start, length = layout[name]
            raw = np.ascontiguousarray(mm[:, start - 1: start - 1 + length])
            out[name] = raw.view(f"S{length}").ravel().astype(np.float64)
        return out

    # Fallback: locate columns by header names, split on commas or whitespace
    sep = "," if "," in header else None
    names = [h.strip() for h in (header.split(",") if sep else header.split())]
    missing = [f for f in fields if f not in names]
    if missing:
        raise ValueError(f"{path.name}: columns {missing} not found in header {names}")
    cols = [names.index(f) for f in fields]
    arr = np.loadtxt(path, delimiter=sep, skiprows=1, usecols=cols, max_rows=max_rows, ndmin=2)
    return {name: arr[:, k] for k, name in enumerate(fields)}


def read_grs_table(path: str | Path, missing: float = 9999.999) -> dict[str, np.ndarray]:
    """Read a GRS element map (*_sr_5x5.tab): centre latitude, centre longitude, value, sigma.

    Longitude is returned east-positive in 0..360. Missing values become NaN.
    """
    rows = []
    with open(path, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            parts = line.replace(",", " ").split()
            try:
                rows.append([float(p) for p in parts])
            except ValueError:
                continue  # header or comment line
    if not rows:
        raise ValueError(f"{Path(path).name}: no numeric rows")
    width = min(len(r) for r in rows)
    arr = np.array([r[:width] for r in rows], dtype=np.float64)
    arr[np.isclose(arr, missing)] = np.nan
    out = {"lat": arr[:, 0], "lon": arr[:, 1] % 360.0, "value": arr[:, 2]}
    if width > 3:
        out["sigma"] = arr[:, 3]
    return out


def nearest_bin(table: dict[str, np.ndarray], lat: float, lon_e: float) -> dict[str, float]:
    """Value of the table bin whose centre is nearest to the point (great-circle distance)."""
    la, lo = np.radians(table["lat"]), np.radians(table["lon"])
    la0, lo0 = np.radians(lat), np.radians(lon_e % 360.0)
    cosd = np.sin(la) * np.sin(la0) + np.cos(la) * np.cos(la0) * np.cos(lo - lo0)
    k = int(np.nanargmax(cosd))
    out = {"lat": float(table["lat"][k]), "lon": float(table["lon"][k]), "value": float(table["value"][k])}
    if "sigma" in table:
        out["sigma"] = float(table["sigma"][k])
    return out
