import math
from fractions import Fraction

import pytest

from klotho.tonos import (
    Scale, Chord, Voicing, ChordSequence, Pitch,
    fold, voice_lead, cent, ratio, frequency,
)
from klotho.tonos.pitch.pitch_collections import (
    AbsolutePitchCollection, RelativePitchCollection,
)

G3 = Pitch('G3').freq
G4 = Pitch('G4').freq


def _in_window(voicing, lo_hz, hi_hz, tol=1e-6):
    return all(lo_hz - tol <= p.freq <= hi_hz + tol for p in voicing.pitches)


class TestFold:
    def test_fold_ratios_into_window(self):
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C5')
        voicing = fold(chord, lo='G3', hi='G4')
        assert isinstance(voicing, Voicing)
        assert _in_window(voicing, G3, G4)

    def test_fold_cents_into_window(self):
        voicing = fold(Voicing([0.0, 400.0, 700.0], interval_type='cents',
                               reference_pitch='C5'),
                       lo='G3', hi='G4')
        assert _in_window(voicing, G3, G4)
        assert all(isinstance(d, float) for d in voicing.degrees)

    def test_fold_preserves_pitch_classes(self):
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C5')
        voicing = fold(chord, lo='G2', hi='G3')
        original = sorted(p.freq for p in chord.pitches)
        folded = sorted(p.freq for p in voicing.pitches)
        for f in folded:
            octaves = [abs(math.log2(f / o)) % 1 for o in original]
            assert any(x < 1e-4 or x > 1 - 1e-4 for x in octaves)

    def test_lo_only_and_hi_only(self):
        chord = Chord(['1/2', '1/1', '4/1'], reference_pitch='C4')
        lo_only = fold(chord, lo='C4')
        assert all(p.freq >= Pitch('C4').freq - 1e-6 for p in lo_only.pitches)
        hi_only = fold(chord, hi='C4')
        assert all(p.freq <= Pitch('C4').freq + 1e-6 for p in hi_only.pitches)

    def test_no_bounds_is_identity(self):
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        voicing = fold(chord)
        assert voicing.degrees == chord.degrees

    def test_bound_types(self):
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        by_str = fold(chord, lo='G3', hi='G4')
        by_pitch = fold(chord, lo=Pitch('G3'), hi=Pitch('G4'))
        by_freq = fold(chord, lo=frequency(G3), hi=frequency(G4))
        assert by_str.degrees == by_pitch.degrees == by_freq.degrees
        # relative bounds resolve against the reference pitch (C4)
        by_ratio = fold(chord, lo=ratio('3/4'), hi=ratio('3/2'))
        c4 = Pitch('C4').freq
        assert _in_window(by_ratio, c4 * 0.75, c4 * 1.5)
        by_cent = fold(chord, lo=cent(-500), hi=cent(700))
        assert _in_window(by_cent, c4 * 2 ** (-500 / 1200), c4 * 2 ** (700 / 1200))

    def test_bare_number_bound_rejected(self):
        chord = Chord(['1/1', '5/4', '3/2'])
        with pytest.raises(TypeError, match='ambiguous'):
            fold(chord, lo=196.0)
        with pytest.raises(TypeError, match='ambiguous'):
            fold(chord, hi=392)

    def test_scale_rejected(self):
        with pytest.raises(TypeError, match='Scale'):
            fold(Scale.ionian('C4'), lo='G3')

    def test_absolute_collection_rejected(self):
        coll = AbsolutePitchCollection(['C4', 'E4', 'G4'])
        with pytest.raises(TypeError, match='relative'):
            fold(coll, lo='G3')

    def test_relative_pitch_collection_accepted(self):
        coll = RelativePitchCollection(['1/1', '3/2'], reference_pitch='C6')
        voicing = fold(coll, lo='G3', hi='G4')
        assert isinstance(voicing, Voicing)
        assert _in_window(voicing, G3, G4)

    def test_inverted_bounds_rejected(self):
        with pytest.raises(ValueError):
            fold(Chord(['1/1', '3/2']), lo='G4', hi='G3')

    def test_window_narrower_than_equave_never_hangs(self):
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        voicing = fold(chord, lo='C4', hi='E4')
        # every degree lands at its placement nearest the window
        assert len(voicing.pitches) == 3
        for p in voicing.pitches:
            below = p.freq / 2
            above = p.freq * 2
            def viol(f):
                if f < Pitch('C4').freq:
                    return math.log(Pitch('C4').freq / f)
                if f > Pitch('E4').freq:
                    return math.log(f / Pitch('E4').freq)
                return 0.0
            assert viol(p.freq) <= min(viol(below), viol(above)) + 1e-9

    def test_custom_equave_displacement(self):
        chord = Chord(['1/1', '3/2'], equave='3/1', reference_pitch='C6')
        voicing = fold(chord, lo='C3', hi='C5')
        original = [p.freq for p in chord.pitches]
        for p in voicing.pitches:
            steps = [math.log(o / p.freq) / math.log(3) for o in original]
            assert any(abs(s - round(s)) < 1e-4 for s in steps)


