"""Build a tracing-enabled graphite2 native library into ``vendor/graphite2/``.

pygraphite2's per-pass shaping trace needs a graphite2 binary compiled
**without** ``GRAPHITE2_NTRACING`` (tracing compiled in). Most distro/release
binaries ship with tracing disabled, so this script builds a tracing-enabled
copy for the **current** platform:

    python scripts/build_tracing_lib.py                            # into vendor/graphite2/
    python scripts/build_tracing_lib.py --source /path/to/graphite  # reuse a clone
    python scripts/build_tracing_lib.py --out /tmp/gr2lib          # custom output dir

Requirements: ``cmake`` and a C/C++ compiler. On Windows the mingw-w64
toolchain (e.g. Strawberry Perl's or MSYS2) is preferred and the mingw runtime
is linked statically so only ``libwinpthread-1.dll`` needs to sit alongside the
DLL.

After building, the script loads the library and verifies ``gr_start_logging``
actually works (returns ``True``).
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/silnrsi/graphite.git"
PINNED_REF = "ca8d821e60a15b6c24e404c9086992c975d8e1cf"  # graphite2 v1.3.15

_OUT_NAMES = {
    "win32": "libgraphite2.dll",
    "darwin": "libgraphite2.dylib",
    "linux": "libgraphite2.so",
}

# Known mingw-w64 toolchains on Windows (preferred over a random gcc on PATH).
_MINGW_DIRS = [
    r"C:\Strawberry\c\bin",
    r"C:\msys64\mingw64\bin",
    r"C:\msys64\ucrt64\bin",
]


def _platform() -> str:
    if sys.platform == "win32":
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"


def _exe(name: str) -> str:
    return name + (".exe" if _platform() == "win32" else "")


def _find(prog: str) -> str | None:
    for d in _MINGW_DIRS:
        p = Path(d) / _exe(prog)
        if p.is_file():
            return str(p)
    return shutil.which(prog)


def _run(args: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(args))
    subprocess.run(args, cwd=cwd, check=True)


def _obtain_source(source: str | None) -> tuple[Path, bool]:
    """Return (source_dir, is_temp); clones the pinned ref if source is None."""
    if source:
        return Path(source), False
    tmp = Path(tempfile.mkdtemp(prefix="gr2src-"))
    _run(["git", "init", "-q", str(tmp)])
    _run(["git", "-C", str(tmp), "fetch", "--depth", "1", REPO_URL, PINNED_REF])
    _run(["git", "-C", str(tmp), "checkout", "-q", "FETCH_HEAD"])
    return tmp, True


def _build(source: Path, out: Path) -> None:
    plat = _platform()
    build = source / "_build-tracing"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir()

    cmake = _find("cmake") or "cmake"
    common = [
        "-S",
        str(source),
        "-B",
        str(build),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_SHARED_LIBS=ON",
        "-DBUILD_TESTING=OFF",
        "-DGRAPHITE2_NTRACING=OFF",
    ]
    if plat == "win32":
        gcc, gxx, make = _find("gcc"), _find("g++"), _find("mingw32-make") or _find("make")
        if not (gcc and gxx and make):
            raise SystemExit(
                "mingw-w64 toolchain not found on PATH or in "
                + ", ".join(_MINGW_DIRS)
                + ". Install it (e.g. Strawberry Perl or MSYS2 mingw64) or add it to PATH."
            )
        _run(
            [
                cmake,
                *common,
                "-G",
                "MinGW Makefiles",
                f"-DCMAKE_C_COMPILER={gcc}",
                f"-DCMAKE_CXX_COMPILER={gxx}",
                f"-DCMAKE_MAKE_PROGRAM={make}",
                "-DCMAKE_SHARED_LINKER_FLAGS=-static-libgcc -static-libstdc++",
            ]
        )
    else:
        _run([cmake, *common])
    _run([cmake, "--build", str(build), "-j"])

    # Prefer the canonical library under build/src (the gr2fonttest copy is
    # identical but rglob order is not guaranteed).
    names = ("libgraphite2.dll", "libgraphite2.dylib", "libgraphite2.so")
    candidates = [build / "src" / n for n in names]
    lib = next((c for c in candidates if c.is_file()), None)
    if lib is None:
        lib = next(build.rglob("libgraphite2.*"), None)
    if lib is None or lib.suffix not in (".dll", ".dylib", ".so"):
        raise SystemExit(f"built library not found under {build}")
    out.mkdir(parents=True, exist_ok=True)
    target = out / _OUT_NAMES[plat]
    shutil.copy2(lib, target)
    print(f"copied {lib} -> {target}")

    if plat == "win32":
        # Copy the mingw runtime that belongs to the same toolchain as gcc.
        gcc = _find("gcc")
        winpthread = None
        if gcc:
            cand = Path(gcc).parent / "libwinpthread-1.dll"
            if cand.is_file():
                winpthread = str(cand)
        if winpthread is None:
            winpthread = shutil.which("libwinpthread-1.dll")
        if winpthread:
            shutil.copy2(winpthread, out / "libwinpthread-1.dll")
            print(f"copied {winpthread} -> {out / 'libwinpthread-1.dll'}")


def _check_start_logging(gr: ctypes.CDLL, path: Path) -> None:
    gr.gr_start_logging.restype = ctypes.c_int
    gr.gr_start_logging.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    gr.gr_stop_logging.restype = None
    gr.gr_stop_logging.argtypes = [ctypes.c_void_p]
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        ok = gr.gr_start_logging(None, tmp.encode("utf-8"))
        gr.gr_stop_logging(None)
        if not ok:
            raise SystemExit(f"gr_start_logging returned false — tracing NOT compiled in ({path})")
    finally:
        with contextlib.suppress(OSError):
            os.remove(tmp)


def _verify(out: Path) -> None:
    """Load the freshly built library and confirm tracing actually works."""
    path = out / _OUT_NAMES[_platform()]
    gr = ctypes.CDLL(str(path))
    _check_start_logging(gr, path)
    print(f"OK: {path.name} loads and gr_start_logging works")


# Wheel staging dir: binaries placed here are packaged into the wheel's
# ``pygraphite2/_lib/`` so ``pip install pygraphite2`` works out of the box.
_WHEEL_LIB_DIR = Path(__file__).resolve().parent.parent / "src" / "pygraphite2" / "_lib"


def _stage_wheel_lib(out: Path) -> None:
    """Mirror the freshly built library into the wheel's ``_lib/`` dir."""
    if not _WHEEL_LIB_DIR.is_dir():
        return
    plat = _platform()
    shutil.copy2(out / _OUT_NAMES[plat], _WHEEL_LIB_DIR / _OUT_NAMES[plat])
    print(f"mirrored {_OUT_NAMES[plat]} -> {_WHEEL_LIB_DIR}")
    if plat == "win32":
        wp = out / "libwinpthread-1.dll"
        if wp.is_file():
            shutil.copy2(wp, _WHEEL_LIB_DIR / "libwinpthread-1.dll")
            print(f"mirrored libwinpthread-1.dll -> {_WHEEL_LIB_DIR}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=None, help="path to an existing graphite source clone (else cloned)")
    ap.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "vendor" / "graphite2"),
        help="output directory (default: vendor/graphite2/)",
    )
    args = ap.parse_args()

    out = Path(args.out)
    source, is_temp = _obtain_source(args.source)
    try:
        _build(source, out)
        _verify(out)
        _stage_wheel_lib(out)
    finally:
        if is_temp:
            shutil.rmtree(source, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
