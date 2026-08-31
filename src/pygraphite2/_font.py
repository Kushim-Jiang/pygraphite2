"""High-level, typed wrapper around the graphite2 native library.

This module depends on the native library; it is only importable when a
graphite2 library could be loaded (see :mod:`pygraphite2._loader`). The public
:class:`GraphiteFont` loads a font fully in memory (no temporary files) and
exposes typed shaping, font metadata and feature enumeration.
"""

from __future__ import annotations

import contextlib
import ctypes
import struct
from ctypes import POINTER, c_size_t, c_uint, c_void_p
from types import TracebackType
from typing import Any, Union

from . import _binding as _g
from ._errors import GraphiteFontError, ShapingError
from ._types import (
    Direction,
    Feature,
    Features,
    FeatureValue,
    Glyph,
    ScriptTag,
    ShapedText,
    StrPath,
)

__all__ = ["FontSource", "GraphiteFont"]

#: A font supplied as raw bytes or as a path to a font file.
FontSource = Union[bytes, bytearray, StrPath]

# Matches graphite2's ``gr_get_table_fn``:
#   void *(*)(const void *appFontHandle, unsigned int name, size_t *len)
_GET_TABLE = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_uint, POINTER(c_size_t))


def _read_font_bytes(font: FontSource) -> bytes:
    """Read a font's raw bytes from bytes input or a file path."""
    if isinstance(font, (bytes, bytearray)):
        return bytes(font)
    with open(font, "rb") as fh:
        return fh.read()


class _Sfnt:
    """Parsed sfnt (TrueType/OpenType) table directory for in-memory faces.

    This is a minimal, self-contained table-directory reader; it lets us hand
    the native library a table callback that serves data straight from a
    bytes buffer instead of writing a temporary file.
    """

    __slots__ = ("_tables",)

    def __init__(self, data: bytes) -> None:
        if len(data) < 12:
            raise GraphiteFontError("font data is too short to be an sfnt font")
        num_tables = struct.unpack(">H", data[4:6])[0]
        tables: dict[int, tuple[int, int]] = {}
        for i in range(num_tables):
            entry = 12 + i * 16
            if entry + 16 > len(data):
                break
            tag = data[entry : entry + 4]
            if len(tag) != 4:
                break
            offset, length = struct.unpack(">II", data[entry + 8 : entry + 16])
            tables[int.from_bytes(tag, "big")] = (offset, length)
        if not tables:
            raise GraphiteFontError("font data contains no sfnt tables")
        self._tables = tables

    def table(self, tag_int: int) -> tuple[int, int] | None:
        """Return ``(offset, length)`` for a table tag integer, or ``None``."""
        return self._tables.get(tag_int)


