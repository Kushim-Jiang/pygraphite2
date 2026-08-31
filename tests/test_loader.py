"""Tests for the cross-platform native library loader.

The loader is lenient by design — it never raises, so these tests always run.
When no library is present they verify the graceful-degradation behaviour; when
one is, they verify discovery/loading round-trips.
"""

from __future__ import annotations

import ctypes
from pathlib import Path

import pygraphite2 as pg
from pygraphite2 import _loader


def test_loader_module_public_api() -> None:
    assert callable(_loader.resolve)
    assert callable(_loader.load)
    assert callable(_loader.is_available)
    assert callable(_loader.configure)
    assert callable(_loader.library_info)


def test_is_available_is_bool() -> None:
    assert isinstance(pg.is_available(), bool)
    assert pg.is_available() == (pg.library_path() is not None)


def test_configure_none_is_idempotent() -> None:
    pg.configure(None)
    # configure() never unloads an already-loaded library; availability stays
    # consistent with what is actually loaded.
    assert pg.is_available() == (pg.library_path() is not None)


def test_configure_bogus_path_does_not_unload() -> None:
    before = pg.is_available()
    pg.configure(Path("C:/definitely/not/a/library.so"))
    assert pg.is_available() == before
    pg.configure(None)


def test_resolve_returns_path_or_none() -> None:
    result = _loader.resolve()
    assert result is None or result.is_file()


def test_load_returns_cdll_or_none() -> None:
    lib = _loader.load()
    assert lib is None or isinstance(lib, ctypes.CDLL)


def test_env_var_honoured(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake = tmp_path / "libgraphite2.so"
    fake.write_bytes(b"not really a library")
    monkeypatch.setenv("PYGRAPHITE2_LIBRARY_PATH", str(fake))
    _loader.configure(None)
    assert _loader.resolve() == fake
    monkeypatch.delenv("PYGRAPHITE2_LIBRARY_PATH", raising=False)
    _loader.configure(None)


def test_library_info_mentions_library_name() -> None:
    assert "graphite2" in pg.library_info().lower()
