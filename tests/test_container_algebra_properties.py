"""Container-algebra invariants -- TemporalUnit, sequences, blocks, units.

TEST-5. Every assertion here is a PROPERTY: it holds by the DEFINITION of
what these containers mean, so there is no literal expected value an
implementation could make agree falsely. Each was derived from a contract
stated in the source -- the class docstrings, Haddad's segmentation and
concatenation rules as quoted and translated there, Python's own definition
of deepcopy, or plain arithmetic necessity -- BEFORE it was run.

They are run over COMPOSITIONS, not single verbs, because composition is
where invariants bite and is the surface no test exercised.


Falsifiability -- each law below was proven able to FAIL.

A property test that passes on its first run proves nothing by itself, so
each of these was break-tested: the named single edit was applied to the
implementation in an isolated copy and the test was observed to go red.
All were verified independently of the author, by agents instructed to
REFUTE the claim, each of which proved its copy was authoritative rather
than silently testing the real installed package.

Recorded HERE rather than only in the session handoff, because the handoff
lives outside this repository and a pointer to it is a dead reference for
anyone auditing these tests later.

* ``test_uts_members_tile_contiguously_under_every_mutator``
      klotho/chronos/temporal_units/temporal.py:1891 (_set_offsets):
      `running_offset += duration` -> `running_offset += duration * 0.5`

* ``test_uts_single_reader_repairs_after_in_place_member_mutation``
      klotho/chronos/temporal_units/temporal.py:2101
      (TemporalUnitSequence.__getitem__): delete the
      `self._ensure_offsets()` line (reverts to pre-388e597 behaviour)

* ``test_scaling_is_linear_in_magnitude_and_preserves_events_and_tempo``
      klotho/chronos/temporal_units/temporal.py:1596 (_scaled): `factor =
      k * Fraction(self.span)` -> `factor = k * Fraction(self.span) * 2`

* ``test_segment_conserves_the_whole_and_composes_with_augment``
      klotho/chronos/temporal_units/algorithms.py:192 (segment,
      TemporalUnit arm): `beat=obj.beat, bpm=obj.bpm)` ->
      `beat=Fraction(1, 4), bpm=obj.bpm)` (test unit's beat is 1/8)

* ``test_decompose_conserves_the_whole_at_leaf_level_and_every_depth``
      klotho/chronos/temporal_units/algorithms.py:385/462/500 (decompose):
      every `bpm = ut._bpm` -> `bpm = 60` (test unit is at bpm 90)

* ``test_fuse_conserves_real_time_and_metric_value``
      klotho/chronos/temporal_units/algorithms.py:621 (fuse):
      reconciliation factor inverted, `_exact_tempo_ratio(ref_bpm) /
      _exact_tempo_ratio(op.bpm)` -> `_exact_tempo_ratio(op.bpm) /
      _exact_tempo_ratio(ref_bpm)`
      NOTE: inert for the uniform-tempo block; the red comes from the
      mixed-tempi block, which is the case the law is about.

* ``test_interleave_is_a_lossless_pure_zip``
      klotho/chronos/temporal_units/algorithms.py:1065 (interleave):
      comment out `out.extend(retrograde[n:])` (drops the longer operand's
      tail)

* ``test_copy_paths_are_independent_of_the_source``
      klotho/chronos/temporal_units/temporal.py:1781 (TemporalUnit.copy
      fast path): `c._rt = self._rt.structural_clone()` -> `c._rt =
      self._rt`

* ``test_block_axis_left_center_right_anchors_and_containment``
      klotho/chronos/temporal_units/temporal.py:2391 (_align_rows):
      `adjustment = duration_diff * (self._axis + 1) / 2` -> `/ 4`
      NOTE: inert for axis=-1 (the adjustment is zero either way); the red
      comes from the axis=0 case.

* ``test_block_realigns_after_live_row_mutation_via_single_reader``
      klotho/chronos/temporal_units/temporal.py:2448
      (TemporalBlock.duration): `geometry = self._ensure_aligned()` ->
      `geometry = self._geometry` (serves the stale geometry)

* ``test_block_events_flattening_is_conservative_and_voice_faithful``
      klotho/chronos/temporal_units/temporal.py:2817 (_walk_block_events,
      nested-block arm): `f'{voice}.{i}'` -> `voice` (stops extending the
      dotted voice path)
      CAVEAT: only the voice-faithfulness half goes red under this
      mutation. The conservation half is unprobed by it.

* ``test_tempo_modulation_preserves_duration_and_spelling``
      klotho/chronos/temporal_units/algorithms.py:1342 (modulate_tempo):
      drop `* Fraction(ut.span)` from the factor (test unit has span=2)

* ``test_uc_parameters_stay_attached_across_subdivide_and_scaling``
      klotho/chronos/temporal_units/temporal.py:1610 (_scaled,
      CompositionalUnit arm): replace `out._mirror_param_state(self)` with
      `pass`

* ``test_rt_and_pt_are_snapshots_not_live_views``
      klotho/chronos/temporal_units/temporal.py:1124 (TemporalUnit.rt
      property): `return self._rt.copy()` -> `return self._rt`

* ``test_repeat_and_self_extend_algebra``
      klotho/chronos/temporal_units/temporal.py:2094-2096
      (TemporalUnitSequence.extend): move `snapshot = list(other_seq)`
      inside the repeat loop (re-reads the growing self, 2**n growth)
"""

