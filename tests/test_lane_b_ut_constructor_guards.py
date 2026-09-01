"""SPAN-GUARD and RT-30 — two more doors on the ``TemporalUnit`` constructor.

Both sit beside the ``beat=0`` / ``bpm=0`` refusals of R13-F
(``tests/test_ut_constructor_contract.py``) and share their register: nothing
is inferred, nothing is repaired, the offending value is named.

**SPAN-GUARD.** ``span`` was never validated. Three shapes got through:

- ``UT(span=0.5)`` -- *blessed by the constructor's own type hint*, which
  advertised ``float`` -- built fine, reported ``.duration == 2.0``, and then
  raised ``AttributeError: 'float' object has no attribute 'numerator'`` on
  ``.events``. The hint was part of the defect and is corrected to
  ``Union[int, Fraction]``.
- ``UT(span=-1)`` built silently with ``.duration == -4.0``: a negative real
  duration that flows into sequences and blocks as a backwards, overlapping
  timeline.
- ``UT(span=0)`` gave ``.duration == 0.0``.

A non-integer ``Fraction`` span is deliberately still ACCEPTED. It is the one
shape of the four that was never broken: ``UT(span=Fraction(1, 2),
tempus='4/4')`` is event-for-event identical to ``UT(tempus='2/4')`` today, so
refusing it would remove working behaviour rather than guard a defect.

**RT-30, the TemporalUnit door.** ``UT(tempus='6/8', prolatio=())`` reported
``.duration == 6.0`` while its single event ran ``36.0`` seconds -- six times
longer, the tempus numerator. An empty ``S`` builds a tree with only a root, so
the root is its own single event and carries ``Meas.numerator * span`` as its
metric duration instead of the measure.

Only the TOP-LEVEL empty tuple is refused. A NESTED empty group is legitimate
and is real emitted data -- ``(1, (1, ()))`` gives durations summing to 1, and
``tests/test_decompose.py``'s ``ASYM_S`` contains exactly that shape.
"""

from fractions import Fraction

import pytest

from klotho.chronos import TemporalUnit
from klotho.thetos.composition.compositional import CompositionalUnit


class TestSpanRefusals:

    @pytest.mark.parametrize('span', [0.5, 2.0, -0.5, 0.0])
    def test_a_float_span_is_refused(self, span):
        with pytest.raises(ValueError, match='span'):
            TemporalUnit(span=span, tempus='4/4', prolatio='d')

    def test_the_float_message_names_the_value_and_the_way_out(self):
        with pytest.raises(ValueError) as excinfo:
            TemporalUnit(span=0.5, tempus='4/4', prolatio='d')
        message = str(excinfo.value)
        assert '0.5' in message
        assert 'Fraction' in message
        assert "tempus='2/4'" in message

    def test_zero_is_refused(self):
        with pytest.raises(ValueError, match='span'):
            TemporalUnit(span=0, tempus='4/4', prolatio='d')

    @pytest.mark.parametrize('span', [-1, -3, Fraction(-1, 2)])
    def test_a_negative_span_is_refused(self, span):
        with pytest.raises(ValueError, match='span'):
            TemporalUnit(span=span, tempus='4/4', prolatio='d')

    def test_a_string_span_is_refused(self):
        with pytest.raises(ValueError, match='span'):
            TemporalUnit(span='2', tempus='4/4', prolatio='d')

    def test_uc_delegates_the_guard(self):
        with pytest.raises(ValueError, match='span'):
            CompositionalUnit(span=0.5, tempus='4/4', prolatio='d')


class TestSpanStillAcceptsWhatWorked:
    """A guard must not change behaviour for valid input."""

    @pytest.mark.parametrize('span,expected', [(1, 4.0), (2, 8.0), (3, 12.0)])
    def test_whole_measure_spans_are_unchanged(self, span, expected):
        ut = TemporalUnit(span=span, tempus='4/4', prolatio='d', bpm=60)
        assert ut.duration == pytest.approx(expected)
        assert len(ut.events) == 1

    def test_a_fractional_fraction_span_still_works(self):
        """Never broken, so never refused -- and it agrees with the tempus form."""
        half = TemporalUnit(span=Fraction(1, 2), tempus='4/4',
                            prolatio=(1, 1), bpm=60)
        ref = TemporalUnit(tempus='2/4', prolatio=(1, 1), bpm=60)
        assert half.duration == pytest.approx(ref.duration)
        assert (half.events.drop(columns=['metric_onset']).values.tolist()
                == ref.events.drop(columns=['metric_onset']).values.tolist())

    def test_a_whole_number_fraction_span_still_works(self):
        ut = TemporalUnit(span=Fraction(2, 1), tempus='4/4',
                          prolatio='d', bpm=60)
        assert ut.duration == pytest.approx(8.0)


class TestEmptyProlatioRefused:

    def test_a_top_level_empty_prolatio_is_refused(self):
        with pytest.raises(ValueError) as excinfo:
            TemporalUnit(tempus='6/8', prolatio=())
        message = str(excinfo.value)
        # H1: a parallel guard at the RhythmTree door raises for the same
        # input with a `subdivisions`-flavoured message. Matching on
        # `prolatio` is what proves THIS door fired.
        assert 'prolatio' in message
        assert 'empty' in message

    def test_the_message_names_the_factor_and_the_way_out(self):
        with pytest.raises(ValueError) as excinfo:
            TemporalUnit(tempus='6/8', prolatio=())
        message = str(excinfo.value)
        assert '6x' in message      # the tempus numerator, the real factor
        assert "'d'" in message

    def test_uc_delegates_the_guard(self):
        with pytest.raises(ValueError, match='prolatio'):
            CompositionalUnit(tempus='4/4', prolatio=())


class TestNestedEmptyGroupsStillBuild:
    """``(D, ())`` is correct today and is real emitted data -- do not refuse it."""

    def test_a_nested_empty_group_still_builds(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, (1, ())), bpm=60)
        assert ut._rt.durations == (Fraction(1, 2), Fraction(1, 2))
        assert ut.duration == pytest.approx(4.0)

    def test_the_decompose_corpus_shape_still_builds(self):
        asym = ((3, ((1, (2, 1, 1)), (2, (1, 1)), (1, ()))),
                (2, ((1, (3, 1, 2)), (1, (1, 1, 1)))),
                (1, ()))
        ut = TemporalUnit(tempus='4/4', prolatio=asym, bpm=60)
        assert sum(ut._rt.durations) == Fraction(1, 1)

    @pytest.mark.parametrize('prolatio', ['d', 'r', 'p', (1,), (1, 1, 1)])
    def test_the_ordinary_prolatio_shapes_are_untouched(self, prolatio):
        ut = TemporalUnit(tempus='4/4', prolatio=prolatio, bpm=60)
        assert ut.duration == pytest.approx(4.0)
