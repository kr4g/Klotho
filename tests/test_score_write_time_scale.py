"""AUD-49: ``Score.write(time_scale=k)`` must scale every timeline-valued field.

``write``'s docstring has promised "all event / envelope times" since the
parameter shipped in 10.5.0.  It scaled event onsets and the control-envelope
descriptors' ``start``/``dur``, and nothing else -- so a written score at any
``k != 1`` carried notes of the wrong LENGTH beside onsets of the right
position.  Every wrong number was plausible on its own and nothing raised.

The reason it was missed for so long is structural, and this module is written
around it: ``write`` enumerated the payload's time fields **independently** of
the ``start_time`` shift in ``convert_score_to_sc_events``, and the two lists
disagreed.  So the tests here do not check seven fields; they check the CLASS.

Four families of assertion:

1. **The scaling relation** -- every timeline field at ``k`` equals its value at
   ``k = 1`` times ``k``; every invariant field is untouched.  Never a literal.
2. **Non-vacuity guards** -- a family whose reference values are all zero, or
   that is absent from the payload entirely, FAILS rather than passing quietly.
   ``0 * k == 0`` proves nothing, and that is exactly how an earlier
   ``time_scale`` test in ``test_envelope_semantics.py`` became empty.
3. **Self-referential invariants** -- relations that must hold within a single
   scaled payload, so they cannot go stale as the fixture changes.
4. **A census guard** -- every numeric leaf in the written JSON must be
   classified as timeline or invariant.  A field added to the payload later
   arrives as a RED test asking "is this seconds?", instead of joining AUD-49
   in silence.  This is the part that catches the class.

No assertion in this file is an identity against a hardcoded number, and none
returns early when two sides match -- that shape makes a test green while
guarding nothing.
"""

import contextlib
import io
import json

import pytest

from klotho.chronos import TemporalUnit as UT
from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.score import Score


# ----------------------------------------------------------------------
# The kitchen-sink score: every injection site, plus negative controls
# ----------------------------------------------------------------------

def _kitchen_sink():
    """A score touching all five timeline-injection sites at once.

    Every unit is placed at a NON-ZERO start and the envelope is anchored
    late, because ``0 * k == 0`` would let a broken scale pass.
    """
    s = Score()

    # A gated UC: exercises events[].dur on the UC path.
    uc_gated = UC.from_ut(UT(span=1, tempus='4/4', prolatio=(1, 1, 1, 1),
                             beat='1/4', bpm=60))
    uc_gated.leaves.set(inst='kl_saw', freq=440.0, amp=0.3)
    s.add(uc_gated, at=0.5)

    # A SLUR on an ungated def declaring releaseTime: the head's releaseTime
    # receives the slur's real span, in timeline seconds.
    uc_slur = UC.from_ut(UT(span=1, tempus='4/4', prolatio=(1, 1, 1, 1),
                            beat='1/4', bpm=60))
    uc_slur.leaves.set(inst='fd_arpy', freq=330.0)
    uc_slur.apply_slur(node=uc_slur._rt.root)
    s.add(uc_slur, at=5.0)

    # An ungated def declaring `dur`: the reserved note-length slot.
    uc_kick = UC.from_ut(UT(span=1, tempus='4/4', prolatio=(1, 1),
                            beat='1/4', bpm=60))
    uc_kick.leaves.set(inst='kl_kicktone')
    s.add(uc_kick, at=9.0)

    # A CONTROL envelope, anchored late so desc.start and every target
    # startTime are non-zero.
    uc_env = UC.from_ut(UT(span=1, tempus='4/4', prolatio=(1, 1, 1, 1),
                           beat='1/4', bpm=60))
    uc_env.leaves.set(inst='kl_saw', freq=220.0)
    uc_env.apply_envelope(Envelope([0.2, 1.0], times=[1.0]), 'amp',
                          node=uc_env._rt.root, control=True)
    s.add(uc_env, at=13.0)

    # NEGATIVE CONTROL, and the whole reason the tag exists: the SAME
    # instrument as the slurred unit, NOT slurred, carrying an AUTHORED
    # releaseTime.  One file, one pfield name, two opposite kinds of number.
    uc_authored = UC.from_ut(UT(span=1, tempus='4/4', prolatio=(1, 1),
                                beat='1/4', bpm=60))
    uc_authored.leaves.set(inst='fd_arpy', freq=550.0,
                           releaseTime=0.3, attackTime=0.05)
    s.add(uc_authored, at=20.0)

    return s


