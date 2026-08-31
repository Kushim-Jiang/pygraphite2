"""Tests for the per-pass shaping trace.

The JSON parser (:mod:`pygraphite2._trace`) is pure Python and is tested with
synthetic documents. The native tracing tests need a graphite2 binary built
with tracing support (``vendor/graphite2/`` ships one); they auto-skip when the
loaded binary lacks it.
"""

from __future__ import annotations

import json

import pytest

import pygraphite2 as pg
from pygraphite2 import _trace
from tests.conftest import MYANMAR, PADAUK, needs_library, needs_padauk

# ── pure-Python parser tests (no native library required) ─────────────

_SAMPLE_LOG = json.dumps(
    [
        {
            "id": "seg-1",
            "passes": [
                {
                    "id": 1,
                    "slotsdir": "ltr",
                    "passdir": "ltr",
                    "slots": [
                        {
                            "gid": 305,
                            "charinfo": {"original": 0, "before": 0, "after": 0},
                            "origin": [0, 0],
                            "advance": [585, 0],
                        },
                        {
                            "gid": 392,
                            "charinfo": {"original": 1, "before": 1, "after": 1},
                            "origin": [585, 0],
                            "advance": [172, 0],
                        },
                    ],
                },
                {
                    "id": 2,
                    "slotsdir": "ltr",
                    "passdir": "ltr",
                    "slots": [
                        {
                            "gid": 392,
                            "charinfo": {"original": 1, "before": 1, "after": 1},
                            "origin": [0, 0],
                            "advance": [172, 0],
                        },
                        {
                            "gid": 305,
                            "charinfo": {"original": 0, "before": 0, "after": 0},
                            "origin": [172, 0],
                            "advance": [585, 0],
                        },
                    ],
                },
            ],
            "output": [
                {
                    "gid": 392,
                    "charinfo": {"original": 1, "before": 1, "after": 1},
                    "origin": [0, 0],
                    "advance": [172, 0],
                },
                {
                    "gid": 305,
                    "charinfo": {"original": 0, "before": 0, "after": 0},
                    "origin": [172, 0],
                    "advance": [585, 0],
                },
            ],
            "advance": [757, 0],
            "outputdir": "ltr",
            "chars": [],
        }
    ]
)


def test_parse_segment_log_basic() -> None:
    stages, final = _trace.parse_segment_log(_SAMPLE_LOG)
    assert len(stages) == 2
    assert stages[0].m == "Pass 1"
    assert stages[1].m == "Pass 2"
    assert [g.gid for g in stages[0].glyphs] == [305, 392]
    assert [g.gid for g in stages[1].glyphs] == [392, 305]
    assert [g.gid for g in final] == [392, 305]
    # slot metadata is preserved
    g = stages[0].glyphs[0]
    assert g.cluster == 0 and g.before == 0 and g.after == 0
    assert g.x_advance == 585.0 and g.y_offset == 0.0


def test_parse_segment_log_takes_last_segment() -> None:
    # Logging is face-wide and accumulates every segment created while active;
    # the parser must use the most recently created (last) segment.
    seg = json.loads(_SAMPLE_LOG)[0]
    doc = json.dumps([seg, seg])
    stages, _ = _trace.parse_segment_log(doc)
    assert len(stages) == 2  # the last segment's passes


def test_parse_segment_log_empty_raises() -> None:
    with pytest.raises(ValueError):
        _trace.parse_segment_log("[]")


def test_parse_segment_log_tolerant_of_nan() -> None:
    # json.cpp can emit bare NaN/Infinity literals; the parser must not choke.
    raw = '[{"passes":[{"id":1,"slots":[{"gid":1,"origin":[NaN,0]}]}],"output":[]}]'
    stages, _ = _trace.parse_segment_log(raw)
    assert stages[0].glyphs[0].x_offset == 0.0


def test_parse_segment_log_bidi_pass_label() -> None:
    raw = '[{"passes":[{"id":-1,"slots":[]}],"output":[]}]'
    stages, _ = _trace.parse_segment_log(raw)
    assert stages[0].m == "Bidi / mirroring pass"


def test_trace_stage_to_dict_schema() -> None:
    stages, _ = _trace.parse_segment_log(_SAMPLE_LOG)
    d = stages[0].to_dict()
    assert set(d) == {"m", "glyphs", "depth", "effective"}
    glyphs = d["glyphs"]
    assert isinstance(glyphs, list)
    assert glyphs[0] == {"g": 305, "cl": 0, "dx": 0, "dy": 0, "ax": 585, "ay": 0, "flags": 0}


# ── native tracing tests (need a tracing-enabled binary) ─────────────


def _tracing_supported() -> bool:
    try:
        with pg.GraphiteFont.from_bytes(PADAUK.read_bytes()) as font:
            return font.tracing_supported()
    except Exception:
        return False


pytestmark = [
    needs_library,
    needs_padauk,
    pytest.mark.skipif(
        not _tracing_supported(), reason="loaded graphite2 binary lacks tracing support"
    ),
]


def test_shape_trace_stages(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        trace = font.shape_trace(MYANMAR, script="mymr")
    assert trace.stages[0].m == "Start of shaping"
    assert trace.stages[-1].m == "End of shaping"
    # at least one Graphite pass between the bookends
    assert len(trace.stages) >= 3
    # passes are labelled
    passes = trace.stages[1:-1]
    assert any(s.m.startswith("Pass ") or s.m == "Bidi / mirroring pass" for s in passes)
    # every stage carries a glyph snapshot
    for s in trace.stages:
        assert all(isinstance(g, pg.Glyph) for g in s.glyphs)


def test_shape_trace_final_matches_shape(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        trace = font.shape_trace(MYANMAR, script="mymr")
        shaped = font.shape(MYANMAR, script="mymr")
    assert [g.gid for g in trace.final] == [g.gid for g in shaped.glyphs]


def test_shape_trace_end_stage_is_final(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        trace = font.shape_trace(MYANMAR, script="mymr")
    assert [g.gid for g in trace.stages[-1].glyphs] == [g.gid for g in trace.final]


def test_shape_trace_start_is_input(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        trace = font.shape_trace(MYANMAR, script="mymr")
    start = trace.stages[0].glyphs
    assert len(start) == len(MYANMAR)
    assert all(g.cluster == i for i, g in enumerate(start))


def test_shape_trace_include_start_false(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        trace = font.shape_trace(MYANMAR, script="mymr", include_start=False)
    assert trace.stages[0].m != "Start of shaping"


def test_shape_trace_stages_to_dicts(padauk_bytes: bytes) -> None:
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        trace = font.shape_trace(MYANMAR, script="mymr")
    rows = trace.stages_to_dicts()
    assert len(rows) == len(trace.stages)
    assert set(rows[1]) == {"m", "glyphs", "depth", "effective"}
    assert set(rows[1]["glyphs"][0]) == {"g", "cl", "dx", "dy", "ax", "ay", "flags"}


def test_start_stop_logging_round_trip(padauk_bytes: bytes, tmp_path) -> None:  # type: ignore[no-untyped-def]
    log = tmp_path / "trace.json"
    with pg.GraphiteFont.from_bytes(padauk_bytes) as font:
        assert font.start_logging(log) is True
        font.shape(MYANMAR, script="mymr")
        font.stop_logging()
    assert log.is_file()
    assert log.stat().st_size > 0


def test_one_shot_shape_trace(padauk_bytes: bytes) -> None:
    trace = pg.shape_trace(padauk_bytes, MYANMAR, script="mymr")
    assert trace.final
    assert trace.stages[-1].m == "End of shaping"
