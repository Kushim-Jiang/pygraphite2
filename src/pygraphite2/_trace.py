"""Parse graphite2's Segment-JSON shaping trace into typed stages.

Graphite2 binaries built **without** ``GRAPHITE2_NTRACING`` can write a JSON
log of every segment they create (see :func:`pygraphite2.GraphiteFont.start_logging`).
Each segment object contains a ``passes`` array; every pass records a snapshot
of the glyph slots, so one pass maps naturally to one "stage" row in a
shaping-debug trace (the same ``{m, glyphs, depth, effective}`` schema used by
Crowbar-style tools and BabelMap's OpenType Test dialog).

This module only parses the JSON — it never touches the native library.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from ._types import Glyph, TraceStage

__all__ = ["parse_segment_log"]

# ``json.cpp`` can emit non-standard float literals (NaN/Infinity) in edge
# cases; map them to 0.0 so the document always parses.
_PARSE_CONSTANTS = {"NaN": 0.0, "Infinity": 0.0, "-Infinity": 0.0}


def _load_tolerant(raw: str) -> Any:
    """Parse the Segment-JSON document (tolerant of NaN/Infinity literals)."""
    return json.loads(raw, parse_constant=lambda c: _PARSE_CONSTANTS.get(c, 0.0))


def _num(value: Any) -> float:
    """Coerce a JSON number to float, mapping anything non-numeric to 0.0."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _slot_to_glyph(slot: dict[str, Any], index: int) -> Glyph:
    """Convert one JSON ``dslot`` object into a typed :class:`Glyph`."""
    charinfo = slot.get("charinfo") or {}
    origin = slot.get("origin") or []
    advance = slot.get("advance") or []
    return Glyph(
        gid=int(slot.get("gid", 0)),
        cluster=int(charinfo.get("original", 0)),
        x_advance=_num(advance[0]) if advance else 0.0,
        y_advance=_num(advance[1]) if len(advance) > 1 else 0.0,
        x_offset=_num(origin[0]) if origin else 0.0,
        y_offset=_num(origin[1]) if len(origin) > 1 else 0.0,
        before=int(charinfo.get("before", 0)),
        after=int(charinfo.get("after", 0)),
        slot_index=index,
    )


def _slots_to_glyphs(slots: Sequence[dict[str, Any]]) -> tuple[Glyph, ...]:
    return tuple(_slot_to_glyph(s, i) for i, s in enumerate(slots))


def _pass_message(pass_obj: dict[str, Any], index: int) -> str:
    """A human-readable label for a Graphite pass."""
    pass_id = pass_obj.get("id", index)
    if pass_id == -1:
        return "Bidi / mirroring pass"
    return f"Pass {int(pass_id)}"


def parse_segment_log(raw: str) -> tuple[tuple[TraceStage, ...], tuple[Glyph, ...]]:
    """Parse a graphite2 Segment-JSON log into typed stages + final glyphs.

    Args:
        raw: The text of the JSON log file written by ``gr_start_logging``.

    Returns:
        ``(stages, final)`` where ``stages`` is one :class:`TraceStage` per
        Graphite pass (each a snapshot of the glyph run) and ``final`` is the
        segment's output slot list.

    Raises:
        ValueError: if the document contains no segments or cannot be parsed.
    """
    data = _load_tolerant(raw)
    segments = data if isinstance(data, list) else [data]
    if not segments:
        raise ValueError("graphite2 trace log contains no segments")
    # Logging is face-wide and accumulates every segment created while active;
    # the segment we just shaped is the most recently created one.
    segment = segments[-1]

    passes = segment.get("passes") or []
    stages = tuple(
        TraceStage(
            m=_pass_message(p, i),
            glyphs=_slots_to_glyphs(p.get("slots") or []),
            depth=0,
            effective=True,
        )
        for i, p in enumerate(passes)
    )

    final_slots = segment.get("output") or (passes[-1].get("slots") if passes else [])
    final = _slots_to_glyphs(final_slots)
    return stages, final
