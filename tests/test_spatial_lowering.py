"""Multichannel output: ``speaker`` routing, track widths, ``meta.spatial``.

The claim this file exists to pin, in one sentence:

    A voice writes to ONE bus channel per loudspeaker, chosen by the LABEL
    the rig carries, and everything that could put it somewhere else is
    refused rather than guessed at.

The pieces, and why each is here rather than assumed:

* **``speaker`` is an mfield, a sibling of ``group``.**  Ryan's definition:
  an mfield is not a pfield but has an effect on one or more pfields.
  ``group`` declares no synth control and its whole effect is to set
  ``out`` -- it picks WHICH BUS.  ``speaker`` does the same at finer grain:
  it picks the LANE within that bus.  Membership in ``ENGINE_MFIELDS`` is
  therefore not a convenience, it is the type of the thing, and it buys the
  inheritance, ``Pattern`` distribution, copy-safety and
  cannot-change-on-a-live-node rules for free.

* **An instrument occupies as many ADJACENT speakers as its ``Out`` is
  wide.**  ``Out.ar(out, sig)`` writes ``sig.numChannels`` consecutive
  channels; that is a fact about SuperCollider, so the design declares and
  validates it instead of fighting it.  A 1-channel def at speaker 17 is a
  point source; a 2-channel def occupies 17 and 18 and pans between two
  REAL speakers, which is what retires the ``HARD_PAN_TRIM_DB = -3.01``
  workaround (no phantom pair is ever summed) and the canary channels (no
  write can leave the array unnoticed).

* **Refusal is a legitimate answer.**  Every message below names the
  offending value and says what to do instead.  The cost of guessing here
  is not a wrong number, it is a sound arriving fifty feet from where it
  was written.

Fixtures: the bundled SynthDefs are all 2 channels wide, so a point source
and a 24-wide insert do not exist in the tree.  Real compiled blobs for
both live in ``fixtures/synthdefs/spatial_probe_*.scsyndef`` -- see
``spatial_probe_build.py`` beside them.
"""

import json
import warnings
from pathlib import Path

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos import SpeakerArray
from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.synthdef import SynthDefFX
from klotho.topos.collections.sequences import Pattern
from klotho.utils.playback.supersonic import registry
from klotho.utils.playback.supersonic.converters import (
    convert_score_to_sc_events,
    convert_to_sc_events,
)

_PROBE_DIR = Path(__file__).parent / 'fixtures' / 'synthdefs'

MONO = 'spatial_probe_mono'     # outs == 1 -- a point source
FX4 = 'spatial_probe_fx4'       # ins/outs == 4
FX24 = 'spatial_probe_fx24'     # ins/outs == 24
FX_ASYM = 'spatial_probe_fx4in2out'   # ins == 4, outs == 2
STEREO = 'kl_tri'               # outs == 2, like every bundled instrument


@pytest.fixture(autouse=True)
def _probe_defs():
    """Register the width probes for the duration of one test.

    Registration is process-global, so the teardown matters: a leaked
    ``spatial_probe_*`` would make an unrelated test's width check pass
    for the wrong reason.
    """
    registry.register_compiled_file(_PROBE_DIR / f'{MONO}.scsyndef',
                                    kind='inst')
    registry.register_compiled_file(_PROBE_DIR / f'{FX4}.scsyndef', kind='fx')
    registry.register_compiled_file(_PROBE_DIR / f'{FX24}.scsyndef', kind='fx')
    registry.register_compiled_file(_PROBE_DIR / f'{FX_ASYM}.scsyndef',
                                    kind='fx')
    try:
        yield
    finally:
        registry.clear_runtime()


def quad(name='QUAD'):
    """A 2x2 grid, labels 1..4, so a lane overrun is two speakers away."""
    return SpeakerArray.grid(cols=2, rows=2, col_spacing=50.0,
                             row_spacing=60.0, name=name)


def pavilion():
    """The Sonic Pavilion: 6x4 at 50 x 60 ft, labels 1..24."""
    return SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0,
                             row_spacing=60.0, name='PAVILION')


def unit(inst=MONO, n=4, speakers=(1, 2, 3, 4)):
    uc = UC(tempus='4/4', prolatio=(1,) * n, beat='1/4', bpm=120, inst=inst)
    if speakers is not None:
        uc.set(uc.leaves, speaker=Pattern(list(speakers)))
    return uc


def news(payload):
    return [e for e in payload['events'] if e['type'] == 'new']