class GraphiteFont:
    """A loaded Graphite font, ready for shaping.

    The font is loaded fully in memory — no temporary files are written. A
    :class:`GraphiteFont` owns native handles, so it should be closed with
    :meth:`close` or used as a context manager to release them deterministically:

    .. code-block:: python

        with pygraphite2.GraphiteFont.from_path("Padauk-Regular.ttf") as font:
            shaped = font.shape("မြန်မာ")

    Unlike the one-shot :func:`pygraphite2.shape`, reusing one instance avoids
    re-parsing the font on every call — the recommended pattern when shaping
    many runs with the same font.
    """

    __slots__ = (
        "_buffer",
        "_closed",
        "_face",
        "_font",
        "_get_table",
        "_handle",
        "_options",
        "_sfnt",
    )

    # Explicit attribute types so that :meth:`close` can release them to None
    # while keeping mypy (strict) happy.
    _buffer: ctypes.Array[ctypes.c_char] | None
    _closed: bool
    _face: Any | None
    _font: Any | None
    _get_table: Any | None
    _handle: c_void_p | None
    _options: int
    _sfnt: _Sfnt

    def __init__(self, font: FontSource, *, options: int = 0) -> None:
        data = _read_font_bytes(font)
        self._options = options
        self._closed = False
        self._sfnt = _Sfnt(data)
        # Stable, non-moving buffer the native library reads during face creation.
        self._buffer = ctypes.create_string_buffer(data, len(data))
        self._handle = ctypes.cast(self._buffer, c_void_p)
        self._face: Any = None
        self._font: Any = None
        self._get_table: Any = None

        base = ctypes.addressof(self._buffer)

        def _get_table_cb(_app_font: Any, name: Any, size_out: Any) -> int:
            # Return the raw address as a plain int: this is the portable way to
            # hand a pointer back from a c_void_p callback (returning a c_void_p
            # object triggers a ctypes regression on some Python 3.13 builds).
            entry = self._sfnt.table(int(name))
            if entry is None:
                size_out.contents.value = 0
                return 0
            offset, length = entry
            size_out.contents.value = length
            return base + offset

        self._get_table = _GET_TABLE(_get_table_cb)

        face = _g.gr2.gr_make_face(self._handle, self._get_table, options)
        if not face:
            raise GraphiteFontError(
                "gr_make_face failed — the data is not a valid Graphite font "
                "(missing or corrupt Silf table?)"
            )
        self._face = face

    # ------------------------------------------------------------------ #
    # Constructors
    # ------------------------------------------------------------------ #

    @classmethod
    def from_bytes(cls, data: bytes, *, options: int = 0) -> GraphiteFont:
        """Create a font from raw font-file bytes."""
        return cls(data, options=options)

    @classmethod
    def from_path(cls, path: StrPath, *, options: int = 0) -> GraphiteFont:
        """Create a font from a font-file path."""
        return cls(path, options=options)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Release the native face/font handles (idempotent)."""
        if self._closed:
            return
        self._closed = True
        if self._font is not None:
            _g.gr2.gr_font_destroy(self._font)
            self._font = None
        if self._face is not None:
            _g.gr2.gr_face_destroy(self._face)
            self._face = None
        self._get_table = None
        self._handle = None
        self._buffer = None

    def _ensure_open(self) -> None:
        if self._closed:
            raise GraphiteFontError("GraphiteFont has been closed")

    def __enter__(self) -> GraphiteFont:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - best-effort during GC
        with contextlib.suppress(Exception):
            self.close()

    # ------------------------------------------------------------------ #
    # Font metadata
    # ------------------------------------------------------------------ #

    @property
    def upem(self) -> int:
        """The font's units-per-em (from the native face info)."""
        self._ensure_open()
        info = _g.gr2.gr_face_info(self._face)
        if not info:
            return 2048
        upem = int(info.contents.upem)
        return upem or 2048

    @property
    def num_glyphs(self) -> int:
        """The number of glyphs in the font."""
        self._ensure_open()
        return int(_g.gr2.gr_face_n_glyphs(self._face))

    @property
    def languages(self) -> tuple[str, ...]:
        """The language tags the font's features are localized for."""
        self._ensure_open()
        count = int(_g.gr2.gr_face_n_languages(self._face))
        return tuple(
            _g.tag_to_str(int(_g.gr2.gr_face_lang_by_index(self._face, i))).decode("ascii")
            for i in range(count)
        )

    def feature_refs(self) -> tuple[Feature, ...]:
        """Enumerate the Graphite features the font exposes.

        Null/sentinel feature entries (an empty tag with no values, emitted by
        some fonts' ``Silf`` tables) are filtered out.
        """
        self._ensure_open()
        count = int(_g.gr2.gr_face_n_fref(self._face))
        result: list[Feature] = []
        for i in range(count):
            feature = self._feature(i)
            if feature.tag:  # skip null/sentinel features
                result.append(feature)
        return tuple(result)

    def _feature(self, index: int) -> Feature:
        fref = _g.gr2.gr_face_fref(self._face, index)
        tag = _g.tag_to_str(int(_g.gr2.gr_fref_id(fref))).decode("ascii")
        n_values = int(_g.gr2.gr_fref_n_values(fref))
        values = tuple(
            FeatureValue(
                value=int(_g.gr2.gr_fref_value(fref, i)),
                label=str(_g.FeatureRef(fref).label(i, 0)),
            )
            for i in range(n_values)
        )
        return Feature(tag, values)

    # ------------------------------------------------------------------ #
    # Shaping
    # ------------------------------------------------------------------ #

    def _make_font_handle(self) -> Any:
        """Create (once) the native ``gr_font`` for this face at upem size."""
        if self._font is None:
            self._font = _g.gr2.gr_make_font(float(self.upem), self._face)
            if not self._font:
                raise GraphiteFontError("gr_make_font failed")
        return self._font

    def shape(
        self,
        text: str,
        *,
        direction: Direction = "ltr",
        script: ScriptTag | None = None,
        lang: str | None = None,
        features: Features | None = None,
    ) -> ShapedText:
        """Shape *text* with Graphite and return the shaped run.

        Args:
            text: The Unicode text to shape.
            direction: ``"ltr"`` or ``"rtl"``.
            script: A four-character script tag (e.g. ``"mymr"``) or a raw tag
                integer; ``None``/``0`` lets the shaper pick a default.
            lang: A four-character language tag used to select feature values
                (e.g. ``"eng"``); only meaningful together with *features*.
            features: Feature tag -> value overrides, e.g. ``{"MyFeat": 1}``.
        """
        self._ensure_open()
        font_handle = self._make_font_handle()
        rtl = 1 if direction == "rtl" else 0

        if isinstance(script, str):
            script_tag = int(_g.gr2.gr_str_to_tag(script.encode("ascii")))
        elif script is None:
            script_tag = 0
        else:
            script_tag = int(script)

        feats_handle: Any = None
        if features:
            lang_tag = int(_g.gr2.gr_str_to_tag(lang.encode("ascii"))) if lang else 0
            fv = _g.FeatureVal(_g.gr2.gr_face_featureval_for_lang(self._face, lang_tag))
            try:
                for name, value in features.items():
                    tag_int = int(_g.gr2.gr_str_to_tag(name.encode("ascii")))
                    fref = _g.FeatureRef(_g.gr2.gr_face_find_fref(self._face, tag_int))
                    fv.set(fref, value)
            except (IndexError, ValueError) as exc:
                raise GraphiteFontError(f"invalid feature overrides: {exc}") from exc
            feats_handle = fv.fval

        encoded = text.encode("utf-8")
        text_buf = ctypes.create_string_buffer(encoded, len(encoded))
        seg = _g.gr2.gr_make_seg(
            font_handle,
            self._face,
            script_tag,
            feats_handle,
            1,  # direction (matches SIL's official binding)
            ctypes.cast(text_buf, c_void_p),
            len(text),  # graphite2's textLength is in characters, not bytes
            rtl,
        )
        if not seg:
            raise ShapingError("gr_make_seg failed")
        try:
            return self._segment_to_shaped(seg, text, direction, script_tag)
        finally:
            _g.gr2.gr_seg_destroy(seg)

    def _segment_to_shaped(
        self, seg: Any, text: str, direction: Direction, script: int
    ) -> ShapedText:
        """Convert a native ``gr_seg`` into a typed :class:`ShapedText`."""
        advance_x = float(_g.gr2.gr_seg_advance_X(seg))
        advance_y = float(_g.gr2.gr_seg_advance_Y(seg))
        glyphs: list[Glyph] = []
        slot = _g.gr2.gr_seg_first_slot(seg)
        index = 0
        while slot:
            origin_x = float(_g.gr2.gr_slot_origin_X(slot))
            origin_y = float(_g.gr2.gr_slot_origin_Y(slot))
            next_slot = _g.gr2.gr_slot_next_in_segment(slot)
            if next_slot:
                next_origin_x = float(_g.gr2.gr_slot_origin_X(next_slot))
                x_advance = next_origin_x - origin_x
            else:
                x_advance = advance_x - origin_x
            glyphs.append(
                Glyph(
                    gid=int(_g.gr2.gr_slot_gid(slot)),
                    cluster=int(_g.gr2.gr_slot_original(slot)),
                    x_advance=x_advance,
                    y_advance=0.0,
                    x_offset=0.0,
                    y_offset=origin_y,
                    before=int(_g.gr2.gr_slot_before(slot)),
                    after=int(_g.gr2.gr_slot_after(slot)),
                    slot_index=index,
                )
            )
            slot = next_slot
            index += 1
        return ShapedText(tuple(glyphs), advance_x, advance_y, text, direction, script)