# --- module-level shared imports and helpers (used by all 15 tests) ---
import copy as _copy
from collections import Counter
from fractions import Fraction

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.chronos.rhythm_trees import Meas
from klotho.chronos.temporal_units.algorithms import (
    augment, decompose, fuse, interleave, modulate_tempo, modulate_tempus, segment)
from klotho.thetos.composition.compositional import CompositionalUnit


def _mag(u):
    """Metric magnitude of a unit: tempus VALUE x span, as an exact Fraction.
    Spelling-independent on purpose (6/20 and 3/10 have equal magnitude);
    spelling contracts are asserted separately via str(tempus)."""
    return Fraction(u.tempus.numerator, u.tempus.denominator) * Fraction(u.span)


def _assert_tiles(s):
    """A sequence means contiguous succession: each member begins where the
    previous one ends, the first at the sequence's own start (0 outside a
    Score), and the whole spans the sum of the members."""
    members = list(s)  # public reader; validates placement on the way out
    assert s.start == 0.0
    if not members:
        assert s.duration == 0.0
        return
    assert members[0].start == s.start
    for prev, cur in zip(members, members[1:]):
        assert cur.start == prev.end, (
            f"member starting at {cur.start} does not begin where the "
            f"previous ends ({prev.end})")
    assert s.duration == pytest.approx(sum(m.duration for m in members), rel=1e-12)
    assert members[-1].end == pytest.approx(s.start + s.duration, rel=1e-12)


def test_uts_members_tile_contiguously_under_every_mutator():
    a = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=120)
    b = TemporalUnit(tempus='3/8', prolatio='p', beat='1/8', bpm=90)
    c = TemporalUnit(tempus='5/4', prolatio=(3, -2), beat='1/4', bpm=60)

    s = TemporalUnitSequence([a, b])
    _assert_tiles(s)
    s.append(c)
    _assert_tiles(s)
    s.prepend(c)
    _assert_tiles(s)
    s.insert(2, b)
    _assert_tiles(s)
    s.remove(0)
    _assert_tiles(s)
    s.replace(0, a)
    _assert_tiles(s)
    s[1] = c
    _assert_tiles(s)
    s.extend([a, b])
    _assert_tiles(s)
    s.append(b, repeat=2)
    _assert_tiles(s)

