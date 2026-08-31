"""Cross-platform discovery and loading of the graphite2 native library.

Search order (first hit wins):

1. An explicit path passed to :func:`configure` — most control.
2. The ``PYGRAPHITE2_LIBRARY_PATH`` environment variable. May point directly
   at a library file, or at a directory that is searched for a
   platform-appropriate file name.
3. A system-installed library via :func:`ctypes.util.find_library` — e.g.
   ``libgraphite2-3`` on Debian/Ubuntu, conda-forge ``graphite2``, Homebrew on
   macOS, or a rare system-wide install on Windows.
4. A library bundled inside the wheel at ``pygraphite2/_lib/`` — reserved for
   future platform-specific wheels that ship prebuilt binaries.
5. A vendored copy in the repository checkout at ``vendor/graphite2/`` —
   developer convenience; this directory never ships inside a wheel.

On Windows the directory containing the library is also registered with
:func:`os.add_dll_directory` so that runtime dependencies (MSYS2's
``libgcc_s_seh-1.dll``, ``libstdc++-6.dll``, ``libwinpthread-1.dll``) resolve
alongside the main library.

The discovery order is intentionally lenient: it never raises. The native
entry points in :mod:`pygraphite2._font` raise :class:`pygraphite2.LibraryNotFound`
with a helpful message when the library is unavailable.
"""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.util
import os
import sys
from collections.abc import Iterator
from pathlib import Path

from ._types import StrPath

__all__ = [
    "configure",
    "is_available",
    "library_info",
    "library_path",
    "load",
    "resolve",
]

# Known per-OS library file names, in preference order.
if os.name == "nt":
    _PLATFORM_NAMES: tuple[str, ...] = ("graphite2.dll", "libgraphite2.dll")
elif sys.platform == "darwin":
    _PLATFORM_NAMES = ("libgraphite2.dylib",)
else:
    _PLATFORM_NAMES = ("libgraphite2.so", "libgraphite2.so.4", "libgraphite2.so.3")

# Package directory: <root>/src/pygraphite2/ (or site-packages/pygraphite2/).
_PACKAGE_DIR = Path(__file__).resolve().parent
# Wheel-local directory for future platform wheels.
_LIB_DIR = _PACKAGE_DIR / "_lib"


def _find_vendor_dir() -> Path:
    """Locate the repository checkout's ``vendor/graphite2/`` directory.

    Walks up from the package directory and returns the first ancestor that
    contains a ``vendor/graphite2`` directory, which makes the discovery robust
    to the layout (``src/pygraphite2/`` vs a flat checkout). In an installed
    wheel there is no vendor directory, so a non-existent fallback path is
    returned (the loader simply never finds anything there).
    """
    for parent in _PACKAGE_DIR.parents:
        candidate = parent / "vendor" / "graphite2"
        if candidate.is_dir():
            return candidate
    return _PACKAGE_DIR.parents[1] / "vendor" / "graphite2"


_VENDOR_DIR = _find_vendor_dir()

# Explicit override set via configure(); None means "auto-discover".
_configured_path: Path | None = None
# Result of the last successful load (cache).
_resolved_path: Path | None = None
_cached_library: ctypes.CDLL | None = None


def _platform_candidates(directory: Path) -> Iterator[Path]:
    """Yield the platform-appropriate library paths inside *directory*."""
    for name in _PLATFORM_NAMES:
        yield directory / name


def _candidate_paths() -> Iterator[Path]:
    """Yield library candidate paths in search order (deduplicated)."""
    seen: set[Path] = set()

    def _offer(path: Path) -> Iterator[Path]:
        if path not in seen:
            seen.add(path)
            yield path

    # 1. explicit runtime configuration
    if _configured_path is not None:
        if _configured_path.is_dir():
            for p in _platform_candidates(_configured_path):
                yield from _offer(p)
        else:
            yield from _offer(_configured_path)

    # 2. environment variable
    env = os.environ.get("PYGRAPHITE2_LIBRARY_PATH")
    if env:
        env_path = Path(env)
        if env_path.is_dir():
            for p in _platform_candidates(env_path):
                yield from _offer(p)
        else:
            yield from _offer(env_path)

    # 3. wheel-local _lib/ directory (bundled in the published wheel)
    #
    #    Preferred over the system library: the bundled binary is built with
    #    tracing enabled (GRAPHITE2_NTRACING off) and is functionally identical
    #    to a plain build for normal shaping, whereas distro/system binaries
    #    usually have tracing compiled out — so shape_trace would silently not
    #    work if the system library won.
    if _LIB_DIR.is_dir():
        for p in _platform_candidates(_LIB_DIR):
            yield from _offer(p)

    # 4. system library
    sys_lib = ctypes.util.find_library("graphite2")
    if sys_lib:
        yield from _offer(Path(sys_lib))

    # 5. vendored checkout directory
    for p in _platform_candidates(_VENDOR_DIR):
        yield from _offer(p)


def resolve() -> Path | None:
    """Return the path of the first existing library file, or ``None``."""
    for p in _candidate_paths():
        try:
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def library_path() -> Path | None:
    """The path of the currently loaded library, or ``None`` if not loaded."""
    return _resolved_path


def _add_windows_dll_dirs(path: Path) -> None:
    """Register the library's directory so Windows finds its dependencies."""
    if os.name != "nt":
        return
    with contextlib.suppress(AttributeError, OSError):
        # Python < 3.8, or the directory is already registered — harmless.
        os.add_dll_directory(str(path.parent))


def load() -> ctypes.CDLL | None:
    """Locate and load the graphite2 native library (cached).

    Returns ``None`` — without raising — when the library cannot be found or
    fails to load.
    """
    global _resolved_path, _cached_library
    if _cached_library is not None:
        return _cached_library
    path = resolve()
    if path is None:
        return None
    _add_windows_dll_dirs(path)
    try:
        _cached_library = ctypes.CDLL(str(path))
        _resolved_path = path
        return _cached_library
    except OSError:
        return None


def is_available() -> bool:
    """Whether the graphite2 native library is currently loadable."""
    return load() is not None


def configure(library_path: StrPath | None = None) -> None:
    """Override library resolution.

    Sets an explicit path (or reverts to automatic discovery with ``None``)
    that is used the first time the library is loaded. The loaded library is
    then cached for the process lifetime, so call this **before** the first
    operation that loads the library (it mainly serves test fixtures and
    scripts that must pin a specific binary before import).
    """
    global _configured_path
    _configured_path = None if library_path is None else Path(library_path)


def library_info() -> str:
    """A human-readable description of the loaded library, or why none is."""
    if _cached_library is not None:
        where = _resolved_path or "unknown location"
        return f"graphite2 loaded from {where}"
    reasons: list[str] = []
    env = os.environ.get("PYGRAPHITE2_LIBRARY_PATH")
    if env:
        reasons.append(f"PYGRAPHITE2_LIBRARY_PATH={env!r} set but no usable library found there")
    else:
        reasons.append("PYGRAPHITE2_LIBRARY_PATH is not set")
    if _LIB_DIR.is_dir():
        reasons.append(f"nothing usable in wheel-local {_LIB_DIR}")
    if _VENDOR_DIR.is_dir():
        names = ", ".join(p.name for p in _platform_candidates(_VENDOR_DIR))
        reasons.append(f"nothing vendored in {_VENDOR_DIR} (expected one of: {names})")
    return "graphite2 unavailable — " + "; ".join(reasons)
