"""Tests for repeat() across the temporal classes (UT, CU, UTS, TB)."""
import pytest

from klotho.chronos.temporal_units.temporal import (
    TemporalBlock,
    TemporalUnit,
    TemporalUnitSequence,
)
from klotho.thetos.composition.compositional import CompositionalUnit


def _ut():
    return TemporalUnit(span=1, tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)


class TestTemporalUnitRepeat:
    def test_returns_sequence_of_copies(self):
        ut = _ut()
        r = ut.repeat(3)
        assert isinstance(r, TemporalUnitSequence)
        assert len(r) == 3
        assert r.duration == pytest.approx(3 * ut.duration)
        assert r.seq[0] is not ut
        assert r.seq[0] is not r.seq[1]

    def test_copies_are_independent(self):
        r = _ut().repeat(2)
        r.seq[0].make_rest(0)
        assert not any(c.is_rest for c in r.seq[1])


class TestCompositionalUnitRepeat:
    def test_preserves_parameters(self):
        cu = CompositionalUnit(span=1, tempus='4/4', prolatio=(1, 1, 1, 1),
                               beat='1/4', bpm=120)
        cu.set_instrument(0, 'kl_sampler1')
        cu.leaves.set_pfields(amp=0.7)
        rc = cu.repeat(2)
        assert isinstance(rc, TemporalUnitSequence) and len(rc) == 2
        for member in rc:
            assert isinstance(member, CompositionalUnit)
            leaf = list(member._rt.leaf_nodes)[0]
            assert member.get_instrument(leaf) == 'kl_sampler1'
            assert list(member)[0].pfields.get('amp') == 0.7


class TestSequenceRepeat:
    def test_nested_sequence(self):
        ut = _ut()
        uts = TemporalUnitSequence([ut, ut])
        ru = uts.repeat(4)
        assert isinstance(ru, TemporalUnitSequence) and len(ru) == 4
        assert all(isinstance(m, TemporalUnitSequence) for m in ru)
        assert ru.duration == pytest.approx(4 * uts.duration)

    def test_consecutive_offsets(self):
        ut = _ut()
        uts = TemporalUnitSequence([ut, ut])
        ru = uts.repeat(3)
        assert ru.seq[1].start == pytest.approx(uts.duration)
        assert ru.seq[2].end == pytest.approx(ru.duration)

    def test_repr_with_container_members(self):
        ru = TemporalUnitSequence([_ut()]).repeat(2)
        assert 'TemporalUnitSequence' in str(ru)


class TestBlockRepeat:
    def test_block_repeat(self):
        ut = _ut()
        tb = TemporalBlock([ut.copy(), TemporalUnitSequence([ut, ut])])
        rt = tb.repeat(2)
        assert isinstance(rt, TemporalUnitSequence) and len(rt) == 2
        assert all(isinstance(m, TemporalBlock) for m in rt)
        assert rt.duration == pytest.approx(2 * tb.duration)

    def test_repeated_blocks_play_offset(self):
        from klotho.utils.playback.supersonic.converters import convert_to_sc_events

        ut = _ut()
        tb = TemporalBlock([ut.copy()])
        evs = convert_to_sc_events(tb.repeat(2))
        assert max(e['start'] for e in evs) >= tb.duration - 1e-6
