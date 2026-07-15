import math
import random

import pytest

from klotho.tonos import (
    Key, Tonality, Voicing, ChordSequence, tonicize, approach,
)
from klotho.tonos.tonality import plain, parse_roman


def _pcs(voicing):
    return ' '.join(p.pitchclass for p in voicing)


def _cents_stack(voicing):
    tones = list(voicing)
    return [1200 * math.log2(b.freq / a.freq) for a, b in zip(tones[:-1], tones[1:])]


class TestKeyMajor:
    C = Key('C4')

    @pytest.mark.parametrize('symbol,pcs', [
        ('I', 'C E G'),
        ('ii', 'D F A'),
        ('V7', 'G B D F'),
        ('Imaj7', 'C E G B'),
        ('ii7', 'D F A C'),
        ('viio', 'B D F'),
        ('viiø7', 'B D F A'),
        ('iv', 'F G# C'),
        ('bIII', 'D# G A#'),
        ('bVI', 'G# C D#'),
        ('bVII', 'A# D F'),
        ('bII', 'C# F G#'),
        ('#IV', 'F# A# C#'),
        ('V7/V', 'D F# A C'),
        ('V7/vi', 'E G# B D'),
        ('viio7/V', 'F# A C D#'),
        ('V7/V/V', 'A C# E G'),
        ('bII7/V', 'G# C D# F#'),
    ])
    def test_pitch_classes(self, symbol, pcs):
        assert _pcs(self.C[symbol]) == pcs

    def test_dim7_is_stacked_minor_thirds(self):
        stack = _cents_stack(self.C['viio7'])
        assert all(250 < step < 350 for step in stack)

    def test_secondary_root_is_pure_fifth_chain(self):
        # V/V/V root: three just fifths above the tonic (27/16 reduced),
        # a syntonic comma from the 5/3 sixth degree — expected JI color.
        root = self.C.root_of('V7/V/V')
        assert root.freq == pytest.approx(self.C.tonic.freq * 27 / 16 * 2)

    def test_rooted_transposes(self):
        D = self.C.rooted('D4')
        assert _pcs(D['I']) == 'D F# A'
        assert D['V7'].reference_pitch.pitchclass == 'A'

    def test_progression_returns_chord_sequence(self):
        seq = self.C.progression(['I', 'IV', 'V7', 'I'])
        assert isinstance(seq, ChordSequence)
        assert len(seq) == 4

    def test_contains(self):
        assert 'V7/V' in self.C
        assert 'X9' not in self.C

    def test_unknown_symbol_raises(self):
        with pytest.raises((KeyError, ValueError)):
            self.C.chord('IX')

    def test_quality_registry_extension(self):
        class MyKey(Key):
            QUALITIES = dict(Key.QUALITIES)
            QUALITIES[('U', 'sus4')] = ('mixolydian', (0, 3, 4))

        assert _pcs(MyKey('C4')['Vsus4']) == 'G C D'

    def test_alternate_tuning_same_theory(self):
        from klotho.tonos import Scale
        edo = Key('C4', scale=Scale(
            [0, 200, 400, 500, 700, 900, 1100], interval_type='cents'))
        # roots come from the supplied tonic scale
        assert edo.root_of('V').freq == pytest.approx(
            edo.tonic.freq * 2 ** (700 / 1200))
        # planted qualities still resolve
        assert len(list(edo['V7'])) == 4


class TestKeyMinor:
    a = Key('A3', 'minor')

    def test_tonic_minor(self):
        assert _pcs(self.a['i']) == 'A C E'

    def test_dominant_major_by_case(self):
        assert _pcs(self.a['V7']) == 'E G# B D'

    def test_subtonic_vs_leading_tone(self):
        assert _pcs(self.a['VII']) == 'G B D'        # natural minor shelf
        assert _pcs(self.a['viio']) == 'G# B D'      # harmonic minor shelf
        assert _pcs(self.a['viio7']) == 'G# B D F'

    def test_neapolitan(self):
        assert _pcs(self.a['bII']) == 'A# D F'

    def test_mode_property_and_validation(self):
        assert self.a.mode == 'minor'
        with pytest.raises(ValueError):
            Key('C4', 'dorian')


class TestSpelling:
    C = Key('C4')

    @pytest.mark.parametrize('symbol,spelled', [
        ('I', 'C4 E4 G4'),
        ('iv', 'F4 Ab4 C5'),
        ('bIII', 'Eb4 G4 Bb4'),
        ('bII', 'Db4 F4 Ab4'),
        ('#IV', 'F#4 A#4 C#5'),
        ('viio7/V', 'F#5 A5 C6 Eb6'),
        ('bII7/V', 'Ab4 C5 Eb5 Gb5'),
    ])
    def test_letter_spelling(self, symbol, spelled):
        assert self.C.spell(symbol) == spelled

    def test_minor_spelling(self):
        a = Key('A3', 'minor')
        assert a.spell('viio7') == 'G#4 B4 D5 F5'
        assert a.spell('bII') == 'Bb3 D4 F4'

    def test_fallback_for_explicit_chords(self):
        world = Tonality('C4', chords={
            'X': Voicing([0, 300, 700], 'cents', reference_pitch='Ab3')})
        # no degree provenance -> falls back to default names, never errors
        assert world.spell('X') == 'G#3 B3 D#4'

    def test_show_prints(self, capsys):
        self.C.show(['I', 'bIII'])
        out = capsys.readouterr().out
        assert 'Eb4 G4 Bb4' in out


