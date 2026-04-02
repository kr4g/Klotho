"""SVG renderer for percussion-style (single-line) notation.

Uses Bravura (SMuFL) font for music glyphs, base64-embedded for portability.
Dimensions derived from bravura_metadata.json where possible.
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from dataclasses import replace as dc_replace
from pathlib import Path

import svgwrite

from ..models import (
    EngravingLeaf, TupletBracket, BeamGroup, NotatedMeasure, NotatedSystem,
    NotatedScore, NoteType,
)
from ..core.duration import beam_count
from . import smufl
from ..constants import BAR_X, END_PAD, TS_DIGIT_W, TS_BARLINE_GAP, TS_NOTE_GAP

# ── Dimensions (SVG px) ───────────────────────────────────────────────
# SMuFL convention: 1 staff-space = font_size / 4
FONT_SIZE = 30
SP = FONT_SIZE / 4                     # 7.5 px per staff-space

STAFF_Y = 110
REST_FONT_SIZE = 26
STEM_LEN = 3.5 * SP                   # ~26 px
STEM_W = max(1.0, 0.12 * SP * 2)      # visible stem width
BEAM_H = 0.5 * SP                     # 3.75 px (from metadata beamThickness)
BEAM_GAP = 0.25 * SP * 2              # 3.75 px (beamSpacing, boosted for clarity)
FLAG_SIZE = FONT_SIZE
DOT_R = 2.0
TIE_H = 8

# Tuplet brackets: innermost sits just above stem tips, outer ones expand upward
# Stem tip ≈ STAFF_Y - STEM_LEN + STEM_ATTACH_DY ≈ 83
# So innermost bracket at ~70, each outer level 14px higher
TUPLET_INNER_Y = 70       # Y of innermost (deepest) tuplet bracket
TUPLET_STEP = 14           # Each outer nesting level goes this much higher
TUPLET_HOOK = 4
TUPLET_FONT = 11

TS_FONT = 20
TS_NUM_Y_OFF = -7                 # Numerator center offset above staff line
TS_DEN_Y_OFF = 7                  # Denominator center offset below staff line
NOTE_X0 = 62
BAR_EXT = 8
RT_Y_OFF = 34
RT_FONT = 9.5

# From Bravura metadata:
#   noteheadBlack bBox: SW=(0,-0.5) NE=(1.18, 0.5)  → width=1.18 sp, height=1.0 sp
#   stemUpSE anchor: (1.18, 0.168)  → stem attaches at right edge, 0.168 sp above center
NH_W = 1.18 * SP                       # ~8.85 px full notehead width
NH = NH_W / 2                          # ~4.4 px half-width
STEM_ATTACH_DY = -0.168 * SP           # stem starts this far above baseline (~-1.26 px)
                                       # (negative = above in SVG coords, INTO the notehead)

# Font paths
_FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"
_OTF = _FONT_DIR / "Bravura.otf"
_FAMILY = "Bravura"
_b64_cache: str | None = None


def _font_b64() -> str:
    global _b64_cache
    if _b64_cache is None:
        with open(_OTF, 'rb') as f:
            _b64_cache = base64.b64encode(f.read()).decode('ascii')
    return _b64_cache


# ── Public API ─────────────────────────────────────────────────────────

def render_measure(
    measure: NotatedMeasure,
    width: float = 800,
    height: float = 200,
    show_rt_text: bool = True,
) -> svgwrite.Drawing:
    if show_rt_text and measure.rt_text:
        n = len(measure.rt_text.split('\n'))
        height = max(height, STAFF_Y + RT_Y_OFF + n * (RT_FONT + 3) + 10)

    # Auto-widen for multi-bar if barline positions exceed default width
    if measure.barline_x_positions:
        needed = measure.barline_x_positions[-1] + END_PAD
        width = max(width, needed)

    dwg = svgwrite.Drawing(size=(f"{width}px", f"{height}px"))
    dwg.add(dwg.rect(insert=(0, 0), size=(width, height), fill="white"))

    if _OTF.exists():
        b64 = _font_b64()
        dwg.defs.add(dwg.style(
            f"@font-face {{ font-family:'{_FAMILY}';"
            f" src:url('data:font/otf;base64,{b64}') format('opentype'); }}"
        ))

    if measure.show_barlines:
        if measure.barline_x_positions:
            # Multi-bar: use computed barline positions
            bl_start = measure.barline_x_positions[0]
            bl_end = measure.barline_x_positions[-1]
            dwg.add(dwg.line(start=(bl_start, STAFF_Y), end=(bl_end, STAFF_Y),
                              stroke="black", stroke_width=0.8))
            for bx in measure.barline_x_positions:
                _barline_at(dwg, bx)
        else:
            # Single measure: compute right edge from events
            rx = (max(e.x for e in measure.events) + END_PAD) if measure.events else width - 20
            rx = min(rx, width - 20)
            dwg.add(dwg.line(start=(BAR_X, STAFF_Y), end=(rx, STAFF_Y),
                              stroke="black", stroke_width=0.8))
            _barline_at(dwg, BAR_X)
            _barline_at(dwg, rx)
        if measure.time_signature is not None:
            _time_sig_at(dwg, measure.time_signature, BAR_X + TS_BARLINE_GAP)
    else:
        # No barlines: just the staff line spanning the events
        if measure.events:
            lx = measure.events[0].x - 10
            rx = measure.events[-1].x + END_PAD
        else:
            lx, rx = 10, width - 10
        dwg.add(dwg.line(start=(lx, STAFF_Y), end=(rx, STAFF_Y),
                          stroke="black", stroke_width=0.8))

    if measure.tempo_beat is not None and measure.tempo_bpm is not None:
        _tempo_marking_at_y(dwg, measure.tempo_beat, measure.tempo_bpm, NOTE_X0)

    beamed = set()
    for bg in measure.beam_groups:
        for i in bg.event_indices:
            beamed.add(i)

    for i, ev in enumerate(measure.events):
        if ev.is_rest:
            _rest_at(dwg, ev)
        else:
            _note_at(dwg, ev, flagged=(i not in beamed))

    for bg in measure.beam_groups:
        _beams_at(dwg, bg, measure.events)

    for i in range(len(measure.events) - 1):
        if measure.events[i].is_tied_forward or measure.events[i + 1].is_continuation_tie:
            _tie_at(dwg, measure.events[i], measure.events[i + 1])

    _tuplets_at(dwg, measure.tuplets, measure.events)

    if show_rt_text and measure.rt_text:
        _rt_text(dwg, measure.rt_text)

    return dwg


def render_system(
    system: NotatedSystem,
    height: float = 200,
    show_rt_text: bool = False,
) -> svgwrite.Drawing:
    """Render a NotatedSystem (horizontal sequence of measures) to SVG.

    Lays out measures left-to-right with a continuous staff line.
    Draws barlines at measure boundaries (single, double, or final).
    Shows tempo markings and time signatures only when they change.
    """
    from ..pipeline_uts import should_show_tempo, should_show_time_sig

    measures = system.measures
    if not measures:
        dwg = svgwrite.Drawing(size=(f"200px", f"{height}px"))
        dwg.add(dwg.rect(insert=(0, 0), size=(200, height), fill="white"))
        return dwg

    # ── Pass 1: Compute per-measure widths and layout positions ──────
    MEAS_LEFT_PAD = 18.0   # Barline → first note within a measure (no time sig)
    SYSTEM_LEFT = BAR_X    # Where the system starts (leaves room for time sig)

    # First measure pad accounts for time sig (OM: get-chiffrage-space)
    first_meas = measures[0]
    if first_meas.show_barlines and first_meas.time_signature:
        FIRST_MEAS_PAD = TS_BARLINE_GAP + _ts_glyph_width(first_meas.time_signature) + TS_NOTE_GAP
    else:
        FIRST_MEAS_PAD = MEAS_LEFT_PAD

    measure_widths = []
    for i, m in enumerate(measures):
        if m.barline_x_positions:
            w = m.barline_x_positions[-1] - m.barline_x_positions[0]
        elif m.events:
            min_x = min(e.x for e in m.events)
            max_x = max(e.x for e in m.events)
            prev_ts = measures[i - 1].time_signature if i > 0 else None
            show_ts = (
                m.show_barlines
                and m.time_signature is not None
                and should_show_time_sig(m.time_signature, prev_ts)
            )
            if show_ts:
                left_gap = (
                    TS_BARLINE_GAP
                    + _ts_glyph_width(m.time_signature)
                    + TS_NOTE_GAP
                )
            else:
                left_gap = FIRST_MEAS_PAD if i == 0 else MEAS_LEFT_PAD
            w = (max_x - min_x) + left_gap + END_PAD
        else:
            w = 100.0

        measure_widths.append(w)

    total_width = SYSTEM_LEFT + sum(measure_widths) + 30  # Right margin

    dwg = svgwrite.Drawing(size=(f"{total_width}px", f"{height}px"))
    dwg.add(dwg.rect(insert=(0, 0), size=(total_width, height), fill="white"))

    if _OTF.exists():
        b64 = _font_b64()
        dwg.defs.add(dwg.style(
            f"@font-face {{ font-family:'{_FAMILY}';"
            f" src:url('data:font/otf;base64,{b64}') format('opentype'); }}"
        ))

    # ── Pass 2: Draw staff line across the full system ───────────────
    staff_end = SYSTEM_LEFT + sum(measure_widths)
    dwg.add(dwg.line(start=(SYSTEM_LEFT, STAFF_Y), end=(staff_end, STAFF_Y),
                      stroke="black", stroke_width=0.8))

    # ── Pass 3: Draw each measure's content ──────────────────────────
    cursor = SYSTEM_LEFT  # Current x position (left edge of measure)
    prev_tempo_beat = None
    prev_tempo_bpm = None
    prev_time_sig = None

    for i, m in enumerate(measures):
        show_ts = (
            m.show_barlines
            and m.time_signature is not None
            and should_show_time_sig(m.time_signature, prev_time_sig)
        )
        if m.barline_x_positions:
            x_offset = cursor - m.barline_x_positions[0]
        elif m.events:
            first_event_x = min(e.x for e in m.events)
            if show_ts:
                target_first = (
                    cursor
                    + TS_BARLINE_GAP
                    + _ts_glyph_width(m.time_signature)
                    + TS_NOTE_GAP
                )
            else:
                target_first = cursor + (
                    FIRST_MEAS_PAD if i == 0 else MEAS_LEFT_PAD
                )
            x_offset = target_first - first_event_x
        else:
            x_offset = 0.0

        _barline_at(dwg, cursor)

        show_tempo = should_show_tempo(
            m.tempo_beat, m.tempo_bpm, prev_tempo_beat, prev_tempo_bpm
        )
        tempo_x = None
        if show_tempo and m.tempo_beat is not None and m.tempo_bpm is not None:
            if show_ts:
                tempo_x = (
                    cursor
                    + TS_BARLINE_GAP
                    + _ts_glyph_width(m.time_signature)
                    + 4
                )
            else:
                tempo_x = cursor + (FIRST_MEAS_PAD if i == 0 else MEAS_LEFT_PAD)

        shifted_events = [dc_replace(ev, x=ev.x + x_offset) for ev in m.events]
        end_bl_x = cursor + measure_widths[i]

        _draw_measure_contents(
            dwg, m, shifted_events, cursor,
            show_ts=show_ts,
            show_tempo=(tempo_x is not None),
            tempo_x=tempo_x,
            is_last_measure=(i == len(measures) - 1),
            end_barline_x=end_bl_x,
        )

        if m.show_barlines and m.time_signature:
            prev_time_sig = m.time_signature
        if m.tempo_beat is not None:
            prev_tempo_beat = m.tempo_beat
        if m.tempo_bpm is not None:
            prev_tempo_bpm = m.tempo_bpm
        cursor = end_bl_x

    return dwg


def render_score(
    score: NotatedScore,
    height: float | None = None,
    show_rt_text: bool = False,
    row_spacing: float = 80.0,
) -> svgwrite.Drawing:
    """Render a NotatedScore (multi-staff TemporalBlock) to SVG.

    Each row gets its own staff line, stacked vertically. A system bracket
    and connecting barline are drawn on the left edge.

    Parameters
    ----------
    score : NotatedScore
        The multi-staff score to render.
    row_spacing : float
        Base vertical distance between staff lines of adjacent rows.
        Automatically increased when per-row tempo markings are needed.
    """
    from ..pipeline_uts import should_show_tempo, should_show_time_sig

    rows = score.rows
    if not rows:
        dwg = svgwrite.Drawing(size=("200px", "200px"))
        dwg.add(dwg.rect(insert=(0, 0), size=(200, 200), fill="white"))
        return dwg

    n_rows = len(rows)

    # ── Determine score-level tempo and whether per-row tempos are needed ──
    score_tempo_beat = None
    score_tempo_bpm = None
    first_system = rows[0]
    if first_system.measures:
        fm = first_system.measures[0]
        if fm.tempo_beat is not None and fm.tempo_bpm is not None:
            score_tempo_beat = fm.tempo_beat
            score_tempo_bpm = fm.tempo_bpm

    # Check if any non-first row has independent tempo (collision risk)
    has_per_row_tempo = False
    for row_idx in range(1, n_rows):
        system = rows[row_idx]
        if system.measures:
            m0 = system.measures[0]
            if m0.tempo_beat is not None and m0.tempo_bpm is not None:
                if m0.tempo_beat != score_tempo_beat or m0.tempo_bpm != score_tempo_bpm:
                    has_per_row_tempo = True
                    break

    # OM: increase vertical spacing when per-row tempos must be drawn
    # to avoid collision with the staff above. TEMPO_ABOVE_STAFF = STAFF_Y - TEMPO_Y.
    TEMPO_ABOVE_STAFF = STAFF_Y - TEMPO_Y   # 60px
    # Need clearance below prev staff's bar extent (BAR_EXT) + padding
    MIN_TEMPO_ROW_SPACING = TEMPO_ABOVE_STAFF + BAR_EXT + 22  # 60+8+22 = 90
    if has_per_row_tempo:
        row_spacing = max(row_spacing, MIN_TEMPO_ROW_SPACING)

    # Compute the staff Y for each row
    first_staff_y = STAFF_Y
    row_staff_ys = [first_staff_y + i * row_spacing for i in range(n_rows)]

    # ── Compute per-row start x (for axis alignment) ─────────────────
    # For rows with offset > 0, the barline starts at the first event's
    # position minus room for time sig, not at BAR_X.
    row_start_xs = []
    for system in rows:
        first_event_x = None
        first_ts = None
        for m in system.measures:
            if m.events:
                first_event_x = m.events[0].x
                first_ts = m.time_signature if m.show_barlines else None
                break
        if first_event_x is not None:
            if first_ts:
                ts_w = _ts_glyph_width(first_ts)
                start_x = first_event_x - ts_w - TS_BARLINE_GAP - TS_NOTE_GAP
            else:
                start_x = first_event_x - 18
            row_start_xs.append(max(start_x, BAR_X))
        else:
            row_start_xs.append(BAR_X)

    max_x = 200.0
    for system, rsx in zip(rows, row_start_xs):
        max_x = max(max_x, _bt_row_max_x_world(system, rsx))

    total_width = max_x + 40
    if height is None:
        height = row_staff_ys[-1] + 80

    dwg = svgwrite.Drawing(size=(f"{total_width}px", f"{height}px"))
    dwg.add(dwg.rect(insert=(0, 0), size=(total_width, height), fill="white"))

    if _OTF.exists():
        b64 = _font_b64()
        dwg.defs.add(dwg.style(
            f"@font-face {{ font-family:'{_FAMILY}';"
            f" src:url('data:font/otf;base64,{b64}') format('opentype'); }}"
        ))

    # ── System bracket on the left ────────────────────────────────────
    bracket_x = BAR_X - 12
    top_y = row_staff_ys[0]
    bot_y = row_staff_ys[-1]
    _system_bracket(dwg, bracket_x, top_y - BAR_EXT, bot_y + BAR_EXT)

    # ── System barline (left edge, connecting all staves) ─────────────
    dwg.add(dwg.line(
        start=(BAR_X, top_y - BAR_EXT),
        end=(BAR_X, bot_y + BAR_EXT),
        stroke="black", stroke_width=1.4,
    ))

    # ── Score-level tempo (from first row's first measure) ──────────
    if score_tempo_beat is not None and score_tempo_bpm is not None:
        tempo_x = row_start_xs[0] + TS_BARLINE_GAP
        if first_system.measures and first_system.measures[0].time_signature:
            ts_w = _ts_glyph_width(first_system.measures[0].time_signature)
            tempo_x = row_start_xs[0] + TS_BARLINE_GAP + ts_w + 4
        _tempo_marking_at_y(dwg, score_tempo_beat, score_tempo_bpm,
                            tempo_x, row_staff_ys[0])

    # ── Draw each row ─────────────────────────────────────────────────
    for row_idx, (system, staff_y) in enumerate(zip(rows, row_staff_ys)):
        _render_row(dwg, system, staff_y, show_rt_text,
                    score_tempo=(score_tempo_beat, score_tempo_bpm),
                    row_start_x=row_start_xs[row_idx])

    return dwg


def _system_bracket(dwg, x: float, y_top: float, y_bot: float):
    """Draw a system bracket on the left edge.

    Uses an SVG path (slight curve) since the SMuFL bracket glyphs are
    designed for fixed staff heights and don't scale well to arbitrary
    system heights.
    """
    h = y_bot - y_top
    # Bezier bracket: slight leftward bulge
    bulge = min(6, h * 0.04)
    tip_top = 2.5  # Small serif at top
    tip_bot = 2.5  # Small serif at bottom
    path_d = (
        f"M{x + tip_top},{y_top} L{x},{y_top}"
        f" C{x - bulge},{y_top + h * 0.3} {x - bulge},{y_bot - h * 0.3} {x},{y_bot}"
        f" L{x + tip_bot},{y_bot}"
    )
    dwg.add(dwg.path(d=path_d, fill="none", stroke="black", stroke_width=1.8))


def _bt_row_dx(system: NotatedSystem, row_start_x: float) -> float:
    measures = system.measures
    if not measures:
        return 0.0
    m0 = measures[0]
    if m0.barline_x_positions:
        measure0_left = m0.barline_x_positions[0]
    elif m0.events:
        measure0_left = min(ev.x for ev in m0.events) - 18.0
    else:
        measure0_left = row_start_x
    return row_start_x - measure0_left


def _bt_row_max_x_world(system: NotatedSystem, row_start_x: float) -> float:
    dx = _bt_row_dx(system, row_start_x)
    xs: list[float] = [row_start_x]
    for m in system.measures:
        for ev in m.events:
            xs.append(ev.x + dx)
        if m.barline_x_positions:
            xs.extend(bx + dx for bx in m.barline_x_positions)
    return max(xs) + 30 if len(xs) > 1 else 200.0


def _draw_measure_contents(
    dwg,
    measure: NotatedMeasure,
    events: list[EngravingLeaf],
    cursor: float,
    staff_y: float = STAFF_Y,
    show_ts: bool = False,
    show_tempo: bool = False,
    tempo_x: float | None = None,
    is_last_measure: bool = False,
    end_barline_x: float | None = None,
):
    if show_ts:
        _time_sig_at(dwg, measure.time_signature, cursor + TS_BARLINE_GAP, staff_y)

    if show_tempo and tempo_x is not None:
        _tempo_marking_at_y(dwg, measure.tempo_beat, measure.tempo_bpm, tempo_x, staff_y)

    beamed = set()
    for bg in measure.beam_groups:
        for idx in bg.event_indices:
            beamed.add(idx)

    for j, ev in enumerate(events):
        if ev.is_rest:
            _rest_at(dwg, ev, staff_y)
        else:
            _note_at(dwg, ev, staff_y, flagged=(j not in beamed))

    for bg in measure.beam_groups:
        _beams_at(dwg, bg, events, staff_y)

    for j in range(len(events) - 1):
        if events[j].is_tied_forward or events[j + 1].is_continuation_tie:
            _tie_at(dwg, events[j], events[j + 1], staff_y)

    _tuplets_at(dwg, measure.tuplets, events, staff_y)

    if measure.barline_x_positions and len(measure.barline_x_positions) > 2:
        bl_dx = cursor - measure.barline_x_positions[0]
        for bx in measure.barline_x_positions[1:-1]:
            _barline_at(dwg, bx + bl_dx, staff_y)

    if end_barline_x is not None:
        bl_type = measure.end_barline_type
        if is_last_measure and bl_type == 'single':
            bl_type = 'final'
        _styled_barline_at(dwg, end_barline_x, staff_y, bl_type)


def _render_row(
    dwg, system: NotatedSystem, staff_y: float, show_rt_text: bool,
    score_tempo: tuple | None = None,
    row_start_x: float = BAR_X,
):
    """Render one row of a score at the given staff_y position.

    Parameters
    ----------
    score_tempo : tuple[Fraction, float] | None
        (beat, bpm) of the score-level tempo already drawn above the top
        staff. Per-row tempo is only drawn when it differs from this.
    row_start_x : float
        X position for this row's opening barline. For left-aligned BTs
        this equals BAR_X; for offset rows (axis != -1) it may be further
        right, leaving blank space before the row starts.
    """
    from ..pipeline_uts import should_show_tempo, should_show_time_sig

    measures = system.measures
    if not measures:
        return

    MEAS_LEFT_PAD = 18.0

    row_dx = _bt_row_dx(system, row_start_x)

    all_xs = [row_start_x]
    for m in measures:
        for ev in m.events:
            all_xs.append(ev.x + row_dx)
        if m.barline_x_positions:
            all_xs.extend(bx + row_dx for bx in m.barline_x_positions)

    if not all_xs:
        return

    staff_start = row_start_x
    staff_end = max(all_xs)

    dwg.add(dwg.line(
        start=(staff_start, staff_y), end=(staff_end, staff_y),
        stroke="black", stroke_width=0.8,
    ))

    _barline_at(dwg, row_start_x, staff_y)

    prev_tempo_beat = None
    prev_tempo_bpm = None
    prev_time_sig = None
    end_x_prev = row_start_x

    for i, m in enumerate(measures):
        if m.barline_x_positions:
            cursor = m.barline_x_positions[0] + row_dx
        else:
            cursor = end_x_prev

        show_ts = (
            m.show_barlines
            and m.time_signature is not None
            and should_show_time_sig(m.time_signature, prev_time_sig)
        )

        draw_events = [dc_replace(ev, x=ev.x + row_dx) for ev in m.events]

        show_tempo = should_show_tempo(
            m.tempo_beat, m.tempo_bpm, prev_tempo_beat, prev_tempo_bpm
        )
        tempo_x = None
        if show_tempo and m.tempo_beat is not None and m.tempo_bpm is not None:
            is_score_tempo = (
                score_tempo is not None
                and i == 0
                and prev_tempo_beat is None
                and m.tempo_beat == score_tempo[0]
                and m.tempo_bpm == score_tempo[1]
            )
            if not is_score_tempo:
                ts_end_x = cursor
                if show_ts:
                    ts_end_x = cursor + TS_BARLINE_GAP + _ts_glyph_width(m.time_signature) + 2
                if show_ts:
                    t0 = (
                        cursor
                        + TS_BARLINE_GAP
                        + _ts_glyph_width(m.time_signature)
                        + 4
                    )
                else:
                    t0 = cursor + MEAS_LEFT_PAD
                tempo_x = max(
                    ts_end_x + 2,
                    t0,
                    (draw_events[0].x if draw_events else t0),
                )

        if m.barline_x_positions:
            end_x = m.barline_x_positions[-1] + row_dx
        elif draw_events:
            end_x = max(ev.x for ev in draw_events) + END_PAD
        else:
            end_x = cursor + 50

        _draw_measure_contents(
            dwg, m, draw_events, cursor,
            staff_y=staff_y,
            show_ts=show_ts,
            show_tempo=(tempo_x is not None),
            tempo_x=tempo_x,
            is_last_measure=(i == len(measures) - 1),
            end_barline_x=end_x,
        )

        end_x_prev = end_x
        if m.show_barlines and m.time_signature:
            prev_time_sig = m.time_signature
        if m.tempo_beat is not None:
            prev_tempo_beat = m.tempo_beat
        if m.tempo_bpm is not None:
            prev_tempo_bpm = m.tempo_bpm


def _barline_at(dwg, x, staff_y: float = STAFF_Y):
    dwg.add(dwg.line(
        start=(x, staff_y - BAR_EXT), end=(x, staff_y + BAR_EXT),
        stroke="black", stroke_width=1.2,
    ))


def _styled_barline_at(dwg, x, staff_y: float = STAFF_Y, style='single'):
    if style == 'none':
        return
    if style == 'double':
        _barline_at(dwg, x - 4, staff_y)
        _barline_at(dwg, x, staff_y)
    elif style == 'final':
        dwg.add(dwg.line(
            start=(x - 5, staff_y - BAR_EXT), end=(x - 5, staff_y + BAR_EXT),
            stroke="black", stroke_width=1.2,
        ))
        dwg.add(dwg.line(
            start=(x, staff_y - BAR_EXT), end=(x, staff_y + BAR_EXT),
            stroke="black", stroke_width=3.0,
        ))
    else:
        _barline_at(dwg, x, staff_y)


def _note_at(dwg, ev: EngravingLeaf, staff_y: float = STAFF_Y, flagged=True):
    x = ev.x

    g = smufl.notehead_glyph(ev.note_type)
    _glyph(dwg, g, x - NH, staff_y)

    has_stem = ev.note_type not in (NoteType.WHOLE,)
    if has_stem:
        sx = _stem_x(ev)
        s_bot = _stem_bottom(staff_y)
        s_top = _stem_top(staff_y)
        dwg.add(dwg.line(start=(sx, s_bot), end=(sx, s_top),
                          stroke="black", stroke_width=STEM_W))

        if flagged:
            fg = smufl.flag_glyph(ev.note_type, stem_up=True)
            if fg:
                _glyph(dwg, fg, sx, s_top, size=FLAG_SIZE)

    for d in range(ev.dots):
        dx = x + NH + 4 + d * 6
        dot_y = staff_y - 4
        dwg.add(dwg.circle(center=(dx, dot_y), r=DOT_R, fill="black"))


def _rest_at(dwg, ev: EngravingLeaf, staff_y: float = STAFF_Y):
    g = smufl.rest_glyph(ev.note_type)
    _glyph(dwg, g, ev.x, staff_y, size=REST_FONT_SIZE, anchor="middle")


def _beams_at(dwg, group: BeamGroup, events: list[EngravingLeaf], staff_y: float = STAFF_Y):
    if len(group.event_indices) < 2:
        return
    idx = group.event_indices
    top = _stem_top(staff_y)

    for lv in range(1, group.max_beam_level + 1):
        by = top + (lv - 1) * (BEAM_H + BEAM_GAP)
        i = 0
        while i < len(idx):
            if beam_count(events[idx[i]].note_type) >= lv:
                rs = i
                while i < len(idx) and beam_count(events[idx[i]].note_type) >= lv:
                    i += 1
                re = i - 1
                x1 = _stem_x(events[idx[rs]])
                x2 = _stem_x(events[idx[re]])
                if rs == re:
                    d = -1 if rs > 0 else 1
                    s = x1 + min(0, d * 8)
                    dwg.add(dwg.rect(insert=(s, by), size=(8, BEAM_H), fill="black"))
                else:
                    dwg.add(dwg.rect(insert=(x1, by), size=(x2 - x1, BEAM_H), fill="black"))
            else:
                i += 1


def _tie_at(dwg, a: EngravingLeaf, b: EngravingLeaf, staff_y: float = STAFF_Y):
    x1 = a.x + NH + 2
    x2 = b.x - NH - 2
    y = staff_y + 6
    mx = (x1 + x2) / 2
    cy = y + TIE_H
    dwg.add(dwg.path(d=f"M{x1},{y} Q{mx},{cy} {x2},{y}",
                      fill="none", stroke="black", stroke_width=1.2))


def _tuplets_at(dwg, tuplets: list[TupletBracket], events: list[EngravingLeaf],
                staff_y: float = STAFF_Y):
    if not tuplets:
        return
    dy = staff_y - STAFF_Y
    st = sorted(tuplets, key=lambda t: len(t.event_indices), reverse=True)
    dep = {}
    for t in st:
        ts = set(t.event_indices)
        dep[t.group_node_id] = sum(
            1 for o in st
            if o.group_node_id != t.group_node_id and ts < set(o.event_indices)
        )
    max_depth = max(dep.values()) if dep else 0

    for t in tuplets:
        if not t.event_indices:
            continue
        d = dep.get(t.group_node_id, 0)
        y = TUPLET_INNER_Y + dy - (max_depth - d) * TUPLET_STEP
        _bracket(dwg, t, events, y)


def _tempo_marking_at_y(dwg, beat, bpm, x, staff_y: float = STAFF_Y):
    from fractions import Fraction
    dy = staff_y - STAFF_Y
    tempo_y = TEMPO_Y + dy
    beat = Fraction(beat)
    note_glyph, n_dots = smufl.metronome_glyph_and_dots(beat)
    _glyph(dwg, note_glyph, x, tempo_y, size=TEMPO_FONT)
    glyph_w = TEMPO_FONT * 0.55
    dot_x = x + glyph_w
    dot_glyph = smufl.GLYPH_CODEPOINTS["metAugmentationDot"]
    for d in range(n_dots):
        _glyph(dwg, dot_glyph, dot_x + d * 5, tempo_y, size=TEMPO_FONT)
    bpm_str = str(int(bpm)) if bpm == int(bpm) else f"{bpm:.1f}"
    eq_x = dot_x + (n_dots * 5 + 3 if n_dots else 3)
    dwg.add(dwg.text(f"= {bpm_str}", insert=(eq_x, tempo_y),
                      font_family="serif", font_size=TEMPO_FONT - 1,
                      font_weight="bold"))


def save_svg(dwg: svgwrite.Drawing, path: str | Path):
    dwg.saveas(str(path), pretty=True)


def svg_to_png(svg_path: str | Path, png_path: str | Path | None = None) -> Path | None:
    svg_path = Path(svg_path)
    exe = shutil.which("rsvg-convert")
    if not exe:
        return None
    out = Path(png_path) if png_path is not None else svg_path.with_suffix(".png")
    subprocess.run([exe, str(svg_path), "-o", str(out)], check=True)
    return out


def export_drawing_png(dwg: svgwrite.Drawing, png_path: str | Path) -> Path:
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    exe = shutil.which("rsvg-convert")
    if not exe:
        raise RuntimeError(
            "rsvg-convert is required for PNG export; install librsvg (e.g. brew install librsvg)."
        )
    fd, tmp_svg = tempfile.mkstemp(suffix=".svg")
    os.close(fd)
    try:
        dwg.saveas(tmp_svg, pretty=True)
        subprocess.run([exe, tmp_svg, "-o", str(png_path)], check=True)
    finally:
        try:
            os.unlink(tmp_svg)
        except OSError:
            pass
    return png_path


# ── Helpers ────────────────────────────────────────────────────────────

def _stem_x(ev: EngravingLeaf) -> float:
    """Stem x = right edge of notehead glyph (stemUpSE.x)."""
    return ev.x - NH + NH_W  # = ev.x + NH


def _stem_bottom(staff_y: float = STAFF_Y) -> float:
    """Stem bottom y = staff line + stem attachment offset (goes INTO notehead)."""
    return staff_y + STEM_ATTACH_DY


def _stem_top(staff_y: float = STAFF_Y) -> float:
    """Stem tip y."""
    return _stem_bottom(staff_y) - STEM_LEN


def _ts_glyph_width(meas) -> float:
    """Compute the horizontal width (px) of a time signature's SMuFL glyphs."""
    max_digits = max(len(str(meas.numerator)), len(str(meas.denominator)))
    return max_digits * TS_DIGIT_W + 2  # +2 for small right padding


