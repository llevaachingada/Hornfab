"""Driver models that turn a stored horn solve into absolute level (report-only, P12 2026-10-27).

``compression.py``: a lumped compression driver (Thiele-Small-style parameters with the DRY moving mass)
driven at a voltage and loaded by the BEM throat impedance. Never imported by the search path.
"""
from .compression import CompressionDriver, band_mean_db, drive, max_spl_db  # noqa: F401
