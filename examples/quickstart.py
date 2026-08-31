"""Quickstart example for pygraphite2.

Run from the repository root with an editable install active:

    uv sync --extra dev
    uv run python examples/quickstart.py
"""

from __future__ import annotations

from pathlib import Path

import pygraphite2

FONT_PATH = Path(__file__).resolve().parent.parent / "vendor" / "fonts" / "Padauk-Regular.ttf"
TEXT = "မြန်မာ"


def main() -> None:
    print("Library:", pygraphite2.library_info())

    if not FONT_PATH.is_file():
        print(f"Test font not found at {FONT_PATH} — see vendor/fonts/README.md")
        return

    data = FONT_PATH.read_bytes()
    print(f"Is Graphite font: {pygraphite2.is_graphite_font(data)}")

    # One-shot shaping: font bytes + text -> list[Glyph]
    glyphs = pygraphite2.shape(data, TEXT, script="mymr")
    print("One-shot shape:")
    for g in glyphs:
        print(f"  gid={g.gid:4d} cluster={g.cluster} advance={g.x_advance:8.1f}")

    # Reusable font object (recommended for many runs with the same font)
    with pygraphite2.GraphiteFont.from_path(FONT_PATH) as font:
        print(f"upem={font.upem} num_glyphs={font.num_glyphs} languages={font.languages}")
        shaped = font.shape(TEXT, script="mymr", features={"kdot": 1})
        print(f"Total advance: {shaped.advance_x:.1f}")


if __name__ == "__main__":
    main()
