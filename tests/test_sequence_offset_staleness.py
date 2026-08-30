"""UTS offsets must not go stale when a member is mutated through the sequence.

``TemporalUnitSequence._set_offsets`` walks the members once and assigns each
an absolute offset from a running sum of the durations it sees at that moment.
Every *sequence-level* mutator calls it -- and nothing calls it when a member
changes duration underneath. A sequence hands out its **live** members
(``seq``, ``s[i]``, iteration), and a container member (a nested
``TemporalUnitSequence`` or ``TemporalBlock``) has mutators of its own, so
``s[0].append(...)`` lengthens member 0 without any sequence-level mutator ever
running. The members then overlap: member 0 ends past where member 1 starts,
with no exception and no warning.

This is the defect commit ``b062260`` fixed for ``TemporalBlock``, one
container down, in the sibling that was not fixed. These tests pin the
read-time validation that closes it, reader by reader.

**The sequence contradicted itself, which is the sharpest way to state it.**
``duration``, ``durations`` and ``onsets`` recompute from the live members
every time and were always right; the members' own ``.start`` -- which is what
every per-unit reader and the lowering walk use -- kept the pre-mutation value.
So ``s.onsets`` and ``[m.start for m in s]`` disagreed about the same sequence.

Each staleness test reads through **one** public reader and no other, because
any other read repairs the offsets as a side effect and would hide a missing
check. For the same reason the mutation is made through the private
``s._seq[i]`` rather than ``s[i]``: reaching the member through a public reader
would run that reader's check first, and the test would no longer be about the
reader it names. ``_seq`` is the documented bypass, exactly as ``blk._rows``
is for the block.

Scope note: this is about staleness only. ``onsets`` ignoring the sequence's
own ``_offset`` (a placed sequence reports onsets relative to itself while its
members report absolute times) is a separate, older defect and is NOT settled
here -- no test below reads ``onsets`` on a placed sequence.
"""

import re

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock


def _u(tempus='4/4', prolatio=(1, 1), bpm=60):
    return TemporalUnit(tempus=tempus, prolatio=prolatio, bpm=bpm)


def _stale_pair():
    """A two-member sequence whose member 0 has grown 2s -> 6s underneath it.

    Correct offsets afterwards are ``[0.0, 6.0]``; the offsets ``_set_offsets``
    last wrote are ``[0.0, 2.0]``, so member 1 starts 4s before member 0 ends.
    """
    s = TemporalUnitSequence([TemporalUnitSequence([_u('2/4')]), _u('4/4')])
    s._seq[0].append(_u('4/4'))
    return s


_TIME = re.compile(r'\d+s:\d+ms')


