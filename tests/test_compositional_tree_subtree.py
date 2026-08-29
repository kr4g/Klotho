"""``uc._rt.subtree(node)`` keeps the parameter layer.

``RhythmTree.subtree`` overrides ``Tree.subtree`` outright: it rebuilds the
subtree from its S-form instead of copying nodes, so it never reached the
``_after_subtree_built`` hook that :class:`ParameterTree` uses to carry its
layer across — and it hardcoded ``RhythmTree`` as the class it built. A
subtree taken from a ``CompositionalUnit`` therefore came back as a plain
rhythm tree with the pfield/mfield registries, every per-node override and
every instrument binding gone, and with no error to say so.

That is the same gap NEW-21 closed on the graft path. It fixed the direction
it was scoped to and left this one.

Values arrive as **effective** values at every node, matching
``ParameterTree.subtree`` (which copies each node's effective dict) and the
graft path. The subtree root has lost its ancestors, so anything it
inherited from outside is materialised there or lost — the governing
instrument included.
"""

import pytest

from klotho.chronos import RhythmTree
from klotho.thetos import Instrument
from klotho.thetos.composition import CompositionalUnit
from klotho.thetos.composition.compositional import CompositionalTree


@pytest.fixture
def uc():
    return CompositionalUnit(span=1, tempus='4/4', prolatio=(1, (1, (1, 1)), 1))


def _branch(uc):
    """The middle child of the root — the one node with children of its own."""
    return sorted(uc._rt.successors(uc._rt.root))[1]


def test_the_subtree_is_a_compositional_tree_not_a_rhythm_tree(uc):
    assert isinstance(uc._rt.subtree(_branch(uc)), CompositionalTree)


def test_the_field_registries_survive(uc):
    uc.root.set_pfields(amp=0.5)
    sub = uc._rt.subtree(_branch(uc))
    assert sub.pfield_names == uc._rt.pfield_names
    assert sub.mfield_names == uc._rt.mfield_names


def test_an_override_on_the_extracted_node_survives(uc):
    node = _branch(uc)
    uc._rt.set_pfields(node, pan=-1.0)
    sub = uc._rt.subtree(node)
    assert sub.get_pfield(sub.root, 'pan') == -1.0


def test_a_value_inherited_from_outside_is_materialised_at_the_root(uc):
    """The root's ancestors are gone, so an inherited value lives there or nowhere."""
    node = _branch(uc)
    uc.root.set_pfields(amp=0.5)
    assert uc._rt.items(node)['amp'] == 0.5      # inherited, not owned
    assert 'amp' not in dict(uc._rt.nodes[node])
    sub = uc._rt.subtree(node)
    assert sub.get_pfield(sub.root, 'amp') == 0.5


def test_every_node_resolves_as_it_did_in_the_source(uc):
    node = _branch(uc)
    uc.root.set_pfields(amp=0.5)
    uc._rt.set_pfields(node, pan=-1.0)
    children = sorted(uc._rt.successors(node))
    uc._rt.set_pfields(children[0], amp=0.9)

    sub = uc._rt.subtree(node)
    pairs = [(node, sub.root)] + list(zip(children, sorted(sub.successors(sub.root))))
    for old_node, new_node in pairs:
        assert dict(sub.items(new_node)) == dict(uc._rt.items(old_node))


def test_an_instrument_bound_inside_the_subtree_survives(uc):
    node = _branch(uc)
    child = sorted(uc._rt.successors(node))[0]
    uc._rt.set_instrument(child, Instrument("lead", {"channel": 3}))
    sub = uc._rt.subtree(node)
    new_child = sorted(sub.successors(sub.root))[0]
    assert sub.get_instrument(new_child) == Instrument("lead", {"channel": 3})


def test_an_instrument_inherited_from_outside_is_carried_to_the_root(uc):
    node = _branch(uc)
    uc._rt.set_instrument(uc._rt.root, Instrument("pad", {"channel": 2}))
    assert uc._rt.get_instrument(node) == Instrument("pad", {"channel": 2})
    sub = uc._rt.subtree(node)
    assert sub.get_instrument(sub.root) == Instrument("pad", {"channel": 2})


def test_a_leaf_subtree_keeps_its_values(uc):
    """A leaf has no S-form, so subtree() gives it the ``(1,)`` fallback.

    The new root gains a child with no source counterpart; it must still
    resolve to the leaf's values, by inheritance from the mapped root.
    """
    leaf = sorted(uc._rt.successors(uc._rt.root))[0]
    uc.root.set_pfields(amp=0.5)
    uc._rt.set_pfields(leaf, pan=0.25)
    sub = uc._rt.subtree(leaf)
    assert sub.get_pfield(sub.root, 'amp') == 0.5
    assert sub.get_pfield(sub.root, 'pan') == 0.25
    synthetic = sorted(sub.successors(sub.root))[0]
    assert sub.get_pfield(synthetic, 'pan') == 0.25


def test_a_plain_rhythm_tree_subtree_is_unchanged():
    """The hook is subclass-only; rhythm trees take the same path as before."""
    rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, (2, (1, 1)), -3))
    sub = rt.subtree(sorted(rt.successors(rt.root))[1])
    assert type(sub) is RhythmTree
    assert not hasattr(sub, '_param_layer')
    assert [sub[n].get('proportion') for n in sorted(sub.nodes)] == [1, 1, 1]
