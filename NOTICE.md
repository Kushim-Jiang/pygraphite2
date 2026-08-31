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
- **Modifications made by pygraphite2**:
  1. Library discovery is routed through `pygraphite2._loader` instead of the
     original env-var / `ctypes.util.find_library` / wheel-path logic.
  2. Type annotations and short docstrings were added.
     The native binding logic itself is unchanged.

The original file header is retained verbatim at the top of `_binding.py`.

## Third-party test data

- **SIL Padauk font** (optional, for golden tests) is Copyright (c) SIL
  International, distributed under the SIL Open Font License 1.1. It is *not*
  distributed with this repository; see `vendor/fonts/README.md` for download
  instructions.
