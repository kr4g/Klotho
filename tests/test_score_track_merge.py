"""Re-registering ``main`` MERGES; it does not replace the whole record.

``Score.track`` exempts the name ``"main"`` from the already-exists refusal
that every other track gets, because ``"main"`` is implicit and master
inserts have to be settable on it.  What that exemption used to do was a
full dict REPLACEMENT, so the ordinary incremental notebook shape ::

    score.track('main', speakers=PAVILION)   # cell 3: declare the rig
    score.track('main', inserts=[limiter])   # cell 9: add a limiter

silently threw the speaker array away -- and with it the stereo fold and the
binaural decoder.  Worse, the insert-width check is gated on the track having
declared labels, so after the erasure the very insert that CAUSED it was then
never width-checked: the caller landed in a known-broken configuration by
following the path the diagnostics recommend.  Nothing was loud about any of
it, and no test in the suite called ``track('main', ...)`` twice.

The rule this file pins, in one sentence:

    **The arguments a call names are set; the arguments it omits keep what
    the earlier call declared.**

Both halves matter.  "Omitted keeps" is what makes the incremental workflow
above work at all.  "Named replaces" is the other defensible half: the caller
stated an intent this time, ``inserts=`` is the whole chain in signal order
exactly as ``speakers=`` is the whole array, and replacement is what keeps a
re-run notebook cell idempotent instead of stacking a second copy of its
chain every time it is executed.  It also leaves ``inserts=[]`` meaning
"empty the chain", which an appending rule could not express.
"""

from pathlib import Path

import pytest

from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.base import Effect
from klotho.thetos.instruments.synthdef import SynthDefFX
from klotho.thetos.spatial import SpeakerArray
from klotho.utils.playback.supersonic import registry

_PROBE_DIR = Path(__file__).parent / 'fixtures' / 'synthdefs'

# Every bundled non-infrastructure SynthDef is stereo, so a 4-wide insert
# does not exist in the tree; these are the compiled probes that
# test_spatial_lowering.py uses for the same reason.
FX4 = 'spatial_probe_fx4'       # ins/outs == 4


@pytest.fixture(autouse=True)
def _probe_defs():
    """Register the width probe for one test, and unregister it after.

    Registration is process-global, so a leaked ``spatial_probe_*`` would
    make an unrelated test's width check pass for the wrong reason.
    """
    registry.register_compiled_file(_PROBE_DIR / f'{FX4}.scsyndef', kind='fx')
    try:
        yield
    finally:
        registry.clear_runtime()


def quad():
    return SpeakerArray.grid(cols=2, rows=2, col_spacing=50.0,
                             row_spacing=60.0, name='QUAD')


def pavilion():
    return SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0,
                             row_spacing=60.0, name='PAVILION')


# ---------------------------------------------------------------------------
# 1. The defect: an omitted argument must not erase what was declared
# ---------------------------------------------------------------------------


class TestOmittedArgumentsAreKept:
    def test_declaring_inserts_later_keeps_the_speaker_array(self):
        """Cell 3 declares the rig, cell 9 adds a master insert."""
        array = quad()
        s = Score().track('main', speakers=array)
        s.track('main', inserts=[SynthDefFX(FX4)])
        assert s.tracks['main']['labels'] == array.labels
        assert s.tracks['main']['speakers'] is array

    def test_the_geometry_survives_not_just_the_labels(self):
        """A labels-only survival would still lose the binaural fold, which
        is the only thing that makes a 24-speaker piece auditionable on
        headphones."""
        array = quad()
        s = Score().track('main', speakers=array)
        s.track('main', inserts=[SynthDefFX(FX4)])
        assert s.tracks['main']['speakers'] is not None
        assert s.tracks['main']['speakers'].positions == array.positions

    def test_the_lane_map_survives_too(self):
        array = quad()
        s = Score().track('main', speakers=array)
        s.track('main', inserts=[SynthDefFX(FX4)])
        assert s.tracks['main']['lanes'] == {lb: i for i, lb
                                             in enumerate(array.labels)}

    def test_declaring_speakers_later_keeps_the_inserts(self):
        """The mirror image: the rig arrives after the master chain."""
        fx = SynthDefFX(FX4)
        s = Score().track('main', inserts=[fx])
        s.track('main', speakers=quad())
        assert s.tracks['main']['inserts'] == [fx]
        assert s._insert_registry[fx.uid] == 'main'

    def test_a_bare_re_registration_changes_nothing(self):
        array = quad()
        fx = SynthDefFX(FX4)
        s = Score().track('main', speakers=array, inserts=[fx])
        s.track('main')
        assert s.tracks['main']['inserts'] == [fx]
        assert s.tracks['main']['speakers'] is array


