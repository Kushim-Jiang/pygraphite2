"""pygraphite2 — cross-platform SIL Graphite2 text shaping.

Public API
----------
- ``shape(font_bytes, text, *, direction="ltr", script=0, features=None)``
  → ``list[Glyph]``  (gid, cluster, x_advance, y_advance, x_offset, y_offset)
- ``is_graphite_font(font_bytes) -> bool``
- ``library_info() -> str``   (which native library is loaded)

Under the hood it vendors SIL's official ctypes binding
(``pygraphite2/graphite2/__init__.py``, from ``silnrsi/graphite``) and discovers
the native ``libgraphite2`` at runtime via ``_loader``:

1. ``PYGRAPHITE2_LIBRARY_PATH``
2. system library (``find_library("graphite2")``)
3. ``pygraphite2/vendor/graphite2/`` (per-OS dll/so/dylib)

No C/C++ compilation needed — the native library is loaded at runtime.
"""
from __future__ import annotations

import io
import os
import tempfile
from typing import NamedTuple

from . import _loader

# ── Native library discovery ─────────────────────────────────────────
_lib_path = _loader.prepare()
if _lib_path is not None:
    os.environ.setdefault("PYGRAPHITE2_LIBRARY_PATH", str(_lib_path))

try:
    from . import graphite2 as _g  # SIL official ctypes binding

    _AVAILABLE = True
    _load_error = ""
except Exception as _e:  # pragma: no cover - depends on host
    _g = None
    _AVAILABLE = False
    _load_error = f"{type(_e).__name__}: {_e}"


def library_info() -> str:
    """Describe which native library is loaded (or why none is)."""
    if not _AVAILABLE:
        return f"graphite2 unavailable — {_load_error}"
    try:
        v = _g.grversion()
        where = _lib_path or os.environ.get("PYGRAPHITE2_LIBRARY_PATH") or "system"
        return f"graphite2 v{v[0]}.{v[1]}.{v[2]} ({where})"
    except Exception as _e:  # pragma: no cover
        return f"graphite2 loaded, but version query failed ({_e})"


# ── Result type ──────────────────────────────────────────────────────
class Glyph(NamedTuple):
    gid: int
    cluster: int
    x_advance: float
    y_advance: float
    x_offset: float
    y_offset: float


# ── Font helpers ─────────────────────────────────────────────────────
def is_graphite_font(font_bytes: bytes) -> bool:
    """True if the font has a ``Silf`` table (i.e. Graphite-enabled)."""
    from fontTools.ttLib import TTFont

    tt = TTFont(io.BytesIO(font_bytes), lazy=True)
    try:
        return "Silf" in tt.reader.tables
    finally:
        tt.close()


def _upem(font_bytes: bytes) -> int:
    from fontTools.ttLib import TTFont

    tt = TTFont(io.BytesIO(font_bytes), lazy=True)
    try:
        return int(tt["head"].unitsPerEm or 2048)
    finally:
        tt.close()


# ── Shaping ──────────────────────────────────────────────────────────
def shape(
    font_bytes: bytes,
    text: str,
    *,
    direction: str = "ltr",
    script: int | bytes = 0,
    features=None,
) -> list[Glyph]:
    """Shape ``text`` with Graphite and return the glyph run (font units).

    Advances are derived from consecutive slot origins (last = segment advance
    minus last origin), matching ``gr2fonttest`` / the golden regression baseline.
    """
    if not _AVAILABLE:
        raise RuntimeError(
            "graphite2 native library not available — " + _load_error +
            ". Set PYGRAPHITE2_LIBRARY_PATH, install libgraphite2, or drop it in "
            "pygraphite2/vendor/graphite2/"
        )

    # gr_make_file_face is the reliable ctypes path → write bytes to a temp file
    fd, tmp = tempfile.mkstemp(suffix=".ttf")
    os.close(fd)
    try:
        with open(tmp, "wb") as fh:
            fh.write(font_bytes)

        face = _g.Face(tmp)  # errcheck raises if no Silf table
        try:
            upem = face.get_upem() or _upem(font_bytes)
            font = _g.Font(face, float(upem))
            try:
                rtl = 1 if direction == "rtl" else 0
                seg = _g.Segment(font, face, script, text, rtl)
                try:
                    slots = seg.slots
                    if not slots:
                        return []
                    total = seg.advance[0]
                    glyphs: list[Glyph] = []
                    for i, s in enumerate(slots):
                        adv_x = (
                            slots[i + 1].origin[0] - s.origin[0]
                            if i + 1 < len(slots)
                            else total - s.origin[0]
                        )
                        glyphs.append(
                            Glyph(
                                gid=int(s.gid),
                                cluster=int(s.original),
                                x_advance=adv_x,
                                y_advance=0.0,
                                x_offset=0.0,
                                y_offset=float(s.origin[1]),
                            )
                        )
                    return glyphs
                finally:
                    del seg
            finally:
                del font
        finally:
            del face
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
