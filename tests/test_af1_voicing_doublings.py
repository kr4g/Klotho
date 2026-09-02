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

import inspect
import re
from fractions import Fraction

import pytest

from klotho.tonos.chords.chord import Chord, ChordSequence, Voicing
from klotho.tonos.chords.voice_leading import fold, voice_lead
from klotho.tonos.pitch.pitch_collections import RelativePitchCollection
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


# ---------------------------------------------------------------------------
# AF-1b: the sibling movers the first pass did not reach.
#
# f1edde3 taught root(), transpose(), equave_shift() and fold() to carry the
# dedupe policy. Three more doors rebuild a Voicing and still dropped it, all
# silently and all in the same shape: as_voicing(), Voicing.from_collection()
# and ChordSequence.voicing() (through Chord.voicing()).
# ---------------------------------------------------------------------------


class TestAsVoicingCarriesThePolicy:
    """``as_voicing()`` is inherited from ``RelativePitchCollection`` and
    rebuilds through the *default* ``Voicing`` constructor, so a
    ``dedupe=False`` voicing came back deduped."""

    def test_as_voicing_keeps_a_unison_doubling(self):
        # as_voicing() re-expresses the SAME degrees as a Voicing; it is
        # not a re-voicing, so the arity it is handed is the arity it owes
        # back. 1/1, 1/1, 3/2 in -> 1/1, 1/1, 3/2 out.
        assert _unison_doubled().as_voicing().degrees == [F(1), F(1), F(3, 2)]

    def test_as_voicing_carries_the_policy_not_just_the_degrees(self):
        # Whatever comes back must ITSELF still be a dedupe=False voicing,
        # or the next move loses the voice instead of this one.
        again = _unison_doubled().as_voicing().transpose('9/8')
        assert again.degrees == [F(9, 8), F(9, 8), F(27, 16)]

    def test_a_voice_led_texture_keeps_its_voice_count_through_as_voicing(self):
        # The workflow from the finding: voice_lead(voices=4) locks four
        # voices (pinned by TestEndToEndVoiceLeadThenMove above), and
        # as_voicing() must not quietly hand back three.
        seq = [Chord(['1/1', '5/4', '3/2']), Chord(['1/1', '6/5', '3/2'])]
        for v in voice_lead(seq, lo='C4', hi='G4', voices=4):
            assert len(v.as_voicing().degrees) == len(v.degrees) == 4

    def test_a_collection_with_no_policy_still_dedupes(self):
        # CONTROL. A plain relative collection has no stored policy, so
        # as_voicing() falls back to Voicing's documented default
        # (dedupe=True). The fix must read a policy, not abolish dedupe.
        plain = RelativePitchCollection(['1/1', '1/1', '3/2'],
                                        reference_pitch='C4')
        assert plain.degrees == [F(1), F(1), F(3, 2)]
        assert plain.as_voicing().degrees == [F(1), F(3, 2)]

    def test_a_dedupe_true_voicing_still_dedupes_through_as_voicing(self):
        # CONTROL, the other half: an explicit dedupe=True Voicing keeps
        # deduping. (Its own constructor already collapsed the pair, so
        # this pins that as_voicing does not resurrect anything either.)
        assert Voicing(['1/1', '1/1', '3/2']).as_voicing().degrees == [
            F(1), F(3, 2)]


class TestFromCollectionCarriesThePolicy:
    """``Voicing.from_collection`` rebuilt through the default constructor
    too, so round-tripping a doubled texture silently lost a voice."""

    def test_from_collection_keeps_a_unison_doubling(self):
        rebuilt = Voicing.from_collection(_unison_doubled())
        assert rebuilt.degrees == [F(1), F(1), F(3, 2)]

    def test_from_collection_carries_the_policy_not_just_the_degrees(self):
        rebuilt = Voicing.from_collection(_unison_doubled())
        # Same derivation as transpose above: every degree times 5/4.
        assert rebuilt.transpose('5/4').degrees == [
            F(5, 4), F(5, 4), F(15, 8)]

    def test_from_collection_of_a_chord_still_dedupes(self):
        # CONTROL. A Chord has no dedupe policy of its own -- it is a
        # pitch-class set by definition -- so the default applies.
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        assert Voicing.from_collection(chord).degrees == [
            F(1), F(5, 4), F(3, 2)]

    def test_from_collection_of_a_dedupe_true_voicing_still_dedupes(self):
        # CONTROL. Source policy is True, so duplicates handed in are
        # dropped -- and the source constructor already dropped them.
        src = Voicing(['1/1', '1/1', '3/2'])
        assert Voicing.from_collection(src).degrees == [F(1), F(3, 2)]


