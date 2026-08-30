"""``interleave`` -- Haddad's *tuilage* (docket OPS-8).

Source: Haddad 2020 thesis sect4.6.2, pp. 133-134, figs. 4.80-4.83; the
2008 English original, pp. 30-32, where he glosses the term himself:

    « un tuilage (« interlocking ») »
    -- "a *tuilage* ('interlocking')"

and, p. 134, on why the operation interests him:

    « l'engendrement par son contraire utilisant le procede de diminution
    genere une fausse symetrie qui nous parait interessante »
    -- "generation by its opposite, using the diminution process,
    produces a *false symmetry* that seems interesting to us."

THE SOURCE-INCLUSIVE TRAP (recorded so nobody re-derives it). Fig. 4.82's
condensed formalism gives FOUR units per operand; the engravings of
fig. 4.80 show FIVE, because each erosion sequence begins with its own
source unit. The tuilage of fig. 4.81 therefore has TEN bars, not eight.
**Source-inclusion is a property of the OPERANDS, not of interleave** --
each erosion sequence carries its own seed -- so ``interleave`` is a pure
strict alternating zip with no ``include_source`` flag. Such a flag would
double-count whenever both operands already carry their seed. It belongs
on the generator instead, and that is where it shipped: OPS-7's
``iterate``, whose ``include_source`` defaults ``True``.

The A and B literals below are therefore hand-written from fig. 4.82 with
fig. 4.80's source prepended, which keeps this pin independent of OPS-3
(diminution) and OPS-7. ``TestGeneratedRoundTrip`` at the foot of this
file closes the loop the other way: ``iterate`` (OPS-7, shipped) builds
A and B from fig. 4.62's single source unit, and the tuilage of those two
generated sequences still reproduces fig. 4.81's ten bars. That is the
proof the two rows agree, and it is where ``include_source`` earns its
default -- turn it off and the tuilage has eight bars and matches
nothing.

Assertions are on the tempus VALUE and the real duration, never on
printed ``Meas`` spelling -- see ``test_segment.py`` for why that
distinction matters. Here the units pass through untouched, so both hold.
"""

from fractions import Fraction

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.chronos.temporal_units.algorithms import interleave


# fig. 4.80, upper stave: the source, then fig. 4.82's A (successive
# deletion of the FIRST prolatio).
A_SPEC = [
    ('1/1', ((2, (2, 1)), 1, 2, 1)),
    ('7/9', (2, 3, 6, 3)),
    ('2/3', (1, 2, 1)),
    ('3/6', (2, 1)),
    ('1/6', (1,)),
]

# fig. 4.80, lower stave: the source, then fig. 4.82's B (successive
# deletion of the LAST prolatio).
B_SPEC = [
    ('1/1', ((2, (2, 1)), 1, 2, 1)),
    ('15/18', (4, 2, 3, 6)),
    ('9/18', (4, 2, 3)),
    ('3/9', (2, 1)),
    ('2/9', (1,)),
]

# fig. 4.81, bar by bar.
FIG_4_81 = ['1/1', '2/9', '7/9', '3/9', '2/3', '9/18', '3/6', '15/18',
            '1/6', '1/1']


def _seq(spec):
    return TemporalUnitSequence(
        [TemporalUnit(tempus=t, prolatio=p) for t, p in spec]
    )


def _val(m):
    """The reduced value of a ``Meas``.

    NOT ``Fraction(meas)``: ``Meas`` is registered as ``numbers.Rational``
    and keeps raw, unreduced numerator/denominator, so ``Fraction(meas)``
    copies them verbatim and ``Fraction(Meas('4/4')) != Fraction(1, 1)``.
    Rebuilding from the two ints is what normalises.
    """
    return Fraction(m.numerator, m.denominator)


def _tempi(uts):
    return [_val(u.tempus) for u in uts.seq]


def _spellings(uts):
    return [str(u.tempus) for u in uts.seq]


class TestFig481Conformance:
    """The published tuilage, ten bars, in order."""

    def test_reproduces_figure_4_81(self):
        c = interleave(_seq(A_SPEC), _seq(B_SPEC))
        assert len(c.seq) == 10
        assert _tempi(c) == [Fraction(t) for t in FIG_4_81]
        # Legal here ONLY because interleave recomputes nothing:
        # the units pass through, so their raw spelling survives.
        assert _spellings(c) == FIG_4_81

    def test_source_unit_appears_twice(self):
        """The "false symmetry" frame: the seed heads C and also ends it.

        A is source-inclusive, so its seed is C[0]; B is source-inclusive
        too, and reversing B moves its seed to the tail of reverse(B),
        which lands last in the zip.
        """
        c = interleave(_seq(A_SPEC), _seq(B_SPEC))
        assert _val(c.seq[0].tempus) == Fraction(1, 1)
        assert _val(c.seq[9].tempus) == Fraction(1, 1)

    def test_a_is_not_a_contiguous_block(self):
        """A lands on the even indices, reverse(B) on the odd ones."""
        a, b = _seq(A_SPEC), _seq(B_SPEC)
        c = interleave(a, b)
        assert _tempi(c)[0::2] == _tempi(a)
        assert _tempi(c)[1::2] == [_val(u.tempus)
                                   for u in reversed(b.seq)]

    def test_prolationes_pass_through_untouched(self):
        a, b = _seq(A_SPEC), _seq(B_SPEC)
        c = interleave(a, b)
        expected = []
        for i, j in zip(a.seq, list(reversed(b.seq))):
            expected += [str(i.prolationis), str(j.prolationis)]
        assert [str(u.prolationis) for u in c.seq] == expected