# ---------------------------------------------------------------------------
# 2. The judgment call: a NAMED argument replaces
# ---------------------------------------------------------------------------


class TestNamedArgumentsReplace:
    def test_a_second_speakers_replaces_the_array(self):
        """Nobody would read ``speakers=A`` then ``speakers=B`` as a
        six-speaker rig."""
        s = Score().track('main', speakers=quad())
        s.track('main', speakers=['FL', 'FR'])
        assert s.tracks['main']['labels'] == ('FL', 'FR')

    def test_a_second_inserts_replaces_the_chain(self):
        """``inserts=`` is the whole chain in signal order, so it replaces.

        Appending would make the order of the chain unstatable -- there
        would be no way to put a limiter BEFORE an already-declared reverb
        -- and it would make a re-run notebook cell stack a second copy of
        its own chain on every execution.
        """
        a = SynthDefFX('kl_reverb', mix=0.3)
        b = SynthDefFX('kl_lpf', freq=900)
        s = Score().track('main', inserts=[a])
        s.track('main', inserts=[b])
        assert s.tracks['main']['inserts'] == [b]

    def test_a_replaced_insert_is_released_and_placeable_again(self):
        """A dropped insert must not stay owned by a chain it has left, or
        the refusal that guards uid sharing starts telling the caller
        something false."""
        a = SynthDefFX('kl_reverb', mix=0.3)
        s = Score().track('main', inserts=[a])
        s.track('main', inserts=[SynthDefFX('kl_lpf', freq=900)])
        assert a.uid not in s._insert_registry
        s.track('pads', inserts=[a])
        assert s.tracks['pads']['inserts'] == [a]

    def test_an_empty_list_empties_the_chain(self):
        a = SynthDefFX('kl_reverb', mix=0.3)
        s = Score().track('main', inserts=[a])
        s.track('main', inserts=[])
        assert s.tracks['main']['inserts'] == []
        assert a.uid not in s._insert_registry

    def test_re_running_the_same_cell_is_idempotent(self):
        """Each execution of a notebook cell builds fresh Effect objects, so
        an appending rule would grow the chain without bound."""
        s = Score()
        for _ in range(3):
            s.track('main', speakers=quad(),
                    inserts=[SynthDefFX(FX4)])
        assert len(s.tracks['main']['inserts']) == 1
        assert len(s._insert_registry) == 1

    def test_keeping_the_old_chain_and_adding_to_it_is_spelled_out(self):
        """The additive form is available -- you write it, in the order you
        want it -- and re-listing an insert already on THIS track is not a
        uid conflict."""
        a = SynthDefFX('kl_reverb', mix=0.3)
        b = SynthDefFX('kl_lpf', freq=900)
        s = Score().track('main', inserts=[a])
        s.track('main', inserts=[a, b])
        assert s.tracks['main']['inserts'] == [a, b]


# ---------------------------------------------------------------------------
# 3. The width check now actually runs -- a behavior change, and a wanted one
# ---------------------------------------------------------------------------