class TestChordVoicingIsOneVoicePerRequestedIndex:
    """``Chord.voicing(index)`` is a gather: it selects one chord tone per
    requested index. Duplicates can only arise from the CALLER repeating an
    index -- cyclic lookup is injective on the index -- so deduping here did
    exactly one thing: silently discard a deliberately doubled voice.

    ``chord[[0, 0, 2]]`` already returns three degrees (the sequence
    ``__getitem__`` builds a plain RelativePitchCollection, which does not
    dedupe), so ``chord.voicing([0, 0, 2])`` returning two was also an
    inconsistency inside one class."""

    def test_a_repeated_index_yields_a_repeated_degree(self):
        # Chord degrees sort to [1/1, 5/4, 3/2]. Cyclic index i maps to
        # (i // 3, i % 3) -> degree[i % 3] * equave ** (i // 3):
        #   0 -> (0, 0) -> 1/1 ; 0 -> 1/1 ; 2 -> (0, 2) -> 3/2.
        # Three indices in, three degrees out, sorted ascending.
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        assert chord.voicing([0, 0, 2]).degrees == [F(1), F(1), F(3, 2)]

    def test_the_sequence_getitem_door_already_agreed(self):
        # The inconsistency this closes: same class, same indices.
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        assert chord[[0, 0, 2]].degrees == [F(1), F(1), F(3, 2)]

    def test_a_doubling_across_equaves_still_reads_as_two_voices(self):
        # CONTROL (passed before this fix): index 3 -> (1, 0) -> 1/1 * 2.
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        assert chord.voicing([0, 3]).degrees == [F(1), F(2)]

    def test_distinct_indices_are_untouched(self):
        # CONTROL: the change must not invent voices where none were asked
        # for. 0 -> 1/1, 1 -> 5/4, 2 -> 3/2, 3 -> 2/1.
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        assert chord.voicing([0, 1, 2, 3]).degrees == [
            F(1), F(5, 4), F(3, 2), F(2)]

    def test_the_requested_voice_count_survives_a_later_move(self):
        # The count the caller asked for is a property of the result, so
        # moving it must not undo it.
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        v = chord.voicing([0, 0, 2])
        assert v.transpose('9/8').degrees == [F(9, 8), F(9, 8), F(27, 16)]
        assert v.root('A4').degrees == [F(1), F(1), F(3, 2)]

    def test_a_slice_cannot_produce_duplicates(self):
        # CONTROL. A slice's indices are distinct by construction, so this
        # is unchanged either way; it guards against a fix that widened
        # into the slice branch by accident.
        chord = Chord(['1/1', '5/4', '3/2'], reference_pitch='C4')
        assert chord.voicing(slice(0, 6)).degrees == [
            F(1), F(5, 4), F(3, 2), F(2), F(5, 2), F(3)]


class TestChordSequenceVoicingKeepsTheRequestedCount:
    """``ChordSequence.voicing`` is the fourth sequence mover, beside
    ``root``/``transpose``/``equave_shift``/``folded``. It reduces each
    element to its Chord form and re-voices it, so it inherited
    ``Chord.voicing``'s silent collapse."""

    def test_four_indices_give_four_voices_on_every_element(self):
        seq = ChordSequence([Chord(['1/1', '5/4', '3/2']),
                             Chord(['1/1', '6/5', '3/2'])])
        assert [len(v.degrees) for v in seq.voicing([0, 0, 2, 3])] == [4, 4]

    def test_the_first_element_is_exactly_the_derived_voicing(self):
        # Chord degrees [1/1, 5/4, 3/2]; indices 0, 0, 2, 3 ->
        # 1/1, 1/1, 3/2, 1/1 * 2 = 2/1; sorted -> [1, 1, 3/2, 2].
        seq = ChordSequence([Chord(['1/1', '5/4', '3/2'])])
        assert seq.voicing([0, 0, 2, 3])[0].degrees == [
            F(1), F(1), F(3, 2), F(2)]

    def test_a_voice_led_sequence_can_be_revoiced_without_losing_a_voice(self):
        # End to end, the same shape as the sibling movers' test above:
        # lock four voices, then re-voice the progression with four
        # indices. Re-voicing REPLACES the old voicing (documented), so
        # what must survive is the count the index list asks for.
        led = voice_lead([Chord(['1/1', '5/4', '3/2']),
                          Chord(['1/1', '6/5', '3/2'])],
                         lo='C4', hi='G4', voices=4)
        revoiced = ChordSequence(led).voicing([0, 0, 2, 3])
        assert [len(v.degrees) for v in revoiced] == [4, 4]

    def test_distinct_indices_are_untouched(self):
        # CONTROL: the corpus only ever passes distinct indices, so no
        # existing call may change. Three in, three out, as before.
        seq = ChordSequence([Chord(['1/1', '5/4', '3/2'])])
        assert seq.voicing([0, 2, 4])[0].degrees == [F(1), F(3, 2), F(5, 2)]


