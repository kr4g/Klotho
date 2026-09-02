"""Operator-algebra composition laws -- the RhythmTree verbs.

TEST-5, and the reason this chunk exists. Operator COMPOSITION has been the
named largest blind spot in this project and no test exercised it: every
operator test ran ONE verb.

Every assertion here is a PROPERTY derived from Haddad's definitions and
from the contracts stated in the source, BEFORE it was run -- so there is no
literal expected value an implementation could make agree falsely. Where an
invariant holds only on a stated domain (canonical forms, coprime tuples,
trees without rests), the restriction is derived from the definition and
named, never discovered by trying inputs until something passed.

The laws are run over PAIRS AND TRIPLES: flatten composed with the box
verbs, diminish then augment, scale after scale_tempus, evide on a scaled
tree, filtrage then the walk, fuse of segment outputs, and the closure of
the whole family under composition.


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

AUD-135 -- these citations name a FUNCTION, never a line number. They
used to carry ``file.py:NNNN``, and five of the fourteen had drifted off
the code they quote: the ``scale`` mutation said ``rhythm_tree.py:1629``
where the line lives at 1755, ``_respell`` said 1254 for 1343, ``segment``
said 1432 for 1517, ``_split_nodes`` said 1265 for 1342, and
``_process_child`` said 710 for 736. A citation that points at the wrong
line is worse than none: the next reader applies the mutation to whatever
happens to be there and concludes the register is fiction. The quoted line
plus its function is stable under every edit that does not touch the code
itself, and ``test_af35_guard_sweep.py`` now checks these citations resolve.

* ``test_flatten_is_a_projection_of_the_event_sequence``
      klotho/chronos/rhythm_trees/algorithms.py :: ``decompose()`` — change
      `s = (-1,) if md < 0 else (1,)` to `s = (1,)` (decompose stops
      carrying rest signs, ALG-1)

* ``test_box_verbs_factor_through_flatten``
      klotho/chronos/rhythm_trees/algorithms.py :: ``flatten()`` — change
      `return fuse(decompose(rt))` to `return fuse(decompose(rt)[::-1])`

* ``test_box_verbs_edit_the_decomposed_sequence``
      klotho/chronos/rhythm_trees/algorithms.py :: ``diminish()`` — change
      `survivors = [p for i, p in enumerate(parts) if i not in drop]` to
      `... if i in drop]`

* ``test_tempus_following_and_preserving_agree_projectively``
      klotho/chronos/rhythm_trees/rhythm_tree.py :: ``scale()`` — change
      `out[k] = out[k] * value` to `out[k] = abs(out[k]) * value` (circle
      scale silently un-rests the scaled event)

* ``test_diminish_then_augment_restores_the_event_sequence``
      klotho/chronos/rhythm_trees/algorithms.py :: ``_as_prolatio()`` —
      change `negative = (num < 0) != (den < 0)` to `negative = False`
      (reinserted rests come back as sounds)

* ``test_preserving_family_inverses_and_meter_invariance``
      klotho/chronos/rhythm_trees/rhythm_tree.py :: ``_respell()`` — change
      `S = tuple(int(d * den) for d in durations)` to `S = tuple(int(abs(d)
      * den) for d in durations)` (the respell drops rest signs)

* ``test_scale_tempus_commutes_and_composes_multiplicatively``
      klotho/chronos/rhythm_trees/algorithms.py :: ``scale_tempus()`` —
      change `meas=Meas(part.meas.numerator * num,` to
      `meas=Meas(part.meas.numerator + num,`

* ``test_augment_batch_equals_sequential_composition``
      klotho/chronos/rhythm_trees/algorithms.py :: ``augment()`` — change
      `for value, p in zip(adds, idx):` to `for off, (value, p) in
      enumerate(zip(adds, idx)):` and `pending.setdefault(p, [])` to
      `pending.setdefault(p + off, [])` (batch indices become
      order-dependent)

* ``test_evide_is_a_support_complement_involution``
      klotho/chronos/rhythm_trees/algorithms.py :: ``evide()`` — change
      `flipped = -int(abs(p)) if p > 0 else int(abs(p))` to `flipped =
      int(abs(p))`

* ``test_filtrage_rests_exactly_the_walked_positions``
      klotho/chronos/rhythm_trees/algorithms.py :: ``filtrage()`` — replace
      the two lines `if p < len(leaves): # CLIP...` /
      `out.make_rest(leaves[p])` with `out.make_rest(leaves[p %
      len(leaves)])` (the documented rejected WRAP alternative)

* ``test_segment_partitions_the_timeline``
      klotho/chronos/rhythm_trees/algorithms.py :: ``segment()`` — in the
      LEFT result change `meas=Meas(num * f.numerator, den *
      f.denominator),` to `meas=Meas(num * g.numerator, den *
      g.denominator),`

* ``test_fuse_of_segment_outputs_restores_or_splits_events``
      klotho/chronos/rhythm_trees/algorithms.py :: ``_split_nodes()`` —
      change `left.append(['leaf', sign * head, nd[2]])` to
      `left.append(['leaf', sign * head, False])` (the left piece of a cut
      leaf loses its inherited tie)

* ``test_operator_family_is_closed``
      klotho/chronos/rhythm_trees/rhythm_tree.py :: ``_process_child()`` —
      change `ratio = Fraction(s, div) * parent_ratio` to `ratio =
      Fraction(s, div + 1) * parent_ratio`
      CAVEAT: this mutation breaks RhythmTree's core duration arithmetic,
      so it reddens far more than closure alone. It proves the test runs
      and can fail; it is NOT a discriminating probe of the closure claim.

* ``test_a_leading_tie_operand_merges_with_its_new_predecessor``
      klotho/chronos/rhythm_trees/algorithms.py :: ``_fuse_parts()`` —
      change `s_out.append(float(w))` to `s_out.append(w)` (the fused
      spelling drops the tie marker)
"""

