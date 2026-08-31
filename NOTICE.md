# NOTICE

## pygraphite2

Copyright (c) 2026 pygraphite2 contributors

Licensed under the MIT License. See `LICENSE`.

## Vendored SIL International ctypes binding

`src/pygraphite2/_binding.py` is a lightly modified copy of the official ctypes
binding for graphite2, originally written by SIL International and distributed
as part of the [`silnrsi/graphite`](https://github.com/silnrsi/graphite)
project.

- **Copyright**: 2013, SIL International, All rights reserved.
- **SPDX license**: `MIT OR MPL-2.0 OR GPL-2.0-or-later`
- **Upstream source**: `silnrsi/graphite` at commit
  `ca8d821e60a15b6c24e404c9086992c975d8e1cf` (v1.3.15, 2026-06-01);
  file `python/graphite2/__init__.py`.
- **Modifications made by pygraphite2**:
  1. Library discovery is routed through `pygraphite2._loader` instead of the
     original env-var / `ctypes.util.find_library` / wheel-path logic.
  2. Type annotations and short docstrings were added.
     The native binding logic itself is unchanged.

The original file header is retained verbatim at the top of `_binding.py`.

To follow upstream updates, run `scripts/sync_upstream.py` — it fetches the
latest upstream source, diffs it against the vendored binding, and prints the
upstream commit so the (small, reviewed) re-sync can be applied. When the
native ABI changes, the vendored tracing DLL in `vendor/graphite2/` must be
rebuilt too (see `vendor/graphite2/README.md`).

## Third-party test data

- **SIL Padauk font** (optional, for golden tests) is Copyright (c) SIL
  International, distributed under the SIL Open Font License 1.1. It is *not*
  distributed with this repository; see `vendor/fonts/README.md` for download
  instructions.