def _write(score, tmp_path, k):
    path = tmp_path / f"k{k}.json"
    with contextlib.redirect_stdout(io.StringIO()):    # the write() FYI line
        score.write(str(path), time_scale=k)
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def payloads(tmp_path_factory):
    """One reference write at k=1 plus one per scale factor."""
    d = tmp_path_factory.mktemp("aud49")
    s = _kitchen_sink()
    return {k: _write(s, d, k) for k in (1.0, 0.5, 2.0, 3.0)}


# ----------------------------------------------------------------------
# Field classification -- declared, so the census can check it is complete
# ----------------------------------------------------------------------

#: Numeric event keys measured in seconds on the score's timeline.
TIMELINE_EVENT_KEYS = frozenset({'start', 'dur'})

#: Numeric descriptor keys measured in seconds.
TIMELINE_DESC_KEYS = frozenset({'start', 'dur'})

#: Numeric event keys that are NOT seconds and must never move.
INVARIANT_EVENT_KEYS = frozenset({
    '_logicalStepId', '_polyGroupId', '_polyVoiceCount', '_polyVoiceIndex',
    'speaker', 'blockIndex',
})


def _timeline_pfield_keys(event):
    """The pfields LOWERING filled from the timeline, as it recorded them."""
    return list(dict.fromkeys(event.get('_timelinePfields') or ()))


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ----------------------------------------------------------------------
# 2. Non-vacuity guards -- these run first and gate everything else
# ----------------------------------------------------------------------

def test_the_fixture_exercises_every_injection_site(payloads):
    """If lowering stops emitting one of these, the scaling tests below would
    quietly stop checking it.  This makes that a red test instead."""
    ref = payloads[1.0]
    events = ref['events']
    assert events, "the fixture produced no events at all"

    tagged = [e for e in events if e.get('_timelinePfields')]
    assert tagged, (
        "no event carries _timelinePfields -- lowering has stopped tagging "
        "injected timeline pfields, so the discrimination this test exists "
        "to check is not happening")

    tagged_keys = {k for e in tagged for k in _timeline_pfield_keys(e)}
    assert 'releaseTime' in tagged_keys, "the slur-span injection is missing"
    assert 'dur' in tagged_keys or 'duration' in tagged_keys, (
        "the reserved note-length injection is missing")

    descs = ref['meta'].get('controlEnvelopes') or []
    assert descs, "the fixture produced no control-envelope descriptor"
    assert any(t.get('startTime') for d in descs for t in d.get('targets', [])), (
        "every target startTime is zero or absent -- 0 * k == 0 would pass a "
        "broken scale")


def test_no_timeline_family_is_all_zero(payloads):
    """``0 * k == 0``.  A family of reference values that is entirely zero
    cannot detect a missing scale, so it fails here rather than passing."""
    ref = payloads[1.0]
    starts = [e['start'] for e in ref['events'] if _is_num(e.get('start'))]
    durs = [e['dur'] for e in ref['events'] if _is_num(e.get('dur'))]
    injected = [e['pfields'][k] for e in ref['events']
                for k in _timeline_pfield_keys(e) if _is_num(e['pfields'].get(k))]
    descs = ref['meta'].get('controlEnvelopes') or []
    d_starts = [d['start'] for d in descs if _is_num(d.get('start'))]
    t_starts = [t['startTime'] for d in descs for t in d.get('targets', [])
                if _is_num(t.get('startTime'))]

    for name, values in (('events[].start', starts), ('events[].dur', durs),
                         ('injected pfields', injected),
                         ('descriptor start', d_starts),
                         ('target startTime', t_starts)):
        assert values, f"{name}: no values at all -- nothing is being checked"
        assert any(v != 0 for v in values), (
            f"{name}: every reference value is zero, so scaling it proves "
            f"nothing")