class TestZipShape:
    def test_returns_a_single_voice_sequence(self):
        c = interleave(_seq(A_SPEC), _seq(B_SPEC))
        assert isinstance(c, TemporalUnitSequence)

    def test_strict_alternation_on_equal_lengths(self):
        a = _seq([('1/4', (1,)), ('2/4', (1,))])
        b = _seq([('3/4', (1,)), ('5/4', (1,))])
        assert _tempi(interleave(a, b)) == [
            Fraction(1, 4), Fraction(5, 4), Fraction(2, 4), Fraction(3, 4)
        ]

    def test_a_bare_unit_is_a_one_unit_operand(self):
        a = TemporalUnit(tempus='1/4', prolatio=(1,))
        b = _seq([('3/4', (1,))])
        assert _tempi(interleave(a, b)) == [Fraction(1, 4), Fraction(3, 4)]

    def test_a_list_of_units_is_an_operand(self):
        a = [TemporalUnit(tempus='1/4', prolatio=(1,))]
        b = [TemporalUnit(tempus='3/4', prolatio=(1,))]
        assert _tempi(interleave(a, b)) == [Fraction(1, 4), Fraction(3, 4)]


class TestAppendTail:
    """The recorded default for unequal lengths -- and it is NOT symmetric.

    Zip to ``min(len(A), len(reverse(B)))``, then append the longer
    operand's remaining units IN THEIR OWN TRAVERSAL ORDER. A's tail is
    therefore appended forward; B's tail is appended in reverse(B) order.
    The two argument orders are not reverses of each other.
    """

    A2 = [('1/1', (1,)), ('1/2', (1,)), ('1/4', (1,))]
    B2 = [('3/1', (1,))]

    def test_a_longer_appends_a_forward(self):
        c = interleave(_seq(self.A2), _seq(self.B2))
        assert _tempi(c) == [Fraction(1), Fraction(3), Fraction(1, 2),
                             Fraction(1, 4)]

    def test_b_longer_appends_reverse_b(self):
        c = interleave(_seq(self.B2), _seq(self.A2))
        assert _tempi(c) == [Fraction(3), Fraction(1, 4), Fraction(1, 2),
                             Fraction(1)]

    def test_the_two_orders_are_not_reverses(self):
        fwd = _tempi(interleave(_seq(self.A2), _seq(self.B2)))
        rev = _tempi(interleave(_seq(self.B2), _seq(self.A2)))
        assert fwd != list(reversed(rev))


class TestLossless:
    """No unit is dropped, so the duration is always the exact sum."""

    def test_equal_lengths(self):
        a, b = _seq(A_SPEC), _seq(B_SPEC)
        assert interleave(a, b).duration == pytest.approx(
            a.duration + b.duration)

    def test_unequal_lengths_both_ways(self):
        a = _seq(TestAppendTail.A2)
        b = _seq(TestAppendTail.B2)
        assert interleave(a, b).duration == pytest.approx(
            a.duration + b.duration)
        assert interleave(b, a).duration == pytest.approx(
            a.duration + b.duration)

    def test_unit_count_is_the_sum(self):
        a, b = _seq(A_SPEC), _seq(B_SPEC)
        assert len(interleave(a, b).seq) == len(a.seq) + len(b.seq)


class TestMixedTempoPassesThrough:
    """No arithmetic crosses operand boundaries, so each unit keeps its
    own beat/bpm and needs no tempo reconciliation."""

    def test_per_unit_tempo_survives(self):
        a = TemporalUnitSequence([
            TemporalUnit(tempus='4/4', prolatio=(1,), bpm=60),
            TemporalUnit(tempus='5/4', prolatio=(1,), beat='1/2', bpm=45),
        ])
        b = TemporalUnitSequence([
            TemporalUnit(tempus='3/8', prolatio=(1,), beat='1/8', bpm=120),
            TemporalUnit(tempus='2/4', prolatio=(1,), beat='1/4', bpm=90),
        ])
        c = interleave(a, b)
        assert [(u.beat, u.bpm) for u in c.seq] == [
            (Fraction(1, 4), 60), (Fraction(1, 4), 90),
            (Fraction(1, 2), 45), (Fraction(1, 8), 120),
        ]
        assert c.duration == pytest.approx(a.duration + b.duration)


class TestMembersAreCopies:
    def test_mutating_the_output_leaves_the_inputs_alone(self):
        a, b = _seq(A_SPEC), _seq(B_SPEC)
        c = interleave(a, b)
        assert c.seq[0] is not a.seq[0]
        assert c.seq[1] is not b.seq[-1]
        c.seq[0].leaves.first.make_rest()
        assert a.seq[0].leaves.first.is_rest is False


