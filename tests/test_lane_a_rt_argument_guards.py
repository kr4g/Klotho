"""Argument guards on the ``RhythmTree`` constructor and its edit verbs.

Three doors let a nonsense argument through and answered with a tree that
looked plausible and was wrong:

  RT-29  ``scale(0, 1/3)`` / ``insert(0, 1/3)`` -- a non-terminating float is
         read DECIMAL-exactly, so ``1/3`` spells the tree
         ``(3333333333333333, 10000000000000000)``. The arithmetic stays
         exact; every print, plot, export and golden of that tree is
         destroyed. ``0.5`` is fine -- the defect is confined to floats whose
         decimal expansion does not terminate.

  RT-33  ``subdivide([leaf, leaf], S)`` validated the leaf precondition for
         every node UP FRONT and then subdivided in a second loop, so a
         repeated node passed the check while it was still a leaf and was
         then subdivided TWICE: ``(1, 1)`` became ``(1 (1 1 1 1))``.

  RT-30  ``RhythmTree(subdivisions=())`` built a tree with only the root,
         whose single event reports the measure's NUMERATOR as its duration
         (``4/4`` -> four whole notes, not one bar). Only the TOP LEVEL is
         broken: a nested empty group is correct and is real emitted data --
         see :class:`TestNestedEmptyIsStillAccepted`.

All three are refusals rather than repairs (Ruling Nine): a repair would
guess at what the composer meant, and guessing is worse than stopping.
"""

from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree as RT


# ----------------------------------------------------------------------
# RT-29 -- a non-terminating float destroys the spelling
# ----------------------------------------------------------------------
class TestNonTerminatingFloatIsRefused:
    """The value that reaches the tree is arithmetically right and unreadable,
    so nothing downstream can notice. The door is the only place to stop it."""

    def test_scale_refuses_one_third_as_a_float(self):
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError, match='non-terminating'):
            rt.scale(0, 1 / 3)

    def test_insert_refuses_one_third_as_a_float(self):
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError, match='non-terminating'):
            rt.insert(0, 1 / 3)

    def test_the_message_names_the_offending_value_and_the_way_out(self):
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError) as exc:
            rt.scale(0, 1 / 3)
        msg = str(exc.value)
        assert repr(1 / 3) in msg                    # the offending value
        assert '3333333333333333/10000000000000000' in msg   # what it becomes
        assert 'Fraction(1, 3)' in msg               # what to write instead
        assert "'1/3'" in msg

    def test_the_refusal_happens_before_any_write(self):
        """A guard that fired mid-rebuild would leave a half-respelled tree."""
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError):
            rt.scale(0, 1 / 3)
        assert rt.group.S == (1, 1)
        assert rt.durations == (Fraction(1, 2), Fraction(1, 2))

    def test_a_paired_call_is_refused_on_the_offending_member(self):
        """``scale([0, 1], [2, 1/3])`` must not scale event 0 and then die."""
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError, match='non-terminating'):
            rt.scale([0, 1], [2, 1 / 3])
        assert rt.group.S == (1, 1)


class TestTerminatingFloatsAndExactTypesStillWork:
    """The guard must not change behaviour for valid input. Every value here
    produced the same answer before the guard existed."""

    @pytest.mark.parametrize('ratio, expected', [
        (0.5, (1, 2)),
        (0.25, (1, 4)),
        (2.0, (2, 1)),
        (3, (3, 1)),
        (Fraction(1, 3), (1, 3)),
        ('1/3', (1, 3)),
    ])
    def test_scale_accepts(self, ratio, expected):
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        rt.scale(0, ratio)
        assert rt.group.S == expected

    @pytest.mark.parametrize('duration, expected', [
        (0.5, (1, 1, 1)),
        (Fraction(1, 3), (2, 3, 3)),
        ('1/3', (2, 3, 3)),
    ])
    def test_insert_accepts(self, duration, expected):
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        rt.insert(0, duration)
        assert rt.group.S == expected

    def test_the_published_haddad_figure_is_unmoved(self):
        """fig. 4.65 -- the pin that would catch a guard rejecting integers."""
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale(2, 3)
        assert rt.group.S == (4, 2, 9, 6, 3)


# ----------------------------------------------------------------------
# RT-33 -- a repeated node subdivides twice
# ----------------------------------------------------------------------
class TestSubdivideRefusesARepeatedNode:

    def test_the_same_leaf_twice_is_refused(self):
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        leaf = rt.leaf_nodes[0]
        with pytest.raises(ValueError, match='more than once'):
            rt.subdivide([leaf, leaf], (1, 1))

    def test_the_tree_is_untouched_by_the_refusal(self):
        """The old code subdivided as it walked, so a late failure would have
        left the earlier nodes already divided."""
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        a, b = rt.leaf_nodes
        with pytest.raises(ValueError, match='more than once'):
            rt.subdivide([a, b, a], (1, 1))
        assert rt.group.S == (1, 1)
        assert rt.durations == (Fraction(1, 2), Fraction(1, 2))

    def test_the_message_names_the_repeated_node(self):
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        leaf = rt.leaf_nodes[0]
        with pytest.raises(ValueError) as exc:
            rt.subdivide([leaf, leaf], (1, 1))
        assert f'node {leaf} ' in str(exc.value)

    def test_distinct_leaves_still_subdivide(self):
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        rt.subdivide(list(rt.leaf_nodes), (1, 1))
        assert rt.durations == (Fraction(1, 4),) * 4

    def test_a_scalar_node_still_subdivides(self):
        rt = RT(span=1, meas='4/4', subdivisions=(1, 1))
        rt.subdivide(rt.leaf_nodes[0], (1, 1))
        assert rt.durations == (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))


# ----------------------------------------------------------------------
# RT-30 -- a top-level empty S, and ONLY the top level
# ----------------------------------------------------------------------
class TestTopLevelEmptySubdivisionsAreRefused:

    def test_empty_tuple_is_refused(self):
        with pytest.raises(ValueError, match='subdivisions cannot be empty'):
            RT(span=1, meas='4/4', subdivisions=())

    def test_empty_list_is_refused_too(self):
        with pytest.raises(ValueError, match='subdivisions cannot be empty'):
            RT(span=1, meas='4/4', subdivisions=[])

    def test_the_message_says_what_to_write_instead(self):
        with pytest.raises(ValueError) as exc:
            RT(span=1, meas='4/4', subdivisions=())
        msg = str(exc.value)
        assert '(1,)' in msg
        assert 'nested' in msg

    def test_the_undivided_measure_it_recommends_actually_works(self):
        rt = RT(span=1, meas='4/4', subdivisions=(1,))
        assert rt.durations == (Fraction(1, 1),)


class TestNestedEmptyIsStillAccepted:
    """A nested ``(D, ())`` is CORRECT -- its durations sum to the measure --
    and it is real emitted data: the asymmetric tree at
    ``tests/test_decompose.py`` (``ASYM_S``) carries three of them. Refusing
    it would break ``decompose``."""

    def test_nested_empty_group_builds(self):
        rt = RT(span=1, meas='4/4', subdivisions=(1, (1, ())))
        assert rt.durations == (Fraction(1, 2), Fraction(1, 2))

    def test_the_decompose_fixture_shape_builds(self):
        asym = ((3, ((1, (2, 1, 1)), (2, (1, 1)), (1, ()))),
                (2, ((1, (3, 1, 2)), (1, (1, 1, 1)))),
                (1, ()))
        rt = RT(span=1, meas='4/4', subdivisions=asym)
        assert sum(abs(d) for d in rt.durations) == Fraction(1, 1)
