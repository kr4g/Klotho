"""Tests for transpose/equave_shift, lattice-family chord(), ChordSequence
conveniences, and Chord/ChordSequence plot shapes."""
from fractions import Fraction

import pytest

from klotho.tonos import Hexany, MasterSet, Pitch, Scale, cent
from klotho.tonos.chords.chord import Chord, ChordSequence, Voicing
from klotho.tonos.pitch.pitch_collections import (
    AbsolutePitchCollection,
    PitchCollection,
    RelativePitchCollection,
)
from klotho.tonos.systems.combination_product_sets import match_pattern
from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice

C4 = Pitch('C4').freq


class TestPitchEquaveShift:
    def test_octave_up_down(self):
        assert Pitch('C4').equave_shift(1).freq == pytest.approx(2 * C4)
        assert Pitch('C4').equave_shift(-2).freq == pytest.approx(C4 / 4)

    def test_custom_equave(self):
        assert Pitch('C4').equave_shift(1, equave='3/1').freq == pytest.approx(3 * C4)


class TestCollectionTranspose:
    def test_chord_reference_carries(self):
        ch = Chord(['1/1', '5/4', '3/2'])
        ch2 = ch.equave_shift(1)
        assert isinstance(ch2, Chord)
        assert ch2.degrees == ch.degrees
        assert ch2.reference_pitch.freq == pytest.approx(2 * C4, rel=1e-4)
        for a, b in zip(ch2.pitches, ch.pitches):
            assert a.freq == pytest.approx(2 * b.freq, rel=1e-4)

    def test_chord_transpose_interval(self):
        ch = Chord(['1/1', '5/4', '3/2'])
        cht = ch.transpose('3/2')
        assert cht.degrees == ch.degrees
        assert cht.reference_pitch.freq == pytest.approx(1.5 * C4, rel=1e-4)

    def test_scale_reference_carries(self):
        sc = Scale()
        sc2 = sc.equave_shift(-1)
        assert isinstance(sc2, Scale)
        assert sc2.degrees == sc.degrees
        assert sc2.reference_pitch.freq == pytest.approx(C4 / 2, rel=1e-4)

    def test_voicing_degrees_carry(self):
        v = Voicing(['1/1', '5/4', '2/1'])
        v2 = v.equave_shift(1)
        assert isinstance(v2, Voicing)
        assert v2.degrees == [Fraction(2, 1), Fraction(5, 2), Fraction(4, 1)]
        assert v2.reference_pitch.freq == pytest.approx(C4)

    def test_voicing_shift_survives_root(self):
        v2 = Voicing(['1/1', '5/4', '2/1']).equave_shift(1)
        v3 = v2.root('Ab3')
        assert v3.degrees == [Fraction(2, 1), Fraction(5, 2), Fraction(4, 1)]

    def test_plain_collection_degrees_carry(self):
        pc = PitchCollection.from_degrees(['1/1', '5/4', '3/2'], equave='2/1')
        pc2 = pc.equave_shift(1)
        assert type(pc2) is RelativePitchCollection
        assert pc2.equave_cyclic
        assert pc2.degrees == [Fraction(2, 1), Fraction(5, 2), Fraction(3, 1)]
        assert pc2.reference_pitch.freq == pytest.approx(C4)

    def test_cents_mode(self):
        pcc = PitchCollection.from_degrees([0.0, 400.0, 700.0], mode='cents', equave=1200.0)
        assert pcc.equave_shift(1).degrees == [1200.0, 1600.0, 1900.0]
        assert pcc.transpose(cent(50)).degrees == [50.0, 450.0, 750.0]

    def test_absolute_collection(self):
        ap = AbsolutePitchCollection(['C4', 'E4', 'G4'])
        ap2 = ap.equave_shift(1)
        assert isinstance(ap2, AbsolutePitchCollection)
        for a, b in zip(ap2.pitches, ap.pitches):
            assert a.freq == pytest.approx(2 * b.freq)

    def test_cent_interval_floats_ratio_degrees(self):
        vf = Voicing(['1/1', '5/4']).transpose(cent(100))
        assert all(isinstance(d, float) for d in vf.degrees)


class TestLatticeChord:
    def test_cps_single_group_parity_with_helper(self):
        hx = Hexany()
        shape = (4, 0, 3)
        old = Chord(sorted(hx[n]['ratio'] for n in shape)).root('Ab3')
        new = hx.chord(shape, root='Ab3')
        assert isinstance(new, Chord)
        assert new.degrees == old.degrees
        assert new.reference_pitch.freq == pytest.approx(old.reference_pitch.freq)

    def test_root_default_and_rooted_instance(self):
        hx = Hexany()
        assert hx.chord((0, 1)).reference_pitch.pitchclass == 'C'
        a = hx.root('Ab3').chord((0, 1))
        b = hx.chord((0, 1), root='Ab3')
        assert a.degrees == b.degrees
        assert a.reference_pitch.freq == pytest.approx(b.reference_pitch.freq)

    def test_match_pattern_groups_to_sequence(self):
        hx = Hexany()
        matches = match_pattern(hx, [4, 0, 3], sort_by='position', include_target=True)
        seq = hx.chord(matches, root='Ab3')
        assert isinstance(seq, ChordSequence)
        assert len(seq) == len(matches)

    def test_mixed_input_raises(self):
        with pytest.raises(ValueError, match='Mixed input'):
            Hexany().chord([0, (1, 2)])

    def test_master_set(self):
        ms = MasterSet.tetrad()
        with pytest.raises(ValueError, match='factors'):
            ms.chord(('A', 'B'))
        msf = ms.with_factors((1, 3, 5, 7))
        mc = msf.chord(('A', 'B', 'C'))
        assert isinstance(mc, Chord) and len(mc.degrees) == 3
        with pytest.raises(KeyError):
            msf.chord(('A', 'Q'))

    def test_tone_lattice(self):
        tl = ToneLattice(dimensionality=2, resolution=2)
        assert isinstance(tl.chord([(1, 0), (0, 1), (1, 1)]), Chord)
        tseq = tl.chord([[(1, 0), (0, 1)], [(2, 0), (0, 2)]])
        assert isinstance(tseq, ChordSequence) and len(tseq) == 2

    def test_tone_lattice_custom_equave(self):
        tl3 = ToneLattice(dimensionality=2, resolution=1, equave=3)
        assert tl3.chord([(1, 0), (0, 1)]).equave == Fraction(3, 1)


