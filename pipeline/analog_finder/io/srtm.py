"""SRTMGL30 tiles (NASA SRTM Global 30 arc second, about 926 m).

Each tile is a zip such as ``e020n40.SRTMGL30.dem.zip`` with a headerless raster
``.dem`` (int16, big-endian, row 0 at the north) and usually a text ``.hdr``.
The tile name gives the upper-left corner: ``e020n40`` = 20 E, 40 N. Tiles are
40 degrees wide and 50 degrees high (4800 x 6000 pixels at 30 arc seconds).
Elevation is metres above the EGM96 geoid; -9999 marks no data (ocean).
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PIXEL_DEG = 1.0 / 120.0
TILE_COLS = 4800
NODATA_BELOW = -9000          # SRTM30 uses -9999
_NAME = re.compile(r"^([ew])(\d{3})([ns])(\d{2,3})", re.I)


@dataclass
class Tile:
    z: np.ndarray             # float32 metres, NaN where there is no data, shape (rows, cols)
    ul_lat: float             # latitude of the north edge
    ul_lon: float             # longitude of the west edge
    name: str


def tile_corner(name: str) -> tuple[float, float]:
    """(ul_lat, ul_lon) from a tile file name such as e020n40.SRTMGL30.dem.zip or W020N40.SRTMGL30.dem.zip."""
    m = _NAME.match(Path(name).name)
    if not m:
        raise ValueError(f"{name}: not an SRTMGL30 tile name (expected e020n40...)")
    ew, lon, ns, lat = m.groups()
    lon, lat = int(lon), int(lat)
    return (lat if ns.lower() == "n" else -lat), (lon if ew.lower() == "e" else -lon)


def _parse_hdr(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            out[parts[0].upper()] = parts[1]
    return out


def read_tile(path: str | Path) -> Tile:
    """Read one SRTMGL30 zip into a float32 array with NaN for no data."""
    path = Path(path)
    ul_lat, ul_lon = tile_corner(path.name)
    with zipfile.ZipFile(path) as z:
        names = {n.lower(): n for n in z.namelist()}
        dem = next((names[n] for n in names if n.endswith(".dem")), None)
        if dem is None:
            raise ValueError(f"{path.name}: no .dem file inside {sorted(names)}")
        raw = z.read(dem)
        hdr_name = next((names[n] for n in names if n.endswith(".hdr")), None)
        hdr = _parse_hdr(z.read(hdr_name).decode("ascii", "replace")) if hdr_name else {}
    cols = int(hdr.get("NCOLS", TILE_COLS))
    n_samples = len(raw) // 2
    if len(raw) % 2 or n_samples % cols:
        raise ValueError(f"{path.name}: {len(raw)} bytes do not fit {cols} columns of int16")
    rows = int(hdr.get("NROWS", n_samples // cols))
    if rows * cols != n_samples:
        raise ValueError(f"{path.name}: header says {rows} x {cols} but the file holds {n_samples} samples")
    byteorder = "<i2" if hdr.get("BYTEORDER", "M").upper() == "I" else ">i2"
    z = np.frombuffer(raw, dtype=byteorder).reshape(rows, cols).astype(np.float32)
    z[z < NODATA_BELOW] = np.nan
    if "ULXMAP" in hdr and "XDIM" in hdr:       # the header agrees with the file name, or the tile is mis-named
        west = float(hdr["ULXMAP"]) - float(hdr["XDIM"]) / 2.0
        if abs(west - ul_lon) > 0.1:
            raise ValueError(f"{path.name}: header puts the west edge at {west}, the name says {ul_lon}")
    return Tile(z=z, ul_lat=ul_lat, ul_lon=ul_lon, name=path.name)


def pixel_of(tile: Tile, lat: float, lon: float) -> tuple[int, int]:
    """(row, col) of the pixel that contains a point (clipped to the tile)."""
    row = int((tile.ul_lat - lat) / PIXEL_DEG)
    col = int((lon - tile.ul_lon) / PIXEL_DEG)
    return min(max(row, 0), tile.z.shape[0] - 1), min(max(col, 0), tile.z.shape[1] - 1)