def test_uts_single_reader_repairs_after_in_place_member_mutation():
    u1 = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=120)
    u2 = TemporalUnit(tempus='7/8', prolatio='p', beat='1/8', bpm=70)
    tail = TemporalUnit(tempus='3/4', prolatio='d', beat='1/4', bpm=60)

    s = TemporalUnitSequence([TemporalUnitSequence([u1]), tail])
    # mutate member 0 THROUGH THE MEMBER'S OWN API
    s[0].append(u2)

    expected_start = u1.duration + u2.duration  # standalone units
    assert expected_start == pytest.approx(7.0, rel=1e-12)  # hand computation
    # ONE reader; no copy, no block nesting, no .seq scan beforehand
    assert s[1].start == pytest.approx(expected_start, rel=1e-9)

def test_scaling_is_linear_in_magnitude_and_preserves_events_and_tempo():
    ut = TemporalUnit(span=2, tempus=Meas(6, 20), prolatio=(2, 1, -1, 1),
                      beat='1/8', bpm=90)
    src_mag = Fraction(6, 20) * 2  # from the authored spec
    assert _mag(ut) == src_mag

    k1, k2 = Fraction(3, 2), Fraction(5, 7)
    for k in (k1, k2):
        r = ut * k
        assert _mag(r) == k * src_mag
        assert r.duration == pytest.approx(float(k) * ut.duration, rel=1e-9)
        assert len(r) == len(ut)
        assert (r.beat, r.bpm) == (ut.beat, ut.bpm)

    assert _mag((ut * k1) * k2) == src_mag * k1 * k2
    assert _mag(ut / k1) == src_mag / k1
    assert _mag((ut * k1) / k1) == src_mag
    # the source never moved
    assert _mag(ut) == src_mag and len(ut) == 4

def test_segment_conserves_the_whole_and_composes_with_augment():
    ut = TemporalUnit(tempus='5/2', prolatio=(2, 1, (2, (1, 1)), 1),
                      beat='1/8', bpm=100)
    for f in (Fraction(1, 8), Fraction(5, 12), Fraction(2, 3)):
        halves = segment(ut, f)
        assert isinstance(halves, TemporalUnitSequence)
        assert len(halves) == 2
        left, right = halves.seq
        assert _mag(left) == f * _mag(ut)
        assert _mag(left) + _mag(right) == _mag(ut)
        assert (left.beat, left.bpm) == (ut.beat, ut.bpm)
        assert (right.beat, right.bpm) == (ut.beat, ut.bpm)
        assert halves.duration == pytest.approx(ut.duration, rel=1e-9)
        _assert_tiles(halves)

    aug = augment(ut, Meas('3/10'), 2)
    assert _mag(aug) == _mag(ut) + Fraction(3, 10)
    halves = segment(aug, '1/3')
    assert _mag(halves.seq[0]) + _mag(halves.seq[1]) == _mag(aug)
    assert halves.duration == pytest.approx(aug.duration, rel=1e-9)

def test_decompose_conserves_the_whole_at_leaf_level_and_every_depth():
    ut = TemporalUnit(span=2, tempus='3/4',
                      prolatio=(2, -1, (2, (1, -1, 1)), 1),
                      beat='1/8', bpm=90)
    total = _mag(ut)
    assert total == Fraction(3, 2)          # from the authored spec
    assert ut.duration == pytest.approx(8.0, rel=1e-12)  # hand computation

    parts = decompose(ut)
    assert len(parts) == 6                   # leaves of the authored spec
    assert sum(_mag(u) for u in parts.seq) == total
    assert parts.duration == pytest.approx(ut.duration, rel=1e-9)
    _assert_tiles(parts)
    rest_units = [u for u in parts.seq
                  if all(h.is_rest for h in u.leaves)]
    assert len(rest_units) == 2              # the two -1s in the spec

    for d in range(0, ut.depth + 1):
        frontier = decompose(ut, depth=d)
        assert sum(_mag(u) for u in frontier.seq) == total
        assert frontier.duration == pytest.approx(ut.duration, rel=1e-9)

