"""Regression harness: exact student-facing call patterns from
examples/mat111mc_notebooks/.

These forms are the course contract — they appear verbatim in the MAT 111MC
notebooks and must keep working through every refactor phase (MIDI/Tone.js
removal, voice-leading rewrite, dispatch registry, Score plotting).

Behavioral details (exact output pitches of ``voice_led``, widget internals)
are intentionally NOT pinned here; only signatures, types, and invariants
students' code relies on.
"""
import pytest

from klotho.semeios.visualization._dispatch import KlothoPlot


@pytest.fixture(autouse=True)
def _mute_display(monkeypatch):
    """Swallow IPython.display calls so tests can run headless."""
    import IPython.display
    monkeypatch.setattr(IPython.display, 'display', lambda *a, **k: None)


class TestCanonicalImports:
    """The import blocks that open nearly every course notebook."""

    def test_top_level(self):
        from klotho import plot, play, set_audio_engine  # noqa: F401

    def test_thetos(self):
        from klotho.thetos import (  # noqa: F401
            CompositionalUnit as UC,
            Ensemble,
            Score,
            SynthDefFX as InsertFX,
        )

    def test_chronos(self):
        from klotho.chronos import (  # noqa: F401
            Meas,
            TemporalUnitSequence as UTS,
            TemporalBlock as BT,
        )

    def test_tonos(self):
        from klotho.tonos import (  # noqa: F401
            Hexany, Eikosany, Pitch, Chord, ChordSequence,
            PitchCollection as PC, Contour, Voicing, fold,
            Key, Tonality, tonicize, approach,
        )

    def test_set_audio_engine_supersonic(self):
        from klotho import set_audio_engine
        set_audio_engine("supersonic")


def _triad_sequence():
    from klotho.tonos import Chord, ChordSequence
    return ChordSequence([
        Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
        Chord(['1/1', '6/5', '3/2'], reference_pitch='A3'),
        Chord(['1/1', '5/4', '3/2', '15/8'], reference_pitch='F3'),
    ])


