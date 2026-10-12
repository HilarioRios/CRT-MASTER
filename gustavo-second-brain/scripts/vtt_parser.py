"""Parses YouTube auto-caption VTT files into clean (start_sec, end_sec, text)
segments.

YouTube auto-captions render as a 2-line "roll-up": each cue block shows the
previous completed line (clean, no tags) followed by the currently-revealing
line (with per-word <c> timing tags, but already containing the full line
text -- the tags are for karaoke-style highlighting, not truncation). Each
such cue is immediately followed by a near-zero-duration "snap" cue
containing just that line's clean, final text. Concretely, for a block of
real speech:

  cue A (real duration): [prev clean line] [new line with <c> tags]
  cue B (near-zero duration, "snap"): [new line, now clean]

So: take the LAST line of each cue block, strip <c> tags (this already
yields the complete line, tags are inline per-word annotations not partial
text), then collapse consecutive cues whose cleaned last-line is identical
-- that's the same spoken line appearing once mid-reveal and once in the
snap cue. The merged segment spans the first occurrence's start to the
last occurrence's end.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TAG_RE = re.compile(r"<[^>]+>")
TIMESTAMP_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
)


@dataclass
class Segment:
    start_sec: float
    end_sec: float
    text: str


def _ts_to_sec(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _clean_text(raw: str) -> str:
    return TAG_RE.sub("", raw).strip()


def parse_vtt(content: str) -> list[Segment]:
    lines = content.splitlines()
    cues: list[tuple[float, float, str]] = []  # (start, end, last-line clean text)

    i = 0
    while i < len(lines):
        m = TIMESTAMP_RE.search(lines[i])
        if not m:
            i += 1
            continue
        start = _ts_to_sec(*m.groups()[0:4])
        end = _ts_to_sec(*m.groups()[4:8])
        i += 1
        block_lines = []
        while i < len(lines) and lines[i] != "":
            block_lines.append(lines[i])
            i += 1
        # last non-whitespace-only line in this block is the current content
        content_lines = [ln for ln in block_lines if ln.strip()]
        if content_lines:
            text = _clean_text(content_lines[-1])
            if text:
                cues.append((start, end, text))

    if not cues:
        return []

    # Collapse consecutive cues with identical clean text (mid-reveal cue +
    # its following snap cue repeating the same finished line).
    collapsed: list[list] = []
    for start, end, text in cues:
        if collapsed and collapsed[-1][2] == text:
            collapsed[-1][1] = end
        else:
            collapsed.append([start, end, text])

    return [Segment(s, e, t) for s, e, t in collapsed]
