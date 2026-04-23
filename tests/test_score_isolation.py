"""Tests that `Score.add` copies the submitted unit so that external
references and score-owned copies evolve independently."""

import pytest

from klotho.chronos import TemporalUnit as UT, TemporalUnitSequence as UTS
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.score import Score


def _uc():
    return UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
              pfields={'amp': 0.5, 'freq': 440.0})


class TestCopyOnAdd:
    def test_external_offset_unchanged(self):
        uc = _uc()
        s = Score()
        s.add(uc, name='a', at=5.0)
        assert uc._offset == 0.0
        assert s['a'].start == 5.0

    def test_external_pfield_mutation_does_not_leak_in(self):
        uc = _uc()
        s = Score()
        s.add(uc, name='a')
        leaf = uc.rt.leaf_nodes[0]
        uc.set_pfields(leaf, amp=0.999)
        assert s['a'].unit.get_pfield(leaf, 'amp') == 0.5

    def test_score_pfield_mutation_does_not_leak_out(self):
        uc = _uc()
        s = Score()
        s.add(uc, name='a')
        leaf = uc.rt.leaf_nodes[0]
        s['a'].set_pfields(leaf, amp=0.999)
        assert uc.get_pfield(leaf, 'amp') == 0.5
        assert s['a'].unit.get_pfield(leaf, 'amp') == 0.999

    def test_external_duration_mutation_via_item_does_not_affect_external(self):
        uc = _uc()
        original_duration = uc.duration
        s = Score()
        s.add(uc, name='a')
        s['a'].set_duration(original_duration * 2)
        assert uc.duration == original_duration
        assert s['a'].duration == pytest.approx(original_duration * 2)

    def test_uts_is_copied(self):
        uc = _uc()
        seq = UTS(ut_seq=[uc, uc])
        original_seq_duration = seq.duration
        s = Score()
        s.add(seq, name='a')
        assert seq._offset == 0.0
        assert seq.duration == original_seq_duration


class TestAutoPromotion:
    def test_ut_promoted_to_uc(self):
        ut = UT(tempus='4/4', prolatio='p', bpm=60)
        s = Score()
        item = s.add(ut, name='a')
        assert isinstance(item.unit, UC)

    def test_uts_of_ut_promoted(self):
        ut = UT(tempus='4/4', prolatio='p', bpm=60)
        seq = UTS(ut_seq=[ut, ut])
        s = Score()
        item = s.add(seq, name='a')
        assert isinstance(item.unit, UTS)
        for member in item.unit._seq:
            assert isinstance(member, UC)