class TestVoiceLead:
    def test_first_chord_keeps_voicing_folded(self):
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C6'),
               Chord(['1/1', '6/5', '3/2'], reference_pitch='A3')]
        led = voice_lead(seq, lo='G3', hi='G4')
        assert len(led) == 2
        assert all(isinstance(v, Voicing) for v in led)
        assert _in_window(led[0], G3, G4)

    def test_minimal_motion_between_chords(self):
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
               Chord(['1/1', '5/4', '3/2'], reference_pitch='G4')]
        led = voice_lead(seq)
        prev = sorted(p.freq for p in led[0].pitches)
        cur = sorted(p.freq for p in led[1].pitches)
        # every voice lands within half an equave of its nearest predecessor
        for f in cur:
            assert min(abs(math.log2(f / p)) for p in prev) <= 0.5 + 1e-6
        # C major -> G major with nearest matching keeps the common tone G
        assert any(abs(math.log2(f / Pitch('G4').freq)) < 1e-4 for f in cur)

    def test_bounds_enforced_on_all_chords(self):
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C6'),
               Chord(['1/1', '6/5', '3/2'], reference_pitch='C2'),
               Chord(['1/1', '5/4', '3/2'], reference_pitch='F5')]
        led = voice_lead(seq, lo='G2', hi='G5')
        for voicing in led:
            assert _in_window(voicing, Pitch('G2').freq, Pitch('G5').freq)

    def test_mixed_ratio_and_cents_sequences(self):
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
               Voicing([0.0, 300.0, 700.0], interval_type='cents',
                       reference_pitch='A3'),
               Chord(['1/1', '6/5', '3/2'], reference_pitch='F4')]
        led = voice_lead(seq, lo='G2', hi='G5')
        assert len(led) == 3
        for prev, cur in zip(led, led[1:]):
            prev_hz = sorted(p.freq for p in prev.pitches)
            cur_hz = sorted(p.freq for p in cur.pitches)
            assert all(abs(math.log2(a / b)) <= 0.5 + 1e-9
                       for a, b in zip(cur_hz, prev_hz))

    def test_different_cardinalities(self):
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
               Chord(['1/1', '5/4', '3/2', '7/4'], reference_pitch='D4'),
               Chord(['1/1', '3/2'], reference_pitch='C4')]
        led = voice_lead(seq, lo='G2', hi='G5')
        assert [len(v.pitches) for v in led] == [3, 4, 2]

    def test_empty_sequence(self):
        assert voice_lead([]) == []

    def test_degree_types_preserved(self):
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C6'),
               Voicing([0.0, 400.0], interval_type='cents', reference_pitch='C2')]
        led = voice_lead(seq, lo='G3', hi='G4')
        assert all(isinstance(d, Fraction) for d in led[0].degrees)
        assert all(isinstance(d, float) for d in led[1].degrees)