# FILE PREAMBLE shared by PROP-RT-01..14 (one file).
from fractions import Fraction
import pytest
from klotho.chronos.rhythm_trees import Meas, RhythmTree
from klotho.chronos.rhythm_trees.algorithms import (
    augment, decompose, diminish, evide, filtrage, flatten, fuse,
    scale_tempus, segment,
)

def leaf_flags(rt):
    return [(Fraction(rt[n]['metric_duration']), bool(rt[n].get('tied', False)))
            for n in rt.leaf_nodes]

def events(rt):
    seq, prev_sounds = [], False
    for d, tied in leaf_flags(rt):
        if d < 0:
            seq.append(d); prev_sounds = False
        elif tied and prev_sounds:
            seq[-1] += d
        else:
            seq.append(d); prev_sounds = True
    return seq

def total(rt):
    return sum(abs(d) for d, _ in leaf_flags(rt))

def boundaries(rt):
    acc, out = Fraction(0), [Fraction(0)]
    for d, _ in leaf_flags(rt):
        acc += abs(d); out.append(acc)
    return out

def support(rt):
    ivs, acc = [], Fraction(0)
    for d, _ in leaf_flags(rt):
        w = abs(d)
        if d > 0:
            if ivs and ivs[-1][1] == acc: ivs[-1] = (ivs[-1][0], acc + w)
            else: ivs.append((acc, acc + w))
        acc += w
    return ivs

def normalized(seq):
    tot = sum(abs(e) for e in seq)
    return [Fraction(e) / tot for e in seq]

def meas_pair(rt):
    return (rt.meas.numerator, rt.meas.denominator)

def signature(rt):
    return (rt.span, meas_pair(rt), rt.subdivisions)

