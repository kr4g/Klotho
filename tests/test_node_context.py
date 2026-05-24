import pytest

from klotho.chronos import TemporalUnit as UT
from klotho.chronos.temporal_units.temporal import UTNodeHandle
from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument


def _ut_nested():
    return UT(tempus="5/8", prolatio=((2, (1, 1, 1)), (1, (1, 1))), beat="1/8", bpm=120)


def _uc_nested():
    return UC(
        tempus="5/8",
        prolatio=((2, (1, 1, 1)), (1, (1, 1))),
        beat="1/8",
        bpm=120,
        inst=SynthDefInstrument.tri(),
    )


class TestNodeHandleAndNodeContext:
    def test_ut_context_exposes_structural_fields(self):
        ut = _ut_nested()
        contexts = []
        _ = ut.leaves.filter(lambda c: contexts.append(c) or True)
        assert contexts
        c0 = contexts[0]
        assert isinstance(c0.id, int)
        assert isinstance(c0.depth, int)
        assert isinstance(c0.sibling_index, int)
        assert isinstance(c0.sibling_total, int)
        assert c0.parent is None or isinstance(c0.parent, UTNodeHandle)

    def test_node_ref_parent_chain_reaches_root(self):
        ut = _ut_nested()
        contexts = []
        _ = ut.leaves.filter(lambda c: contexts.append(c) or True)
        c0 = contexts[0]
        node = c0.parent
        seen = set()
        while node is not None:
            assert node.id not in seen
            seen.add(node.id)
            node = node.parent

    def test_index_vs_sibling_index_semantics(self):
        uc = _uc_nested()
        leaf_contexts = []
        _ = uc.leaves.filter(lambda c: leaf_contexts.append(c) or True)
        assert any(c.index != c.sibling_index for c in leaf_contexts)

        first_branch_children = uc.at_depth(1)[0].children
        child_contexts = []
        _ = first_branch_children.filter(lambda c: child_contexts.append(c) or True)
        assert child_contexts
        assert all(c.index == c.sibling_index for c in child_contexts)


class TestDistributionContextParent:
    def test_parent_view_exposes_uc_fields(self):
        uc = _uc_nested()
        uc.root.set_mfields(section="A")
        contexts = []
        _ = uc.leaves.filter(lambda c: contexts.append(c) or True)
        ctx = contexts[0]
        assert isinstance(ctx.parent.mfields, dict)
        assert ctx.parent.mfields.get("section") == "A"

    def test_parent_has_no_selection_index(self):
        uc = _uc_nested()
        contexts = []
        _ = uc.leaves.filter(lambda c: contexts.append(c) or True)
        ctx = contexts[0]
        with pytest.raises(AttributeError):
            _ = ctx.parent.index