def lanes_of(payload):
    return [(e.get('speaker'), e.get('speakerLane')) for e in news(payload)]


# ---------------------------------------------------------------------------
# 1. speaker is an engine mfield, with everything that implies
# ---------------------------------------------------------------------------


class TestSpeakerIsAnMfield:
    def test_it_lands_in_mfields_not_pfields(self):
        uc = unit(speakers=None)
        uc.set(uc.leaves, speaker=17)
        leaf = uc.leaves[0].id
        assert uc.get_mfield(leaf, 'speaker') == 17
        assert uc.get_pfield(leaf, 'speaker') is None

    def test_it_inherits_from_an_ancestor(self):
        """Set once at the root, effective on every leaf -- the property
        that lets a whole passage sit on one speaker in one line."""
        uc = unit(speakers=None)
        uc.set(uc.root, speaker=9)
        assert [uc.get_mfield(l.id, 'speaker') for l in uc.leaves] == [9] * 4

    def test_a_pattern_distributes_across_the_leaves(self):
        """The travelling gesture: a phrase that walks the array."""
        uc = unit(speakers=None)
        uc.set(uc.leaves, speaker=Pattern([1, 3]))
        assert [uc.get_mfield(l.id, 'speaker') for l in uc.leaves] == [1, 3, 1, 3]

    def test_a_callable_sees_the_node_context(self):
        uc = unit(speakers=None)
        uc.set(uc.leaves, speaker=lambda ctx: ctx.index + 1)
        assert [uc.get_mfield(l.id, 'speaker') for l in uc.leaves] == [1, 2, 3, 4]

    def test_string_labels_work(self):
        """The rig may be labelled 'FL'/'FR', not 1..24."""
        uc = unit(speakers=None)
        uc.set(uc.leaves, speaker=Pattern(['FL', 'FR']))
        assert uc.get_mfield(uc.leaves[0].id, 'speaker') == 'FL'

    def test_it_survives_copy(self):
        uc = unit()
        dup = uc.copy()
        assert [dup.get_mfield(l.id, 'speaker') for l in dup.leaves] == \
            [1, 2, 3, 4]

    def test_a_copy_does_not_alias_the_original(self):
        uc = unit()
        dup = uc.copy()
        dup.set(dup.leaves, speaker=1)
        assert [uc.get_mfield(l.id, 'speaker') for l in uc.leaves] == \
            [1, 2, 3, 4]

    def test_a_pfield_named_speaker_does_not_move_the_routing(self):
        """The collision the pfield/mfield split was built to close, on the
        field it was built for."""
        uc = unit()
        uc.set_pfields(uc.leaves[0].id, speaker=999.0)
        assert uc.get_mfield(uc.leaves[0].id, 'speaker') == 1

    def test_it_cannot_be_changed_on_a_live_node(self):
        """Ruling four: a source does not move across speakers during a
        held note in v1. Engine mfields are already forbidden on a live
        node, so membership in ENGINE_MFIELDS delivers that rule."""
        s = Score()
        h = s.new(0.0, dur=None, inst=STEREO, freq=440.0)
        with pytest.raises(ValueError, match='cannot be changed on a live node'):
            s.set(h, at=1.0, speaker=3)


# ---------------------------------------------------------------------------
# 2. Declaring the array on a track
# ---------------------------------------------------------------------------


