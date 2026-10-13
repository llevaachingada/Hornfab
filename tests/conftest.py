"""Shared fixtures for the hornlab_search test suite.

Wave 1 agents must not edit this file. Everything they might need lives here.

Every test that does not carry one of the ``requires_*`` markers below must pass
with nothing installed but numpy, scipy, pyyaml and pytest.

Other test modules can import helpers directly (``tests/`` is on ``sys.path``
under pytest's default ``prepend`` import mode because it has no ``__init__.py``):

    from conftest import requires_beat, make_fake_response, fibonacci_sphere
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.config import freq_grid, load_config
from hornlab_search.types import Response

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples"
TOOLCHAIN_MD = REPO / "TOOLCHAIN.md"

# Fake-response shape constants. Tests may import these to check their own expectations.
FAKE_FREQS = freq_grid(500, 10000, 12)
FAKE_ANGLE_COUNT = 73            # 2.5 deg steps, -90..+90 inclusive, exact 0
FAKE_BALLOON_POINTS = 512
FAKE_ON_AXIS_DB = 94.0           # absolute dB SPL on axis, every frequency
FAKE_FLOOR = 1e-3                # linear pressure floor (-60 dB re on-axis): no -inf
FAKE_N_DOF = 12_345
FAKE_THROAT_RADIUS_M = 0.0254    # for the synthetic piston-like throat impedance


# ------------------------------------------------------------------ dependency gates

def _have(module: str) -> bool:
    """True if ``module`` is importable. Never raises."""
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


requires_mesher = pytest.mark.skipif(
    not _have("hornlab_mesher"), reason="hornlab_mesher (hornlab-waveguide-mesher) not installed")
requires_beat = pytest.mark.skipif(
    not _have("hornlab_beat_bem"), reason="hornlab_beat_bem not installed")
requires_bempp = pytest.mark.skipif(
    not _have("hornlab_bempp_bem"), reason="hornlab_bempp_bem not installed")


# ------------------------------------------------------------------ helpers

def parse_toolchain(path: Path = TOOLCHAIN_MD) -> dict:
    """Parse ``key: value`` lines from TOOLCHAIN.md.

    Leading list markers / emphasis / backticks are stripped from keys and values.
    Returns {} if the file is absent or unreadable. Never raises.
    """
    out: dict[str, str] = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception:
        return out
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        s = s.lstrip("-*+> ").strip()
        key, _, value = s.partition(":")
        key = key.strip().strip("`*_ ").strip()
        value = value.strip().strip("`*_ ").strip()
        if not key:
            continue
        out[key] = value
    return out


def fibonacci_sphere(n: int) -> np.ndarray:
    """(n, 3) deterministic, near-equal-area unit vectors on the full sphere.

    Midpoint-rule latitude rings: z_i = 1 - (2i + 1)/n, golden-angle azimuth.
    +Z is the on-axis (forward) direction.
    """
    i = np.arange(n, dtype=float)
    z = 1.0 - (2.0 * i + 1.0) / n
    r = np.sqrt(np.clip(1.0 - z * z, 0.0, None))
    phi = i * np.pi * (3.0 - np.sqrt(5.0))
    dirs = np.column_stack([r * np.cos(phi), r * np.sin(phi), z])
    return dirs / np.linalg.norm(dirs, axis=1, keepdims=True)


def cardioid_mag(cos_theta: np.ndarray) -> np.ndarray:
    """Cardioid pressure magnitude (1 + cos theta)/2, floored so dB is finite."""
    return np.maximum((1.0 + np.asarray(cos_theta, dtype=float)) / 2.0, FAKE_FLOOR)


def make_fake_response() -> Response:
    """Deterministic synthetic Response: a frequency-independent cardioid.

    - freqs: freq_grid(500, 10000, 12)
    - cuts: 73 angles, -90..+90 inclusive in 2.5 deg steps, exact 0 at index 36.
      Horizontal cut lies in the XZ plane, vertical in the YZ plane; theta is the
      angle from +Z, so cos(theta) = cos(angle) on both cuts.
    - balloon: 512-point Fibonacci sphere, cos(theta) = z.
    - levels: absolute dB SPL, 94 dB on axis at every frequency, floored at -60 dB re axis.
      On the cuts the minimum is exactly 20*log10(0.5) = -6.02 dB re axis, at +/-90 deg.
    - z_throat: complex (nf,), a piston-like ka^2/(1+ka^2) + j ka/(1+ka^2).
    """
    freqs = np.asarray(FAKE_FREQS, dtype=float)
    nf = freqs.size
    half = (FAKE_ANGLE_COUNT - 1) // 2
    angles = np.arange(-half, half + 1, dtype=float) * (180.0 / (FAKE_ANGLE_COUNT - 1))

    cut_db = FAKE_ON_AXIS_DB + 20.0 * np.log10(cardioid_mag(np.cos(np.radians(angles))))
    # Force the on-axis sample to exactly the reference (cos(0) is exact anyway).
    cut_db[half] = FAKE_ON_AXIS_DB
    spl_h = np.tile(cut_db, (nf, 1))
    spl_v = np.tile(cut_db, (nf, 1))

    dirs = fibonacci_sphere(FAKE_BALLOON_POINTS)
    bal_db = FAKE_ON_AXIS_DB + 20.0 * np.log10(cardioid_mag(dirs[:, 2]))
    spl_bal = np.tile(bal_db, (nf, 1))

    from hornlab_search.constants import C_AIR
    ka = 2.0 * np.pi * freqs * FAKE_THROAT_RADIUS_M / C_AIR
    z_throat = (ka ** 2 + 1j * ka) / (1.0 + ka ** 2)

    return Response(
        freqs_hz=freqs,
        h_angles_deg=angles.copy(),
        v_angles_deg=angles.copy(),
        spl_h_db=spl_h,
        spl_v_db=spl_v,
        balloon_dirs=dirs,
        spl_balloon_db=spl_bal,
        z_throat=z_throat.astype(complex),
        backend="fake",
        n_dof=FAKE_N_DOF,
        meta={"pattern": "cardioid", "on_axis_db": FAKE_ON_AXIS_DB, "floor_lin": FAKE_FLOOR},
    )


# ------------------------------------------------------------------ fixtures

@pytest.fixture(scope="session")
def toolchain() -> dict:
    """Parsed key/value lines from TOOLCHAIN.md. Returns {} if absent,
    never raises, so unit tests run on a machine with no solver."""
    return parse_toolchain(TOOLCHAIN_MD)


@pytest.fixture(scope="session")
def cfg():
    return load_config(EXAMPLES / "osse_baseline.yaml")


@pytest.fixture(scope="session")
def smoke_cfg():
    return load_config(EXAMPLES / "search_smoke.yaml")


@pytest.fixture
def rng():
    return np.random.default_rng(20261013)


@pytest.fixture(scope="session")
def mesher_available() -> bool:
    return _have("hornlab_mesher")


@pytest.fixture(scope="session")
def beat_available() -> bool:
    return _have("hornlab_beat_bem")


@pytest.fixture(scope="session")
def bempp_available() -> bool:
    return _have("hornlab_bempp_bem")


@pytest.fixture
def fake_response() -> Response:
    """A synthetic Response with a cardioid pattern at 12 frequencies,
    73 angles per cut, a 512-point balloon, and no NaN. Metrics and dataset
    tests build on this instead of running a solver."""
    return make_fake_response()


@pytest.fixture
def fibonacci_512() -> np.ndarray:
    return fibonacci_sphere(512)