class TestChordSequenceMethods:
    def test_folded_returns_new_sequence(self):
        seq = ChordSequence([Chord(['1/1', '5/4', '3/2'], reference_pitch='C6'),
                             Chord(['1/1', '6/5', '3/2'], reference_pitch='C2')])
        folded = seq.folded(lo='G3', hi='G4')
        assert isinstance(folded, ChordSequence)
        assert len(folded) == 2
        for voicing in folded:
            assert isinstance(voicing, Voicing)
            assert _in_window(voicing, G3, G4)
        # original untouched
        assert isinstance(seq[0], Chord)

    def test_voice_led_returns_new_sequence(self):
        seq = ChordSequence([Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
                             Chord(['1/1', '6/5', '3/2'], reference_pitch='A3'),
                             Chord(['1/1', '5/4', '3/2'], reference_pitch='F4')])
        led = seq.voice_led(lo='G2', hi='G5')
        assert isinstance(led, ChordSequence)
        assert len(led) == 3
        for prev, cur in zip(led, list(led)[1:]):
            prev_hz = sorted(p.freq for p in prev.pitches)
            cur_hz = sorted(p.freq for p in cur.pitches)
            assert all(abs(math.log2(a / b)) <= 0.5 + 1e-9
                       for a, b in zip(cur_hz, prev_hz))


def _greedy_total_motion(prev_hz, voicing):
    """Reference: per-voice independent nearest-neighbor total motion."""
    total = 0.0
    for p in voicing.pitches:
        total += min(abs(math.log2(p.freq / q)) for q in prev_hz)
    return total


class TestVoiceLeadQuality:
    def test_spread_voicing_does_not_collapse(self):
        # The pre-10.13 per-degree snapping turned this 2-octave spread
        # into a 2-semitone cluster.
        seq = [Voicing(['1/1', '2/1', '4/1'], reference_pitch='C4'),
               Chord(['1/1', '16/15', '15/8'], reference_pitch='C5')]
        led = voice_lead(seq, 'C3', 'C7')
        freqs = sorted(p.freq for p in led[1].pitches)
        spread = math.log2(freqs[-1] / freqs[0])
        assert spread > 1.5

    def test_assignment_no_worse_than_greedy(self):
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
               Chord(['1/1', '9/8', '45/32', '5/3'], reference_pitch='E4'),
               Chord(['1/1', '6/5', '3/2'], reference_pitch='B3')]
        led = voice_lead(seq, 'C3', 'C6')
        for prev, cur in zip(led, led[1:]):
            prev_hz = [p.freq for p in prev.pitches]
            total = 0.0
            for p in cur.pitches:
                total += min(abs(math.log2(p.freq / q)) for q in prev_hz)
            assert total <= _greedy_total_motion(prev_hz, cur) + 1e-9

    def test_common_tone_held(self):
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
               Chord(['1/1', '5/4', '3/2'], reference_pitch='G4')]
        led = voice_lead(seq)
        cur = [p.freq for p in led[1].pitches]
        g4 = Pitch('G4').freq
        assert any(abs(math.log2(f / g4)) < 1e-4 for f in cur)

    def test_result_cardinality_matches_input(self):
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
               Chord(['1/1', '5/4', '3/2', '7/4', '9/8'], reference_pitch='A4')]
        led = voice_lead(seq, 'C3', 'C6')
        assert [len(v.pitches) for v in led] == [3, 5]


