"""
Test script for control envelope guardrails and slur-subdivide fix.

Run with:
    source ~/klotho-venv/bin/activate
    python scripts/test_envelope_guardrails.py
"""
import sys
import warnings

sys.path.insert(0, ".")

from klotho.thetos import CompositionalUnit as UC
from klotho.dynatos import Envelope
from klotho.chronos.temporal_units.algorithms import decompose, modulate_tempo

_passed = 0
_failed = 0


def _run(name, fn):
    global _passed, _failed
    try:
        fn()
        _passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        _failed += 1
        print(f"  FAIL  {name}: {e}")


# ---------------------------------------------------------------------------
# Overlap detection
# ---------------------------------------------------------------------------

def test_overlap_same_pfield_rejected():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    leaves = list(uc.rt.leaf_nodes)
    uc.apply_envelope(env, 'amp', node=leaves[:2], control=True)
    try:
        uc.apply_envelope(env, 'amp', node=leaves[1:3], control=True)
        raise AssertionError("Expected ValueError for overlapping control envelopes")
    except ValueError:
        pass


def test_overlap_different_pfield_allowed():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp', 'pan'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    uc.apply_envelope(env, 'pan', node=uc.rt.root, control=True)
    assert len(uc._control_envelopes) == 2


def test_overlap_disjoint_leaves_allowed():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    leaves = list(uc.rt.leaf_nodes)
    uc.apply_envelope(env, 'amp', node=leaves[:2], control=True)
    uc.apply_envelope(env, 'amp', node=leaves[2:], control=True)
    assert len(uc._control_envelopes) == 2


# ---------------------------------------------------------------------------
# Subdivide auto-heal
# ---------------------------------------------------------------------------

def test_subdivide_heals_control_envelope():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    assert len(uc._control_envelopes) == 1
    old_desc = uc._control_envelopes[0]
    assert old_desc["leaf_subset"] is None

    leaves_before = list(uc.rt.leaf_nodes)
    uc.subdivide(leaves_before[1], (1, 1, 1))

    assert len(uc._control_envelopes) == 1
    resolved = uc._resolve_control_envelope_leaves(uc._control_envelopes[0])
    assert len(resolved) == 6


def test_subdivide_heals_slur():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    leaves = list(uc.rt.leaf_nodes)
    uc.apply_slur(node=leaves[:3])
    assert len(uc._slur_specs) == 1

    uc.subdivide(leaves[1], (1, 1, 1))
    assert len(uc._slur_specs) == 1
    spec = list(uc._slur_specs.values())[0]
    assert len(spec['leaf_nodes']) == 5


def test_subdivide_slur_rest_filter():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    leaves = list(uc.rt.leaf_nodes)
    uc.apply_slur(node=leaves[:3])
    uc.subdivide(leaves[1], (-1, 1))
    found = False
    for spec in uc._slur_specs.values():
        if len(spec['leaf_nodes']) >= 2:
            found = True
            for n in spec['leaf_nodes']:
                assert uc._rt[n].get('proportion', 1) >= 0
    assert found or len(uc._slur_specs) == 0


# ---------------------------------------------------------------------------
# Make rest
# ---------------------------------------------------------------------------

def test_make_rest_filters_control_envelope():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    leaves = list(uc.rt.leaf_nodes)
    uc.make_rest(leaves[0])
    assert len(uc._control_envelopes) == 1
    resolved = uc._resolve_control_envelope_leaves(uc._control_envelopes[0])
    assert leaves[0] not in resolved
    assert len(resolved) == 3


def test_make_rest_removes_empty_envelope():
    uc = UC(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1], times=[1.0])
    leaves = list(uc.rt.leaf_nodes)
    uc.apply_envelope(env, 'amp', node=leaves, control=True)
    assert len(uc._control_envelopes) == 1
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        uc.make_rest(leaves[0])
        uc.make_rest(leaves[1])
    assert len(uc._control_envelopes) == 0


# ---------------------------------------------------------------------------
# Prune / remove_subtree
# ---------------------------------------------------------------------------

