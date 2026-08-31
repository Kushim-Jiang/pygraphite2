# graphite2 native library — how to obtain it per platform

`pygraphite2` does **not** compile graphite2. It loads the native library at
runtime, in this order:

1. `PYGRAPHITE2_LIBRARY_PATH` (env var)
2. system library (`ctypes.util.find_library("graphite2")`)
3. **this folder** (`pygraphite2/vendor/graphite2/`)

Drop the correct file into this folder (or rely on a system install).

| Platform | File(s) to place here | How to get it |
| -------- | --------------------- | ------------- |
| Windows  | `libgraphite2.dll` + `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll` | MSYS2 package `mingw-w64-x86_64-graphite2` (plus matching `gcc-libs`/`libwinpthread` runtime DLLs), or conda-forge `graphite2` (extract `Library/bin/graphite2.dll` + its runtime). |
| Linux    | `libgraphite2.so` (optional) | `sudo apt install libgraphite2-3` (Debian/Ubuntu) or `conda install -c conda-forge graphite2` — system lib is found automatically, no vendoring needed. |
| macOS    | `libgraphite2.dylib` (optional) | `brew install graphite2` (if a formula exists) or `conda install -c conda-forge graphite2` — system lib is found automatically. |

## Test fonts

Graphite fonts carry a `Silf` table. Place a test font (e.g. SIL **Padauk**
`Padauk-Regular.ttf`) in `pygraphite2/vendor/fonts/` for `tests/test_shape.py`.
Download from <https://software.sil.org/padauk/download/> or the
[font-padauk](https://github.com/silnrsi/font-padauk) releases.