class TestVoicesParameter:
    def _triads(self):
        return [Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
                Chord(['1/1', '5/4', '3/2'], reference_pitch='G4'),
                Chord(['1/1', '5/4', '3/2'], reference_pitch='F4')]

    def test_fixed_voice_count_with_doubling(self):
        led = voice_lead(self._triads(), 'C3', 'C6', voices=4)
        for v in led:
            assert len(v.pitches) == 4
            assert _in_window(v, Pitch('C3').freq, Pitch('C6').freq)

    def test_first_chord_doubles_the_root(self):
        # 4:5:6 doubling practice emerges from Barlow simplicity: the root
        # forms the simplest interval classes with the whole sonority.
        led = voice_lead(self._triads(), 'C3', 'C6', voices=4)
        c4 = Pitch('C4').freq
        pcs = sorted(round(1200 * math.log2(p.freq / c4)) % 1200
                     for p in led[0].pitches)
        assert pcs.count(0) == 2  # root doubled at the octave

    def test_all_chord_tones_present(self):
        led = voice_lead(self._triads(), 'C3', 'C6', voices=4)
        for v, ch in zip(led, self._triads()):
            got = {round(1200 * math.log2(p.freq / ch.reference_pitch.freq)) % 1200
                   for p in v.pitches}
            want = {round(1200 * math.log2(float(d))) % 1200 for d in ch.degrees}
            assert want <= got

    def test_voices_smaller_than_cardinality_raises(self):
        with pytest.raises(ValueError, match='more than'):
            voice_lead([Chord(['1/1', '5/4', '3/2', '7/4'])], voices=3)

    def test_doubling_nearest_and_explicit(self):
        led_nearest = voice_lead(self._triads(), 'C3', 'C6', voices=4,
                                 doubling='nearest')
        assert all(len(v.pitches) == 4 for v in led_nearest)
        led_third = voice_lead(self._triads(), 'C3', 'C6', voices=4,
                               doubling=1)
        c4 = Pitch('C4').freq
        pcs = sorted(round(1200 * math.log2(p.freq / c4)) % 1200
                     for p in led_third[0].pitches)
        assert pcs.count(386) == 2  # explicit: the third (5/4) is doubled

    def test_cents_mode_triad_doubles_root_equivalent(self):
        # 12-TET spelling: rational inference still finds the root.
        seq = [Chord([0.0, 400.0, 700.0], 'cents', reference_pitch='C4'),
               Chord([0.0, 400.0, 700.0], 'cents', reference_pitch='G4')]
        led = voice_lead(seq, 'C3', 'C6', voices=4)
        c4 = Pitch('C4').freq
        pcs = sorted(round(1200 * math.log2(p.freq / c4)) % 1200
                     for p in led[0].pitches)
        assert pcs.count(0) == 2

    def test_unison_doubling_survives_conversion(self):
        from klotho.utils.playback.supersonic.converters import chord_to_sc_events
        v = Voicing(['1/1', '1/1', '3/2'], dedupe=False)
        assert len(v.pitches) == 3
        events = chord_to_sc_events(v, duration=0.5)
        news = [ev for ev in events if ev['type'] == 'new']
        assert len(news) == 3


