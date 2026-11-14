"""Print what is inside an HDF4 or NetCDF/HDF5 file: variable names, shapes, scale factors, fill values.

Used to check the real layout of a downloaded product before reading it:
    python -m analog_finder inspect data/raw/earth/modis_lst/<file>.hdf
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

KEYS = ("long_name", "units", "scale_factor", "add_offset", "_FillValue", "valid_range", "Legend", "legend", "scale", "offset")


def _short(v, limit: int = 160) -> str:
    s = str(v).replace("\n", " ")
    return s if len(s) <= limit else s[:limit] + "..."


def inspect_file(path: str | Path, log: Callable[[str], None] = print) -> None:
    path = Path(path)
    ext = path.suffix.lower()
    log(f"{path.name}  ({path.stat().st_size / 1e6:.1f} MB)")
    if ext == ".hdf":
        try:
            from pyhdf.SD import SD, SDC
        except ImportError:
            log('pyhdf is not installed. Run: pip install -e "pipeline[formats]"')
            return
        sd = SD(str(path), SDC.READ)
        glob = sd.attributes()
        log(f"global attributes: {len(glob)}; e.g. " + ", ".join(list(glob)[:12]))
        for name, (dims, shape, typ, _idx) in sd.datasets().items():
            sds = sd.select(name)
            attrs = sds.attributes()
            shown = {k: _short(attrs[k]) for k in KEYS if k in attrs}
            log(f"  {name}  shape={shape}  type={typ}  {shown}")
    elif ext in (".nc", ".nc4", ".h5", ".he5"):
        try:
            import netCDF4
        except ImportError:
            netCDF4 = None
        if netCDF4 is not None:
            with netCDF4.Dataset(path) as ds:
                def walk(g, prefix=""):
                    for name, var in g.variables.items():
                        shown = {k: _short(var.getncattr(k)) for k in KEYS if k in var.ncattrs()}
                        log(f"  {prefix}{name}  shape={var.shape}  dtype={var.dtype}  {shown}")
                    for gname, sub in g.groups.items():
                        log(f"  group {prefix}{gname}/")
                        walk(sub, f"{prefix}{gname}/")
                walk(ds)
                log("global attributes: " + ", ".join(list(ds.ncattrs())[:20]))
        else:
            import h5py
            with h5py.File(path, "r") as f:
                f.visititems(lambda n, o: log(f"  {n}  shape={getattr(o, 'shape', '')}  dtype={getattr(o, 'dtype', '')}")
                             if hasattr(o, "shape") else None)
    else:
        log(f"Unknown file type {ext}")
