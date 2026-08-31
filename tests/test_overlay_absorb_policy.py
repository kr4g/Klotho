"""SLUR-1 -- ABSORB is the single overlay policy, on every leaf-growth path.

Ryan's ruling, 2026-08-30, in his words: *"I was thinking we'd do this
'smartly' so that slurs attempt to 'survive' as best they can. So, eg, if I
subdivide a leaf inside a slur group, the subdivisions also participate in the
slur. If those subdivs include a rest, we split the slur. Slurs must connect at
least two adjacent leaves."*

Ryan's ruling, 2026-08-31, extending it to the other overlay: *"Yes. The
overall theme here is 'common sense' and 'reasonable expectations'."* -- so
control envelopes absorb too, but they get NONE of the slur constraints. A slur
is an arc over sounding notes; an envelope is a curve over a span. It does not
split on a rest and it does not dissolve at one target.

The defect this pins is not missing logic. ``_heal_slurs_after_subdivide`` and
``_heal_envelopes_after_subdivide`` already absorb -- they were wired to exactly
two verbs (``uc.subdivide``, ``uc.graft_subtree``), while every path reached
through ``uc._rt`` fell through ``_announce_leaf_surface_change`` to
``_remap_slur_specs``/``_remap_control_envelopes``, which DROPPED. So the
library answered one musical question two different ways depending on which
handle the caller happened to hold. Measured before the fix, growing the MIDDLE
member of a three-note slur:

    uc.subdivide   -> slur survives over five notes
    uc._rt.*       -> the whole slur is gone, including the two members that
                      never changed and never stopped being leaves

The parametrisation is the point: every door asserts the SAME expectation.

RED BEFORE GREEN. Every test here was written and run BEFORE the fix existed;
22 of the 34 failed, and the four raw doors all failed the same way:

    AssertionError: raw.subdivide: the slur did not survive at all
    assert {}

Two failed on the ``uc.`` path as well -- the reference path stored its
envelope subset out of time order, appending absorbed leaves at the end
rather than in the grown target's place. That was not on anyone's list; the
pin found it.

MUTATION TABLE for the two policy rules, break-tested after the fix:

    TestAbsorbIsTheSinglePolicyForSlurs
        mutation: in ``_remap_slur_specs`` pass 1, replace
        ``members.extend(self._rt.subtree_leaves(target))`` with ``pass``
        -- i.e. restore DROP.
        red: the slur does not survive.

    TestAbsorbIsTheSinglePolicyForControlEnvelopes
        mutation: in ``_remap_control_envelopes``, replace the ``grown``
        expression with ``((target,) if target in leaf_index else ())``
        -- i.e. restore DROP.
        red: the envelope loses the grown target.
"""

import warnings

import pytest

from klotho.chronos import RhythmTree
from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

def _uc(prolatio=(1,) * 6, **pfields):
    uc = UC(tempus='6/4', prolatio=prolatio, beat='1/4', bpm=60,
            pfields=pfields or {'freq': 0})
    return uc


def _tagged(prolatio=(1,) * 6):
    """Every leaf carries an mfield naming the event it IS.

    An mfield, not a pfield: baking an envelope writes pfields, so a pfield
    tag would be overwritten by the very operation under test.
    """
    uc = UC(tempus='6/4', prolatio=prolatio, beat='1/4', bpm=60,
            pfields={'amp': 0.1}, mfields={'tag': ''})
    for i, node in enumerate(uc._rt.leaf_nodes):
        uc.set_mfields(node, tag=f'e{i}')
    return uc


def _spare(uc, exclude):
    """A leaf that is neither *exclude* nor adjacent to the slurred span."""
    return [n for n in uc._rt.leaf_nodes if n != exclude][-1]


