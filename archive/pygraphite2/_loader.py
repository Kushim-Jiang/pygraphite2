"""Cross-platform discovery of the graphite2 native library.

Load order (first hit wins):

1. ``PYGRAPHITE2_LIBRARY_PATH``  — explicit env override (most control; also the
   variable SIL's own binding already honours).
2. System library via ``ctypes.util.find_library("graphite2")`` —
   Linux ``libgraphite2.so`` (``apt install libgraphite2-3`` / conda-forge
   ``graphite2``), macOS ``libgraphite2.dylib`` (Homebrew/conda), Windows only if
   installed system-wide (rare).
3. Vendored copy in ``pygraphite2/vendor/graphite2/`` — per-OS filename
   (``libgraphite2.dll`` / ``libgraphite2.so`` / ``libgraphite2.dylib``).

On Windows the vendored folder is also added to the DLL search path so the MSYS2
runtime DLLs (``libgcc_s_seh-1.dll``, ``libstdc++-6.dll``,
``libwinpthread-1.dll``) resolve alongside the main library.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import os
from pathlib import Path

# pygraphite2/pygraphite2/_loader.py -> pygraphite2/vendor/graphite2/
_VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor" / "graphite2"


def _candidate_paths():
    # 1. env override
    env = os.environ.get("PYGRAPHITE2_LIBRARY_PATH")
    if env:
        yield Path(env)
    # 2. system library
    sys_lib = ctypes.util.find_library("graphite2")
    if sys_lib:
        yield Path(sys_lib)
    # 3. vendored, per-OS
    if os.name == "nt":
        yield _VENDOR_DIR / "libgraphite2.dll"
    elif sys.platform == "darwin":
        yield _VENDOR_DIR / "libgraphite2.dylib"
    else:
        yield _VENDOR_DIR / "libgraphite2.so"


def resolve() -> Path | None:
    """Return the first existing library path, or ``None`` if none is found."""
    for p in _candidate_paths():
        try:
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def prepare() -> Path | None:
    """Find the native library and set up Windows DLL directories.

    Returns the library path (or ``None`` if unavailable). The SIL ctypes binding
    is imported *after* calling this, so it picks the path up via
    ``PYGRAPHITE2_LIBRARY_PATH`` (or its own find_library fallback).
    """
    path = resolve()
    if path is None:
        return None
    if os.name == "nt" and _VENDOR_DIR.is_dir():
        try:
            os.add_dll_directory(str(_VENDOR_DIR))
        except (AttributeError, OSError):
            pass  # older Pythons / already added — harmless
    return path


def load() -> ctypes.CDLL | None:
    """Locate and load the library directly (without the SIL binding)."""
    path = prepare()
    if path is None:
        return None
    try:
        return ctypes.CDLL(str(path))
    except OSError:
        return None
