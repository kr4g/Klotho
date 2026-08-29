"""Three behavioural defects in Pattern and CompositionalUnit.

NEW-09: ``materialize_period`` computed the period from wherever the cursor
happened to be and then cached it forever.
NEW-12: assigning to a public name on a temporal object created a dead
instance attribute that read back but changed nothing.
NEW-21: of the three ways to add structure -- ``subdivide``, graft in
``'adopt'`` mode, graft in ``'replace'`` mode -- only ``'replace'`` lost the
target node's parameters, and on a CompositionalUnit the graft dropped the
donor's field registries entirely.
"""

import pytest

from klotho.chronos import RhythmTree, TemporalUnit, TemporalUnitSequence
from klotho.thetos import CompositionalUnit
from klotho.topos.collections.sequences import Pattern


class TestMaterializePeriod:
    """NEW-09."""

    def test_the_period_does_not_depend_on_when_you_ask(self):
        live = Pattern([1, [2, 3], 4])
        for _ in range(2):
            next(live)
        assert live.materialize_period() == Pattern([1, [2, 3], 4]).materialize_period()

    def test_it_is_stable_across_further_advancing(self):
        p = Pattern([1, [2, 3], 4])
        for _ in range(2):
            next(p)
        first = p.materialize_period()
        for _ in range(3):
            next(p)
        assert p.materialize_period() == first

    def test_it_still_leaves_the_cursor_alone(self):
        p = Pattern([1, [2, 3], 4])
        for _ in range(2):
            next(p)
        before = p.position
        p.materialize_period()
        assert p.position == before
        assert next(p) == 4

    def test_advancing_a_shared_delegate_does_not_rot_the_period(self):
        """The case no cursor-keyed cache could have caught: the delegate's
        cursor moves while the enclosing pattern's stays at 0."""
        inner = Pattern([10, 20, 30])
        outer = Pattern([inner, 99])
        before = outer.materialize_period()
        next(inner)
        assert outer.materialize_period() == before
        assert before == Pattern([Pattern([10, 20, 30]), 99]).materialize_period()

    def test_it_returns_one_full_cycle(self):
        p = Pattern([1, [2, 3], 4])
        assert len(p.materialize_period()) == p.length

    def test_reset_still_clears_the_cache(self):
        p = Pattern([1, [2, 3], 4])
        p.materialize_period()
        p.reset()
        assert p.position == 0
        assert p.materialize_period() == Pattern([1, [2, 3], 4]).materialize_period()


class TestPublicAssignmentIsRefused:
    """NEW-12. Every field on these classes is private and read through a
    property, so a public assignment was always a mistake."""

    def _objects(self):
        return [
            CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120),
            TemporalUnit(tempus='4/4', prolatio=(1, 1)),
            TemporalUnitSequence(),
        ]

    def test_offset_is_refused_on_every_temporal_class(self):
        for obj in self._objects():
            with pytest.raises(AttributeError, match="no settable attribute"):
                obj.offset = 0.1

    def test_the_timing_is_genuinely_unchanged(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        onsets = ut.onsets
        with pytest.raises(AttributeError):
            ut.offset = 5.0
        assert ut.onsets == onsets

    @pytest.mark.parametrize("name", ['offset', 'durations', 'onsets', 'duration'])
    def test_other_read_only_names_are_refused_too(self, name):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1))
        with pytest.raises(AttributeError):
            setattr(ut, name, 1)

    def test_a_typo_is_refused_rather_than_silently_stored(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1))
        with pytest.raises(AttributeError, match="ofset"):
            ut.ofset = 0.1

    def test_a_genuinely_settable_property_still_works(self):
        from klotho.chronos import TemporalBlock
        unit = TemporalUnit(tempus='1/4', prolatio='d', bpm=120)
        blk = TemporalBlock([unit], sort_rows=False)
        blk.axis = 0.5
        assert blk.axis == 0.5
        blk.sort_rows = True
        assert blk.sort_rows is True

    def test_private_writes_are_untouched(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1))
        ut._offset = 2.0
        assert ut._offset == 2.0


class TestGraftAgreesWithSubdivide:
    """NEW-21."""

    @staticmethod
    def _uc():
        uc = CompositionalUnit.from_ut(TemporalUnit(tempus='4/4', prolatio=(1, 1)))
        uc.set_pfields(uc.leaves, freq=440.0)
        target = list(uc.leaves)[1].id
        uc.set_pfields(target, freq=880.0)
        return uc, target

    def test_replace_keeps_the_target_override(self):
        uc, target = self._uc()
        uc.graft_subtree(target, RhythmTree(span=1, meas='1/2', subdivisions=(1, 1, 1)))
        assert [uc.pt[h.id].get('freq') for h in uc.leaves] == [440.0, 880.0, 880.0, 880.0]

    def test_it_matches_what_subdivide_produces(self):
        grafted, target = self._uc()
        grafted.graft_subtree(target, RhythmTree(span=1, meas='1/2', subdivisions=(1, 1, 1)))
        divided, target2 = self._uc()
        divided.subdivide(target2, (1, 1, 1))
        assert [divided.pt[h.id].get('freq') for h in divided.leaves] == \
               [grafted.pt[h.id].get('freq') for h in grafted.leaves]

    def test_adopt_mode_was_already_right_and_stays_right(self):
        uc, target = self._uc()
        uc.graft_subtree(target, RhythmTree(span=1, meas='1/2', subdivisions=(1, 1)),
                         mode='adopt')
        assert all(uc.pt[h.id].get('freq') in (440.0, 880.0) for h in uc.leaves)

    def test_a_donor_brings_its_field_registry(self):
        donor = CompositionalUnit.from_ut(TemporalUnit(tempus='1/2', prolatio=(1, 1)))
        donor.set_pfields(donor.leaves, pan=0.75)
        uc, target = self._uc()
        uc.graft_subtree(target, donor._rt)
        assert 'pan' in uc._rt.pfield_names
        assert 'freq' in uc._rt.pfield_names

    def test_a_donor_brings_its_values(self):
        donor = CompositionalUnit.from_ut(TemporalUnit(tempus='1/2', prolatio=(1, 1)))
        donor.set_pfields(donor.leaves, pan=0.75)
        uc, target = self._uc()
        uc.graft_subtree(target, donor._rt)
        assert any(uc.pt[h.id].get('pan') == 0.75 for h in uc.leaves)

    def test_a_donor_key_wins_over_the_target_override(self):
        """``kept`` restores only what the donor root does not define."""
        donor = CompositionalUnit.from_ut(TemporalUnit(tempus='1/2', prolatio=(1, 1)))
        donor.set_pfields(donor._rt.root, freq=111.0)
        uc, target = self._uc()
        uc.graft_subtree(target, donor._rt)
        assert uc.pt[list(uc.leaves)[1].id].get('freq') == 111.0

    def test_the_public_verb_exists_on_both_classes(self):
        assert hasattr(TemporalUnit, 'graft_subtree')
        assert hasattr(CompositionalUnit, 'graft_subtree')

    def test_a_plain_tree_donor_is_still_accepted(self):
        uc, target = self._uc()
        result = uc.graft_subtree(target, RhythmTree(span=1, meas='1/2',
                                                     subdivisions=(1, 1)))
        assert result in uc._rt

    def test_a_non_tree_is_refused(self):
        uc, target = self._uc()
        with pytest.raises(TypeError, match="Tree"):
            uc.graft_subtree(target, [1, 2, 3])
