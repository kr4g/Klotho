"""LAYER-5 — the TemporalUnit constructor contract (ruling R13-F; NEW-38/39).

Three rules, ruled 2026-08-29:

- ``beat=0`` / ``bpm=0`` RAISE. Never inferred, never coerced — the old
  truthiness test silently replaced explicit zeros with the defaults
  (NEW-38), the exact silent-corruption class W0 exists for.
- ``beat=None`` / ``bpm=None`` are honest defaults (1/tempus-denominator
  and 60), never "tempo-free": the tempo-free object is the RhythmTree.
- The constructor records WHICH slots were explicitly given
  (``ut.attributed``) — NEW-39's prerequisite. Only the constructor ever
  knows (``UT(bpm=60)`` is attributed AT the default value); free to
  record now, unrecoverable later. Inert metadata until the ambient
  context lands. Design record: 06_HADDAD_PROBLEM.md Appendix A.
"""

from fractions import Fraction

import pytest

from klotho.chronos import TemporalUnit
from klotho.thetos.composition.compositional import CompositionalUnit


class TestZerosRaise:
    def test_beat_zero_raises(self):
        with pytest.raises(ValueError, match='beat'):
            TemporalUnit(tempus='4/4', prolatio='p', beat=0)

    def test_bpm_zero_raises(self):
        with pytest.raises(ValueError, match='bpm'):
            TemporalUnit(tempus='4/4', prolatio='p', bpm=0)

    def test_bpm_zero_float_raises(self):
        with pytest.raises(ValueError, match='bpm'):
            TemporalUnit(tempus='4/4', prolatio='p', bpm=0.0)

    def test_uc_delegates_the_guard(self):
        with pytest.raises(ValueError, match='bpm'):
            CompositionalUnit(tempus='4/4', prolatio='p', bpm=0)

    def test_from_rt_delegates_the_guard(self):
        ut = TemporalUnit(tempus='4/4', prolatio='p')
        with pytest.raises(ValueError, match='beat'):
            TemporalUnit.from_rt(ut.rt, beat=0)


class TestHonestDefaults:
    def test_default_beat_is_one_over_the_tempus_denominator(self):
        # the true default -- NOT a universal 1/4 (two records mis-stated it)
        assert TemporalUnit(tempus='6/8', prolatio='p').beat == Fraction(1, 8)
        assert TemporalUnit(tempus='4/4', prolatio='p').beat == Fraction(1, 4)

    def test_default_bpm_is_60(self):
        assert TemporalUnit(tempus='4/4', prolatio='p').bpm == 60


class TestAttribution:
    def test_bare_constructor_attributes_nothing(self):
        assert TemporalUnit().attributed == frozenset()

    def test_each_slot_records_independently(self):
        assert TemporalUnit(tempus='4/4').attributed == frozenset({'tempus'})
        assert TemporalUnit(bpm=96).attributed == frozenset({'bpm'})
        assert TemporalUnit(beat='1/4').attributed == frozenset({'beat'})

    def test_attributed_at_the_default_value_still_counts(self):
        # UT(bpm=60) is attributed AT the default -- the flag cannot be
        # reconstructed from values later, which is the whole point
        assert 'bpm' in TemporalUnit(bpm=60).attributed

    def test_explicitly_passing_the_default_tempus_counts(self):
        # without the sentinel, UT() and UT(tempus='4/4') would be
        # indistinguishable -- and that distinction IS the semantics under
        # a future ambient dial (the second stays sticky, the first follows)
        assert TemporalUnit(tempus='4/4').attributed == frozenset({'tempus'})

    def test_copy_carries_the_flag(self):
        ut = TemporalUnit(tempus='7/8', bpm=90)
        assert ut.copy().attributed == ut.attributed

    def test_uc_records_attribution_too(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1), bpm=120)
        assert uc.attributed == frozenset({'tempus', 'bpm'})

    def test_bare_uc_attributes_nothing(self):
        assert CompositionalUnit().attributed == frozenset()

    def test_uc_copy_carries_the_flag(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1), bpm=120)
        assert uc.copy().attributed == uc.attributed

    def test_existing_bpm_pins_untouched(self):
        # day-one consumers: none; the suite's ut.bpm == 60 pins hold
        assert TemporalUnit().bpm == 60
