"""Print which graphite2 native library pygraphite2 resolves and loads.

Run from an environment where pygraphite2 is installed (or editable-installed):

    uv run python scripts/find_native_lib.py
"""

from __future__ import annotations

from pygraphite2 import _loader, library_info, library_path


def main() -> None:
    resolved = _loader.resolve()
    if resolved is None:
        print("No graphite2 native library found.")
        print(library_info())
        raise SystemExit(1)
    print("Resolved: ", resolved)
    loaded = library_path()
    if loaded is not None:
        print("Loaded:   ", loaded)
    print(library_info())


if __name__ == "__main__":
    main()
