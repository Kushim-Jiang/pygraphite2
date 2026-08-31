# Test fonts

The golden regression tests in `tests/test_shape.py` need a **Graphite** font —
that is, a font with a `Silf` table.

## SIL Padauk 4.000

Place `Padauk-Regular.ttf` **version 4.000** in this folder as
`vendor/fonts/Padauk-Regular.ttf`.

> ⚠️ **Use 4.000, not newer.** Padauk 5.x/6.x moved to OpenType and no longer
> ship a `Silf` table — `pygraphite2.is_graphite_font()` will correctly report
> them as non-Graphite and the golden tests would fail to reproduce.

Download:

- GitHub: <https://github.com/silnrsi/font-padauk/releases/download/v4.000/Padauk-4.000.zip>
- Extract `Padauk-4.000/Padauk-Regular.ttf` into this directory.

The golden values in `tests/conftest.py` were generated with exactly this font
against graphite2 v1.3.14.

Padauk is © SIL International and is distributed under the SIL Open Font
License 1.1. It is included here only for testing; it is *not* shipped in the
PyPI package.
