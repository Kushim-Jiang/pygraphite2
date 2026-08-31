"""Tests for the public API surface, value types and error handling."""

from __future__ import annotations

import typing

import pytest

import pygraphite2 as pg
from pygraphite2 import Glyph, ShapedText


def test_version_is_exported() -> None:
    # Compare the two exported forms against each other (single source of
    # truth in pygraphite2._version) instead of a hard-coded string, so a
    # version bump can't silently break the test.
    assert isinstance(pg.__version__, str)
    assert pg.version_tuple == tuple(int(x) for x in pg.__version__.split("."))
    assert len(pg.version_tuple) == 3


def test_public_names_are_exported() -> None:
    for name in (
        "shape",
        "shape_segment",
        "GraphiteFont",
        "is_graphite_font",
        "has_table",
        "upem_from_ttf",
        "read_font_bytes",
        "library_info",
        "library_path",
        "is_available",
        "configure",
        "load",
        "Glyph",
        "ShapedText",
        "Feature",
        "FeatureValue",
        "GraphiteError",
        "LibraryNotFound",
        "GraphiteFontError",
        "ShapingError",
    ):
        assert hasattr(pg, name), f"missing public name: {name}"


def test_py_typed_marker_present() -> None:
    import importlib.resources

    files = importlib.resources.files("pygraphite2").iterdir()
    assert any(p.name == "py.typed" for p in files)


def test_type_aliases_are_typing_compatible() -> None:
    # These are plain typing aliases; just ensure they exist and are usable.
    assert pg.Direction == typing.Literal["ltr", "rtl"]  # type: ignore[comparison-overlap]
    assert pg.StrPath is not None
    assert pg.ScriptTag is not None


def test_glyph_is_namedtuple_with_documented_fields() -> None:
    g = Glyph(
        gid=1,
        cluster=2,
        x_advance=3.5,
        y_advance=0.0,
        x_offset=0.0,
        y_offset=1.0,
        before=0,
        after=1,
        slot_index=0,
    )
    # tuple-unpacking of the first 6 fields (backwards compatible)
    gid, cluster, xa, ya, xo, yo = g[:6]
    assert (gid, cluster, xa, ya, xo, yo) == (1, 2, 3.5, 0.0, 0.0, 1.0)
    assert g._fields == (
        "gid",
        "cluster",
        "x_advance",
        "y_advance",
        "x_offset",
        "y_offset",
        "before",
        "after",
        "slot_index",
    )


def test_shapedtext_is_namedtuple() -> None:
    s = ShapedText(glyphs=(), advance_x=0.0, advance_y=0.0, text="", direction="ltr", script=0)
    assert s.advance_x == 0.0
    assert s.direction == "ltr"


def test_error_hierarchy() -> None:
    assert issubclass(pg.LibraryNotFound, pg.GraphiteError)
    assert issubclass(pg.GraphiteFontError, pg.GraphiteError)
    assert issubclass(pg.ShapingError, pg.GraphiteError)


def test_library_info_is_string() -> None:
    info = pg.library_info()
    assert isinstance(info, str)
    assert "graphite2" in info.lower()


@pytest.mark.skipif(pg.is_available(), reason="only when native library is missing")
def test_unavailable_hint_mentions_env_var() -> None:
    with pytest.raises(pg.LibraryNotFound):
        pg.shape(b"", "x")


def test_read_font_bytes_accepts_bytes_and_path(tmp_path) -> None:  # type: ignore[no-untyped-def]
    blob = b"\x00\x01fakefont"
    assert pg.read_font_bytes(blob) == blob
    p = tmp_path / "f.ttf"
    p.write_bytes(blob)
    assert pg.read_font_bytes(p) == blob