class TestAnchors:
    def _seq(self):
        return [Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
                Chord(['1/1', '6/5', '3/2'], reference_pitch='A3'),
                Chord(['1/1', '5/4', '3/2'], reference_pitch='F4')]

    def test_anchor_passes_through_verbatim(self):
        v = Voicing(['1/1', '5/4', '2/1'], reference_pitch='D4')
        seq = [Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'), v,
               Chord(['1/1', '6/5', '3/2'], reference_pitch='A3')]
        led = voice_lead(seq, 'C3', 'C5', anchor=1)
        assert [p.freq for p in led[1].pitches] == [p.freq for p in v.pitches]

    def test_anchor_exempt_from_bounds(self):
        v = Voicing(['1/1', '5/4', '3/2'], reference_pitch='C7')  # above hi
        seq = self._seq() + [v]
        led = voice_lead(seq, 'C3', 'C5', anchor=3)
        assert [p.freq for p in led[3].pitches] == [p.freq for p in v.pitches]
        # free chords still bounded
        for i in (0, 1, 2):
            assert _in_window(led[i], Pitch('C3').freq, Pitch('C5').freq)

    def test_anchor_single_int_and_negative(self):
        seq = self._seq()
        by_int = voice_lead(seq, 'C3', 'C5', anchor=2)
        by_neg = voice_lead(seq, 'C3', 'C5', anchor=-1)
        assert [[p.freq for p in a.pitches] for a in by_int] == \
               [[p.freq for p in b.pitches] for b in by_neg]

    def test_anchor_out_of_range_raises(self):
        with pytest.raises(IndexError):
            voice_lead(self._seq(), anchor=5)

    def test_anchored_first_chord_not_folded(self):
        c = Chord(['1/1', '5/4', '3/2'], reference_pitch='C6')  # above hi
        led = voice_lead([c] + self._seq()[1:], 'C3', 'C5', anchor=0)
        assert [p.freq for p in led[0].pitches] == [p.freq for p in c.pitches]

    def test_adjacent_anchors(self):
        seq = self._seq()
        led = voice_lead(seq, 'C3', 'C5', anchor=[0, 1])
        for i in (0, 1):
            assert [p.freq for p in led[i].pitches] == \
                   [p.freq for p in seq[i].pitches]

    def test_drift_distributes_register_gap(self):
        a0 = Voicing(['1/1', '5/4', '3/2'], reference_pitch='C3')
        a4 = Voicing(['1/1', '5/4', '3/2'], reference_pitch='C6')
        mids = [Chord(['1/1', '6/5', '3/2'], reference_pitch='A3'),
                Chord(['1/1', '5/4', '3/2'], reference_pitch='F3'),
                Chord(['1/1', '6/5', '3/2'], reference_pitch='D4')]
        led = voice_lead([a0] + mids + [a4], anchor=[0, 4])
        centroids = [sum(math.log2(p.freq) for p in v.pitches) / len(v.pitches)
                     for v in led]
        steps = [b - a for a, b in zip(centroids, centroids[1:])]
        # monotone climb, no step carrying more than half the total gap
        total = centroids[-1] - centroids[0]
        assert all(s > 0 for s in steps)
        assert max(steps) < total / 2

    def test_anchor_with_voices_extends_without_moving(self):
        v = Voicing(['1/1', '5/4', '3/2'], reference_pitch='D4')
        led = voice_lead([self._seq()[0], v], 'C3', 'C6', voices=4, anchor=1)
        anchored = [p.freq for p in led[1].pitches]
        assert len(anchored) == 4
        for f in [p.freq for p in v.pitches]:
            assert any(abs(g - f) < 1e-6 for g in anchored)


class TestChordSequenceConcatenation:
    def _seq(self, n=1):
        return ChordSequence([Chord(['1/1', '5/4', '3/2'])] * n)

    def test_add_sequences(self):
        s = self._seq(2) + self._seq(3)
        assert isinstance(s, ChordSequence) and len(s) == 5

    def test_add_list_and_radd(self):
        assert len(self._seq(1) + [Chord(['1/1', '3/2'])]) == 2
        assert len([Chord(['1/1', '3/2'])] + self._seq(1)) == 2

    def test_mul(self):
        assert len(self._seq(2) * 3) == 6
        assert len(3 * self._seq(2)) == 6

    def test_iadd_rebinds(self):
        s = self._seq(1)
        orig = s
        s += self._seq(1)
        assert len(s) == 2 and len(orig) == 1

    def test_foreign_types_rejected(self):
        with pytest.raises(TypeError):
            self._seq(1) + 42
        with pytest.raises(TypeError):
            self._seq(1) + ['not a chord']

    def test_constructor_rejects_non_collections(self):
        with pytest.raises(TypeError, match='relative pitch collections'):
            ChordSequence(['1/1', '5/4'])

    def test_voice_led_forwards_kwargs(self):
        seq = self._seq(3)
        led = seq.voice_led('C3', 'C6', voices=4, anchor=0, doubling='nearest')
        assert isinstance(led, ChordSequence)
        assert all(len(v.pitches) == 4 for v in led)


