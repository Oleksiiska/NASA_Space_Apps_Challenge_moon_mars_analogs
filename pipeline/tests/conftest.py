"""Shared fixtures: a temporary project root with the real configs and synthetic raw data."""
from __future__ import annotations

import http.server
import shutil
import threading
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]

LOLA_LABEL = """PDS_VERSION_ID            = "PDS3"
/*** FILE FORMAT ***/
RECORD_TYPE               = FIXED_LENGTH
DATA_SET_ID               = "LRO-L-LOLA-4-GDR-V1.0"
OBJECT                    = UNCOMPRESSED_FILE
FILE_RECORDS              = {n}
RECORD_BYTES              = {record_bytes}
^IMAGE                    = "LDEM_75S_240M.IMG"
DESCRIPTION               = "Synthetic test surface.
   HEIGHT = DN * SCALING_FACTOR; PLANETARY_RADIUS = DN * SCALING_FACTOR + OFFSET"
OBJECT                    = IMAGE
 NAME                     = HEIGHT
 LINES                    = {n}
 LINE_SAMPLES             = {n}
 SAMPLE_TYPE              = LSB_INTEGER
 SAMPLE_BITS              = 16
 UNIT                     = METER
 SCALING_FACTOR           = 0.5
 OFFSET                   = 1737400.
END_OBJECT                = IMAGE
END_OBJECT                = UNCOMPRESSED_FILE
OBJECT                    = IMAGE_MAP_PROJECTION
 MAP_PROJECTION_TYPE      = "POLAR STEREOGRAPHIC"
 MAP_RESOLUTION           = 126.347 <pix/deg>
 A_AXIS_RADIUS            = 1737.4 <km>
 B_AXIS_RADIUS            = 1737.4 <km>
 C_AXIS_RADIUS            = 1737.4 <km>
 FIRST_STANDARD_PARALLEL  = 'N/A'
 POSITIVE_LONGITUDE_DIRECTION = "EAST"
 CENTER_LATITUDE          = -90 <deg>
 CENTER_LONGITUDE         = 0 <deg>
 MAP_SCALE                = {scale} <m/pix>
 MAXIMUM_LATITUDE         = -75 <deg>
 MINIMUM_LATITUDE         = -90 <deg>
 WESTERNMOST_LONGITUDE    = 'N/A'
 EASTERNMOST_LONGITUDE    = 'N/A'
 LINE_PROJECTION_OFFSET   = {off} <pix>
 SAMPLE_PROJECTION_OFFSET = {off} <pix>
 COORDINATE_SYSTEM_TYPE   = "BODY-FIXED ROTATING"
 COORDINATE_SYSTEM_NAME   = "MEAN EARTH/POLAR AXIS OF DE421"
END_OBJECT                = IMAGE_MAP_PROJECTION
END
"""

MOLA_LABEL = """PDS_VERSION_ID            = PDS3
RECORD_TYPE               = FIXED_LENGTH
RECORD_BYTES              = {record_bytes}
FILE_RECORDS              = {lines}
^IMAGE                    = "MEGT90N000EB.IMG"
OBJECT                    = IMAGE
 NAME                     = MEDIAN_TOPOGRAPHY
 LINES                    = {lines}
 LINE_SAMPLES             = {samples}
 SAMPLE_TYPE              = MSB_INTEGER
 SAMPLE_BITS              = 16
 UNIT                     = METER
END_OBJECT                = IMAGE
OBJECT                    = IMAGE_MAP_PROJECTION
 MAP_PROJECTION_TYPE      = "SIMPLE CYLINDRICAL"
 A_AXIS_RADIUS            = 3396.0 <KM>
 B_AXIS_RADIUS            = 3396.0 <KM>
 C_AXIS_RADIUS            = 3396.0 <KM>
 FIRST_STANDARD_PARALLEL  = "N/A"
 POSITIVE_LONGITUDE_DIRECTION = "EAST"
 CENTER_LATITUDE          = 0.0 <DEGREE>
 CENTER_LONGITUDE         = 180.0 <DEGREE>
 MAP_RESOLUTION           = {res} <PIXEL/DEGREE>
 MAP_SCALE                = 3.705 <KM/PIXEL>
 MAXIMUM_LATITUDE         = 90.0 <DEGREE>
 MINIMUM_LATITUDE         = -90.0 <DEGREE>
 WESTERNMOST_LONGITUDE    = 0.0 <DEGREE>
 EASTERNMOST_LONGITUDE    = 360.0 <DEGREE>
 LINE_PROJECTION_OFFSET   = {lo}
 SAMPLE_PROJECTION_OFFSET = {so}
 COORDINATE_SYSTEM_TYPE   = "BODY-FIXED ROTATING"
 COORDINATE_SYSTEM_NAME   = "PLANETOCENTRIC"
END_OBJECT                = IMAGE_MAP_PROJECTION
END
"""

