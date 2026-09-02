"""AF-2 / AUD-9 + AUD-10 -- two mutating doors with no CompositionalTree override.

Every structural verb on ``CompositionalTree`` announces a leaf-surface change so
the overlays drawn against that surface -- slurs, ties, control envelopes -- get
healed or rebaked. Seventeen verbs carry the announcement. Two did not:

* ``scale`` (AUD-9). ``insert`` and ``extract`` are overridden; ``scale``, the
  third member of the same ``_respell`` family, was not. It moves every onset
  without changing the leaf SET, so a control envelope kept values sampled at
  onsets that no longer exist -- wrong music, no exception. The gate in
  ``_queue_envelope_rebakes`` compares leaf IDENTITY and never timing, so BOTH
  halves are needed: an announcement to open the gate, and a gate that can see a
  pure timing change.
* ``replace_node`` (AUD-10). The lowered consequence is worse than a mis-drawn
  slur: the synth is HELD THROUGH the rest and re-``set`` after it, so the rest
  is audibly played.

WHERE THE EXPECTED VALUES COME FROM -- none was produced by running the new code:

* The AUD-9 target values are HAND-COMPUTED from the envelope arithmetic and
  cross-checked against an INDEPENDENT code path (a freshly built unit of the
  scaled shape). span=1 of 4/4 at 1/4=60 is 4.0s; proportions (3,1,1,1) sum to 6,
  so durations are 4*3/6=2.0 and 4*1/6=0.6667 three times, giving onsets
  0, 2.0, 2.6667, 3.3333. A linear 0->1 envelope with endpoint=True spans
  0 -> 4.0, so the sampled values are onset/4: 0.0, 0.5, 0.6667, 0.8333.
* The AUD-10 targets come from the SANCTIONED TWIN: ``make_rest`` is the wired
  door for the same edit and was correct before this fix, so its behaviour is the
  oracle and ``replace_node`` must match it.

PROVEN RED: see handoffs/AF-2.md for the recorded pre-fix run.
"""

import warnings
from fractions import Fraction

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.compositional import CompositionalTree
from klotho.dynatos import Envelope
from klotho.utils.playback.supersonic.converters import convert_to_sc_events


ENV = lambda: Envelope([0, 1], times=[2])


def enveloped():
    uc = UC(span=1, tempus='4/4', prolatio=(1, 1, 1, 1),
            beat='1/4', bpm=60, pfields={'amp': 0.0})
    uc.apply_envelope(ENV(), 'amp', node=uc._rt.root, control=True)
    return uc


def slurred():
    uc = UC(span=1, tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60)
    uc.apply_slur(node=[2, 3, 4])
    return uc


def event_shape(uc):
    out = []
    for e in convert_to_sc_events(uc):
        if not isinstance(e, dict):
            continue
        out.append((e.get('type'), round(float(e.get('start', -1)), 4)))
    return out


# ------------------------------------------------------------------- AUD-9

def test_scale_is_overridden_like_its_family():
    """``insert`` and ``extract`` are overridden; ``scale`` is the third member."""
    assert 'scale' in CompositionalTree.__dict__


def test_baseline_envelope_matches_the_unscaled_shape():
    """CONTROL -- passes before and after. Pins the premise."""
    assert list(enveloped().events['amp']) == [0.0, 0.25, 0.5, 0.75]


def test_scale_rebakes_a_control_envelope():
    """AUD-9. Hand-computed above and cross-checked against a fresh unit below."""
    uc = enveloped()
    uc._rt.scale(0, 3)
    got = [round(float(v), 4) for v in uc.events['amp']]
    assert got == [0.0, 0.5, 0.6667, 0.8333]


def test_scaled_unit_agrees_with_an_independently_built_one():
    """The independent implementation: build the scaled SHAPE from scratch and
    apply the same envelope. Both paths must agree."""
    uc = enveloped()
    uc._rt.scale(0, 3)
    ref = UC(span=1, tempus='4/4', prolatio=(3, 1, 1, 1),
             beat='1/4', bpm=60, pfields={'amp': 0.0})
    ref.apply_envelope(ENV(), 'amp', node=ref._rt.root, control=True)
    assert [round(float(v), 4) for v in uc.events['amp']] == \
           [round(float(v), 4) for v in ref.events['amp']]


def test_scale_really_did_move_the_onsets():
    """CONTROL -- guards the test above from passing vacuously."""
    uc = enveloped()
    uc._rt.scale(0, 3)
    assert [round(float(d), 4) for d in uc.durations] == [2.0, 0.6667, 0.6667, 0.6667]


def test_the_already_wired_door_still_rebakes():
    """CONTROL -- ``insert`` was correct before this change and must stay so."""
    uc = enveloped()
    uc._rt.insert(0, Fraction(1, 4))
    assert [round(float(v), 4) for v in uc.events['amp']] == [0.0, 0.2, 0.4, 0.6, 0.8]


# ------------------------------------------------------------------ AUD-10

def test_replace_node_is_overridden():
    assert 'replace_node' in CompositionalTree.__dict__


def test_make_rest_dissolves_the_slur():
    """CONTROL -- the sanctioned twin, correct before this fix. It is the oracle."""
    uc = slurred()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        uc._rt.make_rest(3)
    assert uc._slur_specs == {}
    assert any('Slur removed' in str(x.message) for x in w)


def test_replace_node_resting_a_leaf_dissolves_the_slur_too():
    """AUD-10. The raw door must reach the same state as its sanctioned twin."""
    uc = slurred()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        uc._rt.replace_node(3, proportion=-1)
    assert uc._slur_specs == {}, "a rest was left inside the slur's member set"
    assert any('Slur removed' in str(x.message) for x in w)


def test_replace_node_does_not_hold_the_synth_through_the_rest():
    """The payload. Before: ('new', 0.0), ('new', 1.0), ('set', 3.0) -- ONE synth
    held from 1.0 straight across the rest at 2.0-3.0 and re-set after it, so the
    rest sounds. It must lower like ``make_rest``: three separate attacks."""
    rested = slurred()
    rested._rt.make_rest(3)
    oracle = event_shape(rested)

    uc = slurred()
    uc._rt.replace_node(3, proportion=-1)
    assert event_shape(uc) == oracle
    assert all(kind == 'new' for kind, _ in event_shape(uc)), (
        "a 'set' means the synth was held through the rest"
    )


def test_replace_node_clearing_tied_by_omission_announces():
    """The tie arm: ``replace_node`` clears ``tied`` by OMISSION, so the surface
    changes without the key ever appearing in the incoming payload."""
    uc = UC(span=1, tempus='4/4', prolatio=(1, 1, 1, 1.0), beat='1/4', bpm=60)
    uc.apply_slur(node=[2, 3, 4])
    before = dict(uc._slur_specs)
    assert before, "precondition: a slur exists"
    uc._rt.replace_node(4, proportion=1)
    assert uc._rt[4].get('tied') in (False, None), "precondition: the tie was cleared"
    for spec in uc._slur_specs.values():
        for n in spec['leaf_nodes']:
            assert uc._rt[n].get('proportion', 1) >= 0
