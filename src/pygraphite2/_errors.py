"""Exception hierarchy for :mod:`pygraphite2`.

All exceptions raised by this package derive from :class:`GraphiteError`, so
callers can catch one type to handle every failure mode.
"""

from __future__ import annotations

__all__ = [
    "GraphiteError",
    "GraphiteFontError",
    "LibraryNotFound",
    "ShapingError",
    "TracingUnavailable",
]


class GraphiteError(Exception):
    """Base class for all pygraphite2 errors."""


class LibraryNotFound(GraphiteError):
    """Raised when the graphite2 native library cannot be located or loaded.

    The graphite2 library is **not** bundled in the default (universal) wheel;
    it is discovered at runtime. See :mod:`pygraphite2._loader` for the search
    order and :func:`pygraphite2.configure` for an explicit override.
    """


class GraphiteFontError(GraphiteError):
    """Raised when a font cannot be opened as a Graphite font.

    Typical causes:

    * the data is not a valid sfnt/TTF/OTF font,
    * the font has no Graphite ``Silf`` table (use :func:`pygraphite2.is_graphite_font`
      to check first),
    * a feature name does not exist on the font.
    """


class ShapingError(GraphiteError):
    """Raised when the native shaper fails to shape a run of text."""


class TracingUnavailable(GraphiteError):
    """Raised when a shaping trace is requested but the loaded graphite2 binary
    cannot produce one.

    The Segment-JSON tracing machinery is compiled out of most release binaries
    (built with ``GRAPHITE2_NTRACING``). Use a binary built with tracing enabled
    (e.g. the one vendored in ``vendor/graphite2/``) to get per-pass traces.
    """
