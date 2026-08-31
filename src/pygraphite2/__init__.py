"""pygraphite2 — a cross-platform, fully typed Python binding for SIL Graphite2 text shaping.

``pygraphite2`` shapes complex scripts with the Graphite smart-font technology.
It wraps SIL's official ctypes binding and discovers the native ``libgraphite2``
at runtime (no C/C++ compilation, no temporary files):

1. an explicit path from :func:`configure`,
2. the ``PYGRAPHITE2_LIBRARY_PATH`` environment variable,
3. a system library (``apt install libgraphite2-3``, conda-forge ``graphite2``, ...),
4. a wheel-bundled library in ``pygraphite2/_lib`` (future platform wheels),
5. a vendored checkout copy in ``vendor/graphite2``.

Typical use:

.. code-block:: python

    import pygraphite2

    font_bytes = open("Padauk-Regular.ttf", "rb").read()
    glyphs = pygraphite2.shape(font_bytes, "မြန်မာ")
    for g in glyphs:
        print(g.gid, g.cluster, g.x_advance)

    with pygraphite2.GraphiteFont.from_path("Padauk-Regular.ttf") as font:
        shaped = font.shape("မြန်မာ", script="mymr", features={"MyFeat": 1})

The pure-Python helpers (:func:`is_graphite_font`, :func:`has_table`,
:func:`upem_from_ttf`) work even when no native library is installed.
"""

from __future__ import annotations

from typing import Any

from ._errors import (
    GraphiteError,
    GraphiteFontError,
    LibraryNotFound,
    ShapingError,
    TracingUnavailable,
)
from ._font_meta import (
    FontSource,
    has_table,
    is_graphite_font,
    read_font_bytes,
    upem_from_ttf,
)
from ._loader import configure, is_available, library_path, load
from ._types import (
    Direction,
    Feature,
    Features,
    FeatureValue,
    Glyph,
    ScriptTag,
    ShapedText,
    ShapedTrace,
    StrPath,
    TraceStage,
)
from ._version import __version__, version_tuple

__all__ = [
    # Type aliases
    "Direction",
    "Feature",
    "FeatureValue",
    "Features",
    "FontSource",
    # Value types
    "Glyph",
    # Exceptions
    "GraphiteError",
    # High-level API
    "GraphiteFont",
    "GraphiteFontError",
    "LibraryNotFound",
    "ScriptTag",
    "ShapedText",
    "ShapedTrace",
    "ShapingError",
    "StrPath",
    "TraceStage",
    "TracingUnavailable",
    # Version
    "__version__",
    "configure",
    "has_table",
    "is_available",
    # Pure-Python helpers (no native lib required)
    "is_graphite_font",
    # Native library control
    "library_info",
    "library_path",
    "load",
    "read_font_bytes",
    "shape",
    "shape_segment",
    "shape_trace",
    "upem_from_ttf",
    "version_tuple",
]

_LIB_HINT = (
    "graphite2 native library not available. Set PYGRAPHITE2_LIBRARY_PATH, "
    "install a system graphite2 (e.g. 'apt install libgraphite2-3' or 'conda "
    "install graphite2'), or drop the library into vendor/graphite2/. Call "
    "pygraphite2.library_info() for details."
)


if is_available():
    # The native class intentionally replaces the degraded stub defined in the
    # else branch; suppress the (expected) type mismatch of that redefinition.
    from ._font import GraphiteFont  # pyright: ignore[reportAssignmentType]
    from ._shaper import shape, shape_segment, shape_trace
else:  # pragma: no cover - depends on host having graphite2

    class GraphiteFont:  # type: ignore[no-redef]
        """Degraded placeholder when the native library is unavailable.

        Importing the name works, but any construction raises
        :class:`LibraryNotFound` with a helpful message.
        """

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise LibraryNotFound(_LIB_HINT)

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        @classmethod
        def from_bytes(cls, data: bytes | bytearray = b"", *, options: int = 0) -> Any:
            return cls(data, options=options)

        @classmethod
        def from_path(cls, path: StrPath = ".", *, options: int = 0) -> Any:
            return cls(path, options=options)

    def shape(
        font: FontSource,
        text: str,
        *,
        direction: Direction = "ltr",
        script: ScriptTag | None = None,
        lang: str | None = None,
        features: Features | None = None,
    ) -> list[Glyph]:
        _ = (font, text, direction, script, lang, features)
        raise LibraryNotFound(_LIB_HINT)

    def shape_segment(
        font: FontSource,
        text: str,
        *,
        direction: Direction = "ltr",
        script: ScriptTag | None = None,
        lang: str | None = None,
        features: Features | None = None,
    ) -> ShapedText:
        _ = (font, text, direction, script, lang, features)
        raise LibraryNotFound(_LIB_HINT)

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
        _ = (font, text, direction, script, lang, features, include_start)
        raise LibraryNotFound(_LIB_HINT)


def library_info() -> str:
    """Describe which native library is loaded (or why none is).

    When a library is loaded this returns its version and source path; when it
    is not, it returns diagnostic hints about the discovery process.
    """
    if not is_available():
        from ._loader import library_info as _loader_library_info

        return _loader_library_info()
    try:
        from . import _binding as _binding_mod

        major, minor, patch = _binding_mod.grversion()
        where = library_path() or "unknown location"
        return f"graphite2 v{major}.{minor}.{patch} ({where})"
    except Exception as exc:  # pragma: no cover - depends on host
        return f"graphite2 loaded, but version query failed ({exc})"