class TestTrackDeclaration:
    def test_a_speaker_array_declares_the_width(self):
        s = Score().track('array', speakers=pavilion())
        assert s.tracks['array']['labels'] == tuple(range(1, 25))
        assert s.tracks['array']['lanes'][1] == 0
        assert s.tracks['array']['lanes'][24] == 23

    def test_a_bare_sequence_of_labels_declares_routing_only(self):
        s = Score().track('array', speakers=range(1, 5))
        assert s.tracks['array']['labels'] == (1, 2, 3, 4)
        assert s.tracks['array']['speakers'] is None

    def test_string_labels_declare_a_track(self):
        s = Score().track('quad', speakers=['FL', 'FR', 'RL', 'RR'])
        assert s.tracks['quad']['lanes'] == {'FL': 0, 'FR': 1, 'RL': 2,
                                               'RR': 3}

    def test_a_bare_count_is_refused_as_ambiguous(self):
        with pytest.raises(ValueError, match='ambiguous'):
            Score().track('array', speakers=24)

    def test_a_bare_count_names_both_conventions_it_refuses_to_pick(self):
        with pytest.raises(ValueError) as e:
            Score().track('array', speakers=24)
        assert '0..n-1' in str(e.value) and '1..n' in str(e.value)

    def test_one_string_is_one_label_not_an_array(self):
        """``speakers='FL'`` would iterate to 'F' and 'L'."""
        with pytest.raises(ValueError, match='one label, not an array'):
            Score().track('array', speakers='FL')

    def test_an_empty_array_is_refused(self):
        with pytest.raises(ValueError, match='declares no speakers'):
            Score().track('array', speakers=[])

    def test_a_duplicate_label_is_refused(self):
        with pytest.raises(ValueError, match='appears twice'):
            Score().track('array', speakers=[1, 2, 2, 3])

    def test_a_float_cannot_name_a_speaker(self):
        with pytest.raises(ValueError, match='must be an int or a str'):
            Score().track('array', speakers=[1.5, 2.5])

    def test_a_bool_cannot_name_a_speaker(self):
        """``True`` is an ``int`` in Python and would collide with 1."""
        with pytest.raises(ValueError, match='must be an int or a str'):
            Score().track('array', speakers=[True, False])

    def test_a_non_sequence_is_refused(self):
        with pytest.raises(ValueError, match='not a sequence'):
            Score().track('array', speakers=object())

    def test_a_track_with_no_speakers_is_unchanged(self):
        s = Score().track('dry')
        assert s.tracks['dry']['labels'] is None


# ---------------------------------------------------------------------------
# 3. Speakers and inserts together -- the crux
# ---------------------------------------------------------------------------


class TestInsertWidth:
    def test_a_matching_insert_is_accepted(self):
        s = Score().track('array', speakers=quad(),
                          inserts=[SynthDefFX(FX4, gain=0.5)])
        assert len(s.tracks['array']['inserts']) == 1

    def test_a_spatial_voice_still_goes_through_the_chain(self):
        """Speakers and inserts compose. A voice does not bypass its
        track's FX because it named a loudspeaker -- a musician reading
        'this staff has reverb' expects it wherever the note sounds."""
        s = Score().track('array', speakers=quad(),
                          inserts=[SynthDefFX(FX4, gain=0.5)])
        s.add(unit(), name='sweep', track='array')
        payload = convert_score_to_sc_events(s)
        assert payload['meta']['inserts']['array'][0]['defName'] == FX4
        assert all(e['group'] == 'array' for e in news(payload))
        assert lanes_of(payload) == [(1, 0), (2, 1), (3, 2), (4, 3)]

    def test_a_stereo_insert_on_a_24_wide_track_is_refused(self):
        with pytest.raises(ValueError) as e:
            Score().track('array', speakers=pavilion(),
                          inserts=[SynthDefFX('kl_reverb')])
        msg = str(e.value)
        assert 'reads 2 and writes 2' in msg
        assert '24 channels wide' in msg
        assert 'In.ar(inBus, 24)' in msg

    def test_a_24_wide_insert_on_a_4_speaker_track_is_refused(self):
        """The mismatch is refused in BOTH directions -- too wide is as
        wrong as too narrow."""
        with pytest.raises(ValueError, match='reads 24 and writes 24'):
            Score().track('array', speakers=quad(),
                          inserts=[SynthDefFX(FX24)])

    def test_a_24_wide_insert_fits_a_24_speaker_track(self):
        s = Score().track('array', speakers=pavilion(),
                          inserts=[SynthDefFX(FX24)])
        assert s.tracks['array']['labels'][-1] == 24

    def test_an_insert_that_reads_wide_and_writes_narrow_is_refused(self):
        """BOTH halves are checked, not just the input.

        An insert reading 4 and writing 2 would take the whole array in and
        put two lanes back, leaving speakers 3 and 4 carrying whatever the
        previous node left there. With only symmetric probes on hand, a
        check that tested ``ins`` and ignored ``outs`` passed every test in
        this file -- which is why this def exists.
        """
        with pytest.raises(ValueError) as e:
            Score().track('array', speakers=quad(),
                          inserts=[SynthDefFX(FX_ASYM)])
        assert 'reads 4 and writes 2' in str(e.value)

    def test_an_insert_of_unknown_width_is_refused_not_guessed(self):
        with pytest.raises(ValueError) as e:
            Score().track('array', speakers=quad(),
                          inserts=[SynthDefFX('no_such_fx')])
        msg = str(e.value)
        assert 'no recorded channel count' in msg
        assert 'io.json' in msg and 'register_synthdef()' in msg

    def test_a_stereo_track_still_takes_a_stereo_insert(self):
        """Non-spatial tracks are untouched: the width contract applies
        only where a width was declared."""
        s = Score().track('wet', inserts=[SynthDefFX('kl_reverb', mix=0.4)])
        assert len(s.tracks['wet']['inserts']) == 1

    def test_a_refused_insert_leaves_the_score_untouched(self):
        """A caught refusal must not leave half a track registered, or the
        insert would be owned by a track that does not exist."""
        s = Score()
        fx = SynthDefFX('kl_reverb')
        with pytest.raises(ValueError):
            s.track('array', speakers=pavilion(), inserts=[fx])
        assert 'array' not in s.tracks
        assert fx.uid not in s._insert_registry
        # ...and the same insert is still placeable somewhere it fits.
        s.track('wet', inserts=[fx])
        assert s.tracks['wet']['inserts'] == [fx]