def _time_sig_at(dwg, meas, x, staff_y: float = STAFF_Y):
    num_glyphs, den_glyphs = smufl.time_sig_glyphs(meas.numerator, meas.denominator)
    num_w = len(str(meas.numerator)) * TS_DIGIT_W
    den_w = len(str(meas.denominator)) * TS_DIGIT_W
    max_w = max(num_w, den_w)
    num_x = x + (max_w - num_w) / 2
    den_x = x + (max_w - den_w) / 2
    _glyph(dwg, num_glyphs, num_x, staff_y + TS_NUM_Y_OFF, size=TS_FONT)
    _glyph(dwg, den_glyphs, den_x, staff_y + TS_DEN_Y_OFF, size=TS_FONT)


def _glyph(dwg, char, x, y, size=FONT_SIZE, anchor="start"):
    dwg.add(dwg.text(char, insert=(x, y),
                      font_family=_FAMILY, font_size=size, text_anchor=anchor))


def _bracket(dwg, t: TupletBracket, events: list[EngravingLeaf], y: float):
    x1 = events[t.event_indices[0]].x - NH - 2
    x2 = events[t.event_indices[-1]].x + NH + 2
    mx = (x1 + x2) / 2
    # Build SMuFL glyph string for the tuplet label
    label_glyphs, label_len = _tuplet_label_glyphs(t.actual, t.normal)
    # Approximate width of label in px (tuplet digits ~1.2 sp at TUPLET_FONT)
    tuplet_sp = TUPLET_FONT / 4
    label_w = label_len * 1.2 * tuplet_sp
    gap = max(7, label_w / 2 + 3)
    sw = 0.8
    dwg.add(dwg.line(start=(x1, y + TUPLET_HOOK), end=(x1, y), stroke="black", stroke_width=sw))
    dwg.add(dwg.line(start=(x1, y), end=(mx - gap, y), stroke="black", stroke_width=sw))
    dwg.add(dwg.line(start=(x2, y + TUPLET_HOOK), end=(x2, y), stroke="black", stroke_width=sw))
    dwg.add(dwg.line(start=(mx + gap, y), end=(x2, y), stroke="black", stroke_width=sw))
    # Draw SMuFL tuplet glyphs centered in the bracket gap
    _glyph(dwg, label_glyphs, mx - label_w / 2, y + 4, size=TUPLET_FONT)