class TestTheWidthCheckNoLongerSlipsThrough:
    def test_a_stereo_insert_added_after_the_array_is_refused(self):
        """Before the merge this was the silent path: the array was erased,
        so ``labels`` was None, so the insert that erased it was never
        checked."""
        s = Score().track('main', speakers=pavilion())
        with pytest.raises(ValueError) as e:
            s.track('main', inserts=[SynthDefFX('kl_reverb')])
        assert 'reads 2 and writes 2' in str(e.value)
        assert '24 channels wide' in str(e.value)

    def test_an_array_declared_over_a_stereo_chain_is_refused(self):
        """Inserts carried over from an earlier call are re-checked, because
        the newly declared array changes the width they must match."""
        s = Score().track('main', inserts=[SynthDefFX('kl_reverb')])
        with pytest.raises(ValueError, match='reads 2 and writes 2'):
            s.track('main', speakers=pavilion())

    def test_a_matching_insert_added_after_the_array_is_accepted(self):
        s = Score().track('main', speakers=quad())
        s.track('main', inserts=[SynthDefFX(FX4)])
        assert len(s.tracks['main']['inserts']) == 1
        assert s.tracks['main']['labels'] == quad().labels

    def test_a_refused_merge_leaves_the_track_exactly_as_it_was(self):
        """Validation still happens before any mutation -- a caught refusal
        must not leave half the merge applied."""
        fx = SynthDefFX('kl_reverb')
        s = Score().track('main', speakers=pavilion())
        with pytest.raises(ValueError):
            s.track('main', inserts=[fx])
        assert s.tracks['main']['inserts'] == []
        assert s.tracks['main']['labels'][-1] == 24
        assert fx.uid not in s._insert_registry


# ---------------------------------------------------------------------------
# 4. What the merge must NOT relax
# ---------------------------------------------------------------------------


class TestTheRefusalsThatStay:
    def test_a_non_main_track_still_cannot_be_re_registered(self):
        s = Score().track('pads')
        with pytest.raises(ValueError, match="already exists"):
            s.track('pads')

    def test_an_insert_owned_by_another_track_is_still_refused(self):
        fx = SynthDefFX('kl_reverb')
        s = Score().track('pads', inserts=[fx])
        with pytest.raises(ValueError, match="already assigned to track 'pads'"):
            s.track('main', inserts=[fx])

    def test_one_insert_cannot_appear_twice_in_one_chain(self):
        """Pre-existing hole, closed here because the merge would otherwise
        widen it: the engine keys an insert node by uid
        (``track.insertNodes[fxUid] = fxNodeId``), so a repeat overwrites the
        first node's handle and leaves it unaddressable for the rest of the
        performance.
        """
        fx = SynthDefFX('kl_reverb')
        s = Score()
        with pytest.raises(ValueError, match='appears twice'):
            s.track('main', inserts=[fx, fx])
        assert 'main' not in s.tracks
        assert s._insert_registry == {}

    def test_a_re_registration_does_not_move_main_in_the_track_order(self):
        """``meta.groups`` and the score plot's band order both come from
        the insertion order of the tracks dict."""
        s = Score().track('main').track('pads').track('drums')
        s.track('main', inserts=[SynthDefFX('kl_reverb')])
        assert list(s.tracks.keys()) == ['main', 'pads', 'drums']


# ---------------------------------------------------------------------------
# 5. What the caller actually gets: the payload
# ---------------------------------------------------------------------------


class TestTheMergedTrackLowersLikeAOneCallDeclaration:
    def test_the_spatial_meta_survives_the_second_call(self):
        """The whole point of the merge, stated at the far end: a rig
        declared in one cell and an insert added in another must still
        produce a spatial payload with its decoder, not a stereo one."""
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )

        s = Score().track('main', speakers=quad())
        s.track('main', inserts=[SynthDefFX(FX4)])
        meta = convert_score_to_sc_events(s)['meta']
        assert meta['spatial']['tracks']['main'] == {'array': 'QUAD',
                                                     'width': 4}
        assert meta['spatial']['arrays']['QUAD']['decoder'] is not None
        assert meta['inserts']['main'][0]['defName'] == FX4


