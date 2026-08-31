"""Track the vendored SIL binding against upstream graphite2.

pygraphite2 vendors two things from `silnrsi/graphite`:

1. the ctypes binding  -> ``src/pygraphite2/_binding.py``
2. the native library  -> ``vendor/graphite2/`` (rebuilt with tracing enabled)

This script fetches the upstream repo at a ref (default: the pinned release
commit recorded in ``NOTICE.md``), diffs the upstream binding against our
vendored copy, and prints the upstream commit so a maintainer can review and
apply the (small) re-sync. It is **read-only** — it never edits files.

When the native ABI changes upstream, the vendored tracing DLL must also be
rebuilt (see ``vendor/graphite2/README.md``).

Usage::

    python scripts/sync_upstream.py                  # against the pinned ref
    python scripts/sync_upstream.py --ref master     # against upstream HEAD
    python scripts/sync_upstream.py --workdir /tmp/graphite  # reuse a clone
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/silnrsi/graphite.git"
# graphite2 v1.3.15 — the release commit this repo is vendored against.
PINNED_REF = "ca8d821e60a15b6c24e404c9086992c975d8e1cf"
UPSTREAM_BINDING = "python/graphite2/__init__.py"
OUR_BINDING = Path(__file__).resolve().parent.parent / "src" / "pygraphite2" / "_binding.py"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _show(repo: Path, ref: str, path: str) -> str | None:
    """Return the file content at ``ref:path`` (or None if absent)."""
    r = _git(repo, "show", f"{ref}:{path}")
    if r.returncode != 0:
        return None
    return r.stdout


# Matches fn('name', ...) / fn("name", ...), allowing the call to be spread
# across lines by a formatter (fn(\n    "name", ...)).
_FN_NAME = re.compile(r"""fn\(\s*(["'])([^"']+)\1""")


def _registered_names(text: str) -> set[str]:
    """Native functions registered via ``fn('name', ...)`` — the ABI surface."""
    return {m.group(2) for m in _FN_NAME.finditer(text)}


def _abi_report(upstream: str, ours: str) -> None:
    """Compare the set of registered native functions (a coarse ABI signal)."""
    up, us = _registered_names(upstream), _registered_names(ours)
    added = sorted(up - us)
    removed = sorted(us - up)
    print("ABI surface (registered fn names):")
    if not added and not removed:
        print("  identical — no new/removed native functions upstream")
    else:
        if added:
            print(f"  NEW upstream functions: {', '.join(added)}")
        if removed:
            print(f"  functions we register that upstream dropped: {', '.join(removed)}")
    print(
        "  (signature changes inside an existing fn() are not detected by this "
        "heuristic — review the diff below for argtypes/restype changes)"
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--ref", default=PINNED_REF, help="upstream git ref to diff against")
    ap.add_argument("--workdir", default=None, help="reuse an existing upstream clone directory")
    args = ap.parse_args()

    if args.workdir:
        repo = Path(args.workdir)
    else:
        repo = Path(tempfile.mkdtemp(prefix="gr2sync-"))
        print(f"Cloning {REPO_URL} (shallow) into {repo} ...")
        r = _git(repo, "clone", "--depth", "1", REPO_URL, str(repo))
        if r.returncode != 0:
            print(r.stderr)
            return 1

    # Resolve the ref to a commit. Prefer a local resolution (works when the
    # commit is already present, e.g. with --workdir); only hit the network if
    # the commit is missing. Shallow-fetching an arbitrary SHA can be flaky, so
    # fall back to a full fetch, then to an unambiguous ref name.
    resolved = _git(repo, "rev-parse", "--verify", f"{args.ref}^{{commit}}").stdout.strip()
    if not resolved:
        for attempt in (
            ["fetch", "--depth", "1", "origin", args.ref],
            ["fetch", "origin", args.ref],
        ):
            r = _git(repo, *attempt)
            if r.returncode != 0:
                continue
            resolved = _git(repo, "rev-parse", "--verify", f"{args.ref}^{{commit}}").stdout.strip()
            if resolved:
                break
    if not resolved:
        print(f"Could not resolve upstream ref {args.ref!r} (network fetch failed?)")
        return 1
    print(f"\nUpstream ref  : {args.ref}")
    print(f"Commit        : {resolved}")
    print(f"Local binding : {OUR_BINDING}")

    upstream = _show(repo, resolved, UPSTREAM_BINDING)
    if upstream is None:
        print(f"\nUpstream has no file at {resolved}:{UPSTREAM_BINDING} — path may have moved.")
        return 1
    ours = OUR_BINDING.read_text(encoding="utf-8")

    # Keep only the parts of the binding that are upstream-authored so the diff
    # ignores our docstring/header additions is not possible generically, so we
    # report a full diff and a line-level summary instead.
    diff_lines = list(
        difflib.unified_diff(
            upstream.splitlines(),
            ours.splitlines(),
            fromfile=f"upstream@{resolved[:12]}:{UPSTREAM_BINDING}",
            tofile="src/pygraphite2/_binding.py (vendored)",
            lineterm="",
        )
    )
    added = sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---"))
    print(
        f"\nDiff vs vendored copy: {removed} lines removed, {added} added "
        f"({'IDENTICAL' if not added and not removed else 'DIFFERS'})"
    )

    _abi_report(upstream, ours)

    # Show a bounded excerpt of the diff (full output can be piped to a file).
    shown = 0
    for ln in diff_lines:
        if ln.startswith(("+++", "---", "@@")):
            continue
        print(ln)
        shown += 1
        if shown >= 120:
            print("... (diff truncated; re-run with output redirected to a file)")
            break

    print(
        "\nNext steps if the binding differs:\n"
        "  1. Review the diff above (we intentionally add loader integration +\n"
        "     type annotations on top of the upstream binding).\n"
        "  2. Apply the upstream changes to src/pygraphite2/_binding.py.\n"
        "  3. If native function signatures changed (ABI), rebuild the tracing DLL\n"
        "     (see vendor/graphite2/README.md) and update the pinned refs in\n"
        "     NOTICE.md and vendor/graphite2/README.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
