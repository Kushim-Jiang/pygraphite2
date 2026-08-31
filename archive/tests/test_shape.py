"""Golden regression tests for pygraphite2 (from the README §7 baseline).

Requires:
- a Graphite font with a Silf table, e.g. SIL Padauk at
  ``pygraphite2/vendor/fonts/Padauk-Regular.ttf``
- a loadable graphite2 native library (see pygraphite2/vendor/graphite2/README.md)

Tests are skipped automatically if either is missing.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygraphite2  # noqa: E402

FONT = ROOT / "vendor" / "fonts" / "Padauk-Regular.ttf"

# README §7 golden baseline (gids; upem = 1024; size passed as upem)
GOLDEN = {
    "မြန်မာ": ([423, 326, 308, 414, 326, 385], 4644),
    "က္က": ([214, 217], None),
    "သာဓု": ([354, 385, 305, 395], None),
}

pytestmark = pytest.mark.skipif(
    not FONT.is_file(),
    reason=f"missing test font: {FONT}",
)


def _lib_available() -> bool:
    return pygraphite2._AVAILABLE


pytestmark = pytest.mark.skipif(
    not _lib_available(),
    reason="graphite2 native library not available",
)


def test_is_graphite_font():
    data = FONT.read_bytes()
    assert pygraphite2.is_graphite_font(data) is True


def test_is_graphite_font_negative():
    # a non-graphite font (e.g. system Arial) must be False
    import glob

    system = glob.glob(r"C:\Windows\Fonts\arial.ttf") or glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    if not system:
        pytest.skip("no system font to test against")
    assert pygraphite2.is_graphite_font(Path(system[0]).read_bytes()) is False


def test_shape_gids_match_golden():
    data = FONT.read_bytes()
    for text, (gids, _width) in GOLDEN.items():
        glyphs = pygraphite2.shape(data, text)
        assert [g.gid for g in glyphs] == gids, f"gid mismatch for {text!r}"


def test_shape_total_width_matches_golden():
    data = FONT.read_bytes()
    text = "မြန်မာ"
    _, width = GOLDEN[text]
    glyphs = pygraphite2.shape(data, text)
    total = sum(g.x_advance for g in glyphs)
    assert abs(total - width) <= 1, f"total advance {total} != {width}"


def test_shape_cluster_indices_monotonic():
    data = FONT.read_bytes()
    glyphs = pygraphite2.shape(data, "သာဓု")
    clusters = [g.cluster for g in glyphs]
    # clusters should be non-decreasing for LTR Myanmar text
    assert clusters == sorted(clusters)
    assert clusters[0] >= 0


def test_library_info_reports_version():
    info = pygraphite2.library_info()
    assert "graphite2" in info.lower()
