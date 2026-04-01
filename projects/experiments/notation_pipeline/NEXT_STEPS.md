# Notation Pipeline — Hand-Off Plan (2026-03-18, rev 2)

## Context

This is a notation rendering pipeline experiment at `projects/experiments/notation_pipeline/`.
It takes Klotho `RhythmTree` objects and produces SVG output using Bravura (SMuFL) music font glyphs.

**CRITICAL RULES:**
1. **DO NOT modify Klotho source code** (`klotho/` directory). This is a sandbox experiment only.
2. **Always use the Bravura/SMuFL music font** for notation glyphs. Never use custom SVG shapes (circles, paths, etc.) as substitutes for font glyphs — this is a "no-no" in music engraving. If a glyph renders poorly at a given size, adjust size/position. If no SMuFL glyph exists for an edge case, **flag it to the user** before implementing a workaround.
3. **The OM (OpenMusic) source code is our gospel.** Always reference it before implementing a strategy. It has answers to almost every problem we face. Only deviate when you have to, and always explain why. Key source files:
   - `/Users/ryanmillett/Downloads/openmusic-master 2/OPENMUSIC/code/projects/musicproject/container/scoreobject.lisp` — `init-seq-from-tree`, QNormalize, Qvalue/extent system
   - `/Users/ryanmillett/Downloads/openmusic-master 2/OPENMUSIC/code/projects/musicproject/functions/trees.lisp` — `reducetree`, `mktree`
   - `/Users/ryanmillett/Downloads/openmusic-master 2/OPENMUSIC/code/projects/musicproject/editor/scoreeditor/` — spacing, layout, drawing, multi-voice alignment
4. **Use the venv** at `/Users/ryanmillett/klotho-venv` for all Python execution.
5. **Output PNGs only.** Render scripts produce SVGs (with base64-embedded Bravura font), then **always** convert to PNG with `rsvg-convert foo.svg -o foo.png`. When visually verifying outputs, **always read the PNG** — never display SVGs. Ideally, render scripts should produce PNGs directly (or at least convert automatically).
6. **Use OM packet spacing for ALL examples.** `spacing_mode='hybrid'` and `'om'` both select OpenMusic `space-packet` layout (`spacing/om_packet.py`). Legacy `space_hybrid` (proportional + min sweep) is only used when barlines are off or for non-`notate` call sites. Always use `'hybrid'` when rendering examples for inspection unless comparing modes. `proportional` / `traditional` remain for regression comparison only.
7. **Clear outputs between revisions:** `rm -rf projects/experiments/notation_pipeline/output/`
8. **Shell permissions:** Read-only commands and `rm` on experiment outputs are always fine. Only prompt for genuinely risky destructive operations on source code or shared state.
9. **Be careful with regressions.** After every code change, re-render ALL examples (RT, UTS, AND BT), convert to PNG, and visually verify that nothing regressed. Check **every** measure in multi-measure examples, not just the first one. Common pitfalls: notes colliding with barlines, time-sig-to-first-note gaps missing in non-first measures, proportional gaps where fixed gaps should be, barline misalignment across BT rows.

---

## Architecture Overview

### Pipeline Flow
```
RhythmTree → notate()      → NotatedMeasure → render_measure() → SVG   (single RT/UT)
UTS        → notate_uts()  → NotatedSystem  → render_system()  → SVG   (horizontal sequence)
BT         → notate_bt()   → NotatedScore   → render_score()   → SVG   (OM packet global walk)
```

### Key Files
```
notation_pipeline/
├── pipeline.py              # notate() — single RT → NotatedMeasure
├── pipeline_uts.py          # notate_uts() — UTS → NotatedSystem  ✅
├── pipeline_bt.py           # notate_bt() — BT → NotatedScore     ✅ (partially — see open issues)
├── models.py                # EngravingLeaf, TupletBracket, BeamGroup,
│                            # NotatedMeasure, NotatedSystem, NotatedScore
├── core/
│   ├── duration.py          # classify_duration(), beam_count()
│   ├── tie_split.py         # split_at_boundaries(), split_duration()
│   ├── tuplet.py            # collect_tuplets(), get_tuplet_scale_for_leaf()
│   └── beam.py              # assign_beams() — OM-style tree-boundary beaming
├── spacing/
│   ├── modes.py             # Legacy spacing; space_with_barlines() for non-OM modes
│   └── om_packet.py         # OM space-packet, ryhtm2pixels, BPF+sentinel (scoretools.lisp)
├── docs/
│   └── OM_PORTING.md        # OM source map + Klotho-only exceptions
├── render/
│   ├── svg_renderer.py      # render_measure(), render_system(), render_score(), save_svg()
│   └── smufl.py             # SMuFL glyph lookup
├── render_examples.py       # Renders 32 RT test cases to output/
├── render_comparison.py     # Renders all examples × 3 spacing modes + barline variants
├── render_containers.py     # Renders 10 UTS + 8 BT test cases to output/containers/
├── assets/fonts/            # Bravura.otf + bravura_metadata.json
└── tests/                   # pytest suite (119 tests, all passing)
```

### Completed Work