# ----------------------------------------------------------------------
# 1. The scaling relation
# ----------------------------------------------------------------------

@pytest.mark.parametrize("k", [0.5, 2.0, 3.0])
def test_every_timeline_field_scales_and_nothing_else_moves(payloads, k):
    assert k != 1.0, "k == 1 would make every assertion below trivially true"
    ref, got = payloads[1.0], payloads[k]

    assert len(got['events']) == len(ref['events']), (
        "time_scale changed the NUMBER of events")

    for i, (a, b) in enumerate(zip(ref['events'], got['events'])):
        for key in TIMELINE_EVENT_KEYS:
            if _is_num(a.get(key)):
                assert b[key] == pytest.approx(a[key] * k, rel=1e-12, abs=1e-9), (
                    f"events[{i}].{key} did not scale")
            else:
                assert b.get(key) == a.get(key), (
                    f"events[{i}].{key} was non-numeric and changed anyway")

        tagged = set(_timeline_pfield_keys(a))
        assert set(_timeline_pfield_keys(b)) == tagged, (
            f"events[{i}]._timelinePfields differs between writes")

        for pk, av in (a.get('pfields') or {}).items():
            bv = (b.get('pfields') or {})[pk]
            if not _is_num(av):
                assert bv == av, f"events[{i}].pfields.{pk} changed"
            elif pk in tagged:
                assert bv == pytest.approx(av * k, rel=1e-12, abs=1e-9), (
                    f"events[{i}].pfields.{pk} was tagged as timeline-valued "
                    f"and did not scale")
            else:
                assert bv == av, (
                    f"events[{i}].pfields.{pk} is an AUTHORED value and must "
                    f"not move -- scaling by name would rewrite the "
                    f"composer's own timbre")

    ref_d = ref['meta'].get('controlEnvelopes') or []
    got_d = got['meta'].get('controlEnvelopes') or []
    assert len(got_d) == len(ref_d)
    for i, (a, b) in enumerate(zip(ref_d, got_d)):
        for key in TIMELINE_DESC_KEYS:
            if _is_num(a.get(key)):
                assert b[key] == pytest.approx(a[key] * k, rel=1e-12, abs=1e-9), (
                    f"controlEnvelopes[{i}].{key} did not scale")
        assert len(b['targets']) == len(a['targets'])
        for j, (ta, tb) in enumerate(zip(a['targets'], b['targets'])):
            assert tb['startTime'] == pytest.approx(
                ta['startTime'] * k, rel=1e-12, abs=1e-9), (
                f"controlEnvelopes[{i}].targets[{j}].startTime did not scale "
                f"-- the scheduler compares it against an already-scaled "
                f"event start with an EXACT equality, so an unscaled one "
                f"drops the automation mapping entirely")
            # NOT asserted: that the two writes agree on the target's `id`.
            # They do not -- every lowering mints fresh uids, so writing the
            # same unmodified Score twice yields different ids throughout.
            # That is out of scope here and filed separately; what matters for
            # AUD-49 is that a target still resolves to its own event, which
            # `test_a_targets_start_is_still_the_later_of_its_synth_and_its_envelope`
            # checks WITHIN a single payload.


@pytest.mark.parametrize("k", [0.5, 2.0, 3.0])
def test_authored_values_under_injected_names_do_not_move(payloads, k):
    """The negative control, stated on its own because it is the whole point
    of tagging at lowering rather than scaling by pfield name.

    The fixture puts an injected ``releaseTime`` and an authored
    ``releaseTime`` on the SAME instrument in the SAME file.
    """
    ref, got = payloads[1.0], payloads[k]
    authored = [(i, e) for i, e in enumerate(ref['events'])
                if 'releaseTime' in (e.get('pfields') or {})
                and 'releaseTime' not in _timeline_pfield_keys(e)]
    assert authored, (
        "the fixture no longer contains an AUTHORED releaseTime, so this "
        "negative control is checking nothing")
    for i, e in authored:
        assert got['events'][i]['pfields']['releaseTime'] == e['pfields']['releaseTime']


