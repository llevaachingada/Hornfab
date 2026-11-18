"""``hornlab_search.system`` — additive modular two-way (horn + vented woofer) system layer.

Strictly additive: nothing in hornlab_search outside this package changes. The canonical
conventions live in :mod:`hornlab_search.system.contracts`.
"""
from __future__ import annotations

from hornlab_search.system.contracts import (
    SCHEMA_VERSION,
    SYSTEM_OBJECTIVE_VERSION,
    TIME_CONVENTION,
    AssetQuality,
    DataQualityError,
    DspPoint,
    DspRanges,
    Fidelity,
    HornAsset,
    HornRef,
    IncompatibleBasis,
    PhaseUnavailable,
    SchemaError,
    SourceBasis,
    SpecFidelity,
    StatusToken,
    SystemMode,
    SystemResponse,
    SystemSpecV1,
    SystemTargets,
    WooferDriver,
    WooferRef,
    parse_system_spec_dict,
)

__all__ = [
    "SCHEMA_VERSION", "TIME_CONVENTION", "SYSTEM_OBJECTIVE_VERSION",
    "AssetQuality", "Fidelity", "SystemMode", "SpecFidelity", "StatusToken",
    "DataQualityError", "IncompatibleBasis", "PhaseUnavailable", "SchemaError",
    "SourceBasis", "HornAsset", "HornRef", "WooferDriver", "WooferRef",
    "DspPoint", "DspRanges", "SystemResponse", "SystemSpecV1", "SystemTargets",
    "parse_system_spec_dict",
]