def test_remove_subtree_invalidates_envelope():
    uc = UC(tempus='4/4', prolatio=((2, (1, 1)), (2, (1, 1))), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    branches = list(uc.rt.at_depth(1))
    uc.apply_envelope(env, 'amp', node=branches[0], control=True)
    assert len(uc._control_envelopes) == 1
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        uc.remove_subtree(branches[0])
    assert len(uc._control_envelopes) == 0


def test_prune_leaf_in_slur():
    uc = UC(tempus='4/4', prolatio=((3, (1, 1, 1)), (2, (1, 1))), beat='1/4', bpm=120, pfields=['amp'])
    branch_leaves = list(uc.rt.subtree_leaves(list(uc.rt.at_depth(1))[0]))
    uc.apply_slur(node=branch_leaves)
    assert len(uc._slur_specs) == 1
    uc.prune(branch_leaves[1])
    for spec in uc._slur_specs.values():
        assert branch_leaves[1] not in spec['leaf_set']


# ---------------------------------------------------------------------------
# clear_parameters
# ---------------------------------------------------------------------------

def test_clear_all_clears_envelopes():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    uc.apply_slur(node=list(uc.rt.leaf_nodes))
    assert len(uc._control_envelopes) == 1
    assert len(uc._slur_specs) >= 1
    uc.clear_parameters()
    assert len(uc._control_envelopes) == 0
    assert len(uc._slur_specs) == 0


def test_clear_node_trims_envelope():
    uc = UC(tempus='4/4', prolatio=((2, (1, 1)), (2, (1, 1))), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    branches = list(uc.rt.at_depth(1))
    uc.apply_envelope(env, 'amp', node=branches[0], control=True)
    uc.clear_parameters(branches[0])
    assert len(uc._control_envelopes) == 0


# ---------------------------------------------------------------------------
# from_subtree / copy
# ---------------------------------------------------------------------------

def test_from_subtree_copies_contained_envelope():
    uc = UC(tempus='4/4', prolatio=((2, (1, 1)), (2, (1, 1))), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    branches = list(uc.rt.at_depth(1))
    uc.apply_envelope(env, 'amp', node=branches[0], control=True)
    new_uc = uc.from_subtree(branches[0])
    assert len(new_uc._control_envelopes) == 1


def test_from_subtree_drops_outside_envelope():
    uc = UC(tempus='4/4', prolatio=((2, (1, 1)), (2, (1, 1))), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    branches = list(uc.rt.at_depth(1))
    uc.apply_envelope(env, 'amp', node=branches[0], control=True)
    new_uc = uc.from_subtree(branches[1])
    assert len(new_uc._control_envelopes) == 0


def test_copy_preserves_envelopes():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    cp = uc.copy()
    assert len(cp._control_envelopes) == 1
    resolved = cp._resolve_control_envelope_leaves(cp._control_envelopes[0])
    assert len(resolved) == 4


# ---------------------------------------------------------------------------
# modulate_tempo
# ---------------------------------------------------------------------------

def test_modulate_tempo_copies_envelopes():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    new_uc = modulate_tempo(uc, '1/4', 60)
    assert len(new_uc._control_envelopes) == 1


# ---------------------------------------------------------------------------
# Decompose slur snipping
# ---------------------------------------------------------------------------

def test_decompose_snips_cross_boundary_slur():
    uc = UC(tempus='5/4', prolatio=((3, (1, 1, 1)), (2, (1, 1))), beat='1/4', bpm=120, pfields=['amp'])
    all_leaves = list(uc.rt.leaf_nodes)
    uc.apply_slur(node=all_leaves)
    uts = decompose(uc, depth=1)
    sub0 = uts.seq[0]
    sub1 = uts.seq[1]
    assert len(sub0._slur_specs) >= 1
    assert len(sub1._slur_specs) >= 1
    for spec in sub0._slur_specs.values():
        assert len(spec['leaf_nodes']) >= 2
    for spec in sub1._slur_specs.values():
        assert len(spec['leaf_nodes']) >= 2


def test_decompose_preserves_contained_slur():
    uc = UC(tempus='5/4', prolatio=((3, (1, 1, 1)), (2, (1, 1))), beat='1/4', bpm=120, pfields=['amp'])
    branch_leaves = list(uc.rt.subtree_leaves(list(uc.rt.at_depth(1))[0]))
    uc.apply_slur(node=branch_leaves)
    uts = decompose(uc, depth=1)
    sub0 = uts.seq[0]
    sub1 = uts.seq[1]
    assert len(sub0._slur_specs) >= 1
    assert len(sub1._slur_specs) == 0


def test_decompose_drops_slur_fragment_too_small():
    uc = UC(tempus='4/4', prolatio=((3, (1, 1, 1)), (1, (1,))), beat='1/4', bpm=120, pfields=['amp'])
    all_leaves = list(uc.rt.leaf_nodes)
    if len(all_leaves) >= 4:
        uc.apply_slur(node=all_leaves)
        uts = decompose(uc, depth=1)
        sub1 = uts.seq[1]
        sub1_leaves = list(sub1.rt.leaf_nodes)
        if len(sub1_leaves) < 2:
            assert len(sub1._slur_specs) == 0


# ---------------------------------------------------------------------------
# Lazy time derivation
# ---------------------------------------------------------------------------

def test_tempo_change_updates_envelope_times():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    resolved_before = uc.resolved_control_envelopes()
    span_before = resolved_before[0]["time_span"]

    uc._bpm = 60
    uc._invalidate_timing_cache()

    resolved_after = uc.resolved_control_envelopes()
    span_after = resolved_after[0]["time_span"]
    assert span_after[1] > span_before[1]


# ===========================================================================
# Complex RT / edge-case tests
# ===========================================================================

# ---------------------------------------------------------------------------
# Deep nested RT structures
# ---------------------------------------------------------------------------

def test_deep_nested_rt_envelope_on_inner_node():
    """Chronostasis-style: 3-limb RT with 4+6+4 leaves.  Env on middle limb only."""
    S = ((3, (1,) * 4), (4, (1,) * 6), (3, (1,) * 4))
    uc = UC(tempus='10/16', prolatio=S, beat='1/16', bpm=140, pfields=['amp'])
    limbs = list(uc.rt.at_depth(1))
    mid_limb = limbs[1]
    mid_leaves = list(uc.rt.subtree_leaves(mid_limb))
    assert len(mid_leaves) == 6
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=mid_limb, control=True)
    desc = uc._control_envelopes[0]
    assert desc["anchor_node"] == mid_limb
    assert desc["leaf_subset"] is None
    resolved = uc._resolve_control_envelope_leaves(desc)
    assert set(resolved) == set(mid_leaves)

    other_leaves = list(uc.rt.subtree_leaves(limbs[0]))
    uc.make_rest(other_leaves[0])
    assert len(uc._resolve_control_envelope_leaves(desc)) == 6


def test_polyriddim_deep_rt_subdivide_and_env():
    """Polyriddim-style deeply nested RT.  Env on root, then subdivide a deep leaf."""
    S = (
        (1, ((6, (1,) * 7), (8, (1,) * 11))),
        (1, ((6, ((3, (1,) * 4), 1, (2, (1,) * 3))), (8, ((3, (1,) * 4), (3, (1,) * 4), (5, (1,) * 5))))),
    )
    uc = UC(tempus='28/16', prolatio=S, beat='1/16', bpm=122, pfields=['amp', 'freq'])
    total_leaves_before = len(list(uc.rt.leaf_nodes))
    env = Envelope([0.2, 0.9, 0.4], times=[0.3, 0.7])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)

    leaves = list(uc.rt.leaf_nodes)
    uc.subdivide(leaves[-1], (1, 1, 1))
    total_leaves_after = len(list(uc.rt.leaf_nodes))
    assert total_leaves_after == total_leaves_before + 2
    resolved = uc._resolve_control_envelope_leaves(uc._control_envelopes[0])
    assert len(resolved) == total_leaves_after


def test_entertain_me_style_two_limb_decompose_with_envs():
    """Entertain-me style: two asymmetric limbs, env on each, decompose at depth=1."""
    S = ((20, ((5, (1,) * 5),) * 4), (15, ((3, (1,) * 3),) * 5))
    uc = UC(tempus='36/16', prolatio=S, beat='1/8', bpm=184, pfields=['amp'])
    limbs = list(uc.rt.at_depth(1))
    env_a = Envelope([0, 1, 0], times=[0.5, 0.5])
    env_b = Envelope([1, 0], times=[1.0])
    uc.apply_envelope(env_a, 'amp', node=limbs[0], control=True)
    uc.apply_envelope(env_b, 'amp', node=limbs[1], control=True)
    assert len(uc._control_envelopes) == 2

    uts = decompose(uc, depth=1)
    sub0, sub1 = uts.seq[0], uts.seq[1]
    assert len(sub0._control_envelopes) == 1
    assert len(sub1._control_envelopes) == 1


# ---------------------------------------------------------------------------
# Per-node scope envelopes
# ---------------------------------------------------------------------------

def test_per_node_scope_creates_multiple_descriptors():
    """per_node scope: each depth-1 node gets its own independent envelope."""
    S = ((3, (1, 1, 1)), (2, (1, 1)), (4, (1, 1, 1, 1)))
    uc = UC(tempus='9/8', prolatio=S, beat='1/8', bpm=100, pfields=['amp'])
    limbs = list(uc.rt.at_depth(1))
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=limbs, scope="per_node", control=True)
    assert len(uc._control_envelopes) == 3
    all_resolved = set()
    for desc in uc._control_envelopes:
        leaves = uc._resolve_control_envelope_leaves(desc)
        all_resolved.update(leaves)
    assert all_resolved == set(uc.rt.leaf_nodes)


def test_per_node_envelope_subdivide_one_branch():
    """per_node envelopes on 3 branches; subdivide a leaf in the middle branch."""
    S = ((2, (1, 1)), (2, (1, 1)), (2, (1, 1)))
    uc = UC(tempus='6/8', prolatio=S, beat='1/8', bpm=120, pfields=['amp'])
    limbs = list(uc.rt.at_depth(1))
    env = Envelope([0, 1], times=[1.0])
    uc.apply_envelope(env, 'amp', node=limbs, scope="per_node", control=True)
    assert len(uc._control_envelopes) == 3

    mid_leaves = list(uc.rt.subtree_leaves(limbs[1]))
    uc.subdivide(mid_leaves[0], (1, 1))

    for desc in uc._control_envelopes:
        leaves = uc._resolve_control_envelope_leaves(desc)
        assert len(leaves) >= 2


# ---------------------------------------------------------------------------
# Offset/take (explicit leaf_subset)
# ---------------------------------------------------------------------------

def test_offset_take_creates_leaf_subset():
    """offset/take restricts to a subset → leaf_subset is not None."""
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, offset=1, take=2, control=True)
    desc = uc._control_envelopes[0]
    assert desc["leaf_subset"] is not None
    assert len(desc["leaf_subset"]) == 2
    resolved = uc._resolve_control_envelope_leaves(desc)
    assert len(resolved) == 2