def test_fuse_conserves_real_time_and_metric_value():
    u1 = TemporalUnit(tempus='2/4', prolatio=(2, 1), beat='1/4', bpm=120)
    u2 = TemporalUnit(tempus=Meas(6, 20), prolatio=(1, 1, 1),
                      beat='1/4', bpm=120)
    u3 = TemporalUnit(tempus='3/8', prolatio='p', beat='1/4', bpm=120)
    same = fuse(u1, u2, u3)
    assert _mag(same) == _mag(u1) + _mag(u2) + _mag(u3)
    assert same.duration == pytest.approx(
        u1.duration + u2.duration + u3.duration, rel=1e-9)
    assert (same.beat, same.bpm) == (u1.beat, u1.bpm)

    m1 = TemporalUnit(tempus='2/4', prolatio=(2, 1), beat='1/4', bpm=120)
    m2 = TemporalUnit(tempus='7/8', prolatio='p', beat='1/8', bpm=70)
    m3 = TemporalUnit(span=2, tempus='3/4', prolatio=(1, 1, 1),
                      beat='1/4', bpm=90)
    mixed = fuse(m1, m2, m3)
    assert mixed.duration == pytest.approx(
        m1.duration + m2.duration + m3.duration, rel=1e-9)
    assert (mixed.beat, mixed.bpm) == (m1.beat, m1.bpm)

    back = fuse(decompose(m2))
    assert _mag(back) == _mag(m2)
    assert back.duration == pytest.approx(m2.duration, rel=1e-9)

def test_interleave_is_a_lossless_pure_zip():
    a = TemporalUnitSequence([
        TemporalUnit(tempus='1/4', prolatio=(1,), beat='1/4', bpm=60),
        TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=120),
        TemporalUnit(tempus='5/8', prolatio='p', beat='1/8', bpm=90),
    ])
    b = TemporalUnitSequence([
        TemporalUnit(tempus='3/4', prolatio=(2, 1), beat='1/4', bpm=100),
        TemporalUnit(tempus='7/8', prolatio='d', beat='1/8', bpm=70),
        TemporalUnit(tempus='1/2', prolatio=(1, -1), beat='1/4', bpm=80),
        TemporalUnit(tempus='4/4', prolatio='p', beat='1/4', bpm=60),
        TemporalUnit(tempus='6/8', prolatio=(3, 3), beat='1/8', bpm=110),
    ])

    def signature(seq):
        return Counter((_mag(u), u.beat, u.bpm) for u in seq.seq)

    expected_sig = signature(a) + signature(b)
    for x, y in ((a, b), (b, a)):
        r = interleave(x, y)
        assert len(r) == len(a) + len(b)
        assert r.duration == pytest.approx(a.duration + b.duration, rel=1e-9)
        assert signature(r) == expected_sig
        _assert_tiles(r)

    # operand isolation: mutate a result member; the operands must not move
    r = interleave(a, b)
    m = r.seq[0]
    m.subdivide(m.leaves.ids[0], (1, 1))
    assert len(a.seq[0]) == 1  # authored spec: prolatio (1,) is one event

def test_copy_paths_are_independent_of_the_source():
    ut = TemporalUnit(tempus='4/4', prolatio=(2, 1, 1), beat='1/4', bpm=60)

    c = ut.copy()
    c.subdivide(c.leaves.ids[0], (1, 1, 1))
    assert len(c) == 5
    assert len(ut) == 3

    dc = _copy.deepcopy(ut)
    dc.subdivide(dc.leaves.ids[0], (1, 1))
    assert len(ut) == 3

    r = ut * Fraction(3, 2)
    r.subdivide(r.leaves.ids[0], (1, 1))
    assert len(ut) == 3

    s = TemporalUnitSequence([ut])       # copies on entry
    sc = s.copy()
    sc.append(ut)
    assert len(s) == 1
    sc2 = s.copy()
    m = sc2[0]
    m.subdivide(m.leaves.ids[0], (1, 1))
    assert len(s[0]) == 3

    blk = TemporalBlock([ut], axis=-1, sort_rows=False)
    bc = blk.copy()
    bc.append(ut)
    assert blk.height == 1
    row = bc[0]
    row.subdivide(row.leaves.ids[0], (1, 1))
    assert len(blk[0]) == 3

    uc = CompositionalUnit(tempus='4/4', prolatio=(2, 1, 1), beat='1/4',
                           bpm=60, pfields={'amp': 0.125})
    cc = uc.copy()
    cc.set_pfields(cc.leaves.ids[0], amp=0.875)
    assert [e.pfields['amp'] for e in uc] == [0.125, 0.125, 0.125]

    # copy-on-entry: mutating the source AFTER construction must not reach
    # the container
    before = len(s[0])
    ut.subdivide(ut.leaves.ids[0], (1, 1, 1, 1))
    assert len(s[0]) == before
    assert len(blk[0]) == before

