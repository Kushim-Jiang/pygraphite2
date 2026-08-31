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
    "ShapedTrace",
    "StrPath",
    "TraceStage",
    "glyph_to_dict",
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


def glyph_to_dict(g: Glyph) -> dict[str, int]:
    """Serialize a :class:`Glyph` to the ``{g, cl, dx, dy, ax, ay, flags}`` shape
    used by shaping-debug UIs (e.g. BabelMap's OpenType Test dialog)."""
    return {
        "g": g.gid,
        "cl": g.cluster,
        "dx": int(g.x_offset),
        "dy": int(g.y_offset),
        "ax": int(g.x_advance),
        "ay": int(g.y_advance),
        "flags": 0,
    }


@dataclass(frozen=True)
class TraceStage:
    """A single snapshot of the glyph run at one point during shaping.

    Mirrors the ``{m, glyphs, depth, effective}`` "stage" rows used by
    Crowbar-style shaping debuggers: for Graphite, one stage corresponds to one
    shaping **pass** (each recorded with its own glyph snapshot).
    """

    #: Human-readable label for this step, e.g. ``"Pass 3"``.
    m: str
    #: The glyph run at this point of shaping.
    glyphs: tuple[Glyph, ...]
    #: Nesting depth (0 for Graphite passes; reserved for nested steps).
    depth: int = 0
    #: Whether this step actually changed the glyph run.
    effective: bool = True

    def to_dict(self) -> dict[str, object]:
        """Serialize to the backend ``{m, glyphs, depth, effective}`` stage schema."""
        return {
            "m": self.m,
            "glyphs": [glyph_to_dict(g) for g in self.glyphs],
            "depth": self.depth,
            "effective": self.effective,
        }


@dataclass(frozen=True)
class ShapedTrace:
    """The full per-pass shaping trace for one run of text."""

    #: The input text that was shaped.
    text: str
    #: The direction the run was shaped with.
    direction: Direction
    #: One stage per Graphite pass, plus optional start/end bookends.
    stages: tuple[TraceStage, ...]
    #: The final glyph run (same slots as the last stage).
    final: tuple[Glyph, ...]
    #: The script tag (as an int) used for shaping.
    script: int = 0

    def stages_to_dicts(self) -> list[dict[str, object]]:
        """Serialize all stages to the backend ``stages`` list schema."""
        return [s.to_dict() for s in self.stages]