def test_offset_take_subdivide_inside_subset():
    """Subdivide a leaf that IS in the offset/take subset."""
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    leaves = list(uc.rt.leaf_nodes)
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, offset=1, take=2, control=True)
    target_leaf = leaves[1]
    uc.subdivide(target_leaf, (1, 1, 1))
    desc = uc._control_envelopes[0]
    resolved = uc._resolve_control_envelope_leaves(desc)
    assert len(resolved) == 4
    assert target_leaf not in resolved


def test_offset_take_subdivide_outside_subset():
    """Subdivide a leaf that is NOT in the offset/take subset — no change."""
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    leaves = list(uc.rt.leaf_nodes)
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, offset=1, take=2, control=True)
    uc.subdivide(leaves[0], (1, 1, 1))
    desc = uc._control_envelopes[0]
    resolved = uc._resolve_control_envelope_leaves(desc)
    assert len(resolved) == 2


# ---------------------------------------------------------------------------
# Chained mutations
# ---------------------------------------------------------------------------

def test_subdivide_then_make_rest_in_envelope():
    """Subdivide a leaf under an env, then rest one of the new children."""
    S = ((3, (1, 1, 1)), (4, (1, 1, 1, 1)))
    uc = UC(tempus='7/8', prolatio=S, beat='1/8', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0.5], times=[0.4, 0.6])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    total_before = len(list(uc.rt.leaf_nodes))

    leaves = list(uc.rt.leaf_nodes)
    uc.subdivide(leaves[0], (1, 1, 1))
    new_children = list(uc.rt.subtree_leaves(leaves[0]))
    uc.make_rest(new_children[1])

    resolved = uc._resolve_control_envelope_leaves(uc._control_envelopes[0])
    assert new_children[1] not in resolved
    assert len(resolved) == total_before + 2 - 1