def test_block_axis_left_center_right_anchors_and_containment():
    def rows():
        return [
            TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=120),
            TemporalUnit(tempus='3/4', prolatio='p', beat='1/4', bpm=90),
            TemporalUnit(tempus='4/4', prolatio='d', beat='1/4', bpm=60),
        ]

    for axis in (-1, 0, 1):
        blk = TemporalBlock(rows(), axis=axis, sort_rows=False)
        assert blk.duration == pytest.approx(4.0, rel=1e-12)
        for row in blk:
            assert row.start >= blk.start - 1e-9
            assert row.end <= blk.end + 1e-9
            if axis == -1:
                assert row.start == pytest.approx(blk.start, abs=1e-12)
            elif axis == 1:
                assert row.end == pytest.approx(blk.end, rel=1e-9)
            else:
                assert row.start + row.duration / 2 == pytest.approx(
                    blk.start + blk.duration / 2, rel=1e-9)

def test_block_realigns_after_live_row_mutation_via_single_reader():
    short_u = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=120)
    long_u = TemporalUnit(tempus='4/4', prolatio='d', beat='1/4', bpm=60)
    extra = TemporalUnit(tempus='4/4', prolatio='d', beat='1/4', bpm=60)

    row_a = TemporalUnitSequence([short_u])
    row_b = TemporalUnitSequence([long_u])
    blk = TemporalBlock([row_a, row_b], axis=1, sort_rows=False)

    blk[0].append(extra)  # live row mutation; block-level mutators untouched

    assert blk.duration == pytest.approx(
        short_u.duration + extra.duration, rel=1e-9)          # 5.0 s
    assert blk[1].end == pytest.approx(blk.end, rel=1e-9)     # re-anchored
    assert blk[1].start == pytest.approx(
        (short_u.duration + extra.duration) - long_u.duration, rel=1e-9)

def test_block_events_flattening_is_conservative_and_voice_faithful():
    ut1 = TemporalUnit(tempus='4/4', prolatio='p', beat='1/4', bpm=60)
    ut2 = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=120)
    ut3 = TemporalUnit(tempus='3/4', prolatio=(2, -1), beat='1/4', bpm=90)
    ut4 = TemporalUnit(tempus='2/4', prolatio='d', beat='1/4', bpm=60)
    ut5 = TemporalUnit(tempus='3/8', prolatio='p', beat='1/8', bpm=90)

    inner_seq = TemporalUnitSequence([ut2, ut3])
    inner_blk = TemporalBlock([ut4, ut5], axis=-1, sort_rows=False)
    blk = TemporalBlock([ut1, inner_seq, inner_blk], axis=-1,
                        sort_rows=False)

    ev = blk.events
    assert len(ev) == 12
    starts = list(ev['start'])
    assert starts == sorted(starts)
    assert (ev['start'] >= blk.start - 1e-9).all()
    assert (ev['end'] <= blk.end + 1e-9).all()
    assert set(ev['voice']) == {'0', '1', '2.0', '2.1'}

    v0 = ev[ev['voice'] == '0']
    assert len(v0) == 4
    assert v0['duration'].sum() == pytest.approx(4.0, rel=1e-9)
    v1 = ev[ev['voice'] == '1']
    assert len(v1) == 4
    assert v1['duration'].sum() == pytest.approx(3.0, rel=1e-9)