class TestStaleOffsetsAfterLiveMemberMutation:

    def test_seq_reoffsets_after_a_member_grows(self):
        s = _stale_pair()
        assert [m.start for m in s.seq] == pytest.approx([0.0, 6.0])

    def test_indexing_reoffsets_after_a_member_grows(self):
        s = _stale_pair()
        assert s[1].start == pytest.approx(6.0)

    def test_iterating_reoffsets_after_a_member_grows(self):
        s = _stale_pair()
        assert [m.start for m in s] == pytest.approx([0.0, 6.0])

    def test_the_printed_table_reoffsets_after_a_member_grows(self):
        # The table is a reader too: it prints each member's Start, Duration
        # and End straight from the live member. Asserted as the sequence's
        # own contract -- member 1 starts where member 0 ends -- so the
        # numbers do not have to be repeated here, and nothing but ``str``
        # is read.
        s = _stale_pair()
        lines = str(s).splitlines()
        first, second = _TIME.findall(lines[1]), _TIME.findall(lines[2])
        assert first[2] == second[0], f'member 0 ends {first[2]}, member 1 starts {second[0]}'

    def test_members_do_not_overlap_after_a_member_grows(self):
        # The defect stated as the thing a composer hears: two members
        # sounding on top of each other.
        s = _stale_pair()
        members = list(s)
        assert members[0].end <= members[1].start + 1e-9

    def test_the_sequence_stops_contradicting_its_own_onsets(self):
        # ``onsets`` was always right and the member starts were wrong; the
        # two must now agree. (Unplaced sequence, so ``onsets``' own
        # offset-blindness is not in play.)
        s = _stale_pair()
        assert [m.start for m in s.seq] == pytest.approx(list(s.onsets))
        assert s.duration == pytest.approx(s.seq[-1].end)

    def test_a_shrinking_member_reoffsets_too(self):
        # The other direction: the sequence gets shorter, so the stale offset
        # leaves member 1 starting after the sequence has already ended.
        s = TemporalUnitSequence([TemporalUnitSequence([_u('4/4'), _u('4/4')]),
                                  _u('4/4')])
        assert [m.start for m in s.seq] == pytest.approx([0.0, 8.0])
        s._seq[0].remove(1)                    # member 0 shrinks 8s -> 4s
        assert [m.start for m in s.seq] == pytest.approx([0.0, 4.0])
        assert s.seq[-1].end == pytest.approx(s.end)

    def test_a_nested_block_member_reoffsets(self):
        # A block member grows the same way a sequence member does, and the
        # block's own realign does not tell its container anything.
        s = TemporalUnitSequence([TemporalBlock([_u('2/4')], sort_rows=False),
                                  _u('4/4')])
        s._seq[0].append(_u('8/4'))            # block row 0 is now 8s
        assert [m.start for m in s.seq] == pytest.approx([0.0, 8.0])
        assert s.duration == pytest.approx(12.0)

    def test_a_placed_sequence_reoffsets_from_its_own_start(self):
        # The repair must resume from the sequence's own ``_offset``, not
        # from zero: this inner sequence sits at 4s inside an outer one.
        outer = TemporalUnitSequence([_u('4/4'),
                                      TemporalUnitSequence(
                                          [TemporalUnitSequence([_u('2/4')]),
                                           _u('4/4')])])
        inner = outer._seq[1]
        assert inner.start == pytest.approx(4.0)
        inner._seq[0].append(_u('4/4'))        # inner member 0: 2s -> 6s
        assert [m.start for m in inner.seq] == pytest.approx([4.0, 10.0])

    def test_deep_nesting_reoffsets_through_every_level(self):
        # Three containers down. Only the outermost sequence is read.
        s = TemporalUnitSequence([TemporalUnitSequence(
                                      [TemporalUnitSequence([_u('2/4')])]),
                                  _u('4/4')])
        s._seq[0]._seq[0].append(_u('4/4'))
        assert [m.start for m in s.seq] == pytest.approx([0.0, 6.0])
        assert s.seq[0].seq[0].seq[-1].end == pytest.approx(6.0)

    def test_block_events_place_a_stale_row_correctly(self):
        # ``TemporalBlock.events`` walks a sequence row's members. The block
        # realigns on its own row *durations*, so a row whose members shifted
        # internally while its total stayed the same does not trigger the
        # block's check -- the sequence has to carry its own.
        one = lambda: _u('4/4', prolatio=(1,))       # one 4s event per unit
        blk = TemporalBlock(
            [TemporalUnitSequence([TemporalUnitSequence([one()]),
                                   TemporalUnitSequence([one(), one()])])],
            sort_rows=False)
        row = blk._rows[0]                     # the block copies on construction
        assert blk.duration == pytest.approx(12.0)

        row._seq[0].append(one())              # member 0: 4s -> 8s
        row._seq[1].remove(1)                  # member 1: 8s -> 4s
        assert blk.duration == pytest.approx(12.0)   # block geometry unmoved

        starts = sorted(blk.events['start'].tolist())
        assert starts == pytest.approx([0.0, 4.0, 8.0])


class TestUnmutatedSequencesAreUnchanged:
    """The fix must be invisible to a sequence nobody mutated through a member."""

    def test_construction_offsets_are_untouched(self):
        s = TemporalUnitSequence([_u('2/4'), _u('4/4'), _u('1/4')])
        assert [m.start for m in s.seq] == pytest.approx([0.0, 2.0, 6.0])
        assert s.duration == pytest.approx(7.0)

    def test_reading_repeatedly_is_idempotent(self):
        s = TemporalUnitSequence([_u('2/4'), _u('4/4')])
        first = [m.start for m in s.seq]
        identities = [id(m) for m in s.seq]
        for _ in range(3):
            s.seq, s[0], list(s), str(s), s.duration, s.onsets
        assert [m.start for m in s.seq] == pytest.approx(first)
        assert [id(m) for m in s.seq] == identities   # members are not rebuilt

    @pytest.mark.parametrize('mutate, expected', [
        (lambda s: s.append(_u('4/4')), [0.0, 2.0]),
        (lambda s: s.prepend(_u('4/4')), [0.0, 4.0]),
        (lambda s: s.insert(1, _u('4/4')), [0.0, 2.0]),
        (lambda s: s.extend([_u('4/4')]), [0.0, 2.0]),
        (lambda s: s.__setitem__(0, _u('4/4')), [0.0]),
        (lambda s: s.replace(0, _u('4/4')), [0.0]),
    ])
    def test_sequence_level_mutators_still_reoffset(self, mutate, expected):
        s = TemporalUnitSequence([_u('2/4')])
        mutate(s)
        assert [m.start for m in s.seq] == pytest.approx(expected)
        assert s.seq[-1].end == pytest.approx(s.end)

    def test_removing_the_last_member_still_reoffsets(self):
        s = TemporalUnitSequence([_u('2/4'), _u('4/4')])
        s.remove(0)
        assert [m.start for m in s.seq] == pytest.approx([0.0])

    def test_empty_sequence_reads_clean(self):
        s = TemporalUnitSequence([])
        assert s.duration == 0.0
        assert s.end == 0.0
        assert list(s) == []
        assert s.seq == []

    def test_copy_still_repairs_and_is_independent(self):
        s = _stale_pair()
        c = s.copy()
        assert [m.start for m in c.seq] == pytest.approx([0.0, 6.0])
        c.append(_u('4/4'))
        assert len(s) == 2
