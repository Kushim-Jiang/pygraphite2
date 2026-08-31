# Changelog

All notable changes to **pygraphite2** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
