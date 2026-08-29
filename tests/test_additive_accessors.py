"""Small additive accessors from the W1 wave (WL-03, WL-04, WL-13, WL-19).

Each closes a gap where the value was reachable but only by a long form, a
private attribute, or hand-written arithmetic. Nothing here changes an
existing answer; every test would raise ``AttributeError`` or ``ImportError``
before the fix rather than assert a different value.
"""

import pytest

from klotho.chronos import TemporalUnit
from klotho.dynatos.envelopes import Envelope
from klotho.thetos import CompositionalUnit
from klotho.thetos.composition.compositional import UCNodeSelector
from klotho.utils.algorithms import tile


def _ut():
    return TemporalUnit(span=1, tempus='4/4', prolatio=(1, -2, 3, 1))


def _uc():
    return CompositionalUnit(span=1, tempus='4/4', prolatio=(1, -2, 3, 1))


class TestSoundingSelector:
    """WL-03. The charter claimed the long form already worked everywhere.
    It did not: ``is_rest`` lived only on the CU handle, so the documented
    ``filter(lambda c: not c.is_rest)`` raised on a plain TemporalUnit."""

    def test_the_long_form_now_works_on_a_temporal_unit(self):
        assert [h.id for h in _ut().leaves.filter(lambda c: not c.is_rest)] == [1, 3, 4]

    def test_sounding_drops_the_rests(self):
        assert [h.id for h in _ut().leaves.sounding] == [1, 3, 4]

    def test_sounding_agrees_with_the_long_form(self):
        ut = _ut()
        assert [h.id for h in ut.leaves.sounding] == \
               [h.id for h in ut.leaves.filter(lambda c: not c.is_rest)]

    def test_it_preserves_the_subclass(self):
        assert isinstance(_uc().leaves.sounding, UCNodeSelector)

    def test_an_all_rest_selection_comes_back_empty(self):
        ut = TemporalUnit(span=1, tempus='4/4', prolatio=(-1, -1))
        assert list(ut.leaves.sounding) == []

    def test_an_all_sounding_selection_is_unchanged(self):
        ut = TemporalUnit(span=1, tempus='4/4', prolatio=(1, 1, 1))
        assert [h.id for h in ut.leaves.sounding] == [h.id for h in ut.leaves]

    def test_is_rest_reads_the_sign_of_the_proportion(self):
        ut = _ut()
        assert [h.is_rest for h in ut.leaves] == [False, True, False, False]


class TestUnsignedDurationAccessors:
    """WL-19. ``real_duration`` stays signed -- the sign is the rest marker
    and third-party code detects rests with ``d < 0`` (ruling R4). These are
    additive, mirroring what ``Chronon`` already shipped."""

    def test_the_handle_gains_an_unsigned_duration(self):
        rest = _ut().leaves[1]
        assert rest.real_duration < 0
        assert rest.duration == abs(rest.real_duration)

    def test_a_sounding_node_is_unaffected(self):
        node = _ut().leaves[0]
        assert node.duration == node.real_duration

    def test_start_and_end_bracket_the_node(self):
        node = _ut().leaves[1]
        assert node.start == node.real_onset
        assert node.end == pytest.approx(node.start + node.duration)

    def test_the_handle_agrees_with_the_chronon(self):
        ut = _ut()
        for handle, chronon in zip(ut.leaves, ut):
            assert handle.duration == chronon.duration
            assert handle.start == pytest.approx(chronon.start)

    def test_real_duration_is_untouched(self):
        assert _ut().durations == tuple(h.real_duration for h in _ut().leaves)


class TestEnvelopeCurve:
    """WL-04. The only real residue of a mostly-refuted item: the curve was
    public in every way except having a name."""

    def test_curve_is_public(self):
        assert Envelope([0, 1, 0], times=[0.1, 0.9], curve=-4).curve == [-4, -4]

    def test_it_is_the_same_object_the_private_attribute_held(self):
        env = Envelope([0, 1, 0], times=[0.1, 0.9], curve=-4)
        assert env.curve is env._curve

    def test_it_sits_beside_the_other_public_accessors(self):
        env = Envelope([0, 1, 0], times=[0.1, 0.9], curve=[2, -2])
        assert len(env.curve) == len(env.values) - 1
        assert env.curve == [2, -2]


class TestTile:
    """WL-13."""

    def test_a_list_tiles_to_a_list(self):
        assert tile([1, 2, 3], 2) == [1, 2, 3, 1, 2, 3]

    def test_a_tuple_tiles_to_a_tuple(self):
        assert tile((1, 2), 3) == (1, 2, 1, 2, 1, 2)

    def test_zero_repetitions_is_empty(self):
        assert tile([1, 2], 0) == []

    def test_one_repetition_is_a_copy(self):
        src = [1, 2]
        out = tile(src, 1)
        assert out == src and out is not src

    def test_a_negative_count_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            tile([1], -1)

    def test_an_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            tile("abc", 2)

    def test_a_numpy_array_tiles(self):
        import numpy as np
        assert list(tile(np.array([1, 2]), 2)) == [1, 2, 1, 2]

    def test_the_return_type_drives_pattern_semantics(self):
        """The reason the docstring calls the type load-bearing."""
        from klotho.topos.collections.sequences import Pattern
        cycling = Pattern(tile([1, 2], 2))
        assert [next(cycling) for _ in range(5)] == [1, 2, 1, 2, 1]
        assert next(Pattern(tile((1, 2), 2))) == (1, 2, 1, 2)

    def test_it_is_exported_from_the_package(self):
        import klotho.utils.algorithms as algs
        assert 'tile' in algs.__all__