class TestTonalityEngine:
    def test_explicit_chords_and_rooted_transposition(self):
        world = Tonality('C4', chords={
            'C':   Voicing([0, 400, 700], 'cents', reference_pitch='C4'),
            'Abm': Voicing([0, 300, 700], 'cents', reference_pitch='Ab3'),
        })
        assert _pcs(world['Abm']) == 'G# B D#'
        up = world.rooted('D4')   # a major second up
        assert up['Abm'].reference_pitch.freq == pytest.approx(
            world['Abm'].reference_pitch.freq * up.tonic.freq / world.tonic.freq)

    def test_scale_stencil_entries(self):
        from klotho.tonos import Scale
        t = Tonality('C4', chords={'home': (Scale.ionian, (0, 2, 4))})
        assert _pcs(t['home']) == 'C E G'

    def test_symbols_and_chords_properties(self):
        a = Tonality('C4', chords={'X': Voicing([0, 400, 700], 'cents')})
        b = Tonality('C4', chords={'Y': Voicing([0, 300, 700], 'cents')})
        assert a.symbols == ('X',)
        merged = Tonality('C4', chords={**a.chords, **b.chords})
        assert merged.symbols == ('X', 'Y')

    def test_degree_quality_falls_out_of_scale(self):
        from klotho.tonos import Scale
        C = Tonality('C4', scale=Scale.ionian)
        assert _pcs(C.degree(0)) == 'C E G'
        assert _pcs(C.degree(2)) == 'E G B'      # iii is minor on its own
        assert _pcs(C.degree(1, stencil=(0, 3, 6))) == 'D G C'   # quartal

    def test_degree_without_scale_raises(self):
        with pytest.raises(ValueError):
            Tonality('C4').degree(0)

    def test_parserless_tonality_rejects_unknown_symbols(self):
        with pytest.raises(KeyError):
            Tonality('C4').chord('Y')

    def test_interface_rewrites_functions_to_symbols(self):
        C = Key('C4')
        iface = C.interface()
        word = iface.rewrite(('t', 's', 'd', 't'), rng=3)
        assert len(word) == 4
        assert all(sym in C for sym in word)

    def test_interface_override_and_empty(self):
        C = Key('C4')
        iface = C.interface({'t': [(1, 'Imaj7')]})
        assert iface.rewrite(('t',), rng=0) == ('Imaj7',)
        with pytest.raises(ValueError):
            Tonality('C4').interface()


class TestParsingAndTransforms:
    def test_parse_roman(self):
        assert parse_roman('bIII') == ('b', 'U', 2, '')
        assert parse_roman('viiø7') == ('', 'L', 6, 'ø7')
        with pytest.raises(ValueError):
            parse_roman('7')

    def test_plain(self):
        assert plain('vi7') == 'vi'
        assert plain('Imaj7') == 'I'
        assert plain('bII7') == 'bII'
        assert plain('V7/vi') == 'V/vi'

    def test_tonicize_skips_tonic_and_strips_quality(self):
        out = tonicize(['I', 'vi7', 'V7'], probability=1.0, rng=1)
        assert out == ['I', 'V7/vi', 'vi7', 'V7/V', 'V7']

    def test_tonicize_custom_dominant(self):
        out = tonicize(['ii'], probability=1.0, dominant='viio7', rng=1)
        assert out == ['viio7/ii', 'ii']

    def test_tonicize_seed_reproducible(self):
        base = ['I', 'vi', 'ii', 'V7', 'I']
        assert tonicize(base, 0.5, rng=7) == tonicize(base, 0.5, rng=7)

    def test_approach_and_tritone(self):
        out = approach(['Imaj7'], probability=1.0, tritone=1.0, rng=1)
        assert out == ['ii7/I', 'bII7/I', 'Imaj7']
        out = approach(['Imaj7'], probability=1.0, tritone=0.0, rng=1)
        assert out == ['ii7/I', 'V7/I', 'Imaj7']

    def test_every_transform_output_resolves(self):
        C = Key('C4')
        word = approach(tonicize(['I', 'vi', 'ii', 'V7', 'I'], 0.6, rng=2),
                        0.4, tritone=0.5, rng=2)
        for sym in word:
            assert len(list(C[sym])) >= 3
