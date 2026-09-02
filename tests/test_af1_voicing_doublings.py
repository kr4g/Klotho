"""AF-1 / AUD-8: a ``Voicing`` built with ``dedupe=False`` must keep its
doublings through ``root()``, ``transpose()``, ``equave_shift()`` and
``fold()``.

``voice_lead(..., voices=N)`` builds exactly such a Voicing (it constructs
its results with ``dedupe=False`` so a fixed voice count survives), and
``ChordSequence`` advertises ``root``/``transpose``/``equave_shift``/
``folded`` as the way to move a progression around. Before the fix those
four methods rebuilt the Voicing through the *default* constructor policy,
so every unison-doubled voice was silently dropped: a locked 4-voice
texture came back as 3 voices, with no exception and no warning.

Two doubling shapes have to be told apart or these tests pass for the
wrong reason:

* an **octave** doubling (``1/1`` with ``2/1``) is two *distinct* degrees,
  so it always survived a rebuild — it is the CONTROL here, not evidence;
* a **unison** doubling (``1/1`` with ``1/1``) is two *equal* degrees, and
  it is the one the default ``dedupe=True`` constructor collapses.

``fold()`` converts the first into the second — folding an octave pair
into a window narrower than the pair makes the two degrees equal — which
is how a real ``voice_lead`` texture loses a voice even though its
doubling was written at the octave.

Every expected value below is derived from the documented contract of the
method under test (degrees untouched by ``root``; degrees multiplied by
the interval in ``transpose``; degrees displaced by whole equaves in
``fold``), not read back out of the implementation.
"""

from fractions import Fraction

import pytest

from klotho.tonos.chords.chord import Chord, ChordSequence, Voicing
from klotho.tonos.chords.voice_leading import fold, voice_lead
from klotho.tonos.tonality import Tonality


F = Fraction


def _unison_doubled():
    """C4 voicing with the root doubled in unison: 1/1, 1/1, 3/2."""
    return Voicing(['1/1', '1/1', '3/2'], dedupe=False, reference_pitch='C4')


def _octave_doubled():
    """C4 voicing with the root doubled at the octave: 1/1, 3/2, 2/1."""
    return Voicing(['1/1', '2/1', '3/2'], dedupe=False, reference_pitch='C4')


class TestUnisonDoublingSurvivesRebuilds:
    """The four rebuilding methods named in AUD-8."""

    def test_construction_keeps_the_unison_pair(self):
        # Precondition, not the finding: dedupe=False stores both copies.
        assert _unison_doubled().degrees == [F(1), F(1), F(3, 2)]

    def test_root_keeps_the_unison_pair(self):
        # root() replaces the reference pitch and nothing else, so the
        # stored interval content must come through unchanged.
        moved = _unison_doubled().root('A4')
        assert moved.degrees == [F(1), F(1), F(3, 2)]
        assert len(moved.pitches) == 3

    def test_transpose_keeps_the_unison_pair(self):
        # A Voicing carries a transposition in its DEGREES (the reference
        # pitch is unchanged): 1/1*5/4 = 5/4, 1/1*5/4 = 5/4, 3/2*5/4 = 15/8.
        moved = _unison_doubled().transpose('5/4')
        assert moved.degrees == [F(5, 4), F(5, 4), F(15, 8)]

    def test_equave_shift_keeps_the_unison_pair(self):
        # equave_shift(1) is transpose(equave) with equave = 2/1:
        # 1*2 = 2, 1*2 = 2, 3/2*2 = 3.
        moved = _unison_doubled().equave_shift(1)
        assert moved.degrees == [F(2), F(2), F(3)]

    def test_fold_keeps_the_unison_pair(self):
        # Reference C4. The three degrees sound C4, C4, G4; the window
        # [C3, C6] contains all three, so every displacement is zero and
        # the degrees come back as written.
        folded = fold(_unison_doubled(), lo='C3', hi='C6')
        assert folded.degrees == [F(1), F(1), F(3, 2)]

    def test_cents_mode_unison_pair_survives_root_and_transpose(self):
        v = Voicing([0.0, 0.0, 700.0], 'cents', dedupe=False,
                    reference_pitch='C4')
        assert len(v.degrees) == 3
        assert v.root('A4').degrees == [0.0, 0.0, 700.0]
        # Cents transposition is additive: 0+200, 0+200, 700+200.
        assert v.transpose('9/8').degrees == pytest.approx(
            [203.910, 203.910, 903.910], abs=1e-3)


class TestOctaveDoublingIsTheControl:
    """These passed BEFORE the fix too. They pin that the fix did not work
    by simply making every rebuild skip dedupe for everything, and they
    keep the unison tests above from passing for the wrong reason."""

    def test_octave_pair_survives_root(self):
        assert _octave_doubled().root('A4').degrees == [F(1), F(3, 2), F(2)]

    def test_octave_pair_survives_transpose(self):
        # 1*5/4 = 5/4, 3/2*5/4 = 15/8, 2*5/4 = 5/2.
        assert _octave_doubled().transpose('5/4').degrees == [
            F(5, 4), F(15, 8), F(5, 2)]