# --- the docstring enumeration (item 4) ------------------------------------
#
# "The policy is carried by root(), transpose(), equave_shift() and fold()"
# stopped being true the moment as_voicing() and from_collection() joined the
# set -- and fold() never *carried* it at all, it hardcodes it. An enumeration
# that is wrong is worse than no enumeration, so it is pinned to behaviour
# here rather than left to drift.

#: door name as spelled in the Voicing docstring -> how to call it.
_CARRIER_DOORS = {
    'root()': lambda v: v.root('A4'),
    'transpose()': lambda v: v.transpose('9/8'),
    'equave_shift()': lambda v: v.equave_shift(1),
    'as_voicing()': lambda v: v.as_voicing(),
    'Voicing.from_collection()': lambda v: Voicing.from_collection(v),
}


def _doors_named_in_the_docstring():
    """The ``name()`` tokens the ``dedupe`` docstring lists as carriers.

    Whitespace is normalized first so the answer does not depend on where
    the paragraph happens to line-wrap.
    """
    doc = ' '.join((inspect.getdoc(Voicing) or '').split())
    head = 'carried by every rebuild'
    tail = 'so a locked voice count'
    if head not in doc or tail not in doc:
        return []
    start = doc.index(head)
    if tail not in doc[start:]:
        return []
    segment = doc[start:doc.index(tail, start)]
    return re.findall(r'``([A-Za-z_.]+\(\))``', segment)


class TestTheDocstringEnumerationIsTrue:

    def test_the_docstring_still_enumerates_its_carriers(self):
        named = _doors_named_in_the_docstring()
        assert named, (
            "the Voicing dedupe docstring no longer enumerates the doors "
            "that carry the policy (or this test's markers went stale)")

    def test_it_names_exactly_the_doors_this_file_exercises(self):
        assert set(_doors_named_in_the_docstring()) == set(_CARRIER_DOORS)

    def test_every_named_door_actually_carries_the_policy(self):
        named = _doors_named_in_the_docstring()
        assert named
        for name in named:
            assert name in _CARRIER_DOORS, (
                f"the Voicing docstring names {name} as carrying the dedupe "
                f"policy, but this test cannot call it -- add it here, or "
                f"stop claiming it there")
            moved = _CARRIER_DOORS[name](_unison_doubled())
            assert len(moved.degrees) == 3, f"{name} dropped a voice"
            # and the POLICY carried, not merely this one result's degrees
            assert len(moved.transpose('9/8').degrees) == 3, (
                f"{name} returned a voicing that loses the doubling on the "
                f"next move")

    def test_the_two_doors_that_SET_the_policy_are_not_claimed_as_carriers(self):
        # fold() and Chord.voicing() hardcode dedupe=False; they do not
        # read the source's policy, so listing them among the carriers
        # would be false in the other direction.
        named = _doors_named_in_the_docstring()
        assert 'fold()' not in named
        assert 'Chord.voicing()' not in named
        assert 'voicing()' not in named