MOON_R = 1737400.0
MARS_R = 3396000.0


def moon_xy(lat, lon):
    """South polar stereographic metres, computed independently of the package code."""
    colat = np.radians(90.0 + np.asarray(lat, dtype=float))
    rho = 2.0 * MOON_R * np.tan(colat / 2.0)
    lam = np.radians(lon)
    return rho * np.sin(lam), rho * np.cos(lam)


def gauss(x, y, x0, y0, sigma):
    return np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2.0 * sigma ** 2))


def write_synthetic_lola(folder: Path, n: int = 1001, scale: float = 480.0) -> Path:
    """LOLA-like polar DEM with a deep pit at Shackleton and a mountain at Mons Mouton."""
    folder.mkdir(parents=True, exist_ok=True)
    c = (n - 1) / 2.0
    cols, rows = np.meshgrid(np.arange(n), np.arange(n))
    x, y = (cols - c) * scale, (c - rows) * scale
    sx, sy = moon_xy(-89.67, 129.78)
    mx, my = moon_xy(-84.6, 31.0)
    z = -3500.0 * gauss(x, y, sx, sy, 6000.0) + 6000.0 * gauss(x, y, mx, my, 25000.0)
    dn = np.rint(z / 0.5).astype("<i2")
    dn.tofile(folder / "ldem_75s_240m.img")
    (folder / "ldem_75s_240m.lbl").write_text(
        LOLA_LABEL.format(n=n, record_bytes=n * 2, scale=f"{scale:g}", off=c), encoding="ascii")
    return folder / "ldem_75s_240m.lbl"


def write_synthetic_mola(folder: Path, res: int = 8) -> Path:
    """MOLA-like global grid: Olympus Mons, Hellas and a uniform 2-degree northward tilt near Jezero."""
    folder.mkdir(parents=True, exist_ok=True)
    lines, samples = 180 * res, 360 * res
    lat = 90.0 - (np.arange(lines) + 0.5) / res
    lon = (np.arange(samples) + 0.5) / res
    lon2, lat2 = np.meshgrid(lon, lat)
    deg_m = np.pi * MARS_R / 180.0
    z = np.zeros((lines, samples))
    z += 21000.0 * np.exp(-(((lat2 - 18.65) * deg_m) ** 2 + ((lon2 - 226.2) * deg_m * np.cos(np.radians(18.65))) ** 2) / (2 * 150e3 ** 2))
    z -= 8000.0 * np.exp(-(((lat2 + 42.7) * deg_m) ** 2 + ((lon2 - 70.0) * deg_m * np.cos(np.radians(42.7))) ** 2) / (2 * 600e3 ** 2))
    tilt = np.tan(np.radians(2.0)) * (lat2 - 18.44) * deg_m      # 2 degree slope, rising to the north
    near = (np.abs(lat2 - 18.44) < 6) & (np.abs(lon2 - 77.45) < 6)
    z = np.where(near, tilt, z)
    np.rint(z).astype(">i2").tofile(folder / "megt90n000eb.img")
    (folder / "megt90n000eb.lbl").write_text(
        MOLA_LABEL.format(lines=lines, samples=samples, record_bytes=samples * 2, res=f"{res:.1f}",
                          lo=lines / 2 + 0.5, so=samples / 2 + 0.5), encoding="ascii")
    return folder / "megt90n000eb.lbl"


