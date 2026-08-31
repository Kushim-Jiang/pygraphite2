"""Public data types returned by :mod:`pygraphite2`.

All types here are simple, immutable value types that are safe to keep around,
compare, and pass between threads.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NamedTuple, Union

__all__ = [
    "Direction",
    "Feature",
    "FeatureValue",
    "Features",
    "Glyph",
    "ScriptTag",
    "ShapedText",
    "StrPath",
]

#: A filesystem path: either ``str`` or :class:`os.PathLike`.
StrPath = Union[str, os.PathLike[str]]

#: Text direction: ``"ltr"`` (left-to-right) or ``"rtl"`` (right-to-left).
Direction = Literal["ltr", "rtl"]

#: A Graphite script selector: a four-character tag such as ``"mymr"`` /
#: ``"latn"``, or a raw 32-bit tag integer (``0`` selects the default).
ScriptTag = Union[str, int]

#: Feature overrides: feature tag -> value, e.g. ``{"MyFeat": 1}``.
Features = Mapping[str, int]


class Glyph(NamedTuple):
    """A single positioned glyph produced by the Graphite shaper.

    Coordinates and advances are in font units (typically ``unitsPerEm`` from
    the font's ``head`` table). ``x_advance`` is derived from consecutive slot
    origins (for the last glyph, the segment advance minus its origin), which
    matches the reference ``gr2fonttest`` tool. ``cluster`` is the index of the
    source character this glyph is associated with; ``before``/``after`` give
    the (inclusive/exclusive) source character range, and ``index`` is the slot
    index within the segment.
    """

    #: Glyph identifier within the font.
    gid: int
    #: Source character index this glyph is associated with.
    cluster: int
    #: Advance in the text direction, in font units.
    x_advance: float
    #: Vertical advance, in font units (0 for horizontal text runs).
    y_advance: float
    #: Horizontal offset from the pen position, in font units.
    x_offset: float
    #: Vertical offset (origin Y / baseline), in font units.
    y_offset: float
    #: First source character index covered by this glyph (inclusive).
    before: int
    #: Last source character index covered by this glyph (exclusive).
    after: int
    #: Slot index within the shaped segment.
    slot_index: int


class ShapedText(NamedTuple):
    """The result of shaping one run of text with Graphite."""

    #: The shaped glyphs, in visual order.
    glyphs: tuple[Glyph, ...]
    #: Total advance along the text direction, in font units.
    advance_x: float
    #: Total vertical advance, in font units.
    advance_y: float
    #: The input text that was shaped.
    text: str
    #: The direction the run was shaped with.
    direction: Direction
    #: The script tag (as an int) used for shaping.
    script: int


@dataclass(frozen=True)
class FeatureValue:
    """A single allowed value of a Graphite feature, with a localized label."""

    #: The integer value.
    value: int
    #: A human-readable label (localized where the font provides one).
    label: str


@dataclass(frozen=True)
class Feature:
    """A named Graphite feature exposed by a font."""

    #: The four-character feature tag, e.g. ``"MyFeat"``.
    tag: str
    #: The allowed values (and their labels) for this feature.
    values: tuple[FeatureValue, ...]