def test_multiple_subdivides_then_copy():
    """Subdivide two different leaves, then copy.  Verify envs survive."""
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    leaves = list(uc.rt.leaf_nodes)
    uc.subdivide(leaves[0], (1, 1))
    leaves2 = list(uc.rt.leaf_nodes)
    uc.subdivide(leaves2[-1], (1, 1, 1))

    total = len(list(uc.rt.leaf_nodes))
    cp = uc.copy()
    cp_resolved = cp._resolve_control_envelope_leaves(cp._control_envelopes[0])
    assert len(cp_resolved) == total


def test_subdivide_slur_then_rest_splits_slur():
    """Subdivide a slurred leaf into (1, -1, 1), then rest another slurred leaf.
    The slur should survive as partitioned segments."""
    S = ((2, (1, 1, 1, 1, 1)), (3, (1, 1, 1)))
    uc = UC(tempus='5/8', prolatio=S, beat='1/8', bpm=120, pfields=['amp'])
    left_leaves = list(uc.rt.subtree_leaves(list(uc.rt.at_depth(1))[0]))
    assert len(left_leaves) == 5
    uc.apply_slur(node=left_leaves)

    uc.subdivide(left_leaves[2], (1, -1, 1))
    new_sub_leaves = list(uc.rt.subtree_leaves(left_leaves[2]))
    sounding_sub = [n for n in new_sub_leaves if uc._rt[n].get('proportion', 1) >= 0]
    assert len(sounding_sub) == 2

    total_slur_leaves = 0
    for spec in uc._slur_specs.values():
        for n in spec['leaf_nodes']:
            assert uc._rt[n].get('proportion', 1) >= 0
        total_slur_leaves += len(spec['leaf_nodes'])
    assert total_slur_leaves >= 2


