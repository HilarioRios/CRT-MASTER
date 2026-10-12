import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from vtt_parser import parse_vtt  # noqa: E402

# Real YouTube auto-caption roll-up shape (placeholder blank-space lines
# omitted -- they carry no content, the parser filters them via .strip()):
# a cue with 2 lines shows [previous completed line] + [new tagged line
# currently revealing -- a NEW phrase, not a continuation of line 1]. Each
# such cue is immediately followed by a "snap" cue restating just the new
# line cleanly, once fully revealed.
ROLLUP_VTT = """WEBVTT
Kind: captions
Language: es

00:00:00.000 --> 00:00:02.070 align:start position:0%
Te<00:00:00.160><c> ha</c><00:00:00.320><c> pasado</c><00:00:00.599><c> que</c>

00:00:02.070 --> 00:00:02.080 align:start position:0%
Te ha pasado que

00:00:02.080 --> 00:00:05.390 align:start position:0%
Te ha pasado que
ves<00:00:02.879><c> un</c><00:00:03.120><c> patron</c><00:00:03.360><c> CRT</c>

00:00:05.390 --> 00:00:05.400 align:start position:0%
ves un patron CRT

00:00:08.000 --> 00:00:10.500 align:start position:0%
Siguiente<00:00:08.300><c> oracion</c><00:00:08.600><c> distinta</c>

00:00:10.500 --> 00:00:10.510 align:start position:0%
Siguiente oracion distinta
"""


def test_collapses_growing_cue_and_its_snap_cue_into_one_segment():
    segments = parse_vtt(ROLLUP_VTT)
    texts = [s.text for s in segments]
    assert texts == ["Te ha pasado que", "ves un patron CRT", "Siguiente oracion distinta"]


def test_no_stray_tags_or_timestamps_in_text():
    segments = parse_vtt(ROLLUP_VTT)
    for s in segments:
        assert "<" not in s.text and ">" not in s.text
        assert "-->" not in s.text


def test_segment_timing_spans_growing_cue_through_its_snap_cue():
    segments = parse_vtt(ROLLUP_VTT)
    # "ves un patron CRT" starts revealing at the growing cue (2.08) and its
    # snap cue ends at 5.4 -- the merged segment should span both.
    merged = segments[1]
    assert merged.start_sec == 2.08
    assert merged.end_sec == 5.4


def test_empty_input_returns_no_segments():
    assert parse_vtt("WEBVTT\n\n") == []