# ---------------------------------------------------------------------------
# 4. Lowering: label -> lane, and the occupancy rules
# ---------------------------------------------------------------------------


class TestLaneResolution:
    def test_labels_resolve_to_lanes(self):
        s = Score().track('array', speakers=quad())
        s.add(unit(), name='sweep', track='array')
        assert lanes_of(convert_score_to_sc_events(s)) == \
            [(1, 0), (2, 1), (3, 2), (4, 3)]

    def test_labels_are_not_lane_indices(self):
        """A rig labelled 101..104 routes to lanes 0..3. Guessing that a
        label IS an index is the off-by-one this design exists to make
        impossible."""
        s = Score().track('array', speakers=[101, 102, 103, 104])
        s.add(unit(speakers=(101, 102, 103, 104)), name='sweep',
              track='array')
        assert lanes_of(convert_score_to_sc_events(s)) == \
            [(101, 0), (102, 1), (103, 2), (104, 3)]

    def test_string_labels_resolve_to_lanes(self):
        s = Score().track('quad', speakers=['FL', 'FR', 'RL', 'RR'])
        s.add(unit(speakers=('FL', 'RR', 'FL', 'RR')), name='x',
              track='quad')
        assert lanes_of(convert_score_to_sc_events(s)) == \
            [('FL', 0), ('RR', 3), ('FL', 0), ('RR', 3)]

    def test_two_voices_on_one_speaker_is_ordinary(self):
        """Not an edge case -- it is the whole reason the bus is widened
        rather than the track narrowed. Both write the same lane and both
        pass through the same chain."""
        s = Score().track('array', speakers=quad(),
                          inserts=[SynthDefFX(FX4)])
        s.add(unit(speakers=(2, 2, 2, 2)), name='a', track='array')
        s.add(unit(speakers=(2, 2, 2, 2)), name='b', track='array')
        payload = convert_score_to_sc_events(s)
        assert len(news(payload)) == 8
        assert set(lanes_of(payload)) == {(2, 1)}

    def test_a_stereo_def_occupies_two_adjacent_speakers(self):
        """``Out.ar(out, sig)`` writes ``sig.numChannels`` consecutive
        channels. A 2-channel def at speaker 1 lands on 1 AND 2, which is
        declared and validated rather than leaked."""
        s = Score().track('array', speakers=quad())
        s.add(unit(inst=STEREO, speakers=(1, 2, 3, 1)), name='x',
              track='array')
        assert lanes_of(convert_score_to_sc_events(s)) == \
            [(1, 0), (2, 1), (3, 2), (1, 0)]

    def test_a_stereo_def_at_the_last_speaker_is_refused(self):
        """Speaker 4 of 4 would occupy 4 and 5. Nothing spills past the
        end of the array in silence -- this is what the canary channels
        used to catch after the fact."""
        s = Score().track('array', speakers=quad())
        s.add(unit(inst=STEREO, speakers=(4, 4, 4, 4)), name='x',
              track='array')
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        msg = str(e.value)
        assert 'writes 2 channels' in msg
        assert 'the array ends at 4' in msg
        assert '1-channel SynthDef' in msg

    def test_a_point_source_at_the_last_speaker_is_fine(self):
        """The remedy the refusal above names actually works."""
        s = Score().track('array', speakers=quad())
        s.add(unit(inst=MONO, speakers=(4, 4, 4, 4)), name='x',
              track='array')
        assert set(lanes_of(convert_score_to_sc_events(s))) == {(4, 3)}

    def test_an_unknown_label_is_refused_and_the_known_ones_listed(self):
        s = Score().track('array', speakers=quad())
        s.add(unit(speakers=(1, 2, 3, 25)), name='x', track='array')
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        msg = str(e.value)
        assert 'no speaker labelled 25' in msg
        assert 'Known speakers: 1, 2, 3, 4' in msg
        assert 'not by a 0-based index' in msg

    def test_a_voice_with_no_speaker_on_a_spatial_track_is_refused(self):
        """Klotho will not pick one of 24 loudspeakers for you."""
        s = Score().track('array', speakers=pavilion())
        s.add(unit(speakers=None), name='x', track='array')
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        msg = str(e.value)
        assert 'names no speaker' in msg
        assert 'set_pfields(speaker=...) does NOT route' in msg

    def test_a_speaker_on_a_non_spatial_track_is_refused(self):
        s = Score().track('dry')
        s.add(unit(), name='x', track='dry')
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        assert 'has no speaker array' in str(e.value)

    def test_a_speaker_with_no_tracks_at_all_is_refused(self):
        """An untagged voice plays through main; main declares nothing."""
        s = Score()
        s.add(unit(), name='x')
        with pytest.raises(ValueError, match="master chain \\('main'\\)"):
            convert_score_to_sc_events(s)

    def test_an_instrument_of_unknown_width_is_refused(self):
        s = Score().track('array', speakers=quad())
        uc = unit(inst='kl_tri')
        uc.set_instrument(uc.leaves, 'kl_tri')
        s.add(uc, name='x', track='array')
        # A def with no io record at all: registered controls, no widths.
        registry._RUNTIME['ghost_inst'] = {
            'b64': '', 'controls': {'freq': 440.0}, 'kind': 'inst', 'io': None}
        registry._REGISTRY_VERSION += 1
        s2 = Score().track('array', speakers=quad())
        s2.add(unit(inst='ghost_inst'), name='x', track='array')
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s2)
        assert 'no recorded channel count' in str(e.value)

    def test_main_can_be_the_spatial_track(self):
        s = Score().track('main', speakers=quad())
        s.add(unit(), name='x')
        assert lanes_of(convert_score_to_sc_events(s)) == \
            [(1, 0), (2, 1), (3, 2), (4, 3)]