class TestEmptyOperands:
    def test_both_empty_is_an_empty_sequence(self):
        c = interleave(TemporalUnitSequence([]), TemporalUnitSequence([]))
        assert isinstance(c, TemporalUnitSequence)
        assert c.seq == []

    def test_one_empty_yields_the_other_in_its_own_order(self):
        a = _seq([('1/4', (1,)), ('2/4', (1,))])
        empty = TemporalUnitSequence([])
        assert _tempi(interleave(a, empty)) == [Fraction(1, 4), Fraction(2, 4)]
        # reverse(A) when A is the SECOND operand.
        assert _tempi(interleave(empty, a)) == [Fraction(2, 4), Fraction(1, 4)]


class TestRefusals:
    def test_a_block_refuses_loudly(self):
        block = TemporalBlock([_seq([('1/4', (1,))])])
        seq = _seq([('1/4', (1,))])
        with pytest.raises(ValueError) as exc:
            interleave(block, seq)
        msg = str(exc.value)
        assert 'TemporalBlock' in msg
        assert 'weave' in msg

    def test_a_block_refuses_in_either_position(self):
        block = TemporalBlock([_seq([('1/4', (1,))])])
        seq = _seq([('1/4', (1,))])
        with pytest.raises(ValueError):
            interleave(seq, block)

    def test_a_foreign_operand_is_a_type_error(self):
        with pytest.raises(TypeError):
            interleave(_seq([('1/4', (1,))]), 'not a sequence')


class TestCompositionalUnitsPassThrough:
    """Unlike ``fuse``, ``interleave`` merges nothing, so a
    ``CompositionalUnit`` needs no parameter-state reconciliation and
    rides through as an ordinary member (see the module docstring of
    ``temporal_units/algorithms.py``)."""

    def test_a_cu_member_survives(self):
        from klotho.thetos.composition.compositional import CompositionalUnit
        cu = CompositionalUnit(tempus='4/4', prolatio=(1, 1))
        b = _seq([('3/4', (1,))])
        c = interleave(cu, b)
        assert isinstance(c.seq[0], CompositionalUnit)
        assert _val(c.seq[0].tempus) == Fraction(1, 1)


class TestGeneratedRoundTrip:
    """The deferral this file opened, now closed: OPS-7's ``iterate``
    generates A and B, and their tuilage is still fig. 4.81.

    VALUES, not spellings. ``iterate`` builds Tempi raw (TEMPO-5) and
    does not chase his editorial reductions, so it prints A's first bar
    as ``14/18`` where he prints ``7/9`` and A's second as ``4/6`` where
    he prints ``2/3``. Same durations; that is the claim the whole
    operator family makes. B's four bars happen to print exactly as he
    does.
    """

    # fig. 4.62, the single source both sequences erode.
    SOURCE = ('1/1', ((2, (2, 1)), 1, 2, 1))

    def _source(self):
        return TemporalUnit(tempus=self.SOURCE[0], prolatio=self.SOURCE[1])

    def _generated_a(self):
        """Delete the FIRST prolatio each step."""
        from klotho.chronos.temporal_units.algorithms import iterate, diminish
        return iterate(self._source(), diminish)

    def _generated_b(self):
        """Delete the LAST prolatio each step -- his ``4 - i``."""
        from klotho.chronos.temporal_units.algorithms import iterate, diminish
        return iterate(self._source(), diminish, index=lambda i: 4 - i)

    def test_generated_a_matches_the_hand_written_literal(self):
        assert _tempi(self._generated_a()) == _tempi(_seq(A_SPEC))

    def test_generated_b_matches_the_hand_written_literal(self):
        assert _tempi(self._generated_b()) == _tempi(_seq(B_SPEC))

    def test_the_generated_tuilage_is_still_figure_4_81(self):
        c = interleave(self._generated_a(), self._generated_b())
        assert len(c.seq) == 10
        assert _tempi(c) == [Fraction(t) for t in FIG_4_81]

    def test_generated_and_literal_tuilages_agree(self):
        generated = interleave(self._generated_a(), self._generated_b())
        literal = interleave(_seq(A_SPEC), _seq(B_SPEC))
        assert _tempi(generated) == _tempi(literal)

    def test_without_source_inclusion_it_is_eight_bars_and_matches_nothing(self):
        """Why ``include_source`` defaults True, demonstrated.

        This is fig. 4.82's condensed formalism taken literally, and it
        is what the engravings contradict.
        """
        from klotho.chronos.temporal_units.algorithms import iterate, diminish
        a = iterate(self._source(), diminish, include_source=False)
        b = iterate(self._source(), diminish, include_source=False,
                    index=lambda i: 4 - i)
        c = interleave(a, b)
        assert len(c.seq) == 8
        assert _tempi(c) != [Fraction(t) for t in FIG_4_81]

    def test_the_seed_still_frames_the_generated_tuilage(self):
        """The "false symmetry": the source heads C and also ends it."""
        c = interleave(self._generated_a(), self._generated_b())
        assert _val(c.seq[0].tempus) == Fraction(1, 1)
        assert _val(c.seq[-1].tempus) == Fraction(1, 1)