class TestDedupeTrueStillDedupes:
    """The default policy is unchanged: dedupe=True is still the default
    and still collapses exact duplicates, at construction and through a
    rebuild. Spec source: the Voicing docstring's own example, which shows
    ``Voicing(["1/1", "1/1", "3/2"]).degrees == [1/1, 3/2]``."""

    def test_default_construction_dedupes(self):
        assert Voicing(['1/1', '1/1', '3/2']).degrees == [F(1), F(3, 2)]

    def test_default_policy_survives_root_and_transpose(self):
        v = Voicing(['1/1', '1/1', '3/2'], reference_pitch='C4')
        assert v.root('A4').degrees == [F(1), F(3, 2)]
        assert v.transpose('5/4').degrees == [F(5, 4), F(15, 8)]
        assert v.equave_shift(1).degrees == [F(2), F(3)]

    def test_a_rebuild_of_a_deduped_voicing_cannot_grow(self):
        # A dedupe=True Voicing has no duplicates to lose, so its voice
        # count is invariant under every rebuild.
        v = Voicing(['1/1', '5/4', '3/2'], reference_pitch='C4')
        for rebuilt in (v.root('A4'), v.transpose('5/4'), v.equave_shift(-1),
                        fold(v, lo='C3', hi='C6')):
            assert len(rebuilt.degrees) == 3


class TestFoldPreservesVoiceCount:
    """fold() is the method that CREATES the collision: it turns an octave
    doubling into a unison one, so before the fix it dropped a voice from
    a texture whose doubling was written at the octave — the shape
    voice_lead actually produces."""

    def test_fold_collapsing_an_octave_pair_keeps_four_voices(self):
        # Reference C4: degrees 1/1, 5/4, 3/2, 2/1 sound C4, E4, G4, C5.
        # The window [C4, B4] excludes C5 (523.25 Hz > 493.88 Hz), so the
        # 2/1 displaces DOWN one octave to 1/1 -- equal to the degree
        # already there. Four voices in, four voices out, two in unison.
        v = Voicing(['1/1', '2/1', '3/2', '5/4'], dedupe=False,
                    reference_pitch='C4')
        assert len(v.degrees) == 4
        folded = fold(v, lo='C4', hi='B4')
        assert folded.degrees == [F(1), F(1), F(5, 4), F(3, 2)]
        assert len(folded.pitches) == 4

    def test_fold_of_a_chord_keeps_its_degree_count(self):
        # Guard in the other direction: a Chord's degrees are distinct
        # pitch classes inside one equave, so folding by whole equaves can
        # never make two of them equal. Passing dedupe=False through fold
        # must not invent a voice here.
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C5')
        assert len(fold(chord, lo='G3', hi='G4').degrees) == 3


class TestEndToEndVoiceLeadThenMove:
    """The composer workflow from the finding: lock a texture with
    voice_lead(voices=N), then move the progression."""

    @staticmethod
    def _led():
        seq = [Chord(['1/1', '5/4', '3/2']), Chord(['1/1', '6/5', '3/2'])]
        return voice_lead(seq, lo='C4', hi='G4', voices=4)

    def test_voice_lead_locks_four_voices(self):
        # voices=4 is a contract of voice_lead itself (unchanged by this
        # fix); it is the precondition for everything below.
        assert [len(v.degrees) for v in self._led()] == [4, 4]

    def test_transposed_sequence_keeps_four_voices(self):
        led = self._led()
        moved = ChordSequence(led).transpose('9/8')
        assert [len(v.degrees) for v in moved] == [4, 4]
        # Every degree is its original times 9/8 -- the transpose contract,
        # applied element-wise, rather than a captured constant.
        for before, after in zip(led, moved):
            assert after.degrees == [d * F(9, 8) for d in before.degrees]

    def test_rooted_sequence_keeps_four_voices(self):
        led = self._led()
        moved = ChordSequence(led).root('A4')
        assert [len(v.degrees) for v in moved] == [4, 4]
        for before, after in zip(led, moved):
            assert after.degrees == before.degrees

    def test_equave_shifted_sequence_keeps_four_voices(self):
        led = self._led()
        moved = ChordSequence(led).equave_shift(-1)
        assert [len(v.degrees) for v in moved] == [4, 4]
        for before, after in zip(led, moved):
            assert after.degrees == [d / 2 for d in before.degrees]

    def test_folded_sequence_keeps_four_voices(self):
        led = self._led()
        moved = ChordSequence(led).folded(lo='C4', hi='G4')
        assert [len(v.degrees) for v in moved] == [4, 4]


class TestTonalityRootedKeepsDoublings:
    """Tonality.rooted() re-roots stored Voicings through Voicing.root, so
    a transposed tonality dropped doublings the same way."""

    def test_rooted_tonality_keeps_a_unison_doubling(self):
        tonality = Tonality('C4', chords={
            'X': Voicing(['1/1', '1/1', '3/2'], dedupe=False,
                         reference_pitch='C4'),
        })
        assert len(tonality['X'].degrees) == 3
        moved = tonality.rooted('E4')
        assert moved['X'].degrees == [F(1), F(1), F(3, 2)]
        assert len(moved['X'].pitches) == 3
