"""Tests for the reusable :class:`pygraphite2.GraphiteFont`."""

from __future__ import annotations

import pytest

import pygraphite2 as pg
from tests.conftest import GOLDEN_GIDS, MYANMAR, needs_library, needs_padauk

pytestmark = [needs_library, needs_padauk]


def test_font_metadata(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        assert font.upem == 1024
        assert font.num_glyphs > 0
        assert isinstance(font.languages, tuple)
        assert font.languages  # Padauk declares languages


def test_font_features_enumerated(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        feats = font.feature_refs()
        assert isinstance(feats, tuple)
        tags = {f.tag for f in feats}
        assert "kdot" in tags  # a known Padauk feature
        for f in feats:
            assert f.tag
            assert isinstance(f.values, tuple)
            assert all(isinstance(v.value, int) for v in f.values)


def test_font_shape_matches_one_shot(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        shaped = font.shape(MYANMAR, script="mymr")
    assert [g.gid for g in shaped.glyphs] == GOLDEN_GIDS[MYANMAR]


def test_font_from_path(padauk_path) -> None:  # type: ignore[no-untyped-def]
    with pg.GraphiteFont.from_path(padauk_path) as font:
        assert font.upem == 1024
        assert font.shape(MYANMAR, script="mymr").glyphs


def test_font_reuse_shapes_multiple_runs(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        a = font.shape("abc")
        b = font.shape("def")
    assert a.glyphs and b.glyphs


def test_font_close_is_idempotent(padauk_bytes: bytes) -> None:
    font = pg.GraphiteFont.from_bytes(padauk_bytes)
    font.close()
    font.close()  # must not raise


def test_font_use_after_close_raises(padauk_bytes: bytes) -> None:
    font = pg.GraphiteFont.from_bytes(padauk_bytes)
    font.close()
    with pytest.raises(pg.GraphiteFontError):
        font.shape(MYANMAR)


def test_font_shape_with_features_and_lang(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        shaped = font.shape(MYANMAR, script="mymr", lang="ksw", features={"kdot": 1})
    assert shaped.glyphs


def test_font_rtl(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        shaped = font.shape("abc", direction="rtl")
    assert shaped.direction == "rtl"
    assert shaped.advance_x > 0


def test_font_from_bytes_accepts_bytearray(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(bytearray(padauk_bytes)) as font:
        assert font.upem == 1024