def test_tempo_modulation_preserves_duration_and_spelling():
    ut = TemporalUnit(span=2, tempus=Meas(6, 20), prolatio=(2, 1, -1),
                      beat='1/8', bpm=90)
    for tb, tm in (('1/4', 60), ('1/8', 120), (Fraction(3, 8), 45),
                   ('1/2', 77.0)):
        r = modulate_tempo(ut, tb, tm)
        assert r.duration == pytest.approx(ut.duration, rel=1e-9)
        assert (r.beat, r.bpm) == (Fraction(tb), tm)

    plain = TemporalUnit(tempus=Meas(6, 20), prolatio=(1, 1),
                         beat='1/8', bpm=90)
    noop = modulate_tempo(plain, '1/8', 90)
    assert str(noop.tempus) == '6/20'
    assert noop.duration == pytest.approx(plain.duration, rel=1e-9)

    r2 = modulate_tempus(ut, 1, Meas('9/16'))
    assert str(r2.tempus) == '9/16'
    assert r2.duration == pytest.approx(ut.duration, rel=1e-9)

def test_uc_parameters_stay_attached_across_subdivide_and_scaling():
    amps = [0.25, 0.5, 0.75]

    uc = CompositionalUnit(tempus='4/4', prolatio=(2, 1, 1), beat='1/4',
                           bpm=60, pfields={'amp': 0.125, 'freq': 440.0})
    for lid, v in zip(uc.leaves.ids, amps):
        uc.set_pfields(lid, amp=v)
    assert [e.pfields['amp'] for e in uc] == amps

    for k in (Fraction(1, 1), Fraction(3, 2)):
        scaled = uc * k
        assert [e.pfields['amp'] for e in scaled] == amps
        assert [e.pfields['freq'] for e in scaled] == [440.0] * 3
        assert _mag(scaled) == k * _mag(uc)

    middle = uc.leaves.ids[1]
    uc.subdivide(middle, (1, 1))
    assert len(uc) == 4
    got = [e.pfields['amp'] for e in uc]
    assert got[0] == amps[0]          # untouched neighbour, before
    assert got[-1] == amps[2]         # untouched neighbour, after
    assert got[1] == amps[1] and got[2] == amps[1]  # cascade to children

def test_rt_and_pt_are_snapshots_not_live_views():
    ut = TemporalUnit(tempus='4/4', prolatio=(2, 1, 1), beat='1/4', bpm=60)
    r = ut.rt
    r.subdivide(r.leaf_nodes[0], (1, 1))
    assert len(ut) == 3                       # authored spec: 3 leaves
    assert len(ut.durations) == 3

    uc = CompositionalUnit(tempus='4/4', prolatio=(2, 1, 1), beat='1/4',
                           bpm=60, pfields={'amp': 0.125})
    p = uc.pt
    p.set_pfields(p.root, amp=999.0)
    assert [e.pfields['amp'] for e in uc] == [0.125, 0.125, 0.125]

def test_repeat_and_self_extend_algebra():
    u = TemporalUnit(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=90)
    assert u.duration == pytest.approx(2.0, rel=1e-12)  # hand computation

    rep = u.repeat(3)
    assert len(rep) == 3
    assert rep.duration == pytest.approx(3 * 2.0, rel=1e-9)
    _assert_tiles(rep)

    u.subdivide(u.leaves.ids[0], (1, 1))     # mutate the seed afterwards
    assert [len(m) for m in rep] == [3, 3, 3]

    s = TemporalUnitSequence([
        TemporalUnit(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=90),
        TemporalUnit(tempus='2/4', prolatio='d', beat='1/4', bpm=60),
    ])
    n0, d0 = len(s), s.duration
    s.extend(s, repeat=2)
    assert len(s) == 3 * n0
    assert s.duration == pytest.approx(3 * d0, rel=1e-9)
    _assert_tiles(s)
