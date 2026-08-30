"""Id-keyed state that lives OUTSIDE the graph must follow content and die
with the node.

``CompositionalUnit`` and ``ParameterLayer`` keep several maps keyed by raw
node id: instrument bindings, slur specs, the Bind memo, and control-envelope
targets. rustworkx REUSES freed node indices, so a map entry left on a deleted
node does not merely leak -- it re-attaches to whatever event lands in that
slot. And a verb that MOVES content between slots (``insert_child``, and the
preserved family's ``_respell`` rebuild) has to carry that state with the
content, or the overlays end up on notes they were never drawn over.

These tests pin the four ways that went wrong: a binding surviving its node
(docket RT-28), and slurs / memoized Bind draws / stale slur specs after a
``_respell`` or a positional insert.
"""

import random

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.parameters.bind import Bind


def _rows_by_freq(uc):
    """``{freq: event row}`` -- freq is the per-note tag these tests set."""
    return {float(row['freq']): row for _, row in uc.events.iterrows()}


class TestBindingsDieWithTheirNode:
    """RT-28: a freed node id must not carry its instrument into its successor."""

    def test_removed_node_does_not_bind_a_later_arrival(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60)
        uc.set_instrument(4, 'ghost')
        uc.remove_subtree(4)

        assert 4 not in uc._rt.node_instruments

        uc.subdivide(3, (1, 1))
        assert set(uc.events['instrument'].dropna()) == set()

    def test_pruned_node_does_not_bind_a_later_arrival(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, (1, (1, 1))), beat='1/4', bpm=60)
        victim = list(uc._rt.successors(uc._rt.root))[-1]
        uc.set_instrument(victim, 'ghost')
        uc.prune(victim)

        assert victim not in uc._rt.node_instruments
        assert set(uc.events['instrument'].dropna()) == set()