# ---------------------------------------------------------------------------
# 6. Un-declaring an array: the symmetry the merge owed ``inserts=[]``
# ---------------------------------------------------------------------------
#
# The merge made "omitted keeps" the rule for ``speakers=`` as well as
# ``inserts=``, and that closed the only door back out of a spatial main:
# ``inserts=[]`` emptied the chain, ``speakers=[]`` raised, and nothing at all
# made a spatial track stereo again.  The error message even advised dropping
# ``speakers=``, which after the merge is exactly the thing that KEEPS the
# array -- it sent the caller in a circle.
#
# The rule now, one sentence for both arguments:
#
#     **An empty collection is the un-declare.**
#
# ``speakers=[]`` is refused only where there is no array to un-declare, which
# is where an empty list is far more likely a label list that computed to
# nothing than a deliberate no-op -- and where it would in any case be
# indistinguishable from leaving the argument off.


class TestAnEmptyArrayUnDeclares:
    def test_speakers_empty_makes_a_spatial_main_stereo_again(self):
        s = Score().track('main', speakers=quad())
        assert s.tracks['main']['labels'] is not None
        s.track('main', speakers=[])
        assert s.tracks['main']['labels'] is None
        assert s.tracks['main']['speakers'] is None
        assert s.tracks['main']['lanes'] is None

    def test_the_track_survives_the_un_declaration(self):
        """Un-declaring the array is not deleting the track: main keeps its
        chain, its place in the track order, and its ability to take
        events."""
        fx = SynthDefFX('kl_reverb', mix=0.3)
        s = Score().track('main', speakers=quad()).track('pads')
        s.track('main', speakers=[], inserts=[fx])
        assert list(s.tracks.keys()) == ['main', 'pads']
        assert s.tracks['main']['inserts'] == [fx]

    def test_an_un_declared_main_lowers_as_an_ordinary_stereo_track(self):
        """The far end: no spatial meta at all, so no decoder and no wide
        buses -- not a 4-lane payload with the geometry quietly missing."""
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )

        s = Score().track('main', speakers=quad())
        s.track('main', speakers=[])
        assert 'spatial' not in convert_score_to_sc_events(s)['meta']

    def test_an_empty_array_is_still_refused_where_there_is_none_to_clear(self):
        """``speakers=[]`` on a track that declares no array would be a
        no-op indistinguishable from omitting the argument, and is much more
        likely a label list that computed to nothing."""
        with pytest.raises(ValueError, match='declares no speakers'):
            Score().track('main', speakers=[])
        with pytest.raises(ValueError, match='declares no speakers'):
            Score().track('pads', speakers=[])

    def test_the_refusal_message_advises_something_that_works(self):
        """The message this replaces ended 'drop speakers= to leave main an
        ordinary stereo track'.  After the merge, dropping ``speakers=`` is
        the thing that KEEPS the array, so the advice was false on exactly
        the score that would need it.  What it says now has to hold.
        """
        with pytest.raises(ValueError) as e:
            Score().track('main', speakers=[])
        msg = str(e.value)
        assert 'leave speakers= off entirely' in msg
        # ... and that is true: on a first registration, no speakers= at all
        # does leave an ordinary stereo track.
        assert Score().track('main').tracks['main']['labels'] is None
        # The message must not still be recommending the circular route.
        assert 'drop speakers= to leave' not in msg

    def test_an_insert_too_wide_for_the_stereo_chain_is_refused(self):
        """The hole the new spelling would otherwise open: an insert
        accepted against a 4-speaker array, carried over by an omitted
        ``inserts=``, would land on a 2-channel chain and read past the bus.
        Nothing downstream would say so.
        """
        s = Score().track('main', speakers=quad(),
                          inserts=[SynthDefFX(FX4)])
        with pytest.raises(ValueError) as e:
            s.track('main', speakers=[])
        assert 'reads 4 and writes 4' in str(e.value)
        assert s.tracks['main']['labels'] == quad().labels   # nothing applied

    def test_restating_the_chain_in_the_same_call_is_accepted(self):
        """What the refusal tells the caller to do has to work."""
        s = Score().track('main', speakers=quad(),
                          inserts=[SynthDefFX(FX4)])
        s.track('main', speakers=[], inserts=[SynthDefFX('kl_reverb')])
        assert s.tracks['main']['labels'] is None
        assert [i.defName for i in s.tracks['main']['inserts']] == ['kl_reverb']

    def test_emptying_both_collections_at_once_is_accepted(self):
        s = Score().track('main', speakers=quad(), inserts=[SynthDefFX(FX4)])
        s.track('main', speakers=[], inserts=[])
        assert s.tracks['main']['labels'] is None
        assert s.tracks['main']['inserts'] == []
        assert s._insert_registry == {}

    def test_a_stereo_insert_carried_over_is_fine(self):
        """Only the too-wide direction is refused; a stereo insert is
        exactly what a stereo chain wants."""
        fx = SynthDefFX('kl_reverb')
        s = Score().track('main', speakers=['FL', 'FR'], inserts=[fx])
        s.track('main', speakers=[])
        assert s.tracks['main']['inserts'] == [fx]

    def test_the_other_empty_shapes_un_declare_too(self):
        """It is emptiness that means un-declare, not the list type."""
        for empty in ((), [], range(0)):
            s = Score().track('main', speakers=quad())
            s.track('main', speakers=empty)
            assert s.tracks['main']['labels'] is None, empty

    def test_an_empty_string_is_still_one_label_not_an_un_declaration(self):
        """A string is refused before emptiness is ever considered -- a
        label that computed to '' must not silently wipe the rig."""
        s = Score().track('main', speakers=quad())
        with pytest.raises(ValueError, match='one label, not an array'):
            s.track('main', speakers='')
        assert s.tracks['main']['labels'] == quad().labels