class TestVoiceLeadPerformance:
    def test_benchmark_guard(self):
        import time
        chords = [Chord([f'{k}/8' for k in range(8, 16)],
                        reference_pitch=Pitch('C4').transpose(f'{i + 8}/8'))
                  for i in range(16)]
        t0 = time.perf_counter()
        voice_lead(chords, 'C2', 'C6')
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.25, f"voice_lead too slow: {elapsed * 1000:.0f} ms"


class TestScaleFactories:
    def test_octatonic(self):
        scale = Scale.octatonic()
        assert scale.degrees == [0.0, 100.0, 300.0, 400.0, 600.0, 700.0, 900.0, 1000.0]
        assert scale.mode(1).degrees == [0.0, 200.0, 300.0, 500.0, 600.0, 800.0, 900.0, 1100.0]

    def test_hexatonic(self):
        assert Scale.hexatonic().degrees == [0.0, 100.0, 400.0, 500.0, 800.0, 900.0]

    def test_wholetone(self):
        assert Scale.wholetone().degrees == [0.0, 200.0, 400.0, 600.0, 800.0, 1000.0]

    def test_pentatonic(self):
        assert Scale.pentatonic().degrees == [Fraction(1, 1), Fraction(9, 8),
                                              Fraction(5, 4), Fraction(3, 2), Fraction(5, 3)]

    def test_harmonic_minor(self):
        assert Scale.harmonic_minor().degrees == [
            Fraction(1, 1), Fraction(9, 8), Fraction(6, 5), Fraction(4, 3),
            Fraction(3, 2), Fraction(8, 5), Fraction(15, 8)]

    def test_melodic_minor(self):
        assert Scale.melodic_minor().degrees == [
            Fraction(1, 1), Fraction(9, 8), Fraction(6, 5), Fraction(4, 3),
            Fraction(3, 2), Fraction(5, 3), Fraction(15, 8)]

    def test_reference_pitch_applies(self):
        scale = Scale.octatonic('A3')
        assert scale[0].freq == pytest.approx(Pitch('A3').freq)
        assert Scale.pentatonic('G3')[0].freq == pytest.approx(Pitch('G3').freq)


class TestPitchArithmetic:
    def test_transpose_ratio_str(self):
        p = Pitch('C4')
        assert p.transpose('3/2').freq == pytest.approx(p.freq * 1.5, rel=1e-4)

    def test_transpose_fraction_and_int(self):
        p = Pitch('C4')
        assert p.transpose(Fraction(2, 1)).freq == pytest.approx(p.freq * 2, rel=1e-4)
        assert p.transpose(2).freq == pytest.approx(p.freq * 2, rel=1e-4)

    def test_transpose_cents(self):
        p = Pitch('C4')
        down_fifth = p.transpose(cent(-500))
        assert down_fifth.freq == pytest.approx(p.freq * 2 ** (-500 / 1200), rel=1e-4)
        assert down_fifth.pitchclass == 'G'
        assert down_fifth.octave == 3

    def test_transpose_ratio_unit(self):
        p = Pitch('A4')
        assert p.transpose(ratio('1/2')).freq == pytest.approx(220.0, rel=1e-4)

    def test_transpose_preserves_partial(self):
        p = Pitch('C4', partial=3)
        assert p.transpose('3/2').partial == 3

    def test_at_octave(self):
        p = Pitch('G5').at_octave(3)
        assert p.pitchclass == 'G'
        assert p.octave == 3
        assert p.freq == pytest.approx(Pitch('G3').freq)

    def test_at_octave_preserves_cents_offset_and_partial(self):
        p = Pitch('C', 5, 14.0, partial=2).at_octave(2)
        assert p.cents_offset == 14.0
        assert p.partial == 2
        assert p.octave == 2
