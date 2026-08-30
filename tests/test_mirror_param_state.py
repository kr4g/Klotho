"""Mirroring parameter state onto a rebuilt unit must follow STRUCTURE, not id.

``modulate_tempo``, ``modulate_tempus`` and ``TemporalUnit._scaled`` all share
one recipe: rebuild the unit from ``ut.prolationis``, then pour the source's
parameter layer, instruments, slurs and control envelopes into it. The pour was
keyed by RAW NODE ID, which only lines up while the source has never been
mutated -- a freshly built tree numbers depth-first (2, 3, 4, 5, 6), while a
source that has been ``subdivide``d or ``remove_subtree``d carries the ids
rustworkx happened to hand it (5, 6, 2, 3, 4).

So ``uc * Fraction(1, 1)`` -- documented as a true no-op -- ROTATED the music,
and a ``remove_subtree``d source lost a value and resurrected the pfield
default 0.0 as real music. The two trees always have the same SHAPE (same
prolationis), so the correspondence is positional, not numeric.
"""

from fractions import Fraction

import pytest

from klotho.chronos.temporal_units.algorithms import modulate_tempo, modulate_tempus
from klotho.dynatos.envelopes import Envelope
from klotho.thetos import CompositionalUnit as UC


def _freqs(uc):
    """The freq of every event, in sounding order."""
    return [e['freq'] for e in uc]


def _tagged(prolatio=(1, 1, 1, 1), freqs=(100.0, 200.0, 300.0, 400.0)):
    """A UC whose every beat carries its own freq tag."""
    uc = UC(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=60,
            pfields={'freq': 0.0})
    for node, freq in zip([h.id for h in uc.leaves], freqs):
        uc.set_pfields(node, freq=freq)
    return uc


def _slur_flags(uc):
    """``[(slur_start, slur_end), ...]`` in sounding order.

    NaN (no flag) is normalised to ``None`` so the rows compare by equality --
    ``nan != nan`` would make every comparison pass.
    """
    def flag(value):
        return None if value != value else float(value)

    return [(flag(row.get('_slur_start')), flag(row.get('_slur_end')))
            for _, row in uc.events.iterrows()]


def _env_leaf_indices(uc):
    """Each control envelope's target leaves, as POSITIONS in the unit."""
    order = list(uc._rt.leaf_nodes)
    spans = []
    for desc in uc._control_envelopes.values():
        subset = desc['leaf_subset']
        if subset is None:
            subset = uc._rt.subtree_leaves(desc['anchor_node'])
        spans.append([order.index(n) for n in subset])
    return spans


class TestMutatedSourceKeepsItsValuesOnItsOwnBeats:
    """The id mismatch only appears once the source has been mutated."""

    def test_identity_scale_after_subdivide_does_not_rotate(self):
        uc = _tagged()
        uc.subdivide([h.id for h in uc.leaves][0], (1, 1))
        before = _freqs(uc)

        assert _freqs(uc * Fraction(1, 1)) == before

    def test_identity_scale_after_remove_subtree_keeps_every_value(self):
        uc = _tagged()
        uc.remove_subtree([h.id for h in uc.leaves][1])
        before = _freqs(uc)

        after = _freqs(uc * Fraction(1, 1))
        # the pfield DEFAULT must never resurface as real music
        assert 0.0 not in after
        assert after == before

    def test_modulate_tempo_after_subdivide_does_not_rotate(self):
        uc = _tagged()
        uc.subdivide([h.id for h in uc.leaves][0], (1, 1))
        before = _freqs(uc)

        assert _freqs(modulate_tempo(uc, '1/4', 120)) == before

    def test_modulate_tempus_after_subdivide_does_not_rotate(self):
        uc = _tagged()
        uc.subdivide([h.id for h in uc.leaves][0], (1, 1))
        before = _freqs(uc)

        assert _freqs(modulate_tempus(uc, 1, '2/4')) == before

    def test_instruments_follow_the_structure_not_the_id(self):
        uc = _tagged()
        uc.subdivide([h.id for h in uc.leaves][0], (1, 1))
        leaves = list(uc._rt.leaf_nodes)
        uc.set_instrument(leaves[3], 'tagged')
        before = list(uc.events['instrument'])

        assert list((uc * Fraction(1, 1)).events['instrument']) == before


class TestOverlaysFollowTheSameMapping:
    """Slur specs and envelope anchors ride the same recipe, by verbatim id."""

    def test_identity_scale_carries_the_slur_over_the_same_notes(self):
        uc = _tagged(freqs=(100.0, 200.0, 300.0, 400.0))
        uc.subdivide([h.id for h in uc.leaves][0], (1, 1))
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur(node=leaves[2:4])
        before = _slur_flags(uc)

        assert _slur_flags(uc * Fraction(1, 1)) == before

    def test_identity_scale_carries_the_envelope_over_the_same_notes(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'amp': 0.0})
        uc.subdivide([h.id for h in uc.leaves][0], (1, 1))
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.1, 0.9]), 'amp', node=leaves[2:4],
                          control=True)
        before = _env_leaf_indices(uc)

        assert _env_leaf_indices(uc * Fraction(1, 1)) == before

    def test_modulate_tempo_carries_the_slur_over_the_same_notes(self):
        uc = _tagged()
        uc.subdivide([h.id for h in uc.leaves][0], (1, 1))
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur(node=leaves[2:4])
        before = _slur_flags(uc)

        assert _slur_flags(modulate_tempo(uc, '1/4', 120)) == before


class TestUnmutatedSourceIsUnaffected:
    """The already-correct case must stay correct."""

    def test_identity_scale_on_a_fresh_unit_is_still_a_no_op(self):
        uc = _tagged()
        assert _freqs(uc * Fraction(1, 1)) == [100.0, 200.0, 300.0, 400.0]