# ---------------------------------------------------------------------------
# 7. The SILENT consequence of the merge: whose geometry the headphones fold
# ---------------------------------------------------------------------------
#
# The binaural fold is ONE decoder on the summed main bus, so when several
# equally-wide spatial tracks declare different arrays, exactly one geometry
# can describe the result.  ``scheduler_score.js`` breaks that tie in main's
# favour (``var chosen = (widest.indexOf('main') !== -1) ? 'main' : widest[0]``).
#
# While the second ``track('main', ...)`` call erased main's array, main was
# not spatial, so it dropped out of the tie and the OTHER track's geometry was
# folded.  Keeping the array puts main back in the tie and main's own geometry
# wins -- measurably different coefficients, no error on either path.  That is
# the correct answer (main is the chain the decoder sits on) but it is a
# behavior change with no diagnostic, so it is pinned here.


class TestWhoseGeometryTheHeadphoneFoldUses:
    @staticmethod
    def _meta(score):
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )
        return convert_score_to_sc_events(score)['meta']

    @staticmethod
    def _other_rig():
        """Same WIDTH as ``quad()``, different geometry -- so the tie is
        real and the two folds are genuinely different."""
        return SpeakerArray.grid(cols=4, rows=1, col_spacing=200.0,
                                 row_spacing=10.0, name='WIDE_ROW')

    def test_main_stays_in_the_tie_after_a_second_registration(self):
        """The input the JS tie-break reads: main must still appear in
        ``meta.spatial.tracks`` at the widest width, or it cannot win."""
        s = Score().track('main', speakers=quad()).track('pads',
                                                         speakers=self._other_rig())
        s.track('main', inserts=[SynthDefFX(FX4)])
        tracks = self._meta(s)['spatial']['tracks']
        assert tracks['main'] == {'array': 'QUAD', 'width': 4}
        assert tracks['pads']['width'] == tracks['main']['width']

    def test_the_two_geometries_really_do_fold_differently(self):
        """Without this the pin above would be about a distinction with no
        audible consequence."""
        s = Score().track('main', speakers=quad()).track('pads',
                                                         speakers=self._other_rig())
        arrays = self._meta(s)['spatial']['arrays']
        assert (arrays['QUAD']['decoder']['coefficients']
                != arrays['WIDE_ROW']['decoder']['coefficients'])

    def test_un_declaring_main_hands_the_fold_back(self):
        """The other half of the same rule, and the reason ``speakers=[]``
        is worth having: a composer who wants the sub-track's geometry
        folded can say so, and the payload shows main out of the tie."""
        s = Score().track('main', speakers=quad()).track('pads',
                                                         speakers=self._other_rig())
        s.track('main', speakers=[])
        tracks = self._meta(s)['spatial']['tracks']
        assert 'main' not in tracks
        assert tracks['pads']['array'] == 'WIDE_ROW'