# ---------------------------------------------------------------------------
# Sparsify interaction
# ---------------------------------------------------------------------------

def test_sparsify_filters_envelope_leaves():
    """Sparsify (which calls make_rest internally) should filter env leaves."""
    import numpy as np
    np.random.seed(99)
    uc = UC(tempus='4/4', prolatio=(1,) * 8, beat='1/8', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    uc.sparsify(0.5)
    resolved = uc._resolve_control_envelope_leaves(uc._control_envelopes[0])
    for n in resolved:
        assert uc._rt[n].get('proportion', 1) >= 0
    rested = [n for n in uc.rt.leaf_nodes if uc._rt[n].get('proportion', 1) < 0]
    assert len(rested) > 0
    assert len(resolved) + len(rested) == 8


# ---------------------------------------------------------------------------
# Bake vs control: bake doesn't create descriptors
# ---------------------------------------------------------------------------

def test_bake_mode_no_descriptor():
    """control=False should bake values into PT but create no descriptor."""
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=False)
    assert len(uc._control_envelopes) == 0
    leaves = list(uc.rt.leaf_nodes)
    vals = [uc.get_pfield(n, 'amp') for n in leaves]
    assert any(v != 0.0 for v in vals)


def test_bake_then_control_same_pfield_rejected():
    """Bake first (no descriptor), then control on same nodes — should succeed
    since bake doesn't register a descriptor.  Then a second control should fail."""
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=False)
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    assert len(uc._control_envelopes) == 1
    try:
        uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Multi-pfield envelopes