class TestPanAlongsideSpeaker:
    def test_pan_is_allowed_on_a_two_channel_def(self):
        """Ruling three: pan becomes pairwise amplitude panning between
        two adjacent REAL speakers, so there is no 3 dB centre bump to
        compensate and ``HARD_PAN_TRIM_DB`` has nothing to correct."""
        s = Score().track('array', speakers=quad())
        uc = unit(inst=STEREO, speakers=(1, 2, 1, 2))
        uc.set_pfields(uc.leaves, pan=0.5)
        s.add(uc, name='x', track='array')
        payload = convert_score_to_sc_events(s)
        assert all(e['pfields']['pan'] == 0.5 for e in news(payload))
        assert lanes_of(payload) == [(1, 0), (2, 1), (1, 0), (2, 1)]

    def test_pan_is_refused_on_a_one_channel_def(self):
        """A point source has no stereo image to pan."""
        s = Score().track('array', speakers=quad())
        uc = unit(inst=MONO)
        uc.set_pfields(uc.leaves, pan=0.5)
        s.add(uc, name='x', track='array')
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        msg = str(e.value)
        assert 'writes 1 channel' in msg
        assert 'point source' in msg
        assert '2-channel SynthDef' in msg

    def test_pan_on_a_point_source_off_a_spatial_track_is_untouched(self):
        """The refusal is about the pair of speakers that is not there,
        so it fires only where an array was declared."""
        s = Score().track('dry')
        uc = unit(inst=MONO, speakers=None)
        uc.set_pfields(uc.leaves, pan=0.5)
        s.add(uc, name='x', track='dry')
        assert len(news(convert_score_to_sc_events(s))) == 4


# ---------------------------------------------------------------------------
# 5. A tie or slur cannot walk the array
# ---------------------------------------------------------------------------


