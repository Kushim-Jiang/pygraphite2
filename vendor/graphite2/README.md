# graphite2 native library

`pygraphite2` does **not** compile graphite2 and does **not** bundle it in the
default wheel. It loads the native library at runtime, in this order:

1. `pygraphite2.configure(path)` — explicit programmatic override (before first use)
2. `PYGRAPHITE2_LIBRARY_PATH` (env var — a file **or** a directory)
3. system library (`ctypes.util.find_library("graphite2")`)
4. **this folder** (`vendor/graphite2/`) — repository checkout convenience
5. (future) a wheel-bundled `pygraphite2/_lib/`

Drop the correct file(s) into this folder (or rely on a system install).

| Platform | File(s) to place here | How to get it |
| -------- | --------------------- | ------------- |
| Windows  | `graphite2.dll` (+ MSYS2 runtime DLLs: `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll`) | MSYS2 package `mingw-w64-x86_64-graphite2` (plus matching `gcc-libs`/`libwinpthread` runtime DLLs), or conda-forge `graphite2` (extract `Library/bin/graphite2.dll` + its runtime). |
| Linux    | (optional) `libgraphite2.so` | `sudo apt install libgraphite2-3` (Debian/Ubuntu) or `conda install -c conda-forge graphite2` — the system lib is found automatically, no vendoring needed. |
| macOS    | (optional) `libgraphite2.dylib` | `brew install graphite2` (if a formula exists) or `conda install -c conda-forge graphite2` — the system lib is found automatically. |

Use `scripts/find_native_lib.py` (or `pygraphite2.library_info()`) to see what
was found.