class TestRespellCarriesOverlays:
    """``insert``/``extract``/``scale`` rebuild every non-root id; the
    overlays keyed by those ids have to travel with the content.

    Not every test here pins the fix: a rebuild whose freed indices happen to
    be reused in the same order lands the old ids back on the right notes, and
    a test built on that shape is green before and after. The one such test in
    this class is named for what it is.
    """

    def test_insert_carries_the_slur_with_its_own_notes(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        for i, node in enumerate(uc._rt.leaf_nodes):
            uc.set_pfields(node, freq=100 * (i + 1))
        uc.apply_slur(node=list(uc._rt.leaf_nodes)[0:2])

        uc._rt.insert(0, '1/4')

        rows = _rows_by_freq(uc)
        assert rows[100.0]['_slur_start'] == 1
        assert rows[200.0]['_slur_end'] == 1
        # the inserted event was never slurred
        assert rows[440.0]['_slur_start'] != 1
        assert rows[440.0]['_slur_end'] != 1

    def test_insert_carries_the_memoized_draw_with_its_node(self):
        random.seed(7)
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        low = Bind(lambda: random.randint(100, 199))
        high = Bind(lambda: random.randint(900, 999))
        uc.set_pfields(leaves[0], freq=low)
        uc.set_pfields(leaves[1], freq=high)
        uc.set_pfields(leaves[2], freq=1.0)
        uc.set_pfields(leaves[3], freq=2.0)
        uc.events  # force the draws to memoize

        uc._rt.insert(0, '1/4')

        reported = {row['node_id']: float(row['freq'])
                    for _, row in uc.events.iterrows()}
        for node in uc._rt.leaf_nodes:
            raw = uc._rt._rx[node].get('freq')
            if raw is low:
                assert 100 <= reported[node] <= 199
            elif raw is high:
                assert 900 <= reported[node] <= 999

    def test_extract_leaves_no_slur_spec_on_a_destroyed_node(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        uc.apply_slur(node=[1, 2])

        uc._rt.extract(0)

        # only one of the slurred leaves survives, so the slur cannot: what
        # must NOT happen is a spec pointing at a node that no longer exists,
        # which made every later read of `events` raise.
        assert len(uc.events) == 3
        for spec in uc._slur_specs.values():
            assert set(spec['leaf_nodes']).issubset(set(uc._rt.leaf_nodes))

    def test_extract_carries_a_surviving_slur_with_its_notes(self):
        """The extracted event sits AFTER the slur, so every survivor shifts
        one id to the right and the slur has to be carried to the new ids.

        The direction is what makes this test bite. Extracting event 0
        instead leaves the surviving slur on the very ids it started on --
        the freed indices happen to be reused so that the old ids still name
        the right notes -- and that version passes with the whole relocation
        fix removed. It is kept, as a guard, in the test below.
        """
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        for i, node in enumerate(uc._rt.leaf_nodes):
            uc.set_pfields(node, freq=100 * (i + 1))
        slurred = list(uc._rt.leaf_nodes)[1:3]
        uc.apply_slur(node=slurred)

        uc._rt.extract(3)

        rows = _rows_by_freq(uc)
        assert rows[200.0]['_slur_start'] == 1
        assert rows[300.0]['_slur_end'] == 1
        assert rows[100.0]['_slur_start'] != 1
        assert rows[100.0]['_slur_end'] != 1
        # ... and the ids really did move. Without this the fixture could
        # drift back to the id-preserving shape and stop testing anything,
        # which is exactly what happened to the version above.
        (spec,) = uc._slur_specs.values()
        assert set(spec['leaf_nodes']) != set(slurred)

    def test_extract_before_the_slur_is_a_regression_guard_only(self):
        """Extracting event 0 leaves the surviving slur on the SAME ids, so
        this passes with or without the relocation fix. It is a real guard on
        ``extract``; it is not coverage of b5be431's relocation contract.
        """
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        for i, node in enumerate(uc._rt.leaf_nodes):
            uc.set_pfields(node, freq=100 * (i + 1))
        uc.apply_slur(node=list(uc._rt.leaf_nodes)[1:3])

        uc._rt.extract(0)

        rows = _rows_by_freq(uc)
        assert rows[200.0]['_slur_start'] == 1
        assert rows[300.0]['_slur_end'] == 1
        assert rows[400.0]['_slur_end'] != 1


class TestInsertChildShiftsLayerState:
    """``insert_child`` shifts the CONTENT of ranks k..n-1 one slot right.
    Layer state keyed by slot has to shift with it, exactly as node data does."""

    def test_instrument_follows_the_content_it_was_bound_to(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        for i, node in enumerate(leaves):
            uc.set_pfields(node, freq=100 * (i + 1))
        uc.set_instrument(leaves[0], 'flute')

        uc._rt.insert_child(uc._rt.root, 0, proportion=1)

        rows = _rows_by_freq(uc)
        assert rows[100.0]['instrument'] == 'flute'
        assert rows[440.0]['instrument'] != 'flute'

    def test_a_copied_unit_heals_its_own_overlays(self):
        """``copy()`` clones the tree, so the copy has to own the healing
        too -- otherwise the same edit corrupts the copy and not the original."""
        uc = UC(tempus='4/4', prolatio=(1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        for i, node in enumerate(leaves):
            uc.set_pfields(node, freq=100 * (i + 1))
        uc.apply_slur(node=leaves[0:2])

        c = uc.copy()
        c._rt.insert_child(c._rt.root, 0, proportion=1)

        rows = _rows_by_freq(c)
        assert rows[100.0]['_slur_start'] == 1
        assert rows[200.0]['_slur_end'] == 1

    def test_slur_follows_the_content_it_was_drawn_over(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        for i, node in enumerate(leaves):
            uc.set_pfields(node, freq=100 * (i + 1))
        uc.apply_slur(node=leaves[0:2])

        uc._rt.insert_child(uc._rt.root, 0, proportion=1)

        rows = _rows_by_freq(uc)
        assert rows[100.0]['_slur_start'] == 1
        assert rows[200.0]['_slur_end'] == 1
        assert rows[440.0]['_slur_start'] != 1