#: Every door through which a leaf can stop being a leaf, with the number of
#: leaves it grows in that leaf's place. ``raw.move_in`` is the door Ryan
#: ruled on explicitly: moved-in music JOINS the slur, with no special case
#: for where the content came from.
GROWTH_DOORS = [
    ('raw.subdivide', lambda uc, n: uc._rt.subdivide(n, (1, 1, 1)), 3),
    ('raw.graft', lambda uc, n: uc._rt.graft_subtree(
        n, RhythmTree(meas='1/4', subdivisions=(1, 1))), 2),
    ('raw.insert_child', lambda uc, n: uc._rt.insert_child(n, 0, proportion=1), 1),
    ('raw.move_subtree', lambda uc, n: uc._rt.move_subtree(_spare(uc, n), n), 1),
    ('uc.subdivide', lambda uc, n: uc.subdivide(n, (1, 1, 1)), 3),
    ('uc.graft_subtree', lambda uc, n: uc.graft_subtree(
        n, RhythmTree(meas='1/4', subdivisions=(1, 1))), 2),
]

DOOR_IDS = [d for d, _, _ in GROWTH_DOORS]


# --------------------------------------------------------------------------
# the policy
# --------------------------------------------------------------------------

class TestAbsorbIsTheSinglePolicyForSlurs:
    """A slurred leaf that grows children hands its place to those children.

    Rule (2) of the ruling, stated for every door rather than for the two
    verbs that happened to implement it.
    """

    @pytest.mark.parametrize('door, grow, grown', GROWTH_DOORS, ids=DOOR_IDS)
    def test_the_children_take_the_grown_members_place(self, door, grow, grown):
        uc = _uc()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2], L[3]])

        grow(uc, L[2])

        assert uc._slur_specs, f'{door}: the slur did not survive at all'
        (spec,) = uc._slur_specs.values()
        expected = (L[1],) + tuple(uc._rt.subtree_leaves(L[2])) + (L[3],)
        assert tuple(spec['leaf_nodes']) == expected, (
            f'{door}: expected the {grown} new leaves in the grown member\'s '
            f'place')

    @pytest.mark.parametrize('door, grow, grown', GROWTH_DOORS, ids=DOOR_IDS)
    def test_members_that_never_changed_are_not_collaterally_dissolved(
            self, door, grow, grown):
        """SLUR-B3. The two outer members never stopped being leaves.

        Under DROP the grown member became a gap, the gap read as an
        intruder, the run split into two one-note fragments, and BOTH
        dissolved -- so an edit to one note destroyed a slur over three.
        """
        uc = _uc()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2], L[3]])

        grow(uc, L[2])

        surviving = {n for spec in uc._slur_specs.values()
                     for n in spec['leaf_nodes']}
        assert L[1] in surviving, f'{door}: L1 was collaterally dissolved'
        assert L[3] in surviving, f'{door}: L3 was collaterally dissolved'

    @pytest.mark.parametrize('door, grow, grown', GROWTH_DOORS, ids=DOOR_IDS)
    def test_a_rest_among_the_new_leaves_splits_rather_than_dissolves(
            self, door, grow, grown):
        """Rule (3): a rest among the subdivisions SPLITS the slur.

        Only meaningful where the door grows enough leaves to leave two
        sounding notes on one side; the others are skipped rather than
        asserted vacuously.
        """
        uc = _uc(prolatio=(1,) * 6)
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2], L[3]])

        grow(uc, L[2])
        grown_leaves = list(uc._rt.subtree_leaves(L[2]))
        if len(grown_leaves) < 2:
            pytest.skip(f'{door} grows {len(grown_leaves)} leaf; no rest to place')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc.make_rest(grown_leaves[0])

        members = [tuple(s['leaf_nodes']) for s in uc._slur_specs.values()]
        flat = {n for m in members for n in m}
        assert grown_leaves[0] not in flat, f'{door}: a rest stayed slurred'
        assert L[1] not in flat, (
            f'{door}: L1 is alone on its side of the rest and must dissolve')
        assert L[3] in flat, f'{door}: the run after the rest must survive'