class TestVoicingTransposeCarriesReferenceAndEquave:
    """Two surviving mutants on the f1edde3 override (M9, M10). The override
    rebuilds the Voicing itself, so it -- and nothing else -- is now
    responsible for handing on the reference pitch and the equave."""

    def test_transpose_keeps_a_non_default_reference_pitch(self):
        # M9. RelativePitchCollection.transpose carries the transposition
        # in the DEGREES and leaves the reference alone, so an A4-rooted
        # voicing stays A4-rooted: 440 Hz * 9/8 = 495.0 Hz and
        # 440 Hz * 3/2 * 9/8 = 742.5 Hz. Dropping the reference resolves
        # to C4 instead, which no test noticed because every other case
        # in this file is already rooted at C4.
        v = Voicing(['1/1', '3/2'], reference_pitch='A4')
        moved = v.transpose('9/8')
        assert moved.reference_pitch.freq == pytest.approx(440.0)
        assert moved.degrees == [F(9, 8), F(27, 16)]
        assert moved.freqs == pytest.approx((495.0, 742.5))

    def test_transpose_keeps_the_reference_pitch_with_doublings_too(self):
        v = Voicing(['1/1', '1/1', '3/2'], dedupe=False, reference_pitch='A4')
        moved = v.transpose('9/8')
        assert moved.reference_pitch.freq == pytest.approx(440.0)
        assert moved.freqs == pytest.approx((495.0, 495.0, 742.5))

    def test_transpose_keeps_a_non_octave_equave(self):
        # M10. Bohlen-Pierce: the equave is the tritave 3/1. Substituting
        # None there silently defaults to the octave, and every LATER
        # equave-relative operation is then wrong by a fifth per step.
        v = Voicing(['1/1', '5/4', '3/2'], equave=3, reference_pitch='C4')
        assert v.equave == F(3)
        moved = v.transpose('5/4')
        assert moved.equave == F(3)
        # degrees: 1/1*5/4, 5/4*5/4, 3/2*5/4
        assert moved.degrees == [F(5, 4), F(25, 16), F(15, 8)]
        # and the consequence a caller would actually hear: one equave up
        # is times THREE, not times two.
        assert moved.equave_shift(1).degrees == [
            F(15, 4), F(75, 16), F(45, 8)]

    def test_transpose_keeps_a_non_octave_equave_in_cents_mode(self):
        # Same mutant, cents spelling: the tritave is 1901.955 cents, and
        # the octave default would be 1200.0.
        v = Voicing([0.0, 400.0], 'cents', 1901.955, reference_pitch='C4')
        moved = v.transpose('9/8')
        assert moved.equave == pytest.approx(1901.955)
        # 1200 * log2(9/8) = 203.910 cents, added to each degree.
        assert moved.degrees == pytest.approx([203.910, 603.910], abs=1e-3)
        assert moved.equave_shift(1).degrees == pytest.approx(
            [2105.865, 2505.865], abs=1e-3)


class TestFoldSetsItsOwnPolicyDeliberately:
    """DECIDED (AF-1b, this lane): ``fold`` keeps its hardcoded
    ``dedupe=False`` and does NOT honour the source collection's policy.

    Reason, and both R12 lenses agree, so this is not a question for Ryan:

    * ``fold``'s own docstring states the contract -- "One degree in, one
      degree out: folding never merges two degrees that land on the same
      pitch, so a doubled voice stays doubled." Honouring a source policy
      of ``True`` would break that stated contract.
    * Musician's lens: folding is octave displacement. Four notes moved
      into a register are still four notes; two of them landing on the
      same pitch is a unison, which a score writes as two noteheads and
      two players play.
    * Programmer's lens: ``fold`` is a per-degree map. ``len(out)`` must
      equal ``len(in)``; a silent arity change is the entire bug class
      this file exists for.

    (The suite could not tell the two readings apart because every fold
    case it had either began from a ``dedupe=False`` voicing or from a
    Chord, whose degrees are distinct pitch classes and so can never
    collide under whole-equave displacement.)"""

    def test_fold_keeps_both_voices_of_a_DEDUPING_source(self):
        # Source policy is True (the default) and its two degrees are
        # distinct, so it is stored intact: [1/1, 2/1].
        v = Voicing(['1/1', '2/1'], reference_pitch='C4')
        assert v.degrees == [F(1), F(2)]
        # Window [C4, B4] = [261.63, 493.88] Hz. 1/1 sounds C4 -> inside,
        # no displacement. 2/1 sounds C5 = 523.25 Hz -> above the window,
        # so it displaces DOWN one equave to 1/1. Two in, two out.
        assert fold(v, lo='C4', hi='B4').degrees == [F(1), F(1)]

    def test_fold_keeps_both_voices_of_a_source_with_no_policy_at_all(self):
        # A plain RelativePitchCollection has no ``_dedupe`` attribute, so
        # "honour the source's policy" would fall back to the deduping
        # default and drop a degree here.
        plain = RelativePitchCollection(['1/1', '2/1'], reference_pitch='C4')
        assert fold(plain, lo='C4', hi='B4').degrees == [F(1), F(1)]

    def test_the_folded_result_keeps_its_count_on_the_next_move(self):
        v = Voicing(['1/1', '2/1'], reference_pitch='C4')
        folded = fold(v, lo='C4', hi='B4')
        assert folded.transpose('9/8').degrees == [F(9, 8), F(9, 8)]
