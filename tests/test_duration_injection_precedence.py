"""What wins when a `duration` pfield meets the auto-injected slot duration.

WL-36. A SynthDef control named exactly ``duration`` receives the event's
real duration, gated or not. What happens when the user *also* authors a
``duration`` is not the same in all of the lowering paths, and Ryan's
2026-08-28 ruling — that ``duration`` "is always overridden by the
auto-filling mechanism" — was applied as **documentation only**: no
behaviour changed and no warning was added.

These tests pin the behaviour that documentation describes. They are
characterization tests, not a specification: every one of them asserts what
the code does today, so that the table in
``docs/architecture/07_PLAYBACK.md`` fails loudly rather than going quietly
wrong. **A change here is not a regression by itself** — it means the doc
needs the same edit, and it means whoever is building the duration-scaling
verb has started resolving the split.

The split, measured 2026-08-29:

============================================  ==================
path                                          on conflict
============================================  ==================
1  CompositionalUnit, object instrument       injection wins
1b CompositionalUnit, string instrument       authored wins
2  simple objects (Pitch, Scale, Chord, ...)  injection wins
3  Score events                               authored wins
============================================  ==================

Row 2 corrects the project record, which had grouped paths 2 and 3 as both
letting the authored value win. ``_inst_note`` does carry a guard for that,
but ``duration``/``dur`` are reserved in ``KNOWN_KWARGS`` and consumed as
the note *length* before ``extra_pfields`` is built, so nothing public can
reach the guard.
"""

import warnings

import pytest

from klotho.tonos import Pitch
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.synthdef import SynthDefKit
from klotho.utils.playback._converter_base import KNOWN_KWARGS
from klotho.utils.playback._sc_assembly import (
    lower_compositional_ir_to_sc_assembly,
)
from klotho.utils.playback.supersonic.converters import (
    _inst_note,
    _resolve_synth,
    convert_score_to_sc_events,
    convert_to_sc_events,
)

SLOT_DUR = 1.0      # 4/4 at bpm=60 with beat=1/4, one leaf per beat
AUTHORED = 0.25


def _news(events):
    return [e for e in events
            if e.get('type') == 'new' and e.get('defName') != '__rest__']


def _uc(inst):
    return UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
              inst=inst, pfields=['duration'])


# --- path 1: CompositionalUnit, object instrument -------------------------

def test_path1_object_instrument_injection_wins():
    uc = _uc(SynthDefKit.beatbox())
    uc.set_pfields(uc.root, duration=AUTHORED)
    events = _news(lower_compositional_ir_to_sc_assembly(uc))
    assert events
    for event in events:
        assert event['pfields']['duration'] == pytest.approx(SLOT_DUR)


def test_path1_without_an_authored_value_still_injects():
    uc = _uc(SynthDefKit.beatbox())
    events = _news(lower_compositional_ir_to_sc_assembly(uc))
    assert events
    for event in events:
        assert event['pfields']['duration'] == pytest.approx(SLOT_DUR)


# --- path 1b: CompositionalUnit, string instrument ------------------------

def test_path1b_string_instrument_authored_value_wins():
    """A string instrument contributes no default pfields, so an authored
    ``duration`` on the event is user-set by definition and is left alone."""
    uc = _uc('kl_sampler2')
    uc.set_pfields(uc.root, duration=AUTHORED)
    events = _news(lower_compositional_ir_to_sc_assembly(uc))
    assert events
    for event in events:
        assert event['pfields']['duration'] == pytest.approx(AUTHORED)


# --- path 2: simple objects ----------------------------------------------

def test_path2_duration_is_a_reserved_kwarg_not_a_pfield():
    """The reason path 2's guard never fires — pin the cause, not just the effect."""
    assert 'duration' in KNOWN_KWARGS
    assert 'dur' in KNOWN_KWARGS


def test_path2_authored_duration_is_read_as_the_note_length():
    events = _news(convert_to_sc_events(Pitch('C4'), inst=SynthDefKit.beatbox(),
                                        duration=AUTHORED))
    assert events[0]['dur'] == pytest.approx(AUTHORED)
    assert events[0]['pfields']['duration'] == pytest.approx(AUTHORED)


def test_path2_injection_wins_over_an_authored_duration():
    """`dur` sets the length; `duration` cannot survive alongside it."""
    events = _news(convert_to_sc_events(Pitch('C4'), inst=SynthDefKit.beatbox(),
                                        dur=2.0, duration=AUTHORED))
    assert events[0]['pfields']['duration'] == pytest.approx(2.0)


def test_path2_guard_exists_but_only_a_direct_internal_call_reaches_it():
    synth, inst_ctx = _resolve_synth(SynthDefKit.beatbox(), 'kl_sine')
    injected = _inst_note('uid', synth, 0.0, 2.0, {'freq': 440.0},
                          extra_pfields=None, inst_ctx=inst_ctx)
    guarded = _inst_note('uid', synth, 0.0, 2.0, {'freq': 440.0},
                         extra_pfields={'duration': AUTHORED}, inst_ctx=inst_ctx)
    assert injected[0]['pfields']['duration'] == pytest.approx(2.0)
    assert guarded[0]['pfields']['duration'] == pytest.approx(AUTHORED)


# --- path 3: Score events -------------------------------------------------

def test_path3_score_authored_value_wins():
    score = Score()
    score.new(start=0.0, dur=2.0, inst=SynthDefKit.beatbox(), duration=AUTHORED)
    events = _news(convert_score_to_sc_events(score)['events'])
    assert events[0]['pfields']['duration'] == pytest.approx(AUTHORED)


def test_path3_without_an_authored_value_still_injects():
    score = Score()
    score.new(start=0.0, dur=2.0, inst=SynthDefKit.beatbox())
    events = _news(convert_score_to_sc_events(score)['events'])
    assert events[0]['pfields']['duration'] == pytest.approx(2.0)


# --- the ruling's own consequence ----------------------------------------

def test_no_warning_is_emitted_on_conflict():
    """R3: documentation only. A per-leaf warning would fire on the canonical
    corpus idiom ``set_pfields(duration=lambda c: c.real_duration)``, which
    authors exactly the slot duration on every leaf and is entirely correct."""
    uc = _uc(SynthDefKit.beatbox())
    uc.set_pfields(uc.root, duration=AUTHORED)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        lower_compositional_ir_to_sc_assembly(uc)
    offending = [w for w in caught if 'duration' in str(w.message).lower()]
    assert not offending, f"unexpected duration warning: {offending}"
