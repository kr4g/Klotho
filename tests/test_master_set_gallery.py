"""Tests for the four new N-D master sets:
twisted_asterisk_s2, antiprism_3, halton_asterisk, wheel_nd.
"""
from collections import defaultdict
from itertools import combinations

import numpy as np
import pytest

from klotho.tonos.systems.combination_product_sets import (
    CombinationProductSet,
    MasterSet,
    MASTER_SETS,
)


NEW_MASTER_SETS = (
    'twisted_asterisk_s2',
    'antiprism_3',
    'halton_asterisk',
    'wheel_nd',
)

EXPECTED_PROPERTIES = {
    'twisted_asterisk_s2': {'n_factors': 6, 'ambient_dim': 3},
    'antiprism_3':         {'n_factors': 6, 'ambient_dim': 3},
    'halton_asterisk':     {'n_factors': 6, 'ambient_dim': 5},
    'wheel_nd':            {'n_factors': 6, 'ambient_dim': 5},
}

SIX_FACTORS = (1, 3, 5, 7, 9, 11)


def _find_subset_sum_collisions(positions, r):
    """Group master-set labels by their r-subset position sums.
    Returns the list of collision groups (subsets with equal sum).
    """
    labels = sorted(positions.keys())
    if r < 1 or r > len(labels):
        return []
    buckets = defaultdict(list)
    for combo in combinations(labels, r):
        s = np.sum([positions[f] for f in combo], axis=0)
        key = tuple(np.round(s, 9))
        buckets[key].append(combo)
    return [v for v in buckets.values() if len(v) > 1]


class TestConstruction:
    """Each new master set constructs with the expected shape metadata."""

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_classmethod_builds(self, name):
        ms = getattr(MasterSet, name)()
        assert isinstance(ms, MasterSet)
        assert ms.name == name

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_has_expected_node_count(self, name):
        ms = getattr(MasterSet, name)()
        assert ms.n_factors == EXPECTED_PROPERTIES[name]['n_factors']

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_has_expected_ambient_dim(self, name):
        ms = getattr(MasterSet, name)()
        any_pos = next(iter(ms.positions.values()))
        assert len(any_pos) == EXPECTED_PROPERTIES[name]['ambient_dim']

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_has_edges(self, name):
        ms = getattr(MasterSet, name)()
        assert len(ms.edges) > 0


class TestRegistry:
    """Registry entries resolve and return equivalent master sets."""

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_name_in_registry(self, name):
        assert name in MASTER_SETS

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_registry_returns_same_structure(self, name):
        from_classmethod = getattr(MasterSet, name)()
        from_registry = MASTER_SETS[name]()
        assert from_classmethod.name == from_registry.name
        assert from_classmethod.n_factors == from_registry.n_factors
        assert sorted(from_classmethod.positions.keys()) == \
               sorted(from_registry.positions.keys())


class TestWithFactors:
    """Each master set accepts factor assignments without error."""

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_with_factors_returns_new_masterset(self, name):
        ms = getattr(MasterSet, name)()
        factored = ms.with_factors(SIX_FACTORS)
        assert isinstance(factored, MasterSet)
        assert factored.factors == SIX_FACTORS
        assert factored.n_factors == ms.n_factors


class TestCPSCompatibility:
    """Each new master set produces a valid Eikosany-sized CPS (r=3)."""

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_cps_builds_with_string(self, name):
        cps = CombinationProductSet(SIX_FACTORS, r=3, master_set=name)
        assert len(cps.ratios) == 20

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_cps_builds_with_instance(self, name):
        ms = getattr(MasterSet, name)()
        cps = CombinationProductSet(SIX_FACTORS, r=3, master_set=ms)
        assert len(cps.ratios) == 20

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    def test_cps_positions_are_populated(self, name):
        cps = CombinationProductSet(SIX_FACTORS, r=3, master_set=name)
        assert len(cps.positions) == 20
        for pos in cps.positions.values():
            assert all(np.isfinite(c) for c in pos)


class TestSubsetSumCleanness:
    """No two r-subsets of master-set positions sum to the same vector."""

    @pytest.mark.parametrize('name', NEW_MASTER_SETS)
    @pytest.mark.parametrize('r', [2, 3, 4, 5])
    def test_no_collisions(self, name, r):
        ms = getattr(MasterSet, name)()
        collisions = _find_subset_sum_collisions(ms.positions, r)
        assert collisions == [], (
            f"{name} has {len(collisions)} collision group(s) at r={r}: "
            f"{collisions[:2]}"
        )


class TestParameterized:
    """halton_asterisk and wheel_nd accept non-default n and ambient_d."""

    def test_halton_asterisk_custom_dims(self):
        ms = MasterSet.halton_asterisk(n=8, ambient_d=7)
        assert ms.n_factors == 8
        assert len(next(iter(ms.positions.values()))) == 7

    def test_wheel_nd_custom_dims(self):
        ms = MasterSet.wheel_nd(n=8, ambient_d=7)
        assert ms.n_factors == 8
        assert len(next(iter(ms.positions.values()))) == 7

    def test_halton_asterisk_cps_at_8_factors(self):
        ms = MasterSet.halton_asterisk(n=8, ambient_d=7)
        cps = CombinationProductSet(
            (1, 3, 5, 7, 9, 11, 13, 17), r=4, master_set=ms)
        assert len(cps.ratios) == 70

    def test_wheel_nd_cps_at_8_factors(self):
        ms = MasterSet.wheel_nd(n=8, ambient_d=7)
        cps = CombinationProductSet(
            (1, 3, 5, 7, 9, 11, 13, 17), r=4, master_set=ms)
        assert len(cps.ratios) == 70

    def test_wheel_nd_rejects_too_few_nodes(self):
        with pytest.raises(ValueError):
            MasterSet.wheel_nd(n=2, ambient_d=3)

    def test_wheel_nd_rejects_low_ambient_d(self):
        with pytest.raises(ValueError):
            MasterSet.wheel_nd(n=6, ambient_d=1)