GRID = {
    'flat':        lambda: RhythmTree(1, '4/4', (1, 1, 1, 1)),
    'haddad_B':    lambda: RhythmTree(1, '1/1', ((2, (2, 1)), 1, 2, 1)),
    'canonical_B': lambda: RhythmTree(1, '18/18', (4, 2, 3, 6, 3)),
    'rests':       lambda: RhythmTree(1, '3/4', (2, -1, 1)),
    'tied':        lambda: RhythmTree(1, '4/4', (1, 1.0, 1, 1)),
    'tie_x_group': lambda: RhythmTree(1, '2/4', ((1, (1, 1.0)), (1, (1.0, 1)))),
    'rest_branch': lambda: RhythmTree(1, '4/4', (1, (-2, (1, 1)), 1)),
    'rest_branch_tied': lambda: RhythmTree(1, '4/4', (1, (-2, (1.0, 1)), 1)),
    'unnorm_meas': lambda: RhythmTree(1, '15/20', (6, 3, 3, 3)),
    'span2':       lambda: RhythmTree(2, '3/4', (1, 2, (1, (1, 1)))),
    'complex':     lambda: RhythmTree(1, '7/5', (3, (2, (1, 1, 1)), -2)),
    'all_rest':    lambda: RhythmTree(1, '4/4', (-1, -2, -1)),
}
MULTI = [k for k in GRID]
FACTORS = [Fraction(1, 2), Fraction(1, 3), Fraction(2, 5), Fraction(3, 8),
           Fraction(3, 7), Fraction(5, 8), Fraction(2, 3)]