class TestHeldNotesDoNotTravel:
    def _tied(self, speakers):
        """Two quarters, the second tied back to the first.

        ``uc._rt.set_node_data(leaf, tied=True)`` is the only way to author
        a tie in this codebase -- there is no ``.tie()`` verb yet.
        """
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120, inst=MONO)
        leaves = [l.id for l in uc.leaves]
        uc.set(leaves[0], speaker=speakers[0])
        uc.set(leaves[1], speaker=speakers[1])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.set_node_data(leaves[1], tied=True)
        return uc

    def test_a_tie_across_one_speaker_joins(self):
        s = Score().track('array', speakers=quad())
        s.add(self._tied((2, 2)), name='x', track='array')
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            payload = convert_score_to_sc_events(s)
        assert len(news(payload)) == 1

    def test_a_tie_across_two_speakers_does_not_join(self):
        """A tie lowers to ONE synth. Joining these would play the whole
        tie out of the head's loudspeaker and never mention the move."""
        s = Score().track('array', speakers=quad())
        s.add(self._tied((2, 3)), name='x', track='array')
        with pytest.warns(UserWarning, match='speaker mismatch'):
            payload = convert_score_to_sc_events(s)
        assert lanes_of(payload) == [(2, 1), (3, 2)]

    def test_a_slur_splits_at_a_speaker_change(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120,
                inst=MONO)
        uc.set(uc.leaves, speaker=1)
        uc.apply_slur([l.id for l in uc.leaves])
        uc.set(uc.leaves[2].id, speaker=3)
        s = Score().track('array', speakers=quad())
        s.add(uc, name='x', track='array')
        payload = convert_score_to_sc_events(s)
        # Two arcs, so two attacks -- and the second is on its own lane.
        spawned = news(payload)
        assert {e['speakerLane'] for e in spawned} == {0, 2}

    def test_the_assembly_layer_carries_the_head_speaker_by_itself(self):
        """Pinned one layer below the converter, on purpose.

        ``lower_compositional_ir_to_sc_assembly`` stamps the head's speaker
        onto a slur's continuation ``set`` events, exactly as it already
        does for ``group`` and for the same reason: a continuation cannot
        move the synth, so it must report where the synth is. Today the
        converter's own pass would re-derive that from the head map, so
        this claim is invisible from the payload -- deleting the assembly
        carry left every other test in this file green. It is pinned here
        because the assembly format has consumers that do not run the
        converter's pass (animation, ``Score.write``, a native SC
        scheduler), and for those the assembly layer is the only place the
        lane is said at all.
        """
        from klotho.utils.playback._sc_assembly import (
            lower_compositional_ir_to_sc_assembly,
        )
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120,
                inst=MONO)
        uc.set(uc.leaves, speaker=3)
        uc.apply_slur([l.id for l in uc.leaves])
        events = lower_compositional_ir_to_sc_assembly(uc)
        sets = [e for e in events if e['type'] == 'set']
        assert sets
        assert all(e.get('speaker') == 3 for e in sets), sets
        spawned = [e for e in events if e['type'] == 'new']
        assert spawned and all(e.get('speaker') == 3 for e in spawned)

    def test_a_slur_continuation_carries_its_head_lane(self):
        """A ``set`` targets a node that already exists; it cannot move
        the synth, so it must report the head's lane rather than none."""
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120,
                inst=MONO)
        uc.set(uc.leaves, speaker=3)
        uc.apply_slur([l.id for l in uc.leaves])
        s = Score().track('array', speakers=quad())
        s.add(uc, name='x', track='array')
        payload = convert_score_to_sc_events(s)
        sets = [e for e in payload['events'] if e['type'] == 'set']
        assert sets
        assert all(e['speakerLane'] == 2 and e['speaker'] == 3 for e in sets)


# ---------------------------------------------------------------------------
# 6. meta.spatial -- the payload contract the JS consumes
# ---------------------------------------------------------------------------


