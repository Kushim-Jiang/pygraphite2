# graphite2 native library

`pygraphite2` does **not** compile graphite2. It loads the native library at
runtime, in this order:

1. `pygraphite2.configure(path)` — explicit programmatic override (before first use)
2. `PYGRAPHITE2_LIBRARY_PATH` (env var — a file **or** a directory)
3. **wheel-bundled** `pygraphite2/_lib/` (prebuilt tracing-enabled binaries)
4. system library (`ctypes.util.find_library("graphite2")`)
5. **this folder** (`vendor/graphite2/`) — repository checkout convenience

The published wheel bundles the binaries (mirrored from here into
`src/pygraphite2/_lib/`), so installed users get them automatically. This
folder serves developers working from a checkout; drop the correct file(s) here
(or rely on a system install) if you want to override the bundled build.

| Platform | File(s) to place here | How to get it |
| -------- | --------------------- | ------------- |
| Windows  | `graphite2.dll` (+ MSYS2 runtime DLLs: `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll`) | MSYS2 package `mingw-w64-x86_64-graphite2` (plus matching `gcc-libs`/`libwinpthread` runtime DLLs), or conda-forge `graphite2` (extract `Library/bin/graphite2.dll` + its runtime). |
| Linux    | (optional) `libgraphite2.so` | `sudo apt install libgraphite2-3` (Debian/Ubuntu) or `conda install -c conda-forge graphite2` |
| macOS    | (optional) `libgraphite2.dylib` | `brew install graphite2` (if a formula exists) or `conda install -c conda-forge graphite2` |

Use `scripts/find_native_lib.py` (or `pygraphite2.library_info()`) to see what
was found.

## Vendored tracing-enabled build (this repo)

This folder ships **tracing-enabled binaries** for the platforms we build
locally — they power the per-pass shaping trace
(`pygraphite2.shape_trace` / `GraphiteFont.start_logging`):

- `libgraphite2.dll` (+ `libwinpthread-1.dll`) — **Windows** (mingw-w64;
  libgcc/libstdc++ linked statically; the UCRT is part of Windows 10+).
- `libgraphite2.so` — **Linux** (built with a conda-forge gcc; depends only on
  glibc ≥ 2.34).
- `libgraphite2.dylib` — **macOS** — produced by
  `.github/workflows/build-dylib.yml` (manual dispatch: it builds on
  `macos-latest` and commits the dylib here + into `_lib/`).

These are **mirrored into `src/pygraphite2/_lib/`**, which is what gets bundled
into the wheel, so installed users on all three platforms get tracing out of
the box. `scripts/build_tracing_lib.py` stages both locations automatically.

All are graphite2 **1.3.15** (upstream commit
`ca8d821e60a15b6c24e404c9086992c975d8e1cf`), compiled from
[`silnrsi/graphite`](https://github.com/silnrsi/graphite) with
**`-DGRAPHITE2_NTRACING=OFF`** (tracing enabled). Most distro/release binaries
compile with `GRAPHITE2_NTRACING=ON` (the default), which makes
`gr_start_logging` a no-op — that is why we vendor purpose-built ones.

### Rebuilding it

`scripts/build_tracing_lib.py` builds a tracing-enabled copy for the **current**
platform and drops it into this folder (or `--out DIR`):

```sh
python scripts/build_tracing_lib.py                      # into vendor/graphite2/
python scripts/build_tracing_lib.py --source /path/to/graphite  # reuse a clone
python scripts/build_tracing_lib.py --out /tmp/gr2lib    # custom output dir
```

It configures cmake with `-DGRAPHITE2_NTRACING=OFF`, builds, copies the library
with the correct per-OS name, and verifies `gr_start_logging` actually works.
On Windows it auto-detects a mingw-w64 toolchain (Strawberry Perl / MSYS2) and
links the mingw runtime statically; on macOS/Linux it uses the system `cmake`
and C/C++ compiler. Requirements: `cmake` and a C/C++ compiler.

Equivalent manual build on Windows (mingw-w64 GCC + cmake):

```sh
cmake -S graphite -B build -G "MinGW Makefiles" \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF \
      -DGRAPHITE2_NTRACING=OFF \
      -DCMAKE_SHARED_LINKER_FLAGS="-static-libgcc -static-libstdc++"
cmake --build build
# copy build/src/libgraphite2.dll and $MINGW/bin/libwinpthread-1.dll here
```

Verify tracing works:

```python
import pygraphite2 as pg

with pg.GraphiteFont.from_path("Padauk-Regular.ttf") as f:
    assert f.tracing_supported()
    print([s.m for s in f.shape_trace("မြန်မာ", script="mymr").stages])
```

> **Note**: tracing-enabled builds are intended for debugging/shaping-trace tooling.
> They are functionally identical for normal shaping but carry the extra
> tracing code. Replace with a plain (non-tracing) DLL if you don't need traces.
