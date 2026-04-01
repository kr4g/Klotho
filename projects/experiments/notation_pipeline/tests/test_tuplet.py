"""Tests for tuplet detection."""

import pytest
from fractions import Fraction

from klotho.chronos import RhythmTree as RT, Meas

from notation_pipeline.core.tuplet import (
    largest_power_of_2_leq,
    _node_is_tuplet,
    _tuplet_inner_note_type,
    collect_tuplets,
    get_tuplet_scale_for_leaf,
)
from notation_pipeline.models import NoteType, TupletBracket


def _detect_at_root(rt):
    """Helper: detect tuplet at root node (no ancestor context)."""
    result = _node_is_tuplet(rt.root, rt, Fraction(1))
    if result is None:
        return None
    actual, normal = result
    parent_dur = abs(Fraction(rt[rt.root].get('metric_duration', 0)))
    inner_note_type = _tuplet_inner_note_type(parent_dur, normal)
    return TupletBracket(
        actual=actual, normal=normal, inner_note_type=inner_note_type,
        event_indices=[], group_node_id=rt.root,
    )


class TestLargestPowerOf2:
    @pytest.mark.parametrize("n, expected", [
        (1, 1), (2, 2), (3, 2), (4, 4), (5, 4), (6, 4), (7, 4), (8, 8),
        (9, 8), (10, 8), (15, 8), (16, 16),
    ])
    def test_values(self, n, expected):
        assert largest_power_of_2_leq(n) == expected


class TestDetectTuplet:
    def test_binary_no_tuplet(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1, 1))
        bracket = _detect_at_root(rt)
        assert bracket is None

    def test_triplet_in_4_4(self):
        # 3 children in 4/4: each gets 1/3 of whole note (not engravable) -> tuplet
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        bracket = _detect_at_root(rt)
        assert bracket is not None
        assert bracket.actual == 3
        assert bracket.normal == 2

    def test_quintuplet(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1, 1, 1))
        bracket = _detect_at_root(rt)
        assert bracket is not None
        assert bracket.actual == 5
        assert bracket.normal == 4

    def test_septuplet(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1, 1, 1, 1, 1))
        bracket = _detect_at_root(rt)
        assert bracket is not None
        assert bracket.actual == 7
        assert bracket.normal == 4

    # --- Meter-aware: NOT tuplets ---
    def test_3_4_three_quarters_not_tuplet(self):
        # 3/4 with (1,1,1): each child = 1/4 (quarter) -> natural, NOT a tuplet
        rt = RT(meas='3/4', subdivisions=(1, 1, 1))
        bracket = _detect_at_root(rt)
        assert bracket is None

    def test_6_8_compound_not_tuplet(self):
        # 6/8 with ((1,(1,1,1)), (1,(1,1,1))): inner groups have 3 children
        # each child = 1/8 (eighth) -> natural compound subdivision, NOT a tuplet
        rt = RT(meas='6/8', subdivisions=((1, (1, 1, 1)), (1, (1, 1, 1))))
        tuplets, _ = collect_tuplets(rt)
        assert len(tuplets) == 0

    def test_3_8_three_eighths_not_tuplet(self):
        rt = RT(meas='3/8', subdivisions=(1, 1, 1))
        bracket = _detect_at_root(rt)
        assert bracket is None

    def test_6_4_not_tuplet(self):
        # 6/4 with (1,1,1,1,1,1): each child = 1/4 (quarter) -> engravable
        rt = RT(meas='6/4', subdivisions=(1, 1, 1, 1, 1, 1))
        bracket = _detect_at_root(rt)
        assert bracket is None


