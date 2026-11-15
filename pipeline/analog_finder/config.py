"""Project paths and YAML configuration.

The project root is the folder that holds ``pipeline/`` and ``data/``.
Override it with the ANALOG_ROOT environment variable (used by the tests).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    env = os.environ.get("ANALOG_ROOT")
    if env:
        return Path(env).resolve()
    # pipeline/analog_finder/config.py -> parents[2] is the repository root
    return Path(__file__).resolve().parents[2]


def config_dir() -> Path:
    return project_root() / "pipeline" / "config"


def data_dir() -> Path:
    return project_root() / "data"


def raw_dir() -> Path:
    return data_dir() / "raw"


def reference_dir() -> Path:
    return data_dir() / "reference"


def cell_deg() -> float:
    """Size of the Earth grid cell in degrees: 0.5 by default, ANALOG_CELL_DEG to build another grid (e.g. 0.25)."""
    return float(os.environ.get("ANALOG_CELL_DEG", "0.5"))


def grid_suffix() -> str:
    """'' for the default 0.5 degree grid, '_025' for 0.25 and so on: other grids live in their own folders."""
    cd = cell_deg()
    return "" if abs(cd - 0.5) < 1e-9 else "_" + f"{cd:g}".replace(".", "")


def processed_dir() -> Path:
    return data_dir() / ("processed" + grid_suffix())


def resolve(rel: str | os.PathLike) -> Path:
    """Resolve a path from a config file relative to the project root."""
    p = Path(rel)
    return p if p.is_absolute() else project_root() / p


def load_yaml(name: str) -> Any:
    path = config_dir() / name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=None)
def _cached(name: str, root: str) -> Any:  # root is part of the cache key
    return load_yaml(name)


def sources() -> dict:
    return _cached("sources.yaml", str(project_root()))


def targets() -> dict:
    return _cached("targets.yaml", str(project_root()))


def tasks() -> dict:
    return _cached("tasks.yaml", str(project_root()))


def datasets(world: str | None = None, access: str | None = None,
             ids: list[str] | None = None) -> list[dict]:
    """Datasets from sources.yaml, optionally filtered."""
    out = []
    for ds in sources()["datasets"]:
        if world and ds.get("world") != world:
            continue
        if access and ds.get("access") != access:
            continue
        if ids and ds["id"] not in ids:
            continue
        out.append(ds)
    return out


def dataset(ds_id: str) -> dict:
    for ds in sources()["datasets"]:
        if ds["id"] == ds_id:
            return ds
    raise KeyError(f"Unknown dataset id: {ds_id}")


def dataset_file(ds_id: str, name: str) -> Path:
    """Local path of one file of a dataset."""
    return resolve(dataset(ds_id)["dest"]) / name