class TestSpatialMeta:
    def test_absent_when_no_track_declares_speakers(self):
        """Omitted when unused, exactly as ``groups`` and ``inserts`` are.
        An always-present ``"spatial": {}`` would move every payload in
        the world -- including the lowering golden -- for no one."""
        s = Score().track('wet', inserts=[SynthDefFX('kl_reverb')])
        s.add(UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120,
                 inst=STEREO), name='x', track='wet')
        assert 'spatial' not in convert_score_to_sc_events(s)['meta']

    def test_present_when_a_track_declares_speakers(self):
        s = Score().track('array', speakers=quad())
        s.add(unit(), name='x', track='array')
        meta = convert_score_to_sc_events(s)['meta']['spatial']
        assert set(meta) == {'arrays', 'tracks'}
        assert meta['tracks'] == {'array': {'array': 'QUAD', 'width': 4}}

    def test_the_array_entry_carries_labels_and_geometry(self):
        s = Score().track('array', speakers=quad())
        s.add(unit(), name='x', track='array')
        entry = convert_score_to_sc_events(s)['meta']['spatial']['arrays']['QUAD']
        assert entry['name'] == 'QUAD'
        assert entry['labels'] == [1, 2, 3, 4]
        assert entry['width'] == 4
        assert entry['positions'] == [[0.0, 0.0], [0.0, 60.0],
                                      [50.0, 0.0], [50.0, 60.0]]
        assert entry['units'] == 'ft'
        assert entry['speedOfSound'] == 1125.0

    def test_the_decoder_block_is_six_floats_per_speaker(self):
        s = Score().track('array', speakers=pavilion())
        s.add(unit(speakers=(1, 2, 3, 4)), name='x', track='array')
        dec = convert_score_to_sc_events(s)['meta']['spatial']['arrays'][
            'PAVILION']['decoder']
        assert dec['kind'] == 'binaural'
        assert dec['stride'] == 6
        assert dec['fields'] == ['delay_l', 'delay_r', 'gain_l', 'gain_r',
                                 'shadow_l_hz', 'shadow_r_hz']
        assert len(dec['coefficients']) == 6 * 24
        assert dec['listener'] == [125.0, 90.0]     # the array's centroid

    def test_the_coefficients_are_the_arrays_own(self):
        """One artifact, shared by the live decoder and the offline fold,
        so the two cannot drift."""
        array = pavilion()
        s = Score().track('array', speakers=array)
        s.add(unit(), name='x', track='array')
        dec = convert_score_to_sc_events(s)['meta']['spatial']['arrays'][
            'PAVILION']['decoder']
        assert tuple(dec['coefficients']) == \
            array.binaural_coefficients().flat()

    def test_a_labels_only_array_carries_no_geometry(self):
        """Honest about having none. A made-up position would produce a
        confident, wrong audition."""
        s = Score().track('array', speakers=range(1, 5))
        s.add(unit(), name='x', track='array')
        entry = convert_score_to_sc_events(s)['meta']['spatial']['arrays'][
            'array']
        assert entry['labels'] == [1, 2, 3, 4]
        assert entry['positions'] is None
        assert entry['decoder'] is None
        assert entry['name'] is None

    def test_two_tracks_sharing_an_array_share_one_entry(self):
        array = quad()
        s = Score()
        s.track('a', speakers=array)
        s.track('b', speakers=array)
        s.add(unit(), name='x', track='a')
        s.add(unit(), name='y', track='b')
        meta = convert_score_to_sc_events(s)['meta']['spatial']
        assert len(meta['arrays']) == 1
        assert meta['tracks']['a']['array'] == meta['tracks']['b']['array']

    def test_two_distinct_arrays_of_the_same_name_do_not_collide(self):
        s = Score()
        s.track('a', speakers=quad('RIG'))
        s.track('b', speakers=SpeakerArray.grid(
            cols=3, rows=1, col_spacing=10.0, row_spacing=10.0, name='RIG'))
        s.add(unit(), name='x', track='a')
        s.add(unit(speakers=(1, 2, 3, 1)), name='y', track='b')
        meta = convert_score_to_sc_events(s)['meta']['spatial']
        assert sorted(meta['arrays']) == ['RIG', 'RIG_2']
        assert meta['tracks']['a']['array'] != meta['tracks']['b']['array']

    def test_the_payload_is_json_serializable(self):
        """It travels to the browser as JSON."""
        s = Score().track('array', speakers=pavilion())
        s.add(unit(), name='x', track='array')
        meta = convert_score_to_sc_events(s)['meta']
        assert json.loads(json.dumps(meta))['spatial']['tracks']['array'][
            'width'] == 24

    def test_the_animated_payload_routes_identically(self):
        """``plot(score).play()`` must sound like ``play(score)``.

        It is a second lowering entry point with its own event walk, so
        without the same routing pass it would carry a speaker LABEL and
        no lane, and every voice would land on lane 0 of its track.
        """
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events,
        )
        def build():
            s = Score().track('array', speakers=quad())
            s.add(unit(), name='x', track='array')
            return s
        plain = lanes_of(convert_score_to_sc_events(build()))
        animated = lanes_of(convert_score_to_sc_animation_events(build()))
        assert animated == plain == [(1, 0), (2, 1), (3, 2), (4, 3)]

    def test_the_animated_payload_refuses_what_the_plain_one_refuses(self):
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events,
        )
        s = Score().track('array', speakers=quad())
        s.add(unit(speakers=(1, 2, 3, 99)), name='x', track='array')
        with pytest.raises(ValueError, match='no speaker labelled 99'):
            convert_score_to_sc_animation_events(s)

    def test_score_write_carries_the_lanes(self, tmp_path):
        s = Score().track('array', speakers=quad())
        s.add(unit(), name='x', track='array')
        out = tmp_path / 'score.json'
        s.write(str(out))
        data = json.loads(out.read_text())
        spawned = [e for e in data['events'] if e['type'] == 'new']
        assert [e['speakerLane'] for e in spawned] == [0, 1, 2, 3]
        assert data['meta']['spatial']['tracks']['array']['width'] == 4

    def test_groups_and_inserts_are_unchanged_beside_it(self):
        s = Score().track('array', speakers=quad(),
                          inserts=[SynthDefFX(FX4)])
        s.add(unit(), name='x', track='array')
        meta = convert_score_to_sc_events(s)['meta']
        assert meta['groups'] == ['array']
        assert list(meta['inserts']) == ['array']