- **Phase 1 (Immediate fixes):** All done — END_PAD for single measures, proportional spacing verified correct, minimum-closeness enforcement in `space_proportional()`, cross-barline examples (30-32), barlines=True/False comparison, float-proportion bug fix in tuplet detection.
- **Phase 2 (UTS):** Implemented — `pipeline_uts.py`, `render_system()`, `NotatedSystem` model, double/final barline glyphs, 10 UTS test cases all rendering correctly. Tempo/time-sig change detection works.
- **Phase 2.5 (Time sig + tuplet glyphs):** Done — replaced serif text with SMuFL time signature glyphs (`timeSig0`–`timeSig9`), fixed positioning after barline with `TS_BARLINE_GAP`, computed ts_extra width from actual glyph metrics. Tuplet bracket labels now use SMuFL tuplet digit glyphs (`tuplet0`–`tuplet9`, `tupletColon`).
- **Phase 3 (BT):** Implemented — `pipeline_bt.py` uses **OpenMusic `space-packet`** over absolute-time packets across all rows, then an event-anchored time→x BPF with **OM-style sentinel** (`build_timebpf_with_sentinel`) for barline interpolation. Legacy union-onset BPF + `min_event_dx` removed as layout authority. `NotatedScore` + `render_score()` unchanged structurally. 8 BT test cases; axis / floating rows remain Klotho-only (see `docs/OM_PORTING.md`).
- **Phase 3.5 (Refinements):** Done —
  - Fixed time sig → first note padding: `pipeline.py:notate()` now dynamically computes `left_margin` from time sig glyph width (`BAR_X + TS_BARLINE_GAP + ts_w + TS_NOTE_GAP`). `render_system()` uses `FIRST_MEAS_PAD` based on first measure's time sig. `pipeline_bt.py` computes `bt_left_margin` from widest time sig across all rows.
  - Fixed tempo collision in BT: `render_score()` detects per-row tempos differing from score-level and increases `row_spacing` (min = `TEMPO_ABOVE_STAFF + 20`).
  - Fixed BT axis alignment: `render_score()` computes per-row `row_start_x` from first event position minus time sig width. `_render_row()` accepts `row_start_x` parameter — offset rows "float" with blank space before them instead of stretching from BAR_X.
- **Phase 4 (BT Spacing & Layout Polish) — PARTIAL:**
  - ✅ **4.1 Tempo positioning:** `TEMPO_Y` lowered from 38→50 (60px above staff instead of 72px). BT `MIN_TEMPO_ROW_SPACING = TEMPO_ABOVE_STAFF + BAR_EXT + 22 = 90` for polytempo layouts, ensuring per-row tempos sit clearly between staves (not confusingly close to the staff above).
  - ✅ **4.2/4.3 BT barline alignment:** `_recompute_barlines()` now always stores `[start_x, end_x]` for every measure (even span=1), using `last_event_x + END_PAD` for the closing barline (OM convention: fixed gap, not proportional). New `_align_shared_barlines()` step ensures UTs across rows sharing the same end time get aligned closing barlines (max end_x wins). `_render_row()` prefers `barline_x_positions[-1]` for the closing barline instead of computing from the last event. Staff line end uses the barline position.
  - ⚠️ **Remaining issues:** See "NEXT" section below — the UTS `render_system()` has a pre-existing time-sig-to-first-note gap bug in non-first measures, and several BT visual details still need attention.

---

## NEXT: Phase 4 Continued — UTS/BT Gap & Layout Issues

### HIGHEST PRIORITY: UTS Time-Sig-to-First-Note Gap in Non-First Measures

**Update (2026-03):** `render_system()` now enforces `first_note_x >= ts_x + ts_w + TS_NOTE_GAP` after the `x_offset` computation when `i > 0` and a time signature is shown. `_render_row()` (BT) applies the same rule using `prev_ts_for_chif` before drawing, shifting note geometry with `ts_shift` when needed. Re-verify visually on all UTS/BT PNGs after large layout changes.

**Problem:** In `render_system()`, the gap between a time signature and the first note after it is only correct in the **first** measure. All subsequent measures that show a time signature (meter changes) have the first note jammed against the time sig glyphs with almost no gap.

**Visible in:** `uts_01`, `uts_03`, `uts_04`, `uts_05`, `uts_07`, `uts_08`, `uts_10` — basically every UTS with a meter change. Also visible in BT examples where `_render_row()` draws time sigs for non-first measures.

**Root cause analysis:**

In `render_system()` (`svg_renderer.py:167`), the layout algorithm works as follows:
1. The first measure uses `FIRST_MEAS_PAD` which is computed from the time sig glyph width: `TS_BARLINE_GAP + _ts_glyph_width(ts) + TS_NOTE_GAP` (~22px for 4/4).
2. Subsequent measures use `MEAS_LEFT_PAD = 18.0` as the base gap between the barline and the first note.
3. When a time sig change occurs at a non-first measure, `ts_extra` is added to the measure width (line 215) AND to the x_offset for event positioning (line 261).

The issue is in **how the original per-measure event positions interact with the system-level x_offset**. Each measure's events are positioned by `notate()` relative to their own `left_margin`. When `render_system()` shifts them with `x_offset`, the shift is computed from the first event's original position:
```python
first_event_x = min(e.x for e in m.events)
x_offset = cursor + meas_pad - first_event_x
x_offset += ts_extra
```

The `ts_extra` shifts events rightward to make room for the time sig. But the time sig is drawn at `cursor + TS_BARLINE_GAP` (line 269), and the first note ends up at approximately `cursor + meas_pad + ts_extra`. The gap between the time sig's right edge and the first note is `meas_pad + ts_extra - (TS_BARLINE_GAP + ts_glyph_width)` = `18 + ts_extra - (4 + ts_w)`. Since `ts_extra = ts_w + 4 + 10`, this simplifies to `18 + 10 = 28`. That should be enough…

**So the bug may be more subtle.** Debug by printing the x positions of time sig glyphs and first notes for each measure in `render_system()`. The issue may be that `ts_extra` is not being applied to the x_offset correctly, or that the measure width calculation is offset from the event positioning calculation.

**What OM does (`space-girl` method, `scoreeditors.lisp`):**

OM uses `get-chiffrage-space` to compute the space reserved for a time signature:
```lisp
;; From scoretools.lisp line 1511-1514:
(defmethod get-chiffrage-space ((self grap-measure) size)
   (if (or (show-chifrage self) (first-of-group? self)) size
     (let ((previous-mes ...))
       (mesure-space self size (not (equal (metric self) (metric previous-mes)))))))
```
- First measure or meter change: reserves **`size`** pixels (= staff font size, ~24px)
- Same meter as previous: also reserves `size` (via `mesure-space`)

