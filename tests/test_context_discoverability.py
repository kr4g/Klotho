"""Forwarded attributes are now discoverable (charter WL-31 + NEW-22).

WL-31 was filed as an absence -- "no branch ordinal in DistributionContext" --
and refuted: ``ctx.sibling_index``, ``ctx.sibling_total`` and ``ctx.depth``
have always worked, forwarded through ``__getattr__`` to the node handle and
chainable up ``ctx.parent``. What was true is that ``dir()`` could not see
them, which is exactly how the audit that filed it concluded they were gone.

So the fix is discoverability, plus the one genuinely missing piece: a whole
path, not just the last step of it.
"""

import pytest

from klotho.chronos import TemporalUnit
from klotho.thetos import CompositionalUnit


def _uc():
    return CompositionalUnit.from_ut(
        TemporalUnit(tempus='4/4', prolatio=(1, (2, (1, 1, 1)), 1)))


def _first_context(uc):
    """The context the distribution machinery actually builds."""
    grabbed = {}

    def probe(ctx):
        grabbed.setdefault('ctx', ctx)
        return 0.5

    uc.set_pfields(uc.leaves, amp=probe)
    return grabbed['ctx']


class TestPath:
    def test_the_root_path_is_empty(self):
        uc = _uc()
        assert uc.pt[uc._rt.root] is not None
        assert uc._rt.path_signature(uc._rt.root, uc._rt.root) == ()

    def test_path_records_the_child_index_at_every_level(self):
        assert [(h.id, h.path) for h in _uc().leaves] == [
            (1, (0,)), (3, (1, 0)), (4, (1, 1)), (5, (1, 2)), (6, (2,))]

    def test_its_length_is_the_depth(self):
        for h in _uc().leaves:
            assert len(h.path) == h.depth

    def test_its_last_step_is_the_sibling_index(self):
        for h in _uc().leaves:
            assert h.path[-1] == h.sibling_index

    def test_it_agrees_with_walking_parent_upward(self):
        for h in _uc().leaves:
            chain, cur = [], h
            while cur is not None and cur.parent is not None:
                chain.append(cur.sibling_index)
                cur = cur.parent
            assert tuple(reversed(chain)) == h.path

    def test_it_is_reachable_from_a_distribution_context(self):
        uc = _uc()
        ctx = _first_context(uc)
        assert ctx.path == (0,)
        assert ctx.parent.path == ()


class TestDirListsWhatGetattrForwards:
    FORWARDED = ('depth', 'path', 'sibling_index', 'sibling_total',
                 'proportion', 'real_onset', 'real_duration', 'leaves')

    @pytest.mark.parametrize("name", FORWARDED)
    def test_the_context_advertises_the_forwarded_name(self, name):
        ctx = _first_context(_uc())
        assert name in dir(ctx)
        assert getattr(ctx, name) is not None or name in ('depth',)

    @pytest.mark.parametrize("name", FORWARDED)
    def test_the_parent_view_advertises_it_too(self, name):
        parent = _first_context(_uc()).parent
        assert name in dir(parent)

    def test_the_parent_view_still_hides_the_selection_fields(self):
        """``index``/``total`` are deliberately absent on a parent -- a parent
        is not part of the current selection -- so dir() must not offer them."""
        parent = _first_context(_uc()).parent
        assert 'index' not in dir(parent)
        assert 'total' not in dir(parent)

    def test_dir_advertises_nothing_that_is_not_there(self):
        """The contract is that every advertised name exists. Some of them
        still raise on a leaf -- ``first_child`` has no child to return --
        which is a real answer, not a missing attribute."""
        ctx = _first_context(_uc())
        for name in dir(ctx):
            if name.startswith('_'):
                continue
            try:
                getattr(ctx, name)
            except AttributeError:
                pytest.fail(f"dir() advertised {name!r} but it does not exist")
            except Exception:
                pass

    def test_a_chronon_advertises_its_node_data_and_real_times(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1))
        chronon = list(ut)[0]
        assert 'real_onset' in dir(chronon)
        assert 'real_duration' in dir(chronon)
        assert 'proportion' in dir(chronon)

    def test_the_handle_does_not_over_advertise(self):
        """UTNodeHandle has no ``__getattr__``, so its dir() was already
        honest; it must not start listing node-data keys that are not
        attributes."""
        handle = _uc().leaves[0]
        assert 'tied' not in dir(handle)
        assert 'path' in dir(handle)
