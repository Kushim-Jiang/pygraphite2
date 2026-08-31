"""Shared pytest fixtures and environment handling for pygraphite2 tests.

These tests need two optional resources, and every test auto-skips when its
resource is missing:

* the **graphite2 native library** (any of the loader's discovery sources);
* a **Graphite test font** (``vendor/fonts/Padauk-Regular.ttf``).

The library is intentionally *not* bundled; tests degrade gracefully so the
pure-Python parts are always exercised.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import pygraphite2

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = REPO_ROOT / "vendor"
GRAPHITE2_DIR = VENDOR_DIR / "graphite2"
FONTS_DIR = VENDOR_DIR / "fonts"
PADAUK = FONTS_DIR / "Padauk-Regular.ttf"

needs_library = pytest.mark.skipif(
    not pygraphite2.is_available(),
    reason="graphite2 native library not available; see pygraphite2.library_info()",
)

needs_padauk = pytest.mark.skipif(
    not PADAUK.is_file(),
    reason=f"missing test font: {PADAUK} (see vendor/fonts/README.md)",
)


def _padauk_bytes() -> bytes:
    return PADAUK.read_bytes()


@pytest.fixture(scope="session")
def padauk_path() -> Path:
    """Path to the Padauk test font (session-scoped)."""
    return PADAUK


@pytest.fixture(scope="session")
def padauk_bytes() -> bytes:
    """Raw bytes of the Padauk test font (session-scoped)."""
    return _padauk_bytes()


@pytest.fixture(scope="session")
def library_info() -> str:
    """Human-readable description of the loaded library."""
    return pygraphite2.library_info()


# A Myanmar phrase used across the golden tests. These exact values were
# produced by the reference `gr2fonttest`-style computation (consecutive slot
# origins) against SIL Padauk 4.000.
MYANMAR = "မြန်မာ"
GOLDEN_GIDS = {
    "မြန်မာ": [392, 305, 290, 383, 305, 354],
    "က္က": [214, 217],
    "သာဓု": [330, 354, 287, 364],
}
GOLDEN_WIDTHS = {
    "မြန်မာ": 2322.0,
    "က္က": 1002.0,
    "သာဓု": 1987.0,
}


def require_padauk_bytes() -> bytes:
    """Return Padauk bytes or raise a skip-compatible error."""
    if not PADAUK.is_file():
        raise pytest.skip.Exception(f"missing test font: {PADAUK}")
    return _padauk_bytes()