# ---------------------------------------------------------------------------
# 8. The duplicate refusal must survive contact with a bare ``Effect``
# ---------------------------------------------------------------------------
#
# ``defName`` belongs to ``SynthDefFX``; the ``Effect`` base class has no such
# attribute.  The duplicate-in-one-chain message named it while formatting the
# advice, so the one input that most needs the teaching message -- an Effect
# subclass that is not a SynthDefFX -- got ``AttributeError: 'Effect' object
# has no attribute 'defName'`` instead, from inside the raise.


class TestTheDuplicateRefusalOnABareEffect:
    def test_a_bare_effect_listed_twice_raises_the_teaching_error(self):
        e = Effect('myfx')
        assert not hasattr(e, 'defName')      # the premise of the bug
        with pytest.raises(ValueError, match='appears twice'):
            Score().track('x', inserts=[e, e])

    def test_the_advice_does_not_name_a_synthdef_that_does_not_exist(self):
        """A bare Effect has no def name to build a second instance FROM,
        so the message must not print ``SynthDefFX('None')``."""
        with pytest.raises(ValueError) as e:
            Score().track('x', inserts=[Effect('myfx'), Effect('myfx')][:1] * 2)
        assert 'None' not in str(e.value)
        assert 'build two instances' in str(e.value)

    def test_a_synthdeffx_still_gets_the_concrete_two_instance_advice(self):
        fx = SynthDefFX('kl_reverb')
        with pytest.raises(ValueError) as e:
            Score().track('x', inserts=[fx, fx])
        assert "SynthDefFX('kl_reverb'), SynthDefFX('kl_reverb')" in str(e.value)

    def test_the_refused_track_is_not_half_registered(self):
        e = Effect('myfx')
        s = Score()
        with pytest.raises(ValueError):
            s.track('x', inserts=[e, e])
        assert 'x' not in s.tracks
        assert s._insert_registry == {}


class TestUnDeclaringWithVoicesStillRoutedToSpeakers:
    """The trap the new spelling could have set, and the reason it does not.

    ``speakers=[]`` can be typed on a score whose voices already carry a
    ``speaker`` mfield.  Nothing in ``track()`` can see those voices, so the
    question is only whether the far end is LOUD about it.  It is: lowering
    refuses a ``speaker=`` on a track with no array, by name and by lane.
    A silent answer here -- the voice quietly reverting to stereo -- would be
    the worse half of the very defect the merge fixed.
    """

    def test_lowering_refuses_the_orphaned_speaker_by_name(self):
        from klotho.chronos.temporal_units import TemporalUnit  # noqa: F401
        from klotho.thetos.composition.compositional import CompositionalUnit
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )

        uc = CompositionalUnit(span=1, tempus='1/1', prolatio=(1, 1))
        uc.set(uc.leaves, speaker=3)
        s = Score().track('main', speakers=quad())
        s.add(uc, track='main')
        assert 'spatial' in convert_score_to_sc_events(s)['meta']

        s.track('main', speakers=[])
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        assert 'speaker=3' in str(e.value)
        assert 'no speaker array' in str(e.value)