Then in `space-girl` (the pairwise spacing method), the gap after a barline is:
```lisp
;; Measure before a note:
(+ count (round size 4) (get-chiffrage-space obji size))
```
Gap = **`size/4 + chiffrage_space`** = `6 + 24` = ~30px at size=24. This is the gap from the barline to the first note, WITH the time sig occupying `chiffrage_space` of those pixels.

**Key OM insight:** OM's `space-size&offset` for a measure returns a 4-element budget: `(barline_gap, time_sig_space, grace_space, body_space)`. In `space-packet`, the maximum of each column across all simultaneous objects is used. The time_sig_space column ensures that ALL voices/rows reserve the same horizontal space for time signatures at each onset, even if only one voice has a meter change.

**Fix strategy:**
1. In `render_system()`, ensure the gap between a mid-system time sig's right edge and the first note is at least `TS_NOTE_GAP` (10px). The computation should be: `first_note_x >= ts_x + ts_glyph_width + TS_NOTE_GAP`.
2. Consider computing `x_offset` and `ts_extra` differently: instead of adding `ts_extra` to the x_offset and hoping it results in the right gap, explicitly compute the first note's target x as `cursor + TS_BARLINE_GAP + ts_glyph_width + TS_NOTE_GAP` and derive the x_offset from that.
3. Apply the same logic in `_render_row()` for BT systems (it has similar code around lines 537-543).
4. **Regression check:** after fixing, verify ALL UTS examples AND all BT examples. The gap should be consistent between the first measure and subsequent measures.

**Relevant files:**
- `svg_renderer.py:167-324` — `render_system()` (UTS rendering)
- `svg_renderer.py:485-616` — `_render_row()` (BT per-row rendering)
- `pipeline.py:notate()` — computes `left_margin` for the first measure

### ✅ DONE: BT Cross-Row Barline Alignment for Same-Duration Rows

