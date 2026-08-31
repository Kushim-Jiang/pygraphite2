"""Golden regression tests for shaping (native library + Padauk font).

The golden values were produced with SIL Padauk **4.000** (the last Graphite
release) against graphite2 v1.3.14, using the reference
consecutive-slot-origin advance computation. The ``vendor/fonts/Padauk-Regular.ttf``
file is the v4.000 build; see ``vendor/fonts/README.md``.

All tests skip automatically if the native library or the test font is missing.
"""

from __future__ import annotations

import pytest

import pygraphite2 as pg
from tests.conftest import GOLDEN_GIDS, GOLDEN_WIDTHS, MYANMAR, needs_library, needs_padauk

pytestmark = [needs_library, needs_padauk]


def test_shape_returns_expected_gids(padauk_bytes: bytes) -> None:
    for text, expected in GOLDEN_GIDS.items():
        glyphs = pg.shape(padauk_bytes, text, script="mymr")
        assert [g.gid for g in glyphs] == expected, f"gid mismatch for {text!r}"


def test_shape_total_width_matches_golden(padauk_bytes: bytes) -> None:
    for text, expected in GOLDEN_WIDTHS.items():
        glyphs = pg.shape(padauk_bytes, text, script="mymr")
        total = sum(g.x_advance for g in glyphs)
        assert abs(total - expected) <= 1.0, f"width mismatch for {text!r}: {total} != {expected}"


def test_shape_segment_metadata(padauk_bytes: bytes) -> None:
    shaped = pg.shape_segment(padauk_bytes, MYANMAR, script="mymr")
    assert shaped.text == MYANMAR
    assert shaped.direction == "ltr"
    assert shaped.advance_x == sum(g.x_advance for g in shaped.glyphs)
    assert shaped.glyphs  # non-empty


def test_shape_glyph_fields(padauk_bytes: bytes) -> None:
    glyphs = pg.shape(padauk_bytes, MYANMAR, script="mymr")
    for i, g in enumerate(glyphs):
        assert g.slot_index == i
        assert 0 <= g.cluster < len(MYANMAR)
        assert g.after >= g.before
        # all advances/offsets are finite numbers
        for value in (g.x_advance, g.y_advance, g.x_offset, g.y_offset):
            assert value == value  # not NaN
            assert value != float("inf")


def test_shape_clusters_cover_source(padauk_bytes: bytes) -> None:
    glyphs = pg.shape(padauk_bytes, MYANMAR, script="mymr")
    clusters = [g.cluster for g in glyphs]
    assert min(clusters) >= 0
    assert set(clusters) == set(range(len(MYANMAR)))


def test_shape_rtl_direction(padauk_bytes: bytes) -> None:
    ltr = pg.shape_segment(padauk_bytes, "abc", direction="ltr")
    rtl = pg.shape_segment(padauk_bytes, "abc", direction="rtl")
    assert ltr.direction == "ltr"
    assert rtl.direction == "rtl"
    assert ltr.advance_x > 0
    assert rtl.advance_x > 0


def test_shape_empty_text(padauk_bytes: bytes) -> None:
    assert pg.shape(padauk_bytes, "") == []
    shaped = pg.shape_segment(padauk_bytes, "")
    assert shaped.glyphs == ()
    assert shaped.advance_x == 0.0


def test_shape_accepts_path_and_bytes(padauk_bytes: bytes, padauk_path) -> None:  # type: ignore[no-untyped-def]
    from_bytes = pg.shape(padauk_bytes, MYANMAR, script="mymr")
    from_path = pg.shape(padauk_path, MYANMAR, script="mymr")
    assert [g.gid for g in from_bytes] == [g.gid for g in from_path]


def test_shape_unknown_feature_raises(padauk_bytes: bytes) -> None:
    with pytest.raises(pg.GraphiteFontError):
        pg.shape(padauk_bytes, MYANMAR, features={"NoSuchFeature": 1})


def test_shape_with_feature_override(padauk_bytes: bytes) -> None:
    # 'kdot' exists in Padauk; passing it should not raise and should shape fine.
    glyphs = pg.shape(padauk_bytes, MYANMAR, script="mymr", features={"kdot": 1})
    assert [g.gid for g in glyphs] == GOLDEN_GIDS[MYANMAR]


def test_shape_garbage_font_raises() -> None:
    with pytest.raises(pg.GraphiteError):
        pg.shape(b"not a font", "abc")