class TestCollectTuplets:
    def test_no_tuplets(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1, 1))
        tuplets, _ = collect_tuplets(rt)
        assert tuplets == []

    def test_flat_triplet(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        tuplets, _ = collect_tuplets(rt)
        assert len(tuplets) == 1
        assert tuplets[0].actual == 3

    def test_nested_triplet_in_binary(self):
        # Binary top level with triplet inside first beat
        rt = RT(meas='4/4', subdivisions=((1, (1, 1, 1)), (1, (1, 1))))
        tuplets, _ = collect_tuplets(rt)
        triplets = [t for t in tuplets if t.actual == 3]
        assert len(triplets) == 1

    def test_nested_both_tuplets(self):
        # quintuplet + triplet in separate groups under binary root
        rt = RT(meas='4/4', subdivisions=((1, (1, 1, 1, 1, 1)), (1, (1, 1, 1))))
        tuplets, _ = collect_tuplets(rt)
        actuals = sorted([t.actual for t in tuplets])
        assert 3 in actuals
        assert 5 in actuals

    def test_compound_6_8_no_tuplets(self):
        rt = RT(meas='6/8', subdivisions=((1, (1, 1, 1)), (1, (1, 1, 1))))
        tuplets, _ = collect_tuplets(rt)
        assert tuplets == []

    # --- New: proportion-based tuplet detection ---
    def test_unequal_binary_proportion_tuplet(self):
        """Binary child count (4) but unequal proportions summing to 10 -> 10:8 tuplet."""
        rt = RT(meas='4/4', subdivisions=((1, (1, 2, 3, 4)), (1, (4, 3, 2, 1))))
        tuplets, _ = collect_tuplets(rt)
        # Two inner groups each have proportion sum 10
        prop_tuplets = [t for t in tuplets if t.actual == 10]
        assert len(prop_tuplets) == 2
        for t in prop_tuplets:
            assert t.normal == 8

    def test_unequal_nonbinary_proportion_tuplet(self):
        """Non-binary child count with unequal proportions: (3,5,3) -> 11:8."""
        rt = RT(meas='3/4', subdivisions=((3, (1, 1)), (5, (1, 1)), (3, (1, 1))))
        tuplets, _ = collect_tuplets(rt)
        root_tuplets = [t for t in tuplets if t.group_node_id == rt.root]
        assert len(root_tuplets) == 1
        assert root_tuplets[0].actual == 11
        assert root_tuplets[0].normal == 8

    def test_ancestor_scale_prevents_false_inner_tuplet(self):
        """Inner node with P!=pow2 should NOT be a tuplet if ancestor already normalises."""
        rt = RT(meas='3/4', subdivisions=(
            (3, (1, (2, (-1, 1, 1)))),
            (5, (1, -2, (1, (1, 1)), 1)),
            (3, (-1, 1, 1)),
        ))
        tuplets, _ = collect_tuplets(rt)
        assert len(tuplets) == 1
        assert tuplets[0].actual == 11
        assert tuplets[0].normal == 8


class TestTupletScaleForLeaf:
    def test_no_tuplet(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1, 1))
        for leaf in rt.leaf_nodes:
            assert get_tuplet_scale_for_leaf(leaf, rt) is None

    def test_triplet_in_4_4(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        _, cache = collect_tuplets(rt)
        for leaf in rt.leaf_nodes:
            scale = get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=cache)
            assert scale == Fraction(2, 3)

    def test_quintuplet(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1, 1, 1))
        _, cache = collect_tuplets(rt)
        for leaf in rt.leaf_nodes:
            scale = get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=cache)
            assert scale == Fraction(4, 5)

    def test_nested_only_inner_tuplet(self):
        # Binary outer, triplet inner on first beat
        rt = RT(meas='4/4', subdivisions=((1, (1, 1, 1)), (1, (1, 1))))
        _, cache = collect_tuplets(rt)
        leaves = list(rt.leaf_nodes)
        # First 3 leaves are in the triplet group
        for leaf in leaves[:3]:
            scale = get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=cache)
            assert scale == Fraction(2, 3)
        # Last 2 leaves are in the binary group
        for leaf in leaves[3:]:
            scale = get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=cache)
            assert scale is None

    def test_3_4_no_tuplet_scale(self):
        # 3/4 with (1,1,1) is NOT a tuplet -> no scale
        rt = RT(meas='3/4', subdivisions=(1, 1, 1))
        _, cache = collect_tuplets(rt)
        for leaf in rt.leaf_nodes:
            assert get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=cache) is None

    def test_6_8_no_tuplet_scale(self):
        rt = RT(meas='6/8', subdivisions=((1, (1, 1, 1)), (1, (1, 1, 1))))
        _, cache = collect_tuplets(rt)
        for leaf in rt.leaf_nodes:
            assert get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=cache) is None

    # --- New: proportion-based scale ---
    def test_unequal_proportion_scale(self):
        """Leaves inside a (1,2,3,4) group get 4/5 scale from 10:8 tuplet."""
        rt = RT(meas='4/4', subdivisions=((1, (1, 2, 3, 4)), (1, (1, 1))))
        _, cache = collect_tuplets(rt)
        leaves = list(rt.leaf_nodes)
        # First 4 leaves in the unequal group
        for leaf in leaves[:4]:
            scale = get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=cache)
            assert scale == Fraction(4, 5), f"leaf {leaf} scale={scale}"
        # Last 2 leaves in the binary group
        for leaf in leaves[4:]:
            scale = get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=cache)
            assert scale is None

    def test_11_8_scale_in_simple_triple(self):
        """Leaves under 11:8 tuplet in 3/4 (simple triple) get binary-context scale."""
        from notation_pipeline.core.duration import classify_duration
        rt = RT(meas='3/4', subdivisions=(
            (3, (1, (2, (-1, 1, 1)))),
            (5, (1, -2, (1, (1, 1)), 1)),
            (3, (-1, 1, 1)),
        ))
        _, cache = collect_tuplets(rt)
        for leaf in rt.leaf_nodes:
            dur = abs(Fraction(rt[leaf]['metric_duration']))
            scale = get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=cache)
            assert scale == Fraction(8, 11)
            result = classify_duration(dur, tuplet_scale=scale)
            assert result is not None, f"leaf {leaf} dur={dur} scale={scale} not engravable"


class TestSplitInTupletContext:
    def test_single_engravable_returns_one_segment(self):
        from notation_pipeline.pipeline import _split_in_tuplet_context

        tuplet_scale = Fraction(4, 7)
        dur = Fraction(2, 7)
        assert _split_in_tuplet_context(dur, tuplet_scale, 2) == [dur]