class TestChordSequenceConveniences:
    def _seq(self):
        return ChordSequence([Chord(['1/1', '5/4', '3/2']), Chord(['1/1', '6/5', '3/2'])])

    def test_voicing_applies_to_all(self):
        v = self._seq().voicing([0, 2, 4])
        assert all(isinstance(x, Voicing) for x in v.chords)
        assert v.chords[0].degrees == [Fraction(1, 1), Fraction(3, 2), Fraction(5, 2)]

    def test_voicing_replaces_existing(self):
        v2 = self._seq().voicing([0, 2, 4]).voicing([0, 1])
        assert v2.chords[0].degrees == [Fraction(1, 1), Fraction(5, 4)]

    def test_root_transpose_shift_map(self):
        seq = self._seq()
        assert all(x.reference_pitch.pitchclass in ('Ab', 'G#') for x in seq.root('Ab3').chords)
        t = seq.transpose('3/2')
        assert t.chords[0].reference_pitch.freq == pytest.approx(1.5 * C4, rel=1e-4)
        s = seq.equave_shift(-1)
        for a, b in zip(s.chords, seq.chords):
            assert a.pitches[0].freq * 2 == pytest.approx(b.pitches[0].freq, rel=1e-4)

    def test_mixed_sequence_carriers(self):
        c = Chord(['1/1', '5/4', '3/2'])
        ms = ChordSequence([c, Voicing(['1/1', '5/4', '2/1'])]).equave_shift(1)
        assert ms.chords[0].degrees == c.degrees
        assert ms.chords[1].degrees == [Fraction(2), Fraction(5, 2), Fraction(4)]


class TestChordShapesInPlots:
    def test_cps_chord_sequence_shape(self):
        from klotho.semeios.visualization._dispatch.plot_cps import _plot_cps
        from klotho.semeios.visualization._animation import AnimatedCPSShapeFigure

        hx = Hexany()
        matches = match_pattern(hx, [4, 0, 3], sort_by='position', include_target=True)
        fig_nodes = _plot_cps(hx, animate=True, shape=[list(m) for m in matches])
        fig_chords = _plot_cps(hx, animate=True, shape=hx.chord(matches))
        assert isinstance(fig_chords, AnimatedCPSShapeFigure)
        ref = sorted(e['pfields']['freq'] for e in fig_nodes.audio_payload['events'])
        got = sorted(e['pfields']['freq'] for e in fig_chords.audio_payload['events'])
        assert got == pytest.approx(ref, rel=1e-3)

    def test_cps_shifted_chords_play_shifted(self):
        from klotho.semeios.visualization._dispatch.plot_cps import _plot_cps

        hx = Hexany()
        matches = match_pattern(hx, [4, 0, 3], include_target=True)
        seq = hx.chord(matches)
        base = sorted(e['pfields']['freq'] for e in
                      _plot_cps(hx, animate=True, shape=seq).audio_payload['events'])
        down = sorted(e['pfields']['freq'] for e in
                      _plot_cps(hx, animate=True, shape=seq.equave_shift(-1)).audio_payload['events'])
        assert down == pytest.approx([f / 2 for f in base], rel=1e-6)

    def test_single_chord_and_static(self):
        from klotho.semeios.visualization._dispatch.plot_cps import _plot_cps

        hx = Hexany()
        _plot_cps(hx, animate=True, shape=hx.chord((4, 0, 3)))
        _plot_cps(hx, shape=hx.chord((4, 0, 3)))

    def test_foreign_ratio_raises(self):
        from klotho.semeios.visualization._dispatch.plot_cps import _plot_cps

        with pytest.raises(ValueError, match='does not correspond'):
            _plot_cps(Hexany(), animate=True, shape=Chord(['1/1', '13/8']))

    def test_master_set_and_lattice_chord_shapes(self):
        from klotho.semeios.visualization._dispatch.plot_cps import _plot_master_set
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice

        ms = MasterSet.tetrad().with_factors((1, 3, 5, 7))
        fig_ms = _plot_master_set(ms, animate=True, shape=ms.chord(('A', 'B', 'C')))
        assert len(fig_ms.audio_payload['events']) == 3

        tl = ToneLattice(dimensionality=2, resolution=2)
        tc = tl.chord([[(1, 0), (0, 1)], [(2, 0), (0, 2)]])
        fig_tl = _plot_lattice(tl, animate=True, shape=tc)
        assert len(fig_tl.audio_payload['events']) == 4
        # voiced (multi-equave) degrees still resolve to nodes
        _plot_lattice(tl, animate=True, shape=tc.voicing([0, 1, 2]))