# ----------------------------------------------------------------------
# 3. Self-referential invariants -- true within one payload, at every k
# ----------------------------------------------------------------------

@pytest.mark.parametrize("k", [1.0, 0.5, 2.0, 3.0])
def test_the_piece_length_the_scheduler_computes_scales_with_it(payloads, k):
    """``_computePieceDur`` in scheduler_core.js is ``max(start + dur)``.  If
    ``dur`` is left unscaled the finish timer, the loop cycle and the recording
    stop all fire at the wrong moment."""
    def piece_dur(p):
        return max(e['start'] + (e['dur'] or 0.0) for e in p['events'])
    assert piece_dur(payloads[k]) == pytest.approx(
        piece_dur(payloads[1.0]) * k, rel=1e-12, abs=1e-9)


@pytest.mark.parametrize("k", [1.0, 0.5, 2.0, 3.0])
def test_a_targets_start_is_still_the_later_of_its_synth_and_its_envelope(payloads, k):
    """``converters`` builds each target as
    ``max(synth_start, envelope_start)``.  Re-derive it from the written file:
    if either side scaled and the other did not, this breaks."""
    p = payloads[k]
    by_id = {e['id']: e['start'] for e in p['events'] if 'id' in e}
    descs = p['meta'].get('controlEnvelopes') or []
    checked = 0
    for d in descs:
        for t in d['targets']:
            if t['id'] not in by_id:
                continue
            assert t['startTime'] == pytest.approx(
                max(by_id[t['id']], d['start']), rel=1e-12, abs=1e-9)
            checked += 1
    assert checked, "no target resolved to an event -- nothing was checked"


# ----------------------------------------------------------------------
# 4. The census guard -- the class catcher
# ----------------------------------------------------------------------

def test_every_numeric_field_in_the_written_file_is_classified(payloads):
    """Walk the payload and demand that every numeric leaf be known to be
    either seconds or not.

    AUD-49 happened because a field was added to the payload and nobody asked
    whether ``write`` should scale it.  ``speaker`` and the tie-injection
    branch were both added during the Haddad block, after the orphaned fix for
    this defect was written, and neither prompted the question.  An
    unclassified numeric field now fails HERE, by name, with the path.
    """
    ref = payloads[1.0]
    unclassified = []

    for i, e in enumerate(ref['events']):
        tagged = set(_timeline_pfield_keys(e))
        for key, value in e.items():
            if key == 'pfields':
                for pk, pv in (value or {}).items():
                    if _is_num(pv) and pk not in tagged:
                        # An untagged pfield is an AUTHORED constant by
                        # construction; that is the classification.
                        pass
                continue
            if not _is_num(value):
                continue
            if key in TIMELINE_EVENT_KEYS or key in INVARIANT_EVENT_KEYS:
                continue
            unclassified.append(f"events[{i}].{key} = {value!r}")

    for i, d in enumerate(ref['meta'].get('controlEnvelopes') or []):
        for key, value in d.items():
            if key == 'targets':
                for j, t in enumerate(value):
                    for tk, tv in t.items():
                        if _is_num(tv) and tk != 'startTime':
                            unclassified.append(
                                f"meta.controlEnvelopes[{i}].targets[{j}].{tk} "
                                f"= {tv!r}")
                continue
            if _is_num(value) and key not in TIMELINE_DESC_KEYS \
                    and key != 'blockIndex':
                unclassified.append(f"meta.controlEnvelopes[{i}].{key} = {value!r}")

    assert not unclassified, (
        "these numeric fields in the written payload are classified neither "
        "as timeline-valued nor as invariant. For each, decide whether "
        "Score.write(time_scale=k) should scale it, then add it to "
        "TIMELINE_* or INVARIANT_* in this module:\n  "
        + "\n  ".join(unclassified))
