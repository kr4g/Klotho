from fractions import Fraction

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.topos.formal_grammars import DerivationTree, derive
from klotho.topos.graphs import Tree


def _chordy_derivation():
    tree = DerivationTree('t', [
        DerivationTree('d', [DerivationTree('s'), DerivationTree('d')]),
        DerivationTree('t'),
    ])
    for leaf, chord in zip(tree.leaves(), [(100.0, 200.0), (150.0, 250.0), (200.0, 300.0)]):
        leaf.data['chord'] = chord
    return tree


class TestFromDerivationTree:
    def test_topology_and_tempus_rule_3(self):
        uc = UC.from_tree(_chordy_derivation(), bpm=60, beat='1/4')
        # no root proportion: tempus = sum of root child proportions / denom
        assert str(uc.tempus) == '2/8'
        assert len(uc._rt.leaf_nodes) == 3

    def test_chord_payloads_land_in_mfields(self):
        uc = UC.from_tree(_chordy_derivation())
        leaves = uc._rt.leaf_nodes
        assert uc.get_mfield(leaves[0], 'chord') == (100.0, 200.0)
        assert uc.get_mfield(leaves[1], 'chord') == (150.0, 250.0)
        assert uc.get_mfield(leaves[2], 'chord') == (200.0, 300.0)

    def test_head_weight(self):
        uc = UC.from_tree(_chordy_derivation(), head_weight=2)
        assert str(uc.tempus) == '3/8'
        assert uc._rt.durations == (Fraction(1, 24), Fraction(1, 12), Fraction(1, 4))

    def test_head_weight_one_uniform(self):
        uc = UC.from_tree(_chordy_derivation())
        assert uc._rt.durations == (Fraction(1, 16), Fraction(1, 16), Fraction(1, 8))

    def test_denom(self):
        uc = UC.from_tree(_chordy_derivation(), denom=4)
        assert str(uc.tempus) == '2/4'

    def test_explicit_tempus_wins(self):
        uc = UC.from_tree(_chordy_derivation(), tempus='4/4')
        assert str(uc.tempus) == '4/4'

    def test_single_node_derivation(self):
        uc = UC.from_tree(DerivationTree('t', chord=(440.0,)))
        assert len(uc._rt.leaf_nodes) == 1
        assert uc.get_mfield(uc._rt.leaf_nodes[0], 'chord') == (440.0,)

    def test_derived_tree_end_to_end(self):
        rules = {'t': [(1.0, ['d', 't'])], 'd': [(1.0, ['s', 'd'])], 's': [(1.0, ['s'])]}
        dtree = derive('t', rules, max_depth=3, rng=2)
        uc = UC.from_tree(dtree, bpm=120, beat='1/4')
        assert len(uc._rt.leaf_nodes) == len(dtree.leaves())

    def test_pfields_via_bind_idiom(self):
        from klotho.thetos import Bind
        uc = UC.from_tree(_chordy_derivation(), bpm=60, beat='1/4')
        uc.root.set_pfields(freq=Bind(lambda c: c.mfields['chord']))
        freqs = [uc.get_pfield(n, 'freq') for n in uc._rt.leaf_nodes]
        assert freqs == [(100.0, 200.0), (150.0, 250.0), (200.0, 300.0)]


class TestFromPlainTree:
    def test_proportions_from_node_attrs(self):
        tree = Tree('root', (1, 1, 1))
        for node, proportion in zip(tree.successors(tree.root), (2, -1, 1)):
            tree.set_node_data(node, proportion=proportion)
        uc = UC.from_tree(tree, denom=4)
        assert str(uc.tempus) == '4/4'
        durations = uc._rt.durations
        assert durations[0] == Fraction(1, 2)
        assert durations[1] == Fraction(-1, 4)
        assert durations[2] == Fraction(1, 4)

    def test_missing_proportions_default_to_one(self):
        tree = Tree('root', ('a', 'b', 'c'))
        uc = UC.from_tree(tree, denom=8)
        assert str(uc.tempus) == '3/8'
        assert all(d == Fraction(1, 8) for d in uc._rt.durations)

    def test_root_proportion_rule_2(self):
        tree = Tree('root', (1, 1))
        tree.set_node_data(tree.root, proportion=3)
        uc = UC.from_tree(tree, denom=8)
        assert str(uc.tempus) == '3/8'

    def test_span_always_one(self):
        uc = UC.from_tree(_chordy_derivation())
        assert uc.span == 1

    def test_extra_attrs_copied_to_mfields(self):
        tree = Tree('root', ('x', 'y'))
        nodes = list(tree.successors(tree.root))
        tree.set_node_data(nodes[0], tag='alpha', weight=1.5)
        tree.set_node_data(nodes[1], tag='beta')
        uc = UC.from_tree(tree)
        leaves = uc._rt.leaf_nodes
        assert uc.get_mfield(leaves[0], 'tag') == 'alpha'
        assert uc.get_mfield(leaves[0], 'weight') == 1.5
        assert uc.get_mfield(leaves[1], 'tag') == 'beta'

    def test_rhythm_and_bookkeeping_keys_not_copied(self):
        tree = Tree('root', (1, 1))
        for node in tree.successors(tree.root):
            tree.set_node_data(node, proportion=2, tag='keep')
        uc = UC.from_tree(tree)
        assert 'proportion' not in uc._rt.mfield_names
        assert 'label' not in uc._rt.mfield_names
        assert 'tag' in uc._rt.mfield_names

    def test_nested_tree(self):
        tree = Tree('root', ('a', ('b', ('c', 'd'))))
        nodes = list(tree.successors(tree.root))
        tree.set_node_data(nodes[1], proportion=2)
        uc = UC.from_tree(tree, denom=8)
        assert str(uc.tempus) == '3/8'
        assert len(uc._rt.leaf_nodes) == 3

    def test_events_carry_mfields(self):
        uc = UC.from_tree(_chordy_derivation(), bpm=60, beat='1/4')
        df = uc.events
        assert list(df['chord']) == [(100.0, 200.0), (150.0, 250.0), (200.0, 300.0)]

    def test_inst_and_fields_forwarded(self):
        uc = UC.from_tree(_chordy_derivation(), inst='default', pfields={'amp': 0.3})
        assert uc.get_instrument(uc._rt.root) == 'default'
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'amp') == 0.3