@pytest.mark.parametrize('key', GRID)
def test_flatten_is_a_projection_of_the_event_sequence(key):
    rt = GRID[key]()
    f1 = flatten(rt)
    assert events(f1) == events(rt)
    assert support(f1) == support(rt)
    assert total(f1) == total(rt)
    f2 = flatten(f1)
    assert signature(f2) == signature(f1)

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', GRID)
def test_box_verbs_factor_through_flatten(key):
    rt = GRID[key]()
    fl = flatten(rt)
    ev = events(rt)
    assert events(augment(fl, Fraction(3, 10), 0)) == \
        events(augment(rt, Fraction(3, 10), 0))
    assert events(scale_tempus(fl, Fraction(3, 2), 0)) == \
        events(scale_tempus(rt, Fraction(3, 2), 0))
    if len(ev) > 1:
        assert events(diminish(fl, (0,))) == events(diminish(rt, (0,)))

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', GRID)
def test_box_verbs_edit_the_decomposed_sequence(key):
    rt = GRID[key]()
    ev = events(rt)
    n = len(ev)

    assert events(diminish(rt, (0,))) == ev[1:]
    assert events(diminish(rt, (n - 1,))) == ev[:-1]
    if n > 2:
        assert events(diminish(rt, (0, n - 1))) == ev[1:-1]

    for pos in sorted({0, n // 2, n}):
        out = augment(rt, Fraction(3, 10), pos)
        assert events(out) == ev[:pos] + [Fraction(3, 10)] + ev[pos:]
    assert events(augment(rt, Fraction(-1, 8), 0)) == [Fraction(-1, 8)] + ev
    operand = RhythmTree(1, '2/8', (1, -1))
    assert events(augment(rt, operand, n)) == ev + events(operand)

    for pos in range(n):
        r = Fraction(5, 3)
        out = scale_tempus(rt, r, pos)
        want = list(ev)
        want[pos] = want[pos] * r
        assert events(out) == want

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', GRID)
def test_tempus_following_and_preserving_agree_projectively(key):
    rt = GRID[key]()
    ev = events(rt)
    n = len(ev)

    for pos in range(n + 1):
        for d in (Fraction(3, 10), Fraction(-1, 8)):
            box = augment(rt, d, pos)
            circ = GRID[key]()
            circ.insert(pos, d)
            assert normalized(events(box)) == normalized(events(circ))
            assert meas_pair(circ) == meas_pair(rt)
            assert circ.span == rt.span

    if n > 1:
        for pos in range(n):
            box = diminish(rt, (pos,))
            circ = GRID[key]()
            circ.extract(pos)
            assert normalized(events(box)) == normalized(events(circ))
            assert meas_pair(circ) == meas_pair(rt)

    for pos in range(n):
        r = Fraction(7, 4)
        box = scale_tempus(rt, r, pos)
        circ = GRID[key]()
        circ.scale(pos, r)
        assert normalized(events(box)) == normalized(events(circ))
        assert meas_pair(circ) == meas_pair(rt)

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', MULTI)
def test_diminish_then_augment_restores_the_event_sequence(key):
    rt = GRID[key]()
    ev = events(rt)
    for i in range(len(ev)):
        if len(ev) < 2:
            break
        out = augment(diminish(rt, (i,)), ev[i], i)
        assert events(out) == ev

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', MULTI)
def test_preserving_family_inverses_and_meter_invariance(key):
    rt = GRID[key]()
    ev = events(rt)

    c = GRID[key]()
    c.insert(1, Fraction(3, 16))
    c.extract(1)
    assert events(c) == ev
    assert meas_pair(c) == meas_pair(rt)
    assert c.span == rt.span

    c = GRID[key]()
    c.scale(0, Fraction(5, 3))
    c.scale(0, Fraction(3, 5))
    assert events(c) == ev
    assert meas_pair(c) == meas_pair(rt)

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', MULTI)
def test_scale_tempus_commutes_and_composes_multiplicatively(key):
    rt = GRID[key]()
    r1, r2 = Fraction(3, 2), Fraction(2, 5)
    a = scale_tempus(scale_tempus(rt, r1, 0), r2, 1)
    b = scale_tempus(scale_tempus(rt, r2, 1), r1, 0)
    batch = scale_tempus(rt, (r1, r2), (0, 1))
    assert events(a) == events(b) == events(batch)

    a = scale_tempus(scale_tempus(rt, Fraction(3, 2), 0), Fraction(4, 3), 0)
    b = scale_tempus(rt, Fraction(2, 1), 0)
    assert events(a) == events(b)

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', MULTI)
def test_augment_batch_equals_sequential_composition(key):
    rt = GRID[key]()
    n = len(events(rt))
    i, j = n - 1, 0
    va, vb = Fraction(1, 4), Fraction(-1, 8)
    batch = augment(rt, (va, vb), (i, j))
    seq = augment(augment(rt, va, i), vb, j)
    assert events(batch) == events(seq)

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', GRID)
def test_evide_is_a_support_complement_involution(key):
    rt = GRID[key]()
    tot = total(rt)
    e1 = evide(rt)

    comp, prev = [], Fraction(0)
    for a, b in support(rt):
        if a > prev:
            comp.append((prev, a))
        prev = b
    if prev < tot:
        comp.append((prev, tot))
    assert support(e1) == comp

    e2 = evide(e1)
    assert support(e2) == support(rt)
    assert [abs(d) for d, _ in leaf_flags(e1)] == \
           [abs(d) for d, _ in leaf_flags(rt)]
    assert meas_pair(e1) == meas_pair(rt) and e1.span == rt.span

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', GRID)
@pytest.mark.parametrize('series', [(2, 1, 3), (1, 1, 1), (3, 4)])
def test_filtrage_rests_exactly_the_walked_positions(key, series):
    rt = GRID[key]()
    f1 = filtrage(rt, series)

    walked, acc = {0}, 0
    for s in series:
        acc += s
        walked.add(acc)
    nleaves = len(leaf_flags(rt))
    walked = {p for p in walked if p < nleaves}

    signs_in = [d > 0 for d, _ in leaf_flags(rt)]
    signs_out = [d > 0 for d, _ in leaf_flags(f1)]
    assert signs_out == [signs_in[i] and i not in walked
                         for i in range(nleaves)]
    assert [abs(d) for d, _ in leaf_flags(f1)] == \
           [abs(d) for d, _ in leaf_flags(rt)]
    assert meas_pair(f1) == meas_pair(rt)

    f2 = filtrage(f1, series)
    assert leaf_flags(f2) == leaf_flags(f1)
    assert f2.subdivisions == f1.subdivisions

    if all(signs_in):
        hollowed = evide(f1)
        assert [d > 0 for d, _ in leaf_flags(hollowed)] == \
               [i in walked for i in range(nleaves)]

# requires the PROP-RT-01 preamble (same file)
@pytest.mark.parametrize('key', GRID)
def test_segment_partitions_the_timeline(key):
    rt = GRID[key]()
    tot = total(rt)
    for f in FACTORS:
        A, B = segment(rt, f)
        cut = f * tot
        assert total(A) == cut and total(B) == tot - cut
        assert A.span == rt.span and B.span == rt.span

        got = set(boundaries(A)) | {total(A) + x for x in boundaries(B)}
        assert got == set(boundaries(rt)) | {cut}

        shifted = [(a + cut, b + cut) for a, b in support(B)]
        merged = list(support(A))
        for iv in shifted:
            if merged and merged[-1][1] == iv[0]:
                merged[-1] = (merged[-1][0], iv[1])
            else:
                merged.append(iv)
        assert merged == support(rt)

# requires the PROP-RT-01 preamble (same file)
def _split_events_at(evseq, cut):
    acc, out = Fraction(0), []
    for e in evseq:
        w = abs(e)
        if acc < cut < acc + w:
            sgn = -1 if e < 0 else 1
            out.append(sgn * (cut - acc))
            out.append(sgn * (acc + w - cut))
        else:
            out.append(e)
        acc += w
    return out

@pytest.mark.parametrize('key', GRID)
def test_fuse_of_segment_outputs_restores_or_splits_events(key):
    rt = GRID[key]()
    tot = total(rt)
    bset = set(boundaries(rt))
    ev = events(rt)
    for f in FACTORS:
        cut = f * tot
        A, B = segment(rt, f)
        got = events(fuse([A, B]))
        want = ev if cut in bset else _split_events_at(ev, cut)
        assert got == want, (key, f)

# requires the PROP-RT-01 preamble (same file) plus this helper:
def assert_closed(rt, context=''):
    assert total(rt) == rt.meas.to_fraction() * rt.span, \
        f"{context}: sum|durations| != meas*span"
    acc = Fraction(0)
    for i, (d, _) in enumerate(leaf_flags(rt)):
        assert rt.onsets[i] == acc, f"{context}: onset[{i}] not a prefix sum"
        acc += abs(d)
    for n in rt.leaf_nodes:
        p = rt[n]['proportion']
        assert p != 0, f"{context}: zero proportion at leaf {n}"
        assert not (p < 0 and bool(rt[n].get('tied', False))), \
            f"{context}: tied rest at leaf {n}"
    rebuilt = RhythmTree(span=rt.span, meas=rt.meas,
                         subdivisions=rt.subdivisions)
    assert list(rebuilt.durations) == list(rt.durations), \
        f"{context}: constructor does not round-trip the tree's own S"

@pytest.mark.parametrize('key', GRID)
def test_operator_family_is_closed(key):
    rt = GRID[key]()
    assert_closed(rt, f'{key}: input')
    ev = events(rt)
    n = len(ev)

    outs = {'flatten': flatten(rt),
            'evide': evide(rt),
            'filtrage': filtrage(rt, (2, 1, 3)),
            'augment': augment(rt, Fraction(3, 10), 0),
            'scale_tempus': scale_tempus(rt, Fraction(3, 2), 0)}
    if n > 1:
        outs['diminish'] = diminish(rt, (0,))
        outs['dim_then_aug'] = augment(diminish(rt, (0,)), ev[0], 0)
    A, B = segment(rt, Fraction(2, 5))
    outs['segment_A'], outs['segment_B'] = A, B
    outs['fuse_of_segment'] = fuse([A, B])
    outs['evide_of_scale'] = evide(scale_tempus(rt, Fraction(3, 2), 0))
    outs['segment_of_augment'] = segment(
        augment(rt, Fraction(3, 10), 0), Fraction(1, 3))[0]
    outs['flatten_of_filtrage'] = fuse(decompose(filtrage(rt, (2, 1, 3))))
    for op, out in outs.items():
        assert_closed(out, f'{key}/{op}')

# requires the PROP-RT-01 preamble (same file)
def test_a_leading_tie_operand_merges_with_its_new_predecessor():
    src = RhythmTree(1, '4/4', (1, 1, 1, 1))
    ev = events(src)

    fundamental = RhythmTree(1, '1/4', (1.0,))
    out = augment(src, fundamental, 2)
    assert events(out) == [ev[0], ev[1] + Fraction(1, 4)] + ev[2:]
    out = augment(src, fundamental, 0)
    assert events(out) == [Fraction(1, 4)] + ev

    composed = RhythmTree(1, '2/4', (1.0, 1))
    out = augment(src, composed, 2)
    assert events(out) == [ev[0], ev[1] + Fraction(1, 4),
                           Fraction(1, 4)] + ev[2:]
    out = augment(src, composed, 0)
    assert events(out) == [Fraction(1, 4), Fraction(1, 4)] + ev
