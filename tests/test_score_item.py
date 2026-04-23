"""Tests for ScoreItem: set_duration (with and without ripple),
stretch, passthrough __getattr__, frozen flag, and read-only time
queries."""

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.score import Score


def _uc():
    return UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
              pfields={'amp': 0.5, 'freq': 440.0})


class TestReadOnlyTimeQueries:
    def test_start_end_duration(self):
        s = Score()
        item = s.add(_uc(), name='a', at=2.0)
        assert item.start == 2.0
        assert item.duration == pytest.approx(item.unit.duration)
        assert item.end == pytest.approx(item.start + item.duration)


class TestSetDuration:
    def test_set_duration_scales_bpm(self):
        s = Score()
        item = s.add(_uc(), name='a')
        old_bpm = item.unit.bpm
        item.set_duration(item.duration * 2)
        assert item.duration == pytest.approx(_uc().duration * 2)
        assert item.unit.bpm == pytest.approx(old_bpm / 2)

    def test_set_duration_zero_raises(self):
        s = Score()
        item = s.add(_uc(), name='a')
        with pytest.raises(ValueError, match="must be positive"):
            item.set_duration(0)

    def test_set_duration_negative_raises(self):
        s = Score()
        item = s.add(_uc(), name='a')
        with pytest.raises(ValueError, match="must be positive"):
            item.set_duration(-1.0)

    def test_set_duration_does_not_move_start(self):
        s = Score()
        item = s.add(_uc(), name='a', at=5.0)
        item.set_duration(1.0)
        assert item.start == 5.0


class TestRipple:
    def test_ripple_shifts_later_items(self):
        s = Score()
        s.add(_uc(), name='a')
        s.add(_uc(), name='b', after='a')
        s.add(_uc(), name='c', after='b')
        b_original_start = s['b'].start
        c_original_start = s['c'].start
        new_dur = s['a'].duration + 2.0
        s['a'].set_duration(new_dur, ripple=True)
        delta = new_dur - _uc().duration
        assert s['b'].start == pytest.approx(b_original_start + delta)
        assert s['c'].start == pytest.approx(c_original_start + delta)

    def test_no_ripple_leaves_later_items(self):
        s = Score()
        s.add(_uc(), name='a')
        s.add(_uc(), name='b', after='a')
        b_original_start = s['b'].start
        s['a'].set_duration(s['a'].duration + 2.0)
        assert s['b'].start == b_original_start

    def test_ripple_does_not_shift_earlier_items(self):
        s = Score()
        s.add(_uc(), name='a')
        s.add(_uc(), name='b', after='a')
        s.add(_uc(), name='c', after='b')
        a_start = s['a'].start
        s['b'].set_duration(s['b'].duration + 1.0, ripple=True)
        assert s['a'].start == a_start


class TestStretch:
    def test_stretch_factor(self):
        s = Score()
        item = s.add(_uc(), name='a')
        base = item.duration
        item.stretch(1.5)
        assert item.duration == pytest.approx(base * 1.5)

    def test_stretch_zero_raises(self):
        s = Score()
        item = s.add(_uc(), name='a')
        with pytest.raises(ValueError, match="must be positive"):
            item.stretch(0)

    def test_stretch_ripple(self):
        s = Score()
        s.add(_uc(), name='a')
        s.add(_uc(), name='b', after='a')
        b_start0 = s['b'].start
        s['a'].stretch(2.0, ripple=True)
        assert s['b'].start > b_start0


class TestFrozen:
    def test_frozen_blocks_set_duration(self):
        s = Score()
        item = s.add(_uc(), name='a')
        item.freeze()
        with pytest.raises(RuntimeError, match="frozen"):
            item.set_duration(5.0)

    def test_frozen_blocks_stretch(self):
        s = Score()
        item = s.add(_uc(), name='a')
        item.freeze()
        with pytest.raises(RuntimeError, match="frozen"):
            item.stretch(2.0)


class TestGetAttrPassthrough:
    def test_leaf_nodes_via_item(self):
        s = Score()
        item = s.add(_uc(), name='a')
        assert tuple(item.leaf_nodes) == item.unit.rt.leaf_nodes

    def test_set_pfields_via_item(self):
        s = Score()
        item = s.add(_uc(), name='a')
        leaf = item.unit.rt.leaf_nodes[0]
        item.set_pfields(leaf, amp=0.8)
        assert item.unit.get_pfield(leaf, 'amp') == 0.8