# ---------------------------------------------------------------------------

def test_multi_pfield_single_envelope():
    """One envelope controlling both amp and pan simultaneously."""
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp', 'pan'])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, ['amp', 'pan'], node=uc.rt.root, control=True)
    assert len(uc._control_envelopes) == 1
    desc = uc._control_envelopes[0]
    assert set(desc["pfields"]) == {'amp', 'pan'}

    try:
        uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
        raise AssertionError("Expected ValueError: amp already covered")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# remove_subtree on sibling preserves other branch env
# ---------------------------------------------------------------------------

def test_remove_sibling_preserves_other_env():
    """Env on branch A, remove branch B entirely — A's env should survive."""
    S = ((3, (1, 1, 1)), (4, (1, 1, 1, 1)), (2, (1, 1)))
    uc = UC(tempus='9/8', prolatio=S, beat='1/8', bpm=120, pfields=['amp'])
    limbs = list(uc.rt.at_depth(1))
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=limbs[0], control=True)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        uc.remove_subtree(limbs[2])
    assert len(uc._control_envelopes) == 1
    resolved = uc._resolve_control_envelope_leaves(uc._control_envelopes[0])
    assert len(resolved) == 3


# ---------------------------------------------------------------------------
# Decompose at depth=2 (deeper decomposition)
# ---------------------------------------------------------------------------

def test_decompose_depth2_with_slur():
    """Decompose at depth=2 on a 3-level deep tree. Slur spans depth-2 nodes."""
    S = ((3, ((1, (1, 1)), (1, (1, 1)), (1, (1, 1)))),
         (2, ((1, (1, 1)), (1, (1, 1)))))
    uc = UC(tempus='5/4', prolatio=S, beat='1/4', bpm=120, pfields=['amp'])
    all_leaves = list(uc.rt.leaf_nodes)
    assert len(all_leaves) == 10
    uc.apply_slur(node=all_leaves)

    uts = decompose(uc, depth=2)
    total_slurred = 0
    for sub in uts:
        sub_leaves = list(sub.rt.leaf_nodes)
        if len(sub._slur_specs) > 0:
            for spec in sub._slur_specs.values():
                assert len(spec['leaf_nodes']) >= 2
                total_slurred += len(spec['leaf_nodes'])
    assert total_slurred >= 2


# ---------------------------------------------------------------------------
# Envelope on single leaf (degenerate case)
# ---------------------------------------------------------------------------

def test_envelope_on_single_leaf():
    """Env on a single leaf — valid (anchor = leaf, leaf_subset = None or {leaf})."""
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    leaves = list(uc.rt.leaf_nodes)
    env = Envelope([0, 1], times=[1.0])
    uc.apply_envelope(env, 'amp', node=leaves[2], control=True)
    desc = uc._control_envelopes[0]
    resolved = uc._resolve_control_envelope_leaves(desc)
    assert resolved == [leaves[2]]

    uc.make_rest(leaves[2])
    assert len(uc._control_envelopes) == 0


# ---------------------------------------------------------------------------
# Rest nodes in initial selection are skipped
# ---------------------------------------------------------------------------