class TestAbsorbIsTheSinglePolicyForControlEnvelopes:
    """Ruling 2026-08-31: control envelopes absorb too.

    And ONLY absorb -- the slur constraints are not copied across by
    symmetry.
    """

    @pytest.mark.parametrize('door, grow, grown', GROWTH_DOORS, ids=DOOR_IDS)
    def test_the_children_take_the_grown_targets_place(self, door, grow, grown):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[2.0]), 'amp',
                          node=[L[1], L[2], L[3]], control=True)

        grow(uc, L[2])

        assert uc._control_envelopes, f'{door}: the envelope did not survive'
        (desc,) = uc._control_envelopes.values()
        expected = (L[1],) + tuple(uc._rt.subtree_leaves(L[2])) + (L[3],)
        assert tuple(desc['leaf_subset']) == expected, (
            f'{door}: expected the new leaves in the grown target\'s place, '
            f'in time order')

    @pytest.mark.parametrize('door, grow, grown', GROWTH_DOORS, ids=DOOR_IDS)
    def test_a_rest_among_the_new_leaves_does_not_split_the_envelope(
            self, door, grow, grown):
        """The asymmetry the ruling insists on.

        An envelope is a curve over a SPAN. A rest inside that span is a
        silent moment in the curve, not a break in it -- so unlike a slur
        the envelope neither splits nor dissolves. The surviving sounding
        targets on BOTH sides stay in the one envelope.
        """
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[2.0]), 'amp',
                          node=[L[1], L[2], L[3]], control=True)

        grow(uc, L[2])
        grown_leaves = list(uc._rt.subtree_leaves(L[2]))
        if len(grown_leaves) < 2:
            pytest.skip(f'{door} grows {len(grown_leaves)} leaf')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc.make_rest(grown_leaves[0])

        assert len(uc._control_envelopes) == 1, (
            f'{door}: a rest must not split the envelope into two')
        (desc,) = uc._control_envelopes.values()
        targets = set(uc.resolved_control_envelopes()[0]['target_nodes'])
        assert L[1] in targets and L[3] in targets, (
            f'{door}: both sides of the rest stay in the one envelope')

    @pytest.mark.parametrize('door, grow, grown', GROWTH_DOORS, ids=DOOR_IDS)
    def test_one_surviving_target_does_not_dissolve_the_envelope(
            self, door, grow, grown):
        """No ``>= 2`` rule for envelopes -- that is a slur property."""
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[2.0]), 'amp',
                          node=[L[1], L[2]], control=True)

        grow(uc, L[2])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc.make_rest(L[1])

        assert uc._control_envelopes, (
            f'{door}: one sounding target is still an envelope')


class TestTheSuppressionFlagIsGone:
    """``_owner_absorbs_leaf_growth`` existed only to paper over the split.

    Ryan's own test of whether this chunk was done right: with one policy
    at the seam there is nothing left for the owning verb to suppress, so
    the flag must not merely be unused -- it must be absent.
    """

    def test_the_flag_has_no_executable_reference_left(self):
        """Code, not prose.

        The docstrings that record WHY the flag is gone still name it, and
        should -- this project keeps its corrections findable. What must not
        survive is a read or a write of it, so the check strips comments and
        docstrings before looking.
        """
        import ast
        import io
        import pathlib
        import tokenize

        def executable_source(path):
            with open(path, 'rb') as fh:
                tokens = list(tokenize.tokenize(fh.readline))
            tree = ast.parse(path.read_text())
            doc_positions = {
                (n.value.lineno, n.value.col_offset)
                for n in ast.walk(tree)
                if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)
            }
            return '\n'.join(
                t.string for t in tokens
                if t.type not in (tokenize.COMMENT, tokenize.NL)
                and t.start not in doc_positions
            )

        root = pathlib.Path(__file__).resolve().parent.parent / 'klotho'
        hits = [str(p) for p in root.rglob('*.py')
                if '_owner_absorbs_leaf_growth' in executable_source(p)]
        assert hits == [], f'the suppression flag is still live in {hits}'

    def test_the_uc_verbs_and_the_seam_agree_without_it(self):
        """The behavioural half: the two handles give the same answer."""
        raw = _uc()
        L = list(raw._rt.leaf_nodes)
        raw.apply_slur([L[1], L[2], L[3]])
        raw._rt.subdivide(L[2], (1, 1, 1))

        owned = _uc()
        M = list(owned._rt.leaf_nodes)
        owned.apply_slur([M[1], M[2], M[3]])
        owned.subdivide(M[2], (1, 1, 1))

        raw_shape = [len(s['leaf_nodes']) for s in raw._slur_specs.values()]
        owned_shape = [len(s['leaf_nodes']) for s in owned._slur_specs.values()]
        assert raw_shape == owned_shape, (
            'the raw tree and the owning verb must answer the same musical '
            'question the same way')
