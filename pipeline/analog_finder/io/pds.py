"""PDS3 detached labels (.lbl) and their binary images (.img).

Covers the two products the project uses:
  * LRO LOLA polar GDR  - int16 little-endian, polar stereographic,
                          height_m = DN * SCALING_FACTOR above a 1737.4 km sphere
  * MGS MOLA MEGDR      - int16 big-endian, simple cylindrical, metres above the areoid

Georeferencing does not rely on LINE/SAMPLE_PROJECTION_OFFSET, because the two
products use different conventions for them. Instead:
  * cylindrical:        MAXIMUM_LATITUDE, WESTERNMOST_LONGITUDE and MAP_RESOLUTION
  * polar stereographic: the pole is at the exact centre of the (square) image
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

_UNIT = re.compile(r"<([^>]*)>")
_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_MISSING = object()

_DTYPES = {
    "LSB_INTEGER": "<i", "PC_INTEGER": "<i", "VAX_INTEGER": "<i",
    "MSB_INTEGER": ">i", "SUN_INTEGER": ">i", "MAC_INTEGER": ">i", "INTEGER": ">i",
    "LSB_UNSIGNED_INTEGER": "<u", "PC_UNSIGNED_INTEGER": "<u",
    "MSB_UNSIGNED_INTEGER": ">u", "UNSIGNED_INTEGER": ">u",
    "PC_REAL": "<f", "IEEE_REAL": ">f", "REAL": ">f", "SUN_REAL": ">f", "MAC_REAL": ">f",
}


def _convert(raw: str) -> Any:
    v = raw.strip()
    if v.startswith("(") and v.endswith(")"):
        return [_convert(x) for x in v[1:-1].split(",") if x.strip()]
    v = _UNIT.sub("", v).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].strip()
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def parse_label(path: str | Path) -> dict:
    """Parse a PDS3 label into a dict.

    Top-level keywords are keys of the result. Keywords inside an
    ``OBJECT = NAME`` block go into ``result[NAME]``. Units are kept in
    ``result["_units"]`` (flat: keyword -> unit, first occurrence wins).
    """
    text = Path(path).read_text(encoding="latin-1")
    text = _COMMENT.sub(" ", text)
    out: dict = {"_units": {}}
    stack: list[dict] = [out]
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if line == "END":
            break
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        # multi-line quoted strings and lists
        for opener, closer in (('"', '"'), ("(", ")")):
            if value.startswith(opener):
                while (value.count('"') % 2 == 1 if opener == '"' else closer not in value) and i < len(lines):
                    value += " " + lines[i].strip()
                    i += 1
                break
        if key in ("OBJECT", "GROUP"):
            block: dict = {}
            stack[-1].setdefault(value, block)
            stack.append(stack[-1][value])
            continue
        if key in ("END_OBJECT", "END_GROUP"):
            if len(stack) > 1:
                stack.pop()
            continue
        unit = _UNIT.search(value)
        if unit:
            out["_units"].setdefault(key, unit.group(1).strip())
        stack[-1].setdefault(key, _convert(value))
    return out


def _find(label: dict, key: str, default: Any = None) -> Any:
    """Look a keyword up at top level, then in nested OBJECT blocks (any depth, first match).

    Real labels nest blocks: LOLA puts ^IMAGE, RECORD_BYTES and the IMAGE object
    inside OBJECT = UNCOMPRESSED_FILE.
    """
    if key in label:
        return label[key]
    for name, v in label.items():
        if not name.startswith("_") and isinstance(v, dict):
            found = _find(v, key, _MISSING)
            if found is not _MISSING:
                return found
    return default


def _block(label: dict, name: str) -> dict:
    """The OBJECT block called ``name`` at any depth, or an empty dict."""
    v = label.get(name)
    if isinstance(v, dict):
        return v
    for k, sub in label.items():
        if not k.startswith("_") and isinstance(sub, dict):
            found = _block(sub, name)
            if found:
                return found
    return {}


def _num(label: dict, key: str, default: Optional[float] = None) -> Optional[float]:
    v = _find(label, key, default)
    return float(v) if isinstance(v, (int, float)) else default


def _sibling(lbl: Path, name: Optional[str]) -> Optional[Path]:
    """Find a data file next to the label, ignoring letter case."""
    wanted = [name.lower()] if name else []
    wanted += [lbl.stem.lower() + ext for ext in (".img", ".dat")]
    by_lower = {p.name.lower(): p for p in lbl.parent.iterdir() if p.is_file()}
    for w in wanted:
        if w in by_lower:
            return by_lower[w]
    return None


@dataclass
class PdsImage:
    data: np.ndarray            # raw DN, shape (lines, samples)
    label: dict
    path: Path
    scale: float = 1.0
    offset: float = 0.0
    geo: Optional["Georef"] = field(default=None)

    @property
    def shape(self) -> tuple[int, int]:
        return self.data.shape

    def height(self, rows: slice = slice(None), cols: slice = slice(None)) -> np.ndarray:
        """Elevation in metres relative to the reference surface (DN * scale)."""
        return self.data[rows, cols].astype(np.float32) * np.float32(self.scale)

    def physical(self, rows: slice = slice(None), cols: slice = slice(None)) -> np.ndarray:
        """DN * scale + offset (for LOLA this is the planetary radius in metres)."""
        return self.data[rows, cols].astype(np.float64) * self.scale + self.offset


def read_image(lbl_path: str | Path, img_path: str | Path | None = None,
               memmap: bool = True) -> PdsImage:
    lbl_path = Path(lbl_path)
    label = parse_label(lbl_path)
    image = _block(label, "IMAGE")
    lines, samples = _find(image, "LINES"), _find(image, "LINE_SAMPLES")
    if lines is None or samples is None:
        lines, samples = _find(label, "LINES"), _find(label, "LINE_SAMPLES")
    if lines is None or samples is None:
        raise ValueError(f"{lbl_path.name}: no LINES / LINE_SAMPLES in the label (found blocks: "
                         f"{[k for k, v in label.items() if isinstance(v, dict)]})")
    lines, samples = int(lines), int(samples)
    sample_type = str(_find(image, "SAMPLE_TYPE", "MSB_INTEGER")).upper()
    bits = int(_find(image, "SAMPLE_BITS", 16))
    if sample_type not in _DTYPES:
        raise ValueError(f"{lbl_path.name}: unsupported SAMPLE_TYPE {sample_type}")
    dtype = np.dtype(f"{_DTYPES[sample_type]}{bits // 8}")

    pointer = _find(label, "^IMAGE")
    name, record = None, 1
    if isinstance(pointer, list):
        for item in pointer:
            if isinstance(item, str):
                name = item
            elif isinstance(item, (int, float)):
                record = int(item)
    elif isinstance(pointer, str):
        name = pointer
    elif isinstance(pointer, (int, float)):
        record = int(pointer)  # attached label: data start at this record of the same file
    if img_path is None:
        img_path = lbl_path if (name is None and isinstance(pointer, (int, float))) else _sibling(lbl_path, name)
    if img_path is None or not Path(img_path).exists():
        raise FileNotFoundError(f"Image file for {lbl_path.name} not found (expected {name or lbl_path.stem + '.img'})")
    img_path = Path(img_path)
    offset_bytes = (record - 1) * int(_find(label, "RECORD_BYTES", 0) or 0)
    need = offset_bytes + lines * samples * dtype.itemsize
    size = img_path.stat().st_size
    if size < need:
        raise ValueError(f"{img_path.name}: file has {size} bytes, label needs {need} (incomplete download?)")
    if memmap:
        data = np.memmap(img_path, dtype=dtype, mode="r", offset=offset_bytes, shape=(lines, samples))
    else:
        data = np.fromfile(img_path, dtype=dtype, count=lines * samples, offset=offset_bytes).reshape(lines, samples)
    scale = float(_find(image, "SCALING_FACTOR", 1.0) or 1.0)
    offset = float(_find(image, "OFFSET", 0.0) or 0.0)
    img = PdsImage(data=data, label=label, path=img_path, scale=scale, offset=offset)
    img.geo = Georef.from_label(label, (lines, samples))
    return img


# --------------------------------------------------------------------------- georeferencing

@dataclass
class Georef:
    kind: str                 # "cylindrical" | "polar_stereo"
    shape: tuple[int, int]
    radius_m: float
    # cylindrical
    res: float = 0.0          # pixels per degree
    max_lat: float = 90.0
    west_lon: float = 0.0
    # polar stereographic
    scale_m: float = 0.0      # metres per pixel
    pole: int = -1            # -1 south, +1 north
    center_lon: float = 0.0

    @staticmethod
    def from_label(label: dict, shape: tuple[int, int]) -> Optional["Georef"]:
        proj = str(_find(label, "MAP_PROJECTION_TYPE", "")).upper()
        radius_km = _num(label, "A_AXIS_RADIUS")
        if radius_km is None:
            return None
        radius_m = radius_km * 1000.0
        if "CYLINDRICAL" in proj or "EQUIRECTANGULAR" in proj:
            res = _num(label, "MAP_RESOLUTION")
            max_lat = _num(label, "MAXIMUM_LATITUDE")
            west = _num(label, "WESTERNMOST_LONGITUDE", 0.0)
            if res is None or max_lat is None:
                return None
            return Georef("cylindrical", shape, radius_m, res=res, max_lat=max_lat, west_lon=west or 0.0)
        if "STEREOGRAPHIC" in proj:
            scale = _num(label, "MAP_SCALE")
            if scale is None:
                return None
            unit = str(label.get("_units", {}).get("MAP_SCALE", "")).lower()
            if "km" in unit or (not unit and scale < 1.0):
                scale *= 1000.0
            center_lat = _num(label, "CENTER_LATITUDE", -90.0)
            return Georef("polar_stereo", shape, radius_m, scale_m=scale,
                          pole=1 if center_lat > 0 else -1,
                          center_lon=_num(label, "CENTER_LONGITUDE", 0.0) or 0.0)
        return None

    # ---- forward: lat/lon (degrees, east-positive) -> fractional row/col (0-based pixel centres)
    def rowcol(self, lat: float, lon: float) -> tuple[float, float]:
        if self.kind == "cylindrical":
            row = (self.max_lat - lat) * self.res - 0.5
            col = ((lon - self.west_lon) % 360.0) * self.res - 0.5
            return row, col
        x, y = self.xy(lat, lon)
        r0, c0 = (self.shape[0] - 1) / 2.0, (self.shape[1] - 1) / 2.0
        return r0 - y / self.scale_m, c0 + x / self.scale_m

    def latlon(self, row: float, col: float) -> tuple[float, float]:
        if self.kind == "cylindrical":
            lat = self.max_lat - (row + 0.5) / self.res
            lon = (self.west_lon + (col + 0.5) / self.res) % 360.0
            return lat, lon
        r0, c0 = (self.shape[0] - 1) / 2.0, (self.shape[1] - 1) / 2.0
        x, y = (col - c0) * self.scale_m, (r0 - row) * self.scale_m
        rho = math.hypot(x, y)
        colat = math.degrees(2.0 * math.atan(rho / (2.0 * self.radius_m)))
        lat = self.pole * (90.0 - colat)
        lon = math.degrees(math.atan2(x, y if self.pole < 0 else -y)) + self.center_lon
        return lat, lon % 360.0

    def xy(self, lat: float, lon: float) -> tuple[float, float]:
        """Polar stereographic metres (sphere, true scale at the pole)."""
        colat = math.radians(90.0 - abs(lat))
        rho = 2.0 * self.radius_m * math.tan(colat / 2.0)
        lam = math.radians(lon - self.center_lon)
        x = rho * math.sin(lam)
        y = rho * math.cos(lam) * (1.0 if self.pole < 0 else -1.0)
        return x, y

    def pixel_size_m(self, lat: float) -> tuple[float, float]:
        """(dx, dy) ground size of a pixel in metres near the given latitude."""
        if self.kind == "cylindrical":
            deg = math.pi * self.radius_m / 180.0
            return deg * math.cos(math.radians(lat)) / self.res, deg / self.res
        # stereographic scale factor k = 2 / (1 + sin|lat|); ground size = map size / k
        k = 2.0 / (1.0 + math.sin(math.radians(abs(lat))))
        return self.scale_m / k, self.scale_m / k

    def window(self, lat: float, lon: float, radius_m: float) -> tuple[slice, slice, bool]:
        """Row/column slices of the bounding box of a circle; third value is True when clipped."""
        row, col = self.rowcol(lat, lon)
        dx, dy = self.pixel_size_m(lat)
        hr, hc = radius_m / dy, radius_m / dx
        r0, r1 = int(math.floor(row - hr)), int(math.ceil(row + hr)) + 1
        c0, c1 = int(math.floor(col - hc)), int(math.ceil(col + hc)) + 1
        n_r, n_c = self.shape
        clipped = r0 < 0 or c0 < 0 or r1 > n_r or c1 > n_c
        return slice(max(r0, 0), min(r1, n_r)), slice(max(c0, 0), min(c1, n_c)), clipped


def mola_tile_bounds(name: str) -> Optional[tuple[float, float, float]]:
    """(top latitude, west longitude, pixels per degree) from a MEGDR file name such as megt90n180gb."""
    m = re.match(r"meg[a-z](\d{2})([ns])(\d{3})([a-z])b", name.lower())
    if not m:
        return None
    lat = float(m.group(1)) * (1.0 if m.group(2) == "n" else -1.0)
    res = {"c": 4, "e": 16, "f": 32, "g": 64, "h": 128}.get(m.group(4))
    return (lat, float(m.group(3)), float(res)) if res else None
