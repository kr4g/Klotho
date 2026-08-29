"""TEMPO-5 — modulation preserves unreduced tempus spelling.

`modulate_tempo` used to compute the new tempus through `Meas.__mul__`,
which gcd-reduces EVEN AT IDENTITY: a no-op reconciliation respelled
6/20 -> 3/10 and 4/4 -> 1/1, violating the irreducibility doctrine `Meas`
exists to protect (Haddad sect4.4.2/4.4.5: reducing a Tempus changes the
unit's *nature*). Ruled a prerequisite for the whole algebra (R13-D): any
reconciliation assembles the new tempus from RAW INTS, and the identity
reconciliation is a true no-op. Feasibility probe:
projects/klotho-evolution/evidence/layer1-probe/.
"""

import pytest

from klotho.chronos import TemporalUnit
from klotho.chronos.rhythm_trees import Meas
from klotho.chronos.temporal_units.algorithms import modulate_tempo


class TestIdentityIsANoOp:
    def test_6_20_keeps_its_spelling(self):
        ut = TemporalUnit(tempus='6/20', prolatio=(2, 1, 1), beat='1/4', bpm=60)
        out = modulate_tempo(ut, ut.beat, ut.bpm)
        assert out.tempus == Meas('6/20')  # Meas __eq__ is strict spelling

    def test_4_4_keeps_its_spelling(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        out = modulate_tempo(ut, ut.beat, ut.bpm)
        assert out.tempus == Meas('4/4')

    def test_identity_preserves_duration_bit_for_bit(self):
        ut = TemporalUnit(tempus='6/20', prolatio=(2, 1, 1), beat='1/4', bpm=60)
        assert modulate_tempo(ut, ut.beat, ut.bpm).duration == ut.duration


class TestReconciliation:
    def test_probe_case_3_20_at_eighth_90_to_quarter_60(self):
        # the LAYER-1 probe's exhibit: exact unreduced reconciliation at
        # the first operand's reference
        ut = TemporalUnit(tempus='3/20', prolatio=(1, 1, 1), beat='1/8', bpm=90)
        out = modulate_tempo(ut, '1/4', 60)
        assert out.tempus == Meas('12/60')
        assert out.duration == pytest.approx(ut.duration, abs=1e-12)

    def test_real_duration_preserved_per_leaf(self):
        ut = TemporalUnit(tempus='3/20', prolatio=(1, 1, 1), beat='1/8', bpm=90)
        out = modulate_tempo(ut, '1/4', 60)
        for a, b in zip(ut.durations, out.durations):
            assert a == pytest.approx(b, abs=1e-12)

    def test_span_folds_into_the_tempus_unreduced(self):
        # the span collapse is documented behavior; the fold now keeps
        # the denominator (span 2 of 6/20 -> 12/20, not 3/5)
        ut = TemporalUnit(span=2, tempus='6/20', prolatio=(2, 1, 1),
                          beat='1/4', bpm=60)
        out = modulate_tempo(ut, ut.beat, ut.bpm)
        assert out.span == 1
        assert out.tempus == Meas('12/20')
        assert out.duration == pytest.approx(ut.duration, abs=1e-12)

    def test_float_bpm_snaps_to_the_intended_rational(self):
        # exactness map (06_HADDAD_PROBLEM sect3.6): tempo floats are
        # recovered by limit_denominator(10**6) -- 87.3 is exactly 873/10
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                          beat='1/4', bpm=87.3)
        out = modulate_tempo(ut, '1/4', 87.3)
        assert out.tempus == Meas('4/4')
