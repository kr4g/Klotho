"""The THIRD id-state event: a leaf that STOPS BEING A LEAF -- plus the two
regressions the DEATH/RELOCATION fix wave introduced around it.

b5be431 framed the id-state contract as exactly two events. ``uc._rt.subdivide``
and ``uc._rt.graft_subtree`` are a third: the edited node's id survives IN
PLACE, but it is interior now, and slur specs and control-envelope subsets
that keep naming it inherit their markers onto every note of the new subtree.
The UC's own verbs heal this by absorbing the new leaves; the raw tree verbs
announced nothing at all.

The two regressions:

* ``_remap_slur_specs`` relocated each member independently and never
  re-checked CONTIGUITY -- ``insert_child`` into the middle of a slurred span
  authored a slur the public ``apply_slur`` refuses to create, with the
  inserted note sitting inside the slur unmarked.
* ``_mirror_param_state``'s topology check raised on a bare-root source
  (prune/remove_subtree can strip a unit to its root, RT-26): ``prolationis``
  reports ``(1,)`` and rebuilding from ``(1,)`` gives root + one child, so
  the shapes legitimately differ by that one degenerate step. All three
  rebuild recipes (``uc * k``, ``modulate_tempo``, ``modulate_tempus``) died.
"""

import warnings
from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree
from klotho.chronos.temporal_units.algorithms import modulate_tempo, modulate_tempus
from klotho.dynatos.envelopes import Envelope
from klotho.thetos import CompositionalUnit as UC


def _tagged(prolatio=(1, 1, 1, 1)):
    """A UC whose every beat carries its own freq tag (100, 200, ...)."""
    uc = UC(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=60,
            pfields={'freq': 0})
    for i, node in enumerate(uc._rt.leaf_nodes):
        uc.set_pfields(node, freq=100 * (i + 1))
    return uc


def _marked(uc, column):
    """Freqs of the events carrying flag 1 in *column* ([] when no slur exists)."""
    ev = uc.events
    if column not in ev.columns:
        return []
    return [float(row['freq']) for _, row in ev.iterrows() if row[column] == 1.0]


class TestLeafStopsBeingALeaf:
    """C-1: raw-tree subdivide/graft must announce the leaf-surface change."""

    def test_raw_subdivide_does_not_inherit_the_slur_onto_the_new_subtree(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])

        uc._rt.subdivide(L[1], (1, 1, 1))

        # the subdivided note is interior now: it cannot be slurred, and its
        # marker must not fan out over the three children it grew
        assert _marked(uc, '_slur_start') == []
        # ...and with one member gone the slur is below two notes: it dissolves
        assert uc._slur_specs == {}

    def test_raw_subdivide_at_the_slur_edge_keeps_the_still_leaf_members(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2], L[3]])

        uc._rt.subdivide(L[3], (1, 1))

        # the two members still on the leaf surface stay slurred; nothing
        # else does
        assert _marked(uc, '_slur_start') == [200.0]
        assert _marked(uc, '_slur_end') == [300.0]
        (spec,) = uc._slur_specs.values()
        assert spec['leaf_nodes'] == (L[1], L[2])

    def test_raw_graft_does_not_inherit_the_slur_onto_the_new_subtree(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])

        uc._rt.graft_subtree(L[1], RhythmTree(meas='1/4', subdivisions=(1, 1)))

        assert _marked(uc, '_slur_start') == []
        assert uc._slur_specs == {}

    def test_raw_subdivide_drops_the_ex_leaf_from_envelope_subsets(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[2.0]), 'freq',
                          node=[L[0], L[1]], control=True)

        uc._rt.subdivide(L[1], (1, 1, 1))

        # the descriptor must not keep naming an id the public API could
        # never have selected as a target
        (desc,) = uc._control_envelopes.values()
        assert L[1] not in desc['leaf_subset']

    def test_uc_verb_still_absorbs_the_new_leaves(self):
        """The owning verb's richer heal must be untouched by the seam."""
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])

        uc.subdivide(L[1], (1, 1, 1))

        (spec,) = uc._slur_specs.values()
        assert len(spec['leaf_nodes']) == 4  # three children + L[2]


class TestRelocationCannotAuthorANonContiguousSlur:
    """C-2: an insertion into a slurred span splits the slur at the intruder,
    exactly as a rest does -- it must never extend over a note that was never
    slurred, and never store a selection ``apply_slur`` refuses."""

    def test_insertion_inside_a_two_note_slur_dissolves_it(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])

        uc._rt.insert_child(uc._rt.root, 2, proportion=1)

        # two one-note fragments are not slurs; nothing stays marked and the
        # inserted note is not swallowed by a span it was never part of
        assert uc._slur_specs == {}
        assert _marked(uc, '_slur_start') == []
        assert _marked(uc, '_slur_end') == []

    def test_insertion_splits_a_longer_slur_and_keeps_the_viable_fragment(self):
        uc = _tagged(prolatio=(1, 1, 1, 1, 1))
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2], L[3]])

        uc._rt.insert_child(uc._rt.root, 3, proportion=1)

        # the fragment before the intruder still has two notes and survives;
        # the one-note fragment after it dissolves
        (spec,) = uc._slur_specs.values()
        leaf_order = list(uc._rt.leaf_nodes)
        indices = [leaf_order.index(n) for n in spec['leaf_nodes']]
        assert indices == [1, 2]
        assert spec['index_range'] == (1, 2)
        assert _marked(uc, '_slur_start') == [200.0]
        assert _marked(uc, '_slur_end') == [300.0]

    def test_every_stored_spec_stays_contiguous_after_insertion(self):
        """The invariant over ALL surviving specs, not only the one its
        siblings name.

        The fixture has to be chosen so that specs survive. On the four-note
        fixture the siblings use, the slur dissolves entirely,
        ``_slur_specs`` is ``{}``, and the loop below runs zero times and
        asserts nothing. Here two slurs are drawn and the insertion lands
        inside the first: the fragment after the intruder survives, and the
        untouched second slur relocates whole, so the loop has two specs to
        check.
        """
        uc = _tagged(prolatio=(1, 1, 1, 1, 1, 1))
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[0], L[1], L[2]])
        uc.apply_slur([L[3], L[4], L[5]])

        uc._rt.insert_child(uc._rt.root, 1, proportion=1)

        # the invariant apply_slur enforces: members occupy consecutive
        # leaf positions (no tie groups in play here)
        assert len(uc._slur_specs) == 2, \
            'the fixture must leave specs behind, or the loop checks nothing'
        leaf_order = list(uc._rt.leaf_nodes)
        for spec in uc._slur_specs.values():
            indices = sorted(leaf_order.index(n) for n in spec['leaf_nodes'])
            assert indices == list(range(indices[0], indices[-1] + 1))


class TestBareRootUnitSurvivesTheRebuildRecipes:
    """C-3: the topology check stays, but the bare-root shape (RT-26) maps
    root-to-root instead of dying."""

    def _bare(self):
        u = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
               pfields={'amp': 0.3})
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for n in list(u._rt.leaf_nodes):
                u.remove_subtree(n)
        return u

    def test_identity_scale_keeps_the_root_values(self):
        out = self._bare() * Fraction(1, 1)
        assert out.events['amp'].tolist() == [0.3]

    def test_modulate_tempo_keeps_the_root_values(self):
        out = modulate_tempo(self._bare(), '1/4', 120)
        assert out.events['amp'].tolist() == [0.3]

    def test_modulate_tempus_keeps_the_root_values(self):
        out = modulate_tempus(self._bare(), 1, '2/4')
        assert out.events['amp'].tolist() == [0.3]