def write_synthetic_prp(path: Path, n: int = 5000, seed: int = 1) -> dict:
    """Diviner PRP-like fixed-width table (210-byte records incl. CRLF, header first)."""
    rng = np.random.default_rng(seed)
    lat = -90.0 + rng.uniform(0.0, 6.0, n)
    lon = rng.uniform(0.0, 360.0, n)
    t_avg = rng.uniform(30.0, 200.0, n)
    t_max = t_avg + rng.uniform(5.0, 150.0, n)
    ice = np.where(t_avg < 90, 0.0, np.where(t_avg < 130, rng.uniform(0.01, 2.8, n), -999.0))
    names = ["tri1_x", "tri1_y", "tri1_z", "tri2_x", "tri2_y", "tri2_z", "tri3_x", "tri3_y", "tri3_z",
             "tri_clon", "tri_clat", "tri_calt", "temp_avg", "temp_max", "ice_depth"]
    starts = [1, 15, 29, 43, 57, 71, 85, 99, 113, 127, 144, 161, 178, 188, 198]
    lengths = [12] * 9 + [15, 15, 15, 8, 8, 11]

    def record(values) -> bytes:
        buf = bytearray(b" " * 208 + b"\r\n")
        for s, ln, v in zip(starts, lengths, values):
            buf[s - 1: s - 1 + ln] = str(v).rjust(ln)[:ln].encode("ascii")
        return bytes(buf)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(record(names))
        for k in range(n):
            vals = [f"{0.0:.4f}"] * 9 + [f"{lon[k]:.6f}", f"{lat[k]:.6f}", f"{-1.0:.6f}",
                                         f"{t_avg[k]:.2f}", f"{t_max[k]:.2f}", f"{ice[k]:.4f}"]
            f.write(record(vals))
    return {"tri_clon": lon, "tri_clat": lat, "temp_avg": t_avg, "temp_max": t_max, "ice_depth": ice}


def write_synthetic_grs(path: Path) -> None:
    """GRS-like 5-degree table: water rises with latitude; polar bins are flagged missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii", newline="\r\n") as f:
        for lat in np.arange(87.5, -90.0, -5.0):
            for lon in np.arange(2.5, 360.0, 5.0):
                v = 9999.999 if abs(lat) > 75 else 2.0 + abs(lat) / 10.0
                f.write(f"{lat:8.2f} {lon:8.2f} {v:9.3f} {0.3:9.3f}\n")


@pytest.fixture()
def project(tmp_path, monkeypatch):
    """Temporary project root: real configs, synthetic raw data."""
    root = tmp_path / "proj"
    shutil.copytree(REPO / "pipeline" / "config", root / "pipeline" / "config")
    (root / "data" / "reference").mkdir(parents=True)
    monkeypatch.setenv("ANALOG_ROOT", str(root))
    return root


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    """Static file server with Range support (python's own handler ignores Range)."""
    ignore_range = False

    def log_message(self, *args):  # keep test output clean
        pass

    def do_GET(self):
        path = Path(self.translate_path(self.path))
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        rng = self.headers.get("Range")
        if rng and not self.ignore_range:
            start = int(rng.split("=")[1].split("-")[0])
            if start >= len(data):
                self.send_response(416)
                self.end_headers()
                return
            body = data[start:]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
        else:
            body = data
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def http_server(tmp_path):
    """Serve tmp_path/'www' on localhost. Yields (base_url, folder, handler_class)."""
    www = tmp_path / "www"
    www.mkdir()

    class Handler(RangeHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(www), **kw)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/", www, Handler
    finally:
        server.shutdown()
        server.server_close()
