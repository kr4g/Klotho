"""TemporalBlock construction guards and the sort_rows deprecation.

WL-32 / NEW-11. The block validated an illegal axis in its setter but not
in its constructor, so the illegal value entered through the front door and
survived `copy()`. Row sorting is on by default and reorders rows silently,
which renames anything keyed by row index.
"""

import warnings

import pytest

from klotho.chronos.temporal_units import TemporalUnit, TemporalBlock


def _u(dur_beats):
    return TemporalUnit(tempus=f'{dur_beats}/4', prolatio='d', bpm=120)


SHORT, LONG = 1, 4


class TestAxisValidation:
    """NEW-11 — constructor and _adopt skipped the setter's validation."""

    @pytest.mark.parametrize('bad', [5, -3, 1.5, -1.0001])
    def test_constructor_rejects_out_of_range_axis(self, bad):
        with pytest.raises(ValueError, match='Axis must be between -1 and 1'):
            TemporalBlock([_u(SHORT), _u(LONG)], axis=bad, sort_rows=False)

    @pytest.mark.parametrize('good', [-1, 0, 1, -0.5, 0.5])
    def test_constructor_accepts_legal_axis(self, good):
        blk = TemporalBlock([_u(SHORT), _u(LONG)], axis=good, sort_rows=False)
        assert blk.axis == float(good)

    def test_constructor_coerces_to_float_like_the_setter(self):
        """BT(axis=0).axis was 0 (int) while blk.axis = 0 gave 0.0."""
        blk = TemporalBlock([_u(SHORT)], axis=0, sort_rows=False)
        assert isinstance(blk.axis, float)

    def test_setter_and_constructor_agree_exactly(self):
        blk = TemporalBlock([_u(SHORT), _u(LONG)], sort_rows=False)
        blk.axis = 0
        from_setter = blk.axis
        from_ctor = TemporalBlock([_u(SHORT), _u(LONG)], axis=0, sort_rows=False).axis
        assert from_setter == from_ctor
        assert type(from_setter) is type(from_ctor)

    def test_setter_still_rejects(self):
        blk = TemporalBlock([_u(SHORT), _u(LONG)], sort_rows=False)
        with pytest.raises(ValueError, match='Axis must be between -1 and 1'):
            blk.axis = 5

    def test_illegal_axis_cannot_survive_a_copy(self):
        """copy() goes through _adopt, which used to propagate it unchecked."""
        blk = TemporalBlock([_u(SHORT), _u(LONG)], sort_rows=False)
        with pytest.raises(ValueError):
            TemporalBlock._adopt(list(blk), axis=5, sort_rows=False)

    def test_nan_axis_rejected(self):
        with pytest.raises(ValueError, match='Axis must be between -1 and 1'):
            TemporalBlock([_u(SHORT)], axis=float('nan'), sort_rows=False)

    def test_rows_stay_inside_the_block_span(self):
        """The concrete harm: axis=5 pushed a row past the block's own end."""
        blk = TemporalBlock([_u(SHORT), _u(LONG)], axis=1, sort_rows=False)
        for row in blk:
            assert row.end <= abs(blk.duration) + 1e-9


class TestSortRowsDeprecation:
    """WL-32 — the default reorders rows; warn before flipping it."""

    def test_default_warns_when_it_actually_reorders(self):
        with pytest.warns(FutureWarning, match='sort_rows'):
            TemporalBlock([_u(SHORT), _u(LONG)])

    def test_explicit_true_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            TemporalBlock([_u(SHORT), _u(LONG)], sort_rows=True)

    def test_explicit_false_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            TemporalBlock([_u(SHORT), _u(LONG)], sort_rows=False)

    def test_single_row_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            TemporalBlock([_u(SHORT)])

    def test_already_ordered_rows_do_not_warn(self):
        """No reorder happened, so there is no exposure to the flip."""
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            TemporalBlock([_u(LONG), _u(SHORT)])

    def test_empty_block_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            TemporalBlock([])

    def test_copy_does_not_warn(self):
        """copy() passes sort_rows explicitly via _adopt."""
        blk = TemporalBlock([_u(SHORT), _u(LONG)], sort_rows=False)
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            blk.copy()

    def test_behavior_is_unchanged_the_flip_is_deferred(self):
        """R4: warn in 10.18, flip at the next major -- not now."""
        with pytest.warns(FutureWarning):
            blk = TemporalBlock([_u(SHORT), _u(LONG)])
        assert abs(blk[0].duration) > abs(blk[1].duration), \
            "default must still sort longest-first in 10.18"


class TestFromTreeMatCanSilenceTheWarning:
    """The trap: from_tree_mat constructs a block internally, so a user had
    no way to pass sort_rows and no way to silence the warning."""

    MAT = (((1, (1, 1)), (2, (1, 1, 1))),
           ((3, (1, 1, 1)), (1, (1, 1))))

    def test_from_tree_mat_accepts_sort_rows(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            TemporalBlock.from_tree_mat(self.MAT, sort_rows=False)

    def test_from_tree_mat_accepts_axis(self):
        blk = TemporalBlock.from_tree_mat(self.MAT, axis=0, sort_rows=False)
        assert blk.axis == 0.0

    def test_from_tree_mat_validates_axis(self):
        with pytest.raises(ValueError, match='Axis must be between -1 and 1'):
            TemporalBlock.from_tree_mat(self.MAT, axis=5, sort_rows=False)


class TestCopyOnAddIsDocumented:
    """WL-32 — rows are deep-copied and neither the fact nor its
    consequence appeared in the docstring."""

    def test_rows_are_copied_not_referenced(self):
        u = _u(SHORT)
        blk = TemporalBlock([u, _u(LONG)], sort_rows=False)
        assert not any(row is u for row in blk)

    def test_docstring_states_the_copy(self):
        doc = TemporalBlock.__doc__
        assert 'copied on entry' in doc

    def test_docstring_warns_about_row_order(self):
        assert 'not the order you passed' in TemporalBlock.__doc__

    def test_docstring_states_the_sort_is_destructive(self):
        assert 'destructive' in TemporalBlock.__doc__

    def test_mutator_docstrings_admit_position_is_not_honoured(self):
        for method in (TemporalBlock.append, TemporalBlock.prepend,
                       TemporalBlock.insert):
            assert 'sort_rows=False' in method.__doc__, method.__name__
