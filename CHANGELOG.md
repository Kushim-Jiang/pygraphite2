# Changelog

All notable changes to **pygraphite2** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-08-31

### Added

- **Bundled native libraries** — the wheel now ships prebuilt tracing-enabled
  `libgraphite2` binaries for **Windows, macOS and Linux** under
  `pygraphite2/_lib/`, so shaping **and** `shape_trace` work out of the box
  after `pip install` — no system Graphite2, no manual DLL provisioning.
  `scripts/build_tracing_lib.py` mirrors builds into `_lib/` automatically, and
  `.github/workflows/build-dylib.yml` builds + commits a **universal2**
  (arm64 + x86_64) macOS dylib on demand.

### Changed

- **Library search order**: the wheel-bundled `_lib/` is now preferred over the
  system library, so the bundled tracing-enabled build wins (it is functionally
  identical for normal shaping) — otherwise `shape_trace` would silently not
  work when a non-tracing distro binary was present.

### Fixed

- `upem_from_ttf` / `has_table` / `is_graphite_font` now handle TrueType
  collections (`.ttc`) by opening the first face — previously they raised
  `TTLibFileIsCollectionError` on macOS (`Helvetica.ttc`) or Windows
  (`msyh.ttc`, `cambria.ttc`, ...).

## [0.3.0] - 2026-08-31

### Added

- **Per-pass shaping trace** (`shape_trace` / `GraphiteFont.shape_trace`,
  `TraceStage`, `ShapedTrace`): captures graphite2's Segment-JSON logging and
  converts it into one stage per Graphite pass (each a snapshot of the glyph
  run), plus "Start of shaping" / "End of shaping" bookends. Output serializes
  to the `{m, glyphs, depth, effective}` / `{g, cl, dx, dy, ax, ay, flags}`
  schema used by Crowbar-style shaping debuggers.
- **`GraphiteFont.start_logging(path)` / `stop_logging()` / `tracing_supported()`**
  — direct access to `gr_start_logging` / `gr_stop_logging`, with runtime
  detection of whether the loaded binary was built with tracing support.
- **`TracingUnavailable`** error raised when a trace is requested from a binary
  without tracing support.
- **Cross-platform tracing**: `scripts/build_tracing_lib.py` builds a
  tracing-enabled graphite2 (`-DGRAPHITE2_NTRACING=OFF`) for the current
  platform (Windows/macOS/Linux) and verifies `gr_start_logging` works;
  `.github/workflows/build-native.yml` builds + verifies `shape_trace` on all
  three OSes in CI; `vendor/graphite2/` now ships a tracing-enabled **Windows
  DLL and Linux `.so`** (graphite2 1.3.15), so `shape_trace` works out of the
  box on both. See `vendor/graphite2/README.md`.

### Fixed

- The loader's vendored-directory discovery now walks up the package's parents
  to find `vendor/graphite2/`, which was broken under the `src/` layout (it
  looked one directory too high, so the vendored library was never found).
- `scripts/build_tracing_lib.py` no longer appends `.exe` when searching for
  `libwinpthread-1.dll` (it used to miss the mingw toolchain's copy and could
  pick up an unrelated one from PATH), and it prefers the canonical
  `build/src` library over the `gr2fonttest` copy.

## [0.2.0] - 2026-08-31

This release is the first from the independent `pygraphite2` repository. The
code previously lived as a sub-package inside another application repository
(see `archive/` for the historical code); it has been fully restructured,
typed, and prepared for publication on PyPI.

### Added

- **Independent repo structure** with a standard `src/` layout and
  `hatchling`-based packaging (PEP 621 metadata).
- **Complete type annotations** across the public API and package internals,
  plus a `py.typed` marker (PEP 561) — the package is `mypy --strict` clean.
- **New high-level `GraphiteFont` class**:
  - fully in-memory font loading via a native table callback (no temp files),
  - `from_bytes` / `from_path` constructors and context-manager support,
  - font metadata: `upem`, `num_glyphs`, `languages`, `feature_refs()`.
- **`shape_segment()`** returning a rich `ShapedText` (glyphs + advances +
  metadata); `shape()` remains as a thin wrapper returning `list[Glyph]`.
- **Feature overrides** — pass `features={"MyFeat": 1}` and an optional
  `lang` tag to `shape()` / `GraphiteFont.shape()`.
- **Explicit error hierarchy** — `GraphiteError`, `LibraryNotFound`,
  `GraphiteFontError`, `ShapingError`.
- **Robust cross-platform loader** (`pygraphite2._loader`) with a documented
  discovery order, an explicit `configure()` override, Windows DLL-directory
  handling, and a helpful `library_info()` diagnostic.
- **CI/CD** — GitHub Actions test matrix (Ubuntu/macOS/Windows × Python 3.9–3.13)
  and a PyPI publishing workflow using trusted publishing.
- **Tooling** — `ruff` lint/format and `mypy` strict configuration wired into
  `pyproject.toml`.

### Changed

- Library discovery is now routed through `pygraphite2._loader` (the vendored
  SIL binding no longer performs its own env-var/file search).
- The golden regression tests are retained from the original project (from
  README §7 of the archive), along with the `vendor/fonts` test-font location.

### Removed

- The old sys.path-based "namespace package" layout that could shadow the real
  package; everything now lives under `src/pygraphite2/`.

## [0.1.0] - (unreleased, archive)

Original implementation archived under `archive/`. See `archive/README.md` and
`archive/CHANGELOG.md` (if present) for historical notes.