def test_env_on_selection_with_preexisting_rests():
    """Apply env to a range that already contains rests — only sounding nodes get baked."""
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, pfields=['amp'])
    leaves = list(uc.rt.leaf_nodes)
    uc.make_rest(leaves[1])
    env = Envelope([0, 1, 0], times=[0.5, 0.5])
    uc.apply_envelope(env, 'amp', node=uc.rt.root, control=True)
    resolved = uc._resolve_control_envelope_leaves(uc._control_envelopes[0])
    assert len(resolved) == 3
    assert leaves[1] not in resolved


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        ("overlap_same_pfield_rejected", test_overlap_same_pfield_rejected),
        ("overlap_different_pfield_allowed", test_overlap_different_pfield_allowed),
        ("overlap_disjoint_leaves_allowed", test_overlap_disjoint_leaves_allowed),
        ("subdivide_heals_control_envelope", test_subdivide_heals_control_envelope),
        ("subdivide_heals_slur", test_subdivide_heals_slur),
        ("subdivide_slur_rest_filter", test_subdivide_slur_rest_filter),
        ("make_rest_filters_control_envelope", test_make_rest_filters_control_envelope),
        ("make_rest_removes_empty_envelope", test_make_rest_removes_empty_envelope),
        ("remove_subtree_invalidates_envelope", test_remove_subtree_invalidates_envelope),
        ("prune_leaf_in_slur", test_prune_leaf_in_slur),
        ("clear_all_clears_envelopes", test_clear_all_clears_envelopes),
        ("clear_node_trims_envelope", test_clear_node_trims_envelope),
        ("from_subtree_copies_contained_envelope", test_from_subtree_copies_contained_envelope),
        ("from_subtree_drops_outside_envelope", test_from_subtree_drops_outside_envelope),
        ("copy_preserves_envelopes", test_copy_preserves_envelopes),
        ("modulate_tempo_copies_envelopes", test_modulate_tempo_copies_envelopes),
        ("decompose_snips_cross_boundary_slur", test_decompose_snips_cross_boundary_slur),
        ("decompose_preserves_contained_slur", test_decompose_preserves_contained_slur),
        ("decompose_drops_slur_fragment_too_small", test_decompose_drops_slur_fragment_too_small),
        ("tempo_change_updates_envelope_times", test_tempo_change_updates_envelope_times),
        # complex RT / edge-case tests
        ("deep_nested_rt_envelope_on_inner_node", test_deep_nested_rt_envelope_on_inner_node),
        ("polyriddim_deep_rt_subdivide_and_env", test_polyriddim_deep_rt_subdivide_and_env),
        ("entertain_me_style_two_limb_decompose_with_envs", test_entertain_me_style_two_limb_decompose_with_envs),
        ("per_node_scope_creates_multiple_descriptors", test_per_node_scope_creates_multiple_descriptors),
        ("per_node_envelope_subdivide_one_branch", test_per_node_envelope_subdivide_one_branch),
        ("offset_take_creates_leaf_subset", test_offset_take_creates_leaf_subset),
        ("offset_take_subdivide_inside_subset", test_offset_take_subdivide_inside_subset),
        ("offset_take_subdivide_outside_subset", test_offset_take_subdivide_outside_subset),
        ("subdivide_then_make_rest_in_envelope", test_subdivide_then_make_rest_in_envelope),
        ("multiple_subdivides_then_copy", test_multiple_subdivides_then_copy),
        ("subdivide_slur_then_rest_splits_slur", test_subdivide_slur_then_rest_splits_slur),
        ("sparsify_filters_envelope_leaves", test_sparsify_filters_envelope_leaves),
        ("bake_mode_no_descriptor", test_bake_mode_no_descriptor),
        ("bake_then_control_same_pfield_rejected", test_bake_then_control_same_pfield_rejected),
        ("multi_pfield_single_envelope", test_multi_pfield_single_envelope),
        ("remove_sibling_preserves_other_env", test_remove_sibling_preserves_other_env),
        ("decompose_depth2_with_slur", test_decompose_depth2_with_slur),
        ("envelope_on_single_leaf", test_envelope_on_single_leaf),
        ("env_on_selection_with_preexisting_rests", test_env_on_selection_with_preexisting_rests),
    ]

    print(f"\nRunning {len(tests)} envelope guardrail tests...\n")
    for name, fn in tests:
        _run(name, fn)
    print(f"\n{'=' * 50}")
    print(f"  {_passed} passed, {_failed} failed out of {_passed + _failed}")
    print(f"{'=' * 50}\n")
    sys.exit(1 if _failed else 0)