def _tuplet_label_glyphs(actual: int, normal: int) -> tuple[str, int]:
    """Return SMuFL glyph string and character count for a tuplet label.

    Following OM convention (``chif2sstr``, rythtools.lisp:230): show just
    the actual count when normal is a power of 2 (obvious from context),
    show ``actual:normal`` when normal is NOT a power of 2 (e.g. ternary).
    """
    if normal > 0 and (normal & (normal - 1)) == 0:
        return smufl.tuplet_number_glyphs(actual), len(str(actual))
    act_str = smufl.tuplet_number_glyphs(actual)
    nor_str = smufl.tuplet_number_glyphs(normal)
    colon = smufl.GLYPH_CODEPOINTS["tupletColon"]
    total_chars = len(str(actual)) + 1 + len(str(normal))
    return act_str + colon + nor_str, total_chars


TEMPO_Y = 50       # Y position for tempo marking (above tuplet brackets)
TEMPO_FONT = 14    # Font size for tempo text


def _rt_text(dwg, text: str):
    y0 = STAFF_Y + RT_Y_OFF
    for i, line in enumerate(text.split('\n')):
        dwg.add(dwg.text(line, insert=(8, y0 + i * (RT_FONT + 3)),
                          font_family="monospace", font_size=RT_FONT, fill="#666"))
