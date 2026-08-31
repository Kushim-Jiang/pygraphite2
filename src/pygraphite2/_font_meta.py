"""Pure-Python font inspection helpers (require ``fonttools``, no native lib).

These functions work even when the graphite2 native library is not installed,
which makes them useful for filtering/classifying fonts before shaping.
"""

from __future__ import annotations

import io
from typing import Union

from fontTools.ttLib import TTFont

from ._types import StrPath

__all__ = [
    "FontSource",
    "has_table",
    "is_graphite_font",
    "read_font_bytes",
    "upem_from_ttf",
]

#: A font given as raw bytes or as a path to a font file.
FontSource = Union[bytes, bytearray, StrPath]


def read_font_bytes(font: FontSource) -> bytes:
    """Return the raw bytes of a font given as bytes or a file path."""
    if isinstance(font, (bytes, bytearray)):
        return bytes(font)
    with open(font, "rb") as fh:
        return fh.read()


def _open_ttf(font: FontSource) -> TTFont:
    """Open a font with fontTools from an in-memory buffer (never a temp file)."""
    return TTFont(io.BytesIO(read_font_bytes(font)), lazy=True)


def has_table(font: FontSource, tag: str) -> bool:
    """Return whether the font contains an sfnt table with the given *tag*.

    Returns ``False`` (instead of raising) when the data cannot be parsed as a
    font at all.
    """
    try:
        tt = _open_ttf(font)
        try:
            return tag in tt.reader.tables
        finally:
            tt.close()
    except Exception:
        return False


def is_graphite_font(font: FontSource) -> bool:
    """Return ``True`` if the font is Graphite-enabled (has a ``Silf`` table)."""
    return has_table(font, "Silf")


def upem_from_ttf(font: FontSource) -> int:
    """Return the font's ``unitsPerEm`` (from the ``head`` table).

    Falls back to ``2048`` when the font has no usable value. The native
    library exposes the same value via ``gr_face_info``; this helper lets you
    query it without loading the library.
    """
    tt = _open_ttf(font)
    try:
        upem = tt["head"].unitsPerEm
        return int(upem) if upem else 2048
    finally:
        tt.close()
