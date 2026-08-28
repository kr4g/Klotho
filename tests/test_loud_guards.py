"""Silent failures that now raise (charter W0 'loudness' items).

Each class here pins a case that used to succeed quietly and produce wrong
music: a discarded argument, a miscounted callable, an instrument that never
got set. The point of every test is the raise, not the happy path.
"""

import pytest

from klotho.chronos.rhythm_trees import RhythmTree
from klotho.thetos.composition.compositional import CompositionalUnit, _callable_arity
from klotho.topos.graphs.trees import Tree


class TestAddChildRejectsPositionalData:
    """NEW-03 — `index` was a dead parameter that silently ate node data."""

    def test_positional_second_arg_now_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(TypeError):
            rt.add_child(rt.root, 5)

    def test_keyword_attrs_still_work(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        child = rt.add_child(rt.root, proportion=3)
        assert rt[child]['proportion'] == 3

    def test_the_value_used_to_be_discarded(self):
        """Regression note: add_child(root, 5) once stored proportion=1.

        It "worked" in the docs only because the example passed 1, which
        happens to equal the backfill default.
        """
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(TypeError):
            rt.add_child(rt.root, 1)

    def test_add_subtree_positional_index_now_raises(self):
        t1 = Tree(1, (1, 1))
        t2 = Tree(1, (1, 1))
        with pytest.raises(TypeError):
            t1.add_subtree(t1.root, t2, 0)

    def test_add_subtree_still_works_without_index(self):
        t1 = Tree(1, (1, 1))
        t2 = Tree(1, (1, 1))
        before = len(list(t1.nodes))
        t1.add_subtree(t1.root, t2)
        assert len(list(t1.nodes)) > before


class TestCallableArity:
    """WL-17 — arity counted required params, so `lambda c=None:` lost its context."""

    def test_defaulted_positional_now_counts(self):
        assert _callable_arity(lambda c=None: c) == 1

    def test_plain_positional_still_counts(self):
        assert _callable_arity(lambda c: c) == 1

    def test_zero_arg_still_zero(self):
        assert _callable_arity(lambda: 1) == 0

    def test_keyword_only_never_counts(self):
        """The documented `ens.drums.pick` idiom is (*, rng=None) — must stay 0."""
        assert _callable_arity(lambda *, rng=None: rng) == 0

    def test_var_positional_counts(self):
        assert _callable_arity(lambda *a: a) == 1

    def test_var_keyword_never_counts(self):
        assert _callable_arity(lambda **k: k) == 0

    def test_mixed_positional_and_keyword_only(self):
        assert _callable_arity(lambda c, *, k=1: c) == 1

    def test_defaulted_callable_receives_context(self):
        """The end-to-end bug: the lambda ran, returned a value, saw no context."""
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), pfields=['amp'])
        seen = []
        uc.leaves.set_pfields(amp=lambda c=None: (seen.append(c), 0.5)[1])
        assert all(c is not None for c in seen), "callable was invoked without context"
        assert len(seen) == 4

    def test_bound_zero_arg_method_idiom_preserved(self):
        """WL-17's constraint: the pick idiom must keep reporting arity 0."""
        class _Picker:
            def pick(self, *, rng=None):
                return 'kl_tri'
        assert _callable_arity(_Picker().pick) == 0


class TestSetInstrumentLoudness:
    """WL-16 — unrecognized shapes left the instrument None and lowered as kl_tri."""

    def _uc(self):
        return CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1))

    def test_plain_list_now_raises(self):
        uc = self._uc()
        with pytest.raises(TypeError, match='not a usable instrument'):
            uc.set_instrument(uc.root, ['not', 'an', 'instrument'])

    def test_dict_now_raises(self):
        uc = self._uc()
        with pytest.raises(TypeError, match='not a usable instrument'):
            uc.set_instrument(uc.root, {'def': 'kl_tri'})

    def test_none_now_raises(self):
        uc = self._uc()
        with pytest.raises(TypeError, match='not a usable instrument'):
            uc.set_instrument(uc.root, None)

    def test_error_message_names_the_accepted_shapes(self):
        uc = self._uc()
        with pytest.raises(TypeError) as exc:
            uc.set_instrument(uc.root, object())
        msg = str(exc.value)
        for shape in ('Instrument', 'Effect', 'str', 'int', 'Pattern', 'callable'):
            assert shape in msg, f"accept-list omits {shape!r}: {msg}"

    def test_string_instrument_still_accepted(self):
        uc = self._uc()
        uc.set_instrument(uc.root, 'kl_tri')
        assert uc._rt.get_instrument(uc._rt.root) == 'kl_tri'

    def test_callable_returning_garbage_is_caught_by_the_layer(self):
        """The second hole: the caller-level guard never sees a callable's return."""
        uc = self._uc()
        with pytest.raises(TypeError, match='not a usable instrument'):
            uc.leaves.set_instrument(lambda c: ['garbage'])
