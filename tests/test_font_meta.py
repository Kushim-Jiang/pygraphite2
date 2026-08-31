"""Pure-Python font inspection tests (no native library required)."""

from __future__ import annotations

import os
from pathlib import Path

import pygraphite2 as pg
from tests.conftest import needs_padauk


def _system_plain_font() -> bytes | None:
    """Return bytes of a known non-Graphite font, or ``None`` if none found."""
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
        Path("/System/Library/Fonts/Helvetica.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    ]
    for p in candidates:
        if p.is_file():
            return p.read_bytes()
    return None


@needs_padauk
def test_is_graphite_font_true(padauk_bytes: bytes) -> None:
    assert pg.is_graphite_font(padauk_bytes) is True


def test_is_graphite_font_false_for_plain_ttf() -> None:
    font = _system_plain_font()
    if font is None:
        import pytest

        pytest.skip("no system non-Graphite font found")
    assert pg.is_graphite_font(font) is False


def test_is_graphite_font_false_for_garbage() -> None:
    assert pg.is_graphite_font(b"this is not a font") is False


@needs_padauk
def test_has_table(padauk_bytes: bytes) -> None:
    assert pg.has_table(padauk_bytes, "Silf") is True
    assert pg.has_table(padauk_bytes, "head") is True
    assert pg.has_table(padauk_bytes, "zzzz") is False


@needs_padauk
def test_upem_from_ttf(padauk_bytes: bytes) -> None:
    assert pg.upem_from_ttf(padauk_bytes) == 1024


def test_upem_from_ttf_plain_font() -> None:
    font = _system_plain_font()
    if font is None:
        import pytest

        pytest.skip("no system non-Graphite font found")
    assert pg.upem_from_ttf(font) > 0


@needs_padauk
def test_helpers_accept_path_too(padauk_path) -> None:  # type: ignore[no-untyped-def]
    assert pg.is_graphite_font(padauk_path) is True
    assert pg.upem_from_ttf(padauk_path) == 1024