**Status: Fixed.** `_align_shared_barlines()` in `pipeline_bt.py` correctly groups UTs by end time and takes the max `end_x` across all rows. `_render_row()` uses `barline_x_positions[-1]` for the closing barline. Verified visually in `bt_01_same_meter_tempo` (both rows same width, barlines aligned) and `bt_02_dense_vs_sparse` (sparse row extends full width to match dense row's barline).

**How it works:** Each measure's closing barline = `last_event_x + END_PAD`. For rows sharing the same end time, `_align_shared_barlines()` takes the max end_x across all rows and applies it to all. The densest row drives the barline position; sparser rows get extended to match.

**OM reference for future improvement:** OM's `space-packet` approach is more thorough — it ensures ALL voices get the same x allocation at each onset via a shared cursor that advances by `max(body_size, size/4, size * ryhtm2pixels(nextdur))` across all voices. Our approach (per-row spacing + post-hoc alignment) is simpler but produces equivalent results for the common case. If edge cases arise, consider refactoring toward OM's shared-cursor approach.

### THIRD PRIORITY: BT Time-Sig-to-First-Note Gap

**Problem:** Same as the UTS issue above, but in `_render_row()`. The first note in each BT row is tight against the time signature. This affects `bt_03`, `bt_04`, `bt_05`, `bt_06`, `bt_07`, `bt_08`.

**Root cause:** In `_render_row()`, time sigs are drawn at `cursor + TS_BARLINE_GAP` (line 541), but the notes are positioned by the timebpf which doesn't account for per-row time sig glyph width. The `bt_left_margin` computation (pipeline_bt.py:89-98) only ensures the FIRST measure of the FIRST row has enough room. Non-first rows and non-first measures within a UTS row don't get the same treatment.

**Fix strategy:**
1. In `_render_row()`, after drawing a time sig, compute the minimum x for the first note: `min_note_x = ts_x + ts_glyph_width + TS_NOTE_GAP`.
2. If any event in the current measure has `ev.x < min_note_x`, shift ALL events in the measure rightward by the deficit. This is a local adjustment that doesn't affect the global timebpf — it just prevents visual collision.
3. Alternatively, adjust the timebpf construction to account for time sig space at each UT boundary. For each UT that starts with a meter change, add `ts_glyph_width + TS_BARLINE_GAP + TS_NOTE_GAP` to the `min_dx` at that time point. This is closer to OM's approach where `get-chiffrage-space` reserves space in the spacing budget.

### LOWER PRIORITY: System Bracket in Non-Left-Aligned BTs

**Problem:** The system bracket (curly brace on the left) is drawn from `BAR_X - 12` spanning from the top row's staff to the bottom row's staff. For right-aligned (axis=1) and center-aligned (axis=0) BTs, shorter rows start further right, so the bracket only visually connects to the rows that start at `BAR_X`. Offset rows have their opening barlines detached from the bracket.

**Current behavior:** The bracket is drawn at a fixed x position. For left-aligned BTs (axis=-1), all rows start at `BAR_X`, so the bracket correctly connects everything. For other alignments, the bracket connects to the longest row(s) but offset rows float independently.

**This is arguably correct** — in OM, all voices always left-align, so there's no equivalent issue. For Klotho's axis feature, the bracket connecting the left edge makes visual sense as a "system start" marker even if some rows don't start there. However, it does look odd when only the top row touches the bracket.

**Possible improvements:**
1. Only draw the bracket portion that spans rows starting at `BAR_X` (skip rows with `row_start_x > BAR_X`).
2. Draw a secondary bracket or connector at each offset row's `row_start_x`.
3. Accept current behavior and document it as intentional for now.

---

## OM Spacing Algorithm — Detailed Reference

This section summarizes the key OM algorithms extracted from the source code, for reference when debugging or implementing spacing fixes.

### OM's Two-Pass Spacing System

**Pass 1: `space-objects` / `do-space-objects` (scoretools.lisp:2368-2487)**
1. Collect `(onset_time, graphic_object)` pairs from all voices
2. Group by onset via `group-space-objects` — objects sharing the same onset are bundled into a "packet"
3. Walk packets left-to-right, calling `space-packet` for each

**`space-size&offset` — Per-Object Space Budget (scoretools.lisp:2413-2440)**

Each object returns a 4-element list: `(barline_gap, time_sig_space, grace_space, body_space)`.

For a **measure**:
```lisp
(list (if (first-of-group? self) 0 (round size 2))  ; barline gap
      (get-chiffrage-space self size)                 ; time sig space
      0                                               ; grace notes
      (round size 2))                                 ; body
```
- First measure: 0 barline gap
- Subsequent measures: `size/2` (~12px at size=24)
- Time sig always reserves `size` (~24px) via `get-chiffrage-space`

For a **chord/note**:
```lisp
(list 0 0 (+ grace_space accidental_space) notehead_width)
```

**`space-packet` — Accumulating Offsets (scoretools.lisp:2453-2468)**
```lisp
;; Find maximum needed in each column across ALL simultaneous objects (all voices)
maxpixelclef = max(all barline_gaps)
maxpixelmeasure = max(all time_sig_spaces)
maxpixelgraces = max(all grace_spaces)
maxpixelsize = max(all body_spaces, size/4)
;; Each object positioned at: count + maxpixelclef + maxpixelmeasure + maxpixelgraces
;; Cursor advances by: sum of all max columns + max(body, size/4, proportional_duration_width)
```

Key insight: **the columns are additive and the max across all voices wins**. This is how OM ensures all voices get the same horizontal allocation at each time slot.

### OM's Proportional Duration Width

**`ryhtm2pixels` (scoretools.lisp:2491-2494)**
```lisp
(defvar *factor-spacing* 3/2)
(defun ryhtm2pixels (ms)
  (max 0.25 (expt *factor-spacing* (log (/ ms 1000) 2))))
```
Logarithmic proportional spacing. Duration in milliseconds → multiplier:
- 1000ms (quarter at q=60): `1.5^0` = **1.0**
- 500ms (eighth at q=60): `1.5^-1` = **0.667**
- 2000ms (half at q=60): `1.5^1` = **1.5**
- 250ms (16th at q=60): `1.5^-2` = **0.444**

The final cursor advance = `max(body_size, size/4, size * ryhtm2pixels(nextdur))`.

### OM's `space-girl` — Pairwise Spacing (scoreeditors.lisp:2500-2555)

Alternative to `space-packet`, works pairwise between adjacent objects:

**Measure → Note:**
```lisp
gap = size/4 + get-chiffrage-space(measure, size)
```
= `6 + 24` = ~30px. This is the total gap from barline to first note, with the time sig occupying part of those 24px.

**Note → Note:**
```lisp
gap = 2*maxdur + size * ryhtm2pixels(dt) + size/4
```
= `~10 + proportional + ~6` — accounts for note body width + proportional duration + minimum pad.

**Note → Barline:**
```lisp
;; Same onset: size/2 (~12px)
;; Different onsets: same proportional formula as note→note
```

### OM's `timebpf` — Time-to-Pixel BPF (scoreeditors.lisp:6706-6737)

After layout, OM builds a Break-Point Function mapping ms → x-pixel:
```lisp
(simple-bpf-from-list (reverse (cons (+ 1000 (car lx)) lx))
                      (reverse (cons (+ 20 (car ly)) ly)))
```
Note: OM adds a **sentinel point** 1000ms past the last onset, 20px past the last x. This ensures the BPF can extrapolate slightly beyond the last laid-out event (e.g., for drawing the final barline). Our pipeline currently extrapolates to the last onset x, which is why the "barline on top of last note" bug occurred.

`get-x-pos` then interpolates: for times beyond the last point, it falls back to `1 pixel per staff-size ms`.

### OM's Barline Alignment for Multi-Voice (scoretools.lisp:1189-1242)

**`get-aligne-measures`:** Collects all measure offsets across all voices, builds a global sorted set of unique onsets, then maps each measure to its voice/position. Used by `draw-aligned-measures` to draw vertical barlines connecting aligned measures across voices.

Key: barlines that coincide in time across voices are drawn as a single vertical line spanning all staves. Non-coincident barlines are drawn independently per voice.

---

## Key Constants (Current Values)

### svg_renderer.py
```python
FONT_SIZE = 30           # Bravura glyph base size
SP = FONT_SIZE / 4       # 7.5 px per staff-space
STAFF_Y = 110            # Staff line Y position
BAR_X = 44               # Opening barline X
NOTE_X0 = 62             # (legacy — left_margin is now computed dynamically)
TS_FONT = 20             # Time sig glyph size
TS_BARLINE_GAP = 4       # Gap between barline and time sig
TS_NOTE_GAP = 10         # Gap between time sig right edge and first note
TS_DIGIT_W = 1.7 * TS_SP # ~8.5 px per digit
TEMPO_Y = 50             # Tempo marking Y (50 = 60px above STAFF_Y)
TEMPO_FONT = 14          # Tempo text size
END_PAD = 14             # Last note → barline gap (fixed, not proportional — OM convention)
TUPLET_INNER_Y = 70      # Innermost tuplet bracket Y
TUPLET_STEP = 14         # Each outer nesting level goes this much higher
```

### pipeline_bt.py
```python
time_scale = 80.0        # px/sec for timebpf proportional mapping
min_event_dx = 20.0      # Minimum px between adjacent time points in timebpf
```

### Dynamic left_margin Computation
In `pipeline.py:notate()`, when `barlines=True`:
```python
left_margin = max(left_margin, BAR_X + TS_BARLINE_GAP + ts_glyph_width + TS_NOTE_GAP)
```
Same logic in `pipeline_bt.py` for the widest time sig across all BT rows (but only for the first measure — non-first measures are NOT yet handled).

---

## BT Pipeline Step-by-Step (pipeline_bt.py)

Understanding this pipeline is critical for debugging BT layout issues.

```
notate_bt(bt):
  Step 1: Notate each row independently (notate() or notate_uts())
          → Each row gets its own NotatedSystem with events positioned by
            the per-row spacing algorithm (space_hybrid). These positions
            are RELATIVE to the row's own left_margin and spacing.

  Step 2: Collect all unique onset times across ALL rows.
          → Only onsets, NOT end times. (Adding end times causes proportional
             barline gaps — see the regression we fixed.)

  Step 3: Build global timebpf (time→x mapping).
          → Proportional: x += max(dt * time_scale, min_event_dx)
          → bt_left_margin accounts for the widest time sig across first measures.

  Step 4: Re-space each row using the global timebpf.
          → _apply_global_x() maps each event's metric onset to absolute time,
            then interpolates the timebpf to get the new x position.
          → This overwrites the per-row spacing from Step 1.

  Step 5: Recompute barline positions.
          → Opening barlines: from timebpf (onset times ARE in the BPF).
          → Closing barlines: last_event_x + END_PAD (fixed gap, NOT from timebpf).
          → Always stores [start_x, ..., end_x] in barline_x_positions.

  Step 6: Cross-row barline alignment.
          → _align_shared_barlines() groups UTs by end time (rounded to avoid
            float noise), takes the max end_x across all rows in each group.
```

**Known limitations:**
- Step 3's `min_event_dx` is a flat constant. OM uses per-onset `space-packet` with `max(body_size, size/4, proportional_width)`. A more OM-faithful approach would compute `min_dx` per time-point pair based on the glyph widths of events at that time point across all rows.
- Step 5's closing barline uses `last_event_x + END_PAD`. OM instead advances the cursor by the proportional duration of the last event, which naturally places the barline. Our approach is simpler but may produce slightly different results for measures ending with long notes vs. short notes.
- The timebpf doesn't include end times (intentionally — adding them caused proportional gaps). This means `_interp_timebpf()` for a time past the last onset returns the last onset's x, which is fine because we compute closing barlines from events, not from the timebpf.

---

## Klotho API Summary (for reference)

```python
# TemporalUnit
ut.rt           # RhythmTree (copy)
ut.beat         # Fraction — beat unit (e.g., 1/4)
ut.bpm          # int/float — beats per minute
ut.tempus       # Meas — time signature
ut.offset       # float — absolute start time (seconds), settable
ut.duration     # float — total duration (seconds)
ut.onsets       # tuple of float — real-time onset per leaf (seconds)
ut.durations    # tuple of float — real-time duration per leaf (seconds)

# TemporalUnitSequence
uts.seq         # list[TemporalUnit] — units in order
uts.onsets      # tuple of float — onset of each unit (cumulative)
uts.durations   # tuple of float — duration of each unit
uts.duration    # float — total duration (sum)
uts.offset      # float — absolute start time, settable (propagates to all units)

# TemporalBlock
bt.rows         # list[TemporalUnit | TemporalUnitSequence | TemporalBlock]
bt.height       # int — number of rows
bt.duration     # float — max row duration
bt.axis         # int — alignment: -1 (left), 0 (center), 1 (right)
bt.offset       # float — absolute start time
```

**Row alignment (`_align_rows`):** Each row's `.offset` is pre-computed based on axis:
- `adjustment = (max_duration - row_duration) × (axis + 1) / 2`
- `row.offset = block.offset + adjustment`
- axis=-1 → all rows start together; axis=0 → shorter rows centered; axis=1 → all rows end together

**NOTE:** `TemporalBlock` may reorder rows internally (e.g., by duration). The order of `bt.rows` may differ from the order passed to the constructor. This means the top row in the rendered output may not correspond to the first element of the original list. This is a Klotho source behavior — DO NOT modify it. Just be aware when writing test cases.

---

## TESTING & WORKFLOW

### Commands
```bash
# Run tests
/Users/ryanmillett/klotho-venv/bin/python -m pytest projects/experiments/notation_pipeline/tests/ -x -q

# Clear + render all RT examples (hybrid/OM-style spacing only)
rm -rf projects/experiments/notation_pipeline/output/
/Users/ryanmillett/klotho-venv/bin/python projects/experiments/notation_pipeline/render_examples.py

# Render UTS + BT container examples
/Users/ryanmillett/klotho-venv/bin/python projects/experiments/notation_pipeline/render_containers.py

# Convert ALL SVGs to PNGs (batch)
for f in projects/experiments/notation_pipeline/output/**/*.svg; do rsvg-convert "$f" -o "${f%.svg}.png"; done
for f in projects/experiments/notation_pipeline/output/*.svg; do rsvg-convert "$f" -o "${f%.svg}.png"; done

# Render comparison (all 3 spacing modes — only for debugging/comparison, not routine)
/Users/ryanmillett/klotho-venv/bin/python projects/experiments/notation_pipeline/render_comparison.py
```

**IMPORTANT:** Always convert to PNG and display PNGs. Never show SVG output to the user. All render scripts use `spacing_mode='hybrid'` (OM-style) by default.

### Visual Verification Checklist

Read **PNG** files directly for visual inspection (Claude Code is multimodal). **CHECK EVERY MEASURE**, not just the first. Always verify:
- Notes are correctly spaced (proportional, not equidistant)
- The gap between time sig and first note is consistent across ALL measures
- The gap between the last note and the closing barline is a fixed END_PAD (not proportional to the last note's duration)
- Barlines are at the right positions
- Tuplet brackets span the correct notes with correct labels
- Beams connect properly
- Ties render across the correct events
- No glyph collisions (notes on barlines, notes on time sigs, etc.)
- Time signatures use SMuFL glyphs and are properly positioned
- Tempo markings appear only where tempo changes, properly spaced from the staff
- **BT: onset alignment across rows (events at same absolute time share same x)**
- **BT: per-row barlines are independent unless meters coincide**
- **BT: rows with same meter+tempo have aligned closing barlines**
- **BT: axis-aligned rows float correctly (no stretched staff lines)**
- **BT: system bracket connects to the left-aligned rows**

### RT Syntax (critical — AIs often get this wrong)
```python
from klotho.chronos import RhythmTree as RT, Meas

RT(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))            # 4 quarters
RT(meas='4/4', subdivisions=((1,(1,1,1)), 1, 1, (1,(1,1))))  # nested groups
RT(meas='4/4', subdivisions=(1, -1, 1, 1))                   # rest (negative int)
RT(meas='4/4', subdivisions=(1, 1.0, 1, 1))                  # tie (float)
RT(span=2, meas='4/4', subdivisions=(1,1,1,1,1,1,1,1))       # 2 bars of 4/4
# Leaves: positive int (note), negative int (rest), float (tie continuation)
# Proportions: (weight, (child, child, ...)) for nested groups
# Unequal weights: (3, 1, 2, 2) — proportional durations
```

---

## KEY OM SOURCE REFERENCES

| File | What to study |
|------|---------------|
| `container/scoreobject.lisp` | Qvalue/extent, `init-seq-from-tree`, QNormalize |
| `functions/trees.lisp` | `reducetree`, `mktree`, tree simplification |
| `editor/scoreeditor/scoretools.lisp` | `space-objects`, `space-packet`, `group-space-objects`, `space-size&offset`, `get-chiffrage-space`, `mesure-space`, `draw-beams-note-in-group`, `get-aligne-measures`, `draw-aligned-measures` |
| `editor/scoreeditor/rendering.lisp` | `grap-group`, beam/tuplet rendering, `draw-staff`, `draw-tempo` |
| `editor/scoreeditor/scoreeditors.lisp` | Multi-voice layout, `get-x-pos`, `timebpf`, `space-girl`, `draw-measure-signature`, `make-score-bpf-time` |
| `editor/scoreeditor/pagination.lisp` | `collect-rectangles`, barline placement, measure layout, `page-draw-aligned-measures`, `draw-measure-bar` |
| `editor/scoreeditor/tempo-change.lisp` | `draw-tempi-in-mes`, `compute-next-dynamic-pos` — tempo positioning with collision avoidance |
| `import-export/export-mxml.lisp` | MusicXML export, Qvalue→note-type mapping |

**Location:** `/Users/ryanmillett/Downloads/openmusic-master 2/OPENMUSIC/code/projects/musicproject/`

---

## OTHER REFERENCES

### Old Score Layout Experiments

`projects/experiments/score_layout/` contains an earlier multi-staff timeline layout system with:
- **Two layout strategies:** A (uniform height) and B (occupancy skyline / space-efficient packing)
- **Silhouette rendering** using matplotlib — shows hierarchical nesting as filled polygons
- **BT axis alignment patterns** — closure-based recursion, depth-based inset scaling
- **Validation:** `validate_no_overlap(blocks)` ensures no two blocks occupy the same (lane, time) region

Key files: `layout.py` (lane assignment), `render.py` (matplotlib visualization), `generators.py` (test compositions).

These patterns may be useful for future pagination, nested BTs, or multi-system layout.

---

## ADDITIONAL NOTES

- **Code hygiene matters.** This experiment will become actual Klotho API code. Reuse, don't duplicate. Keep the pipeline modular with clear pass separation.
- **BT axis alignment is our own convention.** OM does not have a direct equivalent of Klotho's `axis` parameter for TemporalBlock. OM's `poly` objects always left-align voices. The axis=-1 (left), 0 (center), 1 (right) alignment of rows with different durations is a Klotho-specific feature. When implementing axis-related layout, we cannot defer to OM — we must design our own conventions. The general onset-alignment and timebpf approach from OM still applies, but the "floating" row placement is novel.
- **System bracket:** Currently implemented as an SVG bezier path in `_system_bracket()`. SMuFL bracket glyphs (`bracket`, `bracketTop`, `bracketBottom`) exist but are designed for fixed staff heights and don't scale to arbitrary system heights. This is flagged — if a better approach is found, replace the path.
- **OM sentinel point in timebpf:** OM adds a point 1000ms past the last onset, 20px past the last x, to ensure smooth extrapolation for final barlines. We chose NOT to do this because it introduces proportional gaps where we want fixed END_PAD gaps. If the fixed-gap approach causes other issues, reconsider adding a sentinel.
- **Future: nested BTs.** BTs that contain other BTs = nested systems. The architecture should be recursive-ready even if we don't implement it yet.
- **Future: animation.** Note highlighting during playback. Study Klotho's existing animation pattern at `klotho/semeios/visualization/_animation/`. Not in scope for this pass but keep SVG element IDs predictable for future animation hookup.
- **Future: grace notes.** Zero-valued leaves (`0` in subdivisions). Deferred until RT validates them.
- **Future: smart beam grouping.** Optional auto-beaming of adjacent ungrouped notes. User wants this as an opt-in flag, not default behavior.
- **Future: `RT.from_durations()` — port of OM's `mktree`.** A class method on `RhythmTree` that takes a flat list of durations (Fractions, e.g. `[1/4, 1/8, 1/8, -1/4, 1/4]`) and a time signature, and returns a fully constructed RT with inferred hierarchical grouping. Negative values = rests, float values = tied continuations (OM convention). The algorithm distributes events across measures, then into beats, then applies conventional grouping heuristics per beat. **OM source references (all under `/Users/ryanmillett/Downloads/openmusic-master 2/OPENMUSIC/code/projects/musicproject/functions/trees.lisp`):**
  - `mktree` (line 329) — entry point; computes number of measures needed, calls `simple->tree`
  - `simple->tree` (line 210) — converts absolute-onset list into measure sequence via `buildmeasure-seq`
  - `buildmeasure-seq` (line 186) — distributes events across measures using `filter-events-between`, calls `build-one-measure` per measure
  - `build-one-measure` (line 154) — distributes events within a measure into per-beat subtrees, calls `create-beat` per beat, then `fuse-pauses-and-tied-notes-between-beats` to merge cross-beat ties/rests
  - `create-beat` (line 112) — builds a single beat's subtree from local onsets via `make-sub-tree` → `better-predefined-subdiv?`
  - `better-predefined-subdiv?` (line 236) — hardcoded pattern-matching for ~12 common rhythmic patterns, producing one level of inner grouping (e.g. `(3 1 1 1)` → `(3, (1 (1 1 1)))`)
  - `make-sub-tree` (line 87) — converts local onset list to proportional cell; marks tied-from-previous notes as floats
  - `make-proportional-cell` (line 40) — converts duration list to integer proportions via LCM
  - `fuse-pauses-and-tied-notes-between-beats` (line 127) — merges consecutive tied notes (floats) and consecutive rests across beat boundaries
  Maximum tree depth from `mktree` is 4 levels (voice → measure → beat → sub-beat group → leaf). The sub-beat grouping is not recursive — `better-predefined-subdiv?` applies exactly once per beat. For deeper nesting, OM expects the user to write the tree directly.
  **Implementation notes:** This would live on the Klotho `RhythmTree` class itself (not in the experiment). For multi-measure results, it could return either a single `RT` with `span > 1` or a `TemporalUnitSequence`. The `better-predefined-subdiv?` heuristics are specific to Western notation conventions and could be made extensible.
- **Future: tie-group-aware pfield distribution in UC.** Currently, UC's `set_pfields`, `set_mfields`, `apply_envelope`, `sparsify`, and playback converters all treat every RT leaf as an independent event. Tied leaves (`tied=True`) are continuations of the previous leaf and should be treated as part of the same sounding event. **Design (agreed upon):**
  - **Tie groups are inferred from node data, not stored.** Walk `rt.leaf_nodes` in order: `tied=False` starts a new group, `tied=True` extends the current group. A convenience method `rt.tie_group(leaf_id)` returns the full group (attack + continuations).
  - **Tie groups are atomic for pfield assignment.** Setting a value on any member propagates to the whole group. `set_pfields(continuation_leaf, freq=440)` sets freq on the entire tie group.
  - **Distribution (Patterns/callables) skips continuations.** `index` and `total` in `DistributionContext` count attacks only. Continuation leaves inherit from their attack leaf after distribution. This matches the existing `include_rests=False` pattern — rests are skipped by default, and ties follow the same convention.
  - **Envelopes sample at every leaf onset regardless of ties.** Envelopes shape continuous parameters over time; the tied leaf's onset is a valid sample point for amplitude shaping even though it's the same sounding note.
  - **`sparsify` and `make_rest` operate on whole tie groups.** Resting a continuation rests the whole group. Resting an attack rests the whole group.
  - **`subdivide` on a tied leaf preserves tie status.** New children inherit `tied=True` from the subdivided continuation leaf.
  - **No new `include_ties` flag.** Tie-group coherence is always enforced for discrete values (scalars, Patterns, callables). Envelopes already behave correctly by design.
  - **Affected code:** `_distribute_to_targets`, `_build_pfield_context`, `DistributionContext`, `set_pfields`, `set_mfields`, `set_instrument`, `_materialize_events`, `__iter__`, `__len__`, `events` DataFrame, `sparsify`, `make_rest`, playback converters (`_sc_assembly.py`).
  - **Key files:** `klotho/thetos/composition/compositional.py`, `klotho/chronos/rhythm_trees/rhythm_tree.py`, `klotho/chronos/temporal_units/temporal.py`, `klotho/utils/playback/_sc_assembly.py`.
- **Future: LilyPond/MusicXML export.** Low priority.
- **Future: connected barlines for aligned measures.** OM draws vertical barlines connecting all staves when measures align in time. We draw independent per-row barlines. Adding connected barlines would make the temporal alignment more visually explicit. Study `draw-aligned-measures` in scoretools.lisp.
- **Future: OM-style `space-packet` for BT.** The most correct approach would replace our flat `min_event_dx` with a per-time-point computation that takes the max glyph width across all rows. This would implement OM's `space-packet` "take the max" logic directly in `_build_timebpf()`.
- **Future: BT row-padding with rest UTs ("silent gap filling").**
  When a `TemporalBlock` has rows of unequal duration, the `axis` parameter aligns them (left, center, right), leaving temporal gaps on one or both sides of shorter rows. Currently these gaps are truly empty — no rests, no events. For notation purposes (and for theoretical completeness), we want to **pad each row with rest UT(s)** so every row spans the full BT duration.

  **Context:** This is an analytical notation system; correctness over performability. Irrational tempus values (2/7, 12/13, etc.) are fine. The goal is that each padded row is a valid `TemporalUnitSequence` whose total duration exactly equals `bt.duration`.

  **The gap:** For a row with duration `D` in a BT of duration `T` with axis `a`:
  - Pre-gap (before row): `(T - D) * (a + 1) / 2`
  - Post-gap (after row):  `(T - D) * (1 - a) / 2` (equivalently `T - D - pre_gap`)
  - axis=-1 → all pre-gap is 0, post-gap = T - D
  - axis=0  → pre-gap = post-gap = (T - D) / 2
  - axis=1  → pre-gap = T - D, post-gap is 0
  - Continuous axis values between -1 and 1 interpolate.
  - A row can itself be a UT, UTS, or nested BT; the gap is relative to the row's `.duration`.

  **What Haddad does (thesis §4.8):** In Haddad's framework, silence padding is never post-hoc — it's a structural product of the compositional process. Canons and homothetic polyphonies express the offset as cumulative UT sums converted to silence (`(Σut_k) & (UT)_(s)`). The "triangle" shape (our `axis`) emerges from these offset silences. There is no separate padding algorithm because the padding IS part of the algebraic construction.

  **Our situation is different:** Klotho's `TemporalBlock` assembles arbitrary, independently-created rows. The gap must be computed after the fact. We need an algorithm.

  **Approaches (in order of simplicity):**

  **Approach A: Single rest UT per gap.**
  For each non-zero gap, construct one rest UT:
  - Use the same `beat` and `bpm` as the adjacent row element (first UT for pre-gap, last UT for post-gap).
  - Compute `gap_tempus = gap_seconds / beat_duration(beat, bpm)` as a `Fraction`.
  - Build `TemporalUnit(tempus=gap_tempus, prolatio=(-1,), beat=beat, bpm=bpm)`.
  - Prepend/append to the row (wrapping in a UTS if necessary).

  Pros: Simple, exact, always produces a row that sums to `bt.duration`.
  Cons: The gap tempus may be an unusual fraction (e.g. 4/119 if tempos nearly match). This is theoretically valid but visually odd for analysis — a single measure with a single rest under a complex bracket. Also, if the gap is very large (many seconds), a single-measure rest with a huge tempus (e.g. 47/4) is less readable than multiple measures.

  **Approach B: Decompose gap into whole measures + remainder.**
  Use the adjacent UT's meter as a template:
  1. Compute how many complete measures of that meter fit in the gap.
  2. Build N whole-rest UTs with that meter.
  3. Build one final rest UT for the fractional remainder (if any).
  4. Assemble as a UTS prefix/suffix.

  Pros: Produces readable multi-measure rests for large gaps (e.g. 3 measures of 4/4 rest + 1 measure of 1/4 rest). Common cases (same meter, integer tempo ratios) produce clean output.
  Cons: The remainder UT still has the "odd tempus" issue from Approach A. Meter choice for the template is somewhat arbitrary (which adjacent UT?).

  **Approach C: Derive gap structure from the longest row.**
  Instead of using the adjacent row's meter, use the *longest* row (the one defining `bt.duration`) as a structural reference:
  1. The longest row's UTs define a sequence of time regions.
  2. For each shorter row, identify which regions of the longest row overlap with the gap.
  3. Build rest UTs that mirror those regions' meters and tempos.

  Pros: The rest measures "match" the longest row's metric structure, making cross-staff reading easier (rest barlines align with the reference row's barlines). This is closest to what a human copyist would do in a polytempo score.
  Cons: More complex. The longest row's tempo/meter may be unrelated to the short row's, making the rest UTs feel structurally arbitrary. Doesn't generalize well when rows have nested BTs.

  **Approach D: Hybrid — Approach B with Approach C alignment.**
  Decompose the gap into whole measures (Approach B) but choose the meter breakpoints so that rest-measure barlines align with the longest row's barlines where possible. Where the gap doesn't align to a barline, use the longest row's meter for the partial measure.

  Pros: Best of both worlds — readable multi-measure rests with cross-staff barline alignment.
  Cons: Most complex to implement. May produce rest measures with slightly odd meters at the boundaries.

  **Approach E: Notation-pipeline-only (no BT mutation).**
  Don't modify the `TemporalBlock` or its rows at all. Instead, handle padding purely in the notation pipeline (`pipeline_bt.py`):
  1. Detect gaps at notation time.
  2. Generate synthetic `NotatedMeasure` objects filled with rest events.
  3. Insert them into the `NotatedSystem` before/after the real measures.

  Pros: Keeps the Klotho data model clean — `TemporalBlock` remains a pure alignment container. The padding is a rendering concern, not a structural one.
  Cons: The padding logic lives in the notation layer rather than the temporal layer, which means other consumers of `TemporalBlock` (playback, analysis) don't benefit. Also, computing tempus/meter for synthetic measures from raw seconds requires the same logic as Approaches A–D.

  **Recommendation:** Start with **Approach A** (simplest, always correct) as a utility function, probably at the `TemporalBlock` or `chronos` level — something like `bt.padded_rows()` that returns a list of UTS where each row has been wrapped with rest UTs to match `bt.duration`. This keeps the original BT immutable while providing a padded view. Later, upgrade to **Approach B** or **D** for better readability if needed. **Approach E** may also be useful as a complementary notation-layer convenience, but the core gap-filling logic should live in `chronos` since it's fundamentally a temporal operation.

  **Beat/BPM constraints for rest UTs:**
  The tempus of a rest UT can be whatever fraction the gap requires — that's fine. But the `beat` and `bpm` used to construct the rest UT should stay within musically meaningful ranges to avoid degenerate notation (e.g. a tempo marking of `1/256 = 9.7`). Proposed bounds:
  - **beat**: minimum 1/16, maximum 3/4 (dotted half). Tuplet-derived beats (e.g. 1/6, 1/10, 1/12) are acceptable as long as the denominator stays within these bounds.
  - **bpm**: minimum ~24, maximum ~300.
  The algorithm should pick `beat` and `bpm` for the rest UT from the adjacent row element first (most natural choice). If that combination falls outside bounds for the computed gap, adjust: e.g. halve/double the beat and compensate bpm, or choose the nearest row element whose beat/bpm is in range. The tempus absorbs whatever is left — and "it is what it is."

  **Edge cases to handle:**
  - Gap is zero (row duration == bt.duration): no padding needed.
  - Row is already a UTS: prepend/append rest UTs to the sequence.
  - Row is a single UT: wrap in UTS, then prepend/append.
  - Row is a nested BT: compute its `.duration`, pad the outer wrapper (the nested BT becomes one element in a UTS with rest UT(s) flanking it).
  - Continuous axis values (e.g. axis=0.3): both pre- and post-gap are non-zero; pad both sides.
  - Very small gaps (sub-32nd-note): theoretically valid but may produce visually heavy notation for near-zero silence. Consider an optional tolerance parameter that absorbs gaps below a threshold into the adjacent event (opt-in, not default — correctness first).