# ---------------------------------------------------------------------------
# 7. The bare (track-less) path
# ---------------------------------------------------------------------------


class TestBarePath:
    def test_a_speaker_without_a_score_is_refused(self):
        with pytest.raises(ValueError) as e:
            convert_to_sc_events(unit())
        msg = str(e.value)
        assert 'needs a Score' in msg
        assert "score.track('array', speakers=" in msg

    def test_a_bare_unit_with_no_speaker_still_plays(self):
        assert len(convert_to_sc_events(unit(speakers=None))) == 4


# ---------------------------------------------------------------------------
# 8. Standalone events
# ---------------------------------------------------------------------------


class TestStandaloneEvents:
    def test_score_new_routes_speaker_to_an_mfield(self):
        s = Score().track('array', speakers=quad())
        s.new(0.0, 0.5, MONO, track='array', freq=880.0, speaker=3)
        payload = convert_score_to_sc_events(s)
        assert lanes_of(payload) == [(3, 2)]
        assert 'speaker' not in news(payload)[0]['pfields']

    def test_an_unknown_label_on_a_standalone_event_is_refused(self):
        s = Score().track('array', speakers=quad())
        s.new(0.0, 0.5, MONO, track='array', speaker=9)
        with pytest.raises(ValueError, match='no speaker labelled 9'):
            convert_score_to_sc_events(s)

    def test_a_loose_event_with_no_speaker_on_a_spatial_track_is_refused(self):
        s = Score().track('array', speakers=quad())
        s.new(0.0, 0.5, MONO, track='array', freq=880.0)
        with pytest.raises(ValueError, match='names no speaker'):
            convert_score_to_sc_events(s)


# ---------------------------------------------------------------------------
# 9. register_synthdef derives widths for runtime defs
# ---------------------------------------------------------------------------


class TestRuntimeWidths:
    def test_a_registered_file_records_its_widths(self):
        from klotho.thetos.instruments._shared import ss_synth_channels
        assert ss_synth_channels(MONO) == (0, 1)
        assert ss_synth_channels(FX4) == (4, 4)
        assert ss_synth_channels(FX24) == (24, 24)

    def test_clearing_the_registry_drops_them(self):
        from klotho.thetos.instruments._shared import ss_synth_channels
        registry.clear_runtime()
        assert ss_synth_channels(MONO) == (None, None)

    def test_bundled_widths_are_unaffected(self):
        from klotho.thetos.instruments._shared import ss_synth_channels
        assert ss_synth_channels('kl_saw') == (0, 2)
        assert ss_synth_channels('kl_reverb') == (2, 2)

    def test_register_synthdef_derives_widths_from_supriya(self):
        """The door a composer authoring their own insert actually uses.
        Without this, every Supriya-authored insert fails the width check
        for lack of data."""
        pytest.importorskip('supriya')
        from supriya import SynthDefBuilder
        from supriya.ugens import In, ReplaceOut

        from klotho.thetos.instruments._shared import ss_synth_channels

        with SynthDefBuilder(inBus=0.0, outBus=0.0) as b:
            ReplaceOut.ar(bus=b['outBus'],
                          source=In.ar(bus=b['inBus'], channel_count=4))
        registry.register_synthdef(b.build(name='rt_probe_fx4'), kind='fx')
        assert ss_synth_channels('rt_probe_fx4') == (4, 4)
        # ...and it is immediately usable as an insert of that width.
        s = Score().track('array', speakers=quad(),
                          inserts=[SynthDefFX('rt_probe_fx4')])
        assert s.tracks['array']['inserts'][0].defName == 'rt_probe_fx4'


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
