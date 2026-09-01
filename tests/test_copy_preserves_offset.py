"""``copy()`` preserves placement (``_offset``) on all four containers.

Every one of ``TemporalUnit.copy``, ``TemporalUnitSequence.copy``,
``TemporalBlock.copy`` and ``CompositionalUnit.copy`` states offset
preservation in its own docstring, and each gives the same reason: it is
what lets a container (``TemporalUnitSequence``, ``TemporalBlock``,
``Score``) rebuild its layout by copying its members. Nothing asserted
it. A mutation sweep set each ``c._offset`` to ``0.0`` in turn and the
full suite stayed green all four times -- so four containers could have
silently forgotten where they sit, and every rebuilt layout would have
collapsed to time zero with no exception anywhere.

**These tests read through the PUBLIC placement path, not ``_offset``.**
An object is placed by being the second member of a sequence whose first
member lasts four seconds, and the placement is read back as ``.start``.
That matters: a test that sets ``_offset`` by hand and reads it back is a
test of attribute assignment, and it will pass against a ``copy()`` that
no container can actually use. Here the offset is assigned by the
sequence, the way real code assigns it, and read by the same accessor
the lowering walk uses.

Note that ``TemporalUnitSequence`` COPIES its members on construction, so
``UTS([lead, obj])[1]`` -- not ``obj`` -- is the placed object. That is
itself the mechanism under test: the sequence placed a copy, so if
``copy()`` dropped the offset the member would already be wrong.

These are tests only. ``copy()`` is correct as written.
"""

import warnings

import pytest

from klotho.chronos import (
    TemporalUnit as UT,
    TemporalUnitSequence as UTS,
    TemporalBlock as BT,
)
from klotho.thetos import CompositionalUnit as UC


LEAD_SECONDS = 4.0


def _lead():
    """A 4/4 bar at 60 bpm: exactly ``LEAD_SECONDS`` long."""
    return UT(tempus='4/4', prolatio=(1,), bpm=60)


def _placed(obj):
    """Put *obj* second in a sequence and return the placed member.

    The sequence assigns the offset; the returned object is the
    sequence's own member (sequences copy on construction), so it is
    already the product of one ``copy()`` at a non-zero offset.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return UTS([_lead(), obj])[1]


def _unit():
    return UT(tempus='4/4', prolatio=(1, 1), bpm=60)


def _sequence():
    return UTS([UT(tempus='4/4', prolatio=(1, 1), bpm=60)])


def _block():
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return BT([UTS([UT(tempus='4/4', prolatio=(1, 1), bpm=60)])],
                  sort_rows=False)


def _compositional():
    return UC(tempus='4/4', prolatio=(1, 1), bpm=60)


BUILDERS = [
    pytest.param(_unit, id='TemporalUnit'),
    pytest.param(_sequence, id='TemporalUnitSequence'),
    pytest.param(_block, id='TemporalBlock'),
    pytest.param(_compositional, id='CompositionalUnit'),
]


@pytest.mark.parametrize('build', BUILDERS)
class TestCopyPreservesPlacement:
    def test_the_fixture_really_is_placed(self, build):
        """Guard on the test itself: if the sequence stopped assigning the
        offset, every assertion below would pass for the wrong reason."""
        assert _placed(build()).start == pytest.approx(LEAD_SECONDS)

    def test_copy_keeps_the_placement(self, build):
        placed = _placed(build())
        assert placed.copy().start == pytest.approx(LEAD_SECONDS)

    def test_copy_of_an_unplaced_object_stays_at_zero(self, build):
        """The other half of preservation: it copies the offset, it does
        not invent one."""
        assert build().copy().start == pytest.approx(0.0)

    def test_copy_returns_the_same_type(self, build):
        obj = build()
        assert type(obj.copy()) is type(obj)

    def test_a_copy_can_be_re_placed_without_inheriting_the_old_offset(
            self, build):
        """What the containers actually do with the copy: a member copied
        out of one sequence and put into another takes the new
        sequence's placement, not the old one."""
        placed = _placed(build())
        re_placed = UTS([placed.copy()])[0]
        assert re_placed.start == pytest.approx(0.0)


def test_every_copy_docstring_still_claims_offset_preservation():
    """The four docstrings are the reason these tests exist; if one is
    rewritten to drop the claim, the claim should be re-litigated rather
    than quietly diverge from the tests below it."""
    import inspect
    for cls in (UT, UTS, BT, UC):
        doc = inspect.getdoc(cls.copy) or ''
        assert '_offset' in doc, f'{cls.__name__}.copy stopped claiming it'
