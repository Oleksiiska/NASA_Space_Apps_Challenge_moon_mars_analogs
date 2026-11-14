"""Data layer for the Moon/Mars terrestrial analog finder.

Layout (see README.md):
    config.py    project paths, YAML configs
    fetch/       downloads from the official challenge resources
    io/          readers for PDS3 images and PDS tables
    prep/        Earth land grid, reference layers (targets, known analogs)
    features/    terrain and Sun-geometry features
    targets/     feature "fingerprints" of the Moon and Mars targets
    export/      compact binary grid for the web app
"""

__version__ = "0.1.0"