class TestVoiceLedContract:
    """seq.voice_led(lo, hi) — the dominant harmony idiom in the course."""

    def test_positional_note_names(self):
        from klotho.tonos import ChordSequence, Voicing
        voiced = _triad_sequence().voice_led('C3', 'C5')
        assert isinstance(voiced, ChordSequence)
        assert len(voiced) == 3
        assert all(isinstance(ch, Voicing) for ch in voiced)

    def test_star_unpacked_range_tuple(self):
        RANGE = ('G2', 'G5')
        voiced = _triad_sequence().voice_led(*RANGE)
        assert len(voiced) == 3

    def test_result_is_indexable_and_iterable(self):
        voiced = _triad_sequence().voice_led('C3', 'C5')
        first = voiced[0]
        assert first is not None
        seen = [ch for i, ch in enumerate(voiced)]  # Aphex Twin loop idiom
        assert len(seen) == 3

    def test_pitches_land_inside_bounds(self):
        from klotho.tonos import Pitch
        lo_hz = Pitch('C3').freq * 0.99
        hi_hz = Pitch('C5').freq * 1.01
        voiced = _triad_sequence().voice_led('C3', 'C5')
        for ch in voiced:
            for p in ch.pitches:
                assert lo_hz <= p.freq <= hi_hz

    def test_voicing_and_equave_shift_chaining(self):
        seq = _triad_sequence()
        assert seq.voicing([0, 2, 3]) is not None
        assert seq.equave_shift(-1).voicing([-1, 0, 1]) is not None
        assert seq[0].equave_shift(-2).voicing([0, 1, 2]) is not None

    def test_chord_voicing_accepts_range(self):
        ch = _triad_sequence()[0]
        assert ch.voicing(range(-len(ch) // 2, len(ch) + 1)) is not None

    def test_fold_positional_none_lo(self):
        from klotho.tonos import Voicing, fold
        v = Voicing(['1/1', '5/4', '3/2'], reference_pitch='C4')
        assert fold(v, None, 'C5') is not None

    def test_chord_root_rebuild(self):
        from klotho.tonos import Chord
        assert Chord([1, '5/4', '3/2']).root('A') is not None


class TestLatticeShapePath:
    """plot(lattice, shape=chord_sequence) — Tetris / Tonnetz notebooks."""

    def test_voiced_sequence_resolves_as_shape(self):
        from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice
        from klotho.semeios.visualization.plots import plot
        tl = ToneLattice.from_generators(('6/5', '5/4'), resolution=3,
                                         equave_reduce=False)
        placements = [[(0, 0), (0, 1), (1, 0)], [(0, -1), (1, -1), (1, 0)]]
        seq = tl.chord(placements)
        for s in (seq, seq.voice_led('C3', 'C5')):
            p = plot(tl, shape=s, figsize=(4, 4))
            assert isinstance(p, KlothoPlot)
            assert p._build_static() is not None


def _u(tempus='4/4', prolatio=(1, 2, 1), bpm=120):
    from klotho.chronos.temporal_units.temporal import TemporalUnit
    return TemporalUnit(tempus=tempus, prolatio=prolatio, bpm=bpm)


def _uc(**kw):
    from klotho.thetos import CompositionalUnit as UC
    kw.setdefault('tempus', '4/4')
    kw.setdefault('prolatio', (1, 1, 2))
    kw.setdefault('bpm', 120)
    return UC(**kw)


class TestPlotForms:
    """The plot(...) forms students call, all of which must keep returning a
    KlothoPlot with a callable .play (or display statically and return None)."""

    def test_temporal_unit_ratios_layout(self):
        from klotho import plot
        p = plot(_u(), layout='ratios', figsize=(10, 0.5))
        assert isinstance(p, KlothoPlot)
        assert callable(p.play)
        assert p._build_static() is not None

    def test_uc_tree_layout(self):
        from klotho import plot
        p = plot(_uc(beat='1/8', bpm=132), layout='tree', figsize=(12, 2.2))
        assert isinstance(p, KlothoPlot)
        assert p._build_static() is not None

    def test_temporal_block(self):
        from klotho import plot
        from klotho.chronos import TemporalBlock as BT
        p = plot(BT([_u(), _u('3/4', 'p', 90)]))
        assert isinstance(p, KlothoPlot)
        assert p._build_static() is not None

    def test_uts(self):
        from klotho import plot
        from klotho.chronos import TemporalUnitSequence as UTS
        p = plot(UTS([_u(), _u('3/4', 'p', 90)]))
        assert isinstance(p, KlothoPlot)
        assert p._build_static() is not None

    def test_scale_static_plot(self):
        from klotho import plot
        from klotho.tonos import Scale
        assert plot(Scale(['1/1', '9/8', '5/4', '3/2', '5/3'])) is None

    def test_hexany_plot(self):
        from klotho import plot
        from klotho.tonos import Hexany
        p = plot(Hexany(), figsize=(4, 4))
        assert isinstance(p, KlothoPlot)
        assert p._build_static() is not None


class TestPlayForms:
    """play(...) forms from the notebooks (headless: display muted).
    These execute the full conversion + widget-HTML pipeline."""

    def test_play_chord_sequence(self):
        from klotho import play
        play(_triad_sequence(), dur=0.1)

    def test_play_voicing_with_strum_and_pfields(self):
        from klotho import play
        ch = _triad_sequence()[0]
        play(ch.voicing([0, 2, 4]), inst='kl_tri', dur=0.2,
             strum=0.1, releaseTime=0.5)

    def test_play_pitch(self):
        from klotho import play
        from klotho.tonos import Pitch
        play(Pitch('C4'), dur=0.2)

    def test_play_scale_with_equaves(self):
        from klotho import play
        from klotho.tonos import Scale
        play(Scale(['1/1', '9/8', '5/4', '3/2', '5/3']), dur=0.1, equaves=2)

    def test_play_uts_and_bt(self):
        from klotho import play
        from klotho.chronos import TemporalUnitSequence as UTS, TemporalBlock as BT
        play(UTS([_u(), _u('3/4', 'p', 90)]))
        play(BT([_u(), _u('5/8', (2, -1, 3), 100)]))

    def test_play_uc_with_chord_freq(self):
        from klotho import play
        from klotho.tonos import Chord
        uc = _uc()
        uc.root.set(freq=Chord(['1/1', '5/4', '3/2'], reference_pitch='C4'),
                    amp=0.5)
        play(uc)


class TestScorePatterns:
    """Score assembly + play(score) — used in nearly every later notebook."""

    def _score(self):
        from klotho.thetos import Score, SynthDefFX as InsertFX
        score = Score()
        score.track('drums',
                    inserts=[InsertFX('kl_distortion', dist=0.12, mix=0.25)])
        score.track('hats')
        return score

    def test_track_append_add_clear(self):
        from klotho.chronos import TemporalUnitSequence as UTS
        score = self._score()
        score.append(_uc(), name='start', track='drums')
        score.add(UTS([_u(), _u('3/4', 'p', 90)]), name='office hours',
                  after='start', track='hats')
        assert 'start' in score
        assert len(score) == 2
        score.clear(keep_tracks=True)
        assert len(score) == 0
        assert 'drums' in score.tracks

    def test_play_score(self):
        from klotho import play
        score = self._score()
        score.append(_uc(), name='start', track='drums')
        play(score)


class TestPitchMidiIncidental:
    """Pitch.midi / Pitch.from_midi are pitch math (Microtonal Tetris uses
    them) — they survive the MIDI-playback removal untouched."""

    def test_midi_property_roundtrip(self):
        from klotho.tonos import Pitch
        assert abs(Pitch('A4').midi - 69.0) < 1e-6
        assert abs(Pitch.from_midi(69).freq - 440.0) < 0.5
