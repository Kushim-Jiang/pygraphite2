# pygraphite2

**Cross-platform, fully typed Python binding for [SIL Graphite2](https://graphite.sil.org/) text shaping.**

`pygraphite2` shapes complex scripts (Myanmar, Tai, many of the world's
orthographies that need smart-font rules) using the Graphite rendering
technology. It is a **pure-Python** package — it wraps SIL's official ctypes
binding and loads the native `libgraphite2` at runtime, so there is **no C/C++
compilation** and no build toolchain required to install it. Prebuilt native
libraries for **Windows, macOS and Linux are bundled inside the wheel**, so
normal shaping **and** the per-pass shaping trace work immediately after
`pip install`, with no system Graphite2 and no manual DLL provisioning.

```python
import pygraphite2

font = open("Padauk-Regular.ttf", "rb").read()
glyphs = pygraphite2.shape(font, "မြန်မာ")
for g in glyphs:
    print(f"gid={g.gid} cluster={g.cluster} advance={g.x_advance:.1f}")
```

## Features

- **Fully typed** — ships a `py.typed` marker and complete inline annotations
  (`mypy --strict` clean on the package).
- **Cross-platform, works out of the box** — Windows / macOS / Linux. The
  wheel bundles prebuilt native libraries (`pygraphite2/_lib/`), which are
  preferred over any system install (so tracing works); an explicit
  `configure()` / `PYGRAPHITE2_LIBRARY_PATH` override still wins, and Windows
  DLL-directory handling covers the mingw runtime dependency.
- **No temp files** — fonts are loaded fully in memory through a native table
  callback; nothing is ever written to disk.
- **Rich, ergonomic API** — glyph runs with advances/clusters, RTL support,
  script & language selection, feature overrides, and font metadata
  (units-per-em, glyph count, languages, feature enumeration).
- **Graceful degradation** — the pure-Python helpers
  (`is_graphite_font`, `has_table`, `upem_from_ttf`) work even without the
  native library; shaping calls raise a clear, actionable
  `pygraphite2.LibraryNotFound`.

## Installation

```bash
pip install pygraphite2        # or: uv add pygraphite2
```

The wheel is a universal (`py3-none-any`) wheel that **bundles the prebuilt
native libraries** for Windows, macOS and Linux under `pygraphite2/_lib/` — no
system `libgraphite2` and no manual DLL provisioning needed for shaping **or**
tracing (the bundled binaries are tracing-enabled, so `shape_trace` works too).

The native library is still loaded at runtime and overridable, so you can point
at a different build when you need to (see [Native library](#native-library)).

For development from source:

```bash
uv sync --extra dev          # or: pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

## Native library

`pygraphite2` locates `libgraphite2` at runtime in this order (first hit wins):

| # | Source | How |
|---|--------|-----|
| 1 | `pygraphite2.configure(path)` | explicit programmatic override |
| 2 | `PYGRAPHITE2_LIBRARY_PATH` env var | path to a file **or** a directory |
| 3 | Wheel-bundled `pygraphite2/_lib/` | prebuilt tracing-enabled binaries for Windows/macOS/Linux |
| 4 | System library | `ctypes.util.find_library("graphite2")` |
| 5 | Vendored checkout `vendor/graphite2/` | developer convenience |

The bundled `_lib/` library is used unless you override it. To instead rely on
a system/manual install, the per-OS ways to obtain `libgraphite2` are:

- **Debian/Ubuntu**: `sudo apt install libgraphite2-3`
- **conda-forge**: `conda install graphite2`
- **macOS**: `brew install graphite2` (if a formula is available) or conda-forge
- **Windows**: MSYS2 package `mingw-w64-x86_64-graphite2` (drop
  `graphite2.dll` plus its runtime DLLs into `vendor/graphite2/`), or conda-forge

Check what is loaded with `pygraphite2.library_info()`:

```python
>>> import pygraphite2
>>> pygraphite2.library_info()
'graphite2 v1.3.14 (D:\\...\\libgraphite2.dll)'
```

## API

### Shaping

- `pygraphite2.shape(font, text, *, direction="ltr", script=None, lang=None, features=None) -> list[Glyph]`
  — one-shot shaping; returns the glyph run.
- `pygraphite2.shape_segment(...) -> ShapedText` — same, but returns the full
  run (`glyphs` + `advance_x`/`advance_y` + metadata).
- `pygraphite2.GraphiteFont(font, *, options=0)` / `from_bytes` / `from_path`
  — a reusable font object; the recommended API when shaping many runs with the
  same font. Usable as a context manager.

`font` may be **raw bytes** or a **path** to a font file.

### Glyph & ShapedText

`Glyph` is a `NamedTuple`:

| field | meaning |
|-------|---------|
| `gid` | glyph id in the font |
| `cluster` | source character index this glyph is associated with |
| `x_advance` / `y_advance` | advances in font units (from slot origins, matching `gr2fonttest`) |
| `x_offset` / `y_offset` | offsets in font units |
| `before` / `after` | source character range covered (inclusive/exclusive) |
| `slot_index` | slot index within the segment |

`ShapedText` adds `advance_x`, `advance_y`, `text`, `direction`, `script`.

### Font inspection (pure Python — no native lib needed)

- `pygraphite2.is_graphite_font(font) -> bool` — has a `Silf` table?
- `pygraphite2.has_table(font, tag) -> bool`
- `pygraphite2.upem_from_ttf(font) -> int`
- `pygraphite2.read_font_bytes(font) -> bytes`

### Font metadata (needs the native lib)

On a `GraphiteFont` instance: `upem`, `num_glyphs`, `languages`,
`feature_refs()` (returns `tuple[Feature, ...]`, each with `tag` and `values`).

### Example with features and RTL

```python
with pygraphite2.GraphiteFont.from_path("MyGraphite.ttf") as font:
    shaped = font.shape(
        "\u0645\u0627",
        direction="rtl",
        script="arab",
        lang="urd",
        features={"StylSet": 1},
    )
    print(shaped.advance_x)
```

### Per-pass shaping trace (needs a tracing-enabled binary)

`pygraphite2.shape_trace(font, text, ...)` / `GraphiteFont.shape_trace(...)`
return a **step-by-step shaping trace** — one `TraceStage` per Graphite pass,
each a snapshot of the glyph run, bookended by "Start of shaping" (input glyphs)
and "End of shaping" (final glyphs). This is directly renderable by
Crowbar-style shaping debuggers (e.g. BabelMap's OpenType Test dialog):

```python
import pygraphite2 as pg

trace = pg.shape_trace(open("Padauk-Regular.ttf", "rb").read(), "မြန်မာ", script="mymr")
for stage in trace.stages:
    print(stage.m, [g.gid for g in stage.glyphs])
# Start of shaping [305, 392, 290, 383, 305, 354]
# Pass 1 ...
# ... the pass where reordering happens ...
# End of shaping [392, 305, 290, 383, 305, 354]
```

- `TraceStage.to_dict()` / `ShapedTrace.stages_to_dicts()` serialize to the
  `{m, glyphs, depth, effective}` / `{g, cl, dx, dy, ax, ay, flags}` schema used
  by shaping-debug UIs.
- Requires a graphite2 binary built **with** tracing support
  (`GRAPHITE2_NTRACING` off). `GraphiteFont.tracing_supported()` reports whether
  the loaded binary can trace; otherwise `shape_trace` raises `TracingUnavailable`.
  `vendor/graphite2/` ships tracing-enabled binaries for **Windows and Linux**, and
  `.github/workflows/build-native.yml` builds + verifies tracing on macOS too —
  see `vendor/graphite2/README.md`.
- Lower-level control: `GraphiteFont.start_logging(path)` / `stop_logging()`
  wrap graphite2's Segment-JSON logging directly.

## Error handling

All exceptions derive from `pygraphite2.GraphiteError`:

- `LibraryNotFound` — no native library could be located/loaded.
- `GraphiteFontError` — invalid font data, missing `Silf` table, unknown feature.
- `ShapingError` — the native shaper failed.
- `TracingUnavailable` — a trace was requested but the binary has no tracing support.

## Development

- **Tests**: `pytest` — native tests auto-skip when the library is missing;
  golden tests auto-skip when the Padauk test font is missing (place
  `Padauk-Regular.ttf` in `vendor/fonts/`).
- **Lint**: `ruff check .`  &nbsp; **Format**: `ruff format .`
- **Types**: `mypy src` (strict)
- **CI**: `.github/workflows/ci.yml` runs the test matrix on
  Ubuntu/macOS/Windows and multiple Python versions; `.github/workflows/build-native.yml`
  builds a tracing-enabled graphite2 from the pinned upstream source and verifies
  `shape_trace` on all three OSes; `.github/workflows/publish.yml`
  publishes to PyPI via trusted publishing on version tags.

## Licensing & attribution

- pygraphite2's own code is MIT-licensed.
- The vendored ctypes binding (`src/pygraphite2/_binding.py`) is © 2013
  SIL International and is distributed under its original multi-license
  (`MIT OR MPL-2.0 OR GPL-2.0-or-later`). See `NOTICE.md`.

The project's SPDX license expression is therefore
`MIT OR MPL-2.0 OR GPL-2.0-or-later`.
