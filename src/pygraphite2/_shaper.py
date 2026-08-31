"""One-shot functional shaping API.

These helpers load a font, shape a single run, and discard the font. For
shaping many runs with the same font, prefer the reusable
:class:`pygraphite2.GraphiteFont`.
"""

from __future__ import annotations

from ._font import FontSource, GraphiteFont
from ._types import Direction, Features, Glyph, ScriptTag, ShapedText, ShapedTrace

__all__ = ["shape", "shape_segment", "shape_trace"]


def shape(
    font: FontSource,
    text: str,
    *,
    direction: Direction = "ltr",
    script: ScriptTag | None = None,
    lang: str | None = None,
    features: Features | None = None,
) -> list[Glyph]:
    """Shape *text* with Graphite and return the glyph run.

    Convenience wrapper around :func:`shape_segment` that returns just the
    glyphs. For repeated shaping with the same font, prefer
    :class:`pygraphite2.GraphiteFont` to avoid re-loading the face each call.
    """
    return list(
        shape_segment(
            font, text, direction=direction, script=script, lang=lang, features=features
        ).glyphs
    )


def shape_segment(
    font: FontSource,
    text: str,
    *,
    direction: Direction = "ltr",
    script: ScriptTag | None = None,
    lang: str | None = None,
    features: Features | None = None,
) -> ShapedText:
    """Shape *text* with Graphite and return the full shaped run.

    Returns a :class:`ShapedText` carrying the glyphs plus total advances.
    """
    with GraphiteFont(font) as font_obj:
        return font_obj.shape(
            text, direction=direction, script=script, lang=lang, features=features
        )


def shape_trace(
    font: FontSource,
    text: str,
    *,
    direction: Direction = "ltr",
    script: ScriptTag | None = None,
    lang: str | None = None,
    features: Features | None = None,
    include_start: bool = True,
) -> ShapedTrace:
    """Shape *text* and return a per-pass shaping trace.

    One-shot wrapper around :meth:`pygraphite2.GraphiteFont.shape_trace`.
    Requires a graphite2 binary built with tracing support (see
    :class:`pygraphite2.TracingUnavailable`).
    """
    with GraphiteFont(font) as font_obj:
        return font_obj.shape_trace(
            text,
            direction=direction,
            script=script,
            lang=lang,
            features=features,
            include_start=include_start,
        )
