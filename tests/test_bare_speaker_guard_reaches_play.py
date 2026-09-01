"""The bare-speaker guard must run on the paths ``play``/``plot`` actually take.

``_refuse_bare_speaker`` was called from exactly one place,
:func:`convert_to_sc_events`.  But nothing that reaches
``convert_to_sc_events`` has mfield storage: ``Pitch``, ``Chord``,
``Scale``, ``Spectrum``, ``RhythmTree`` and a bare ``TemporalUnit`` cannot
emit a ``speaker`` key at all.  The one type that can — a
:class:`CompositionalUnit`, alone or inside a UTS/BT — is routed by
``player.play`` to :func:`convert_to_sc_payload`, and by ``plot(...).play()``
to the animation converters, and NONE of those called the guard.

So the guard was dead for exactly the type it was written for.  Measured
before the fix (2026-09-01), a UC carrying ``speaker=Pattern([1,2,3,4])``::

    convert_to_sc_events(uc)                    REFUSED
    convert_to_sc_payload(uc)          [play]   NO REFUSAL -> speaker 1..4, lane None
    compositional_unit_to_sc_animation_events   NO REFUSAL -> speaker 1..4, lane None
    convert_to_sc_payload(UTS[uc])     [play]   NO REFUSAL
    convert_to_sc_payload(BT[uc])      [play]   NO REFUSAL
    temporal_container_to_sc_animation_events   NO REFUSAL

``scheduler_core.js`` reads ``ev.speakerLane || 0`` and ignores ``speaker``
entirely, so every one of those voices collapsed onto lane 0 — the
composer's whole spatial intent dropped without a word, which is precisely
what the guard's own docstring says it exists to prevent.

The other half of this file is the constraint: through a ``Score`` the
spatial path resolves labels to lanes and refuses only the genuinely
unresolvable, and it must keep doing exactly that.
"""

from pathlib import Path

import pytest

from klotho.chronos import TemporalUnitSequence, TemporalBlock
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos import SpeakerArray
from klotho.thetos.composition.score import Score
from klotho.topos.collections.sequences import Pattern
from klotho.utils.playback.supersonic import registry
from klotho.utils.playback.supersonic.converters import (
    compositional_unit_to_sc_animation_events,
    convert_score_to_sc_animation_events,
    convert_score_to_sc_events,
    convert_to_sc_events,
    convert_to_sc_payload,
    temporal_container_to_sc_animation_events,
)

_PROBE_DIR = Path(__file__).parent / 'fixtures' / 'synthdefs'
MONO = 'spatial_probe_mono'      # outs == 1 -- a point source


@pytest.fixture(autouse=True)
def _probe_defs():
    """Register the 1-channel probe for one test, then clear it.

    Registration is process-global; a leaked ``spatial_probe_*`` would make
    an unrelated test's width check pass for the wrong reason.
    """
    registry.register_compiled_file(_PROBE_DIR / f'{MONO}.scsyndef',
                                    kind='inst')
    try:
        yield
    finally:
        registry.clear_runtime()


def quad():
    """A 2x2 grid, labels 1..4."""
    return SpeakerArray.grid(cols=2, rows=2, col_spacing=50.0,
                             row_spacing=60.0, name='QUAD')


def unit(speakers=(1, 2, 3, 4)):
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120,
            inst=MONO)
    if speakers is not None:
        uc.set(uc.leaves, speaker=Pattern(list(speakers)))
    return uc


def _news(payload):
    events = payload['events'] if isinstance(payload, dict) else payload
    return [e for e in events if e.get('type') == 'new']


def _lanes(payload):
    return [(e.get('speaker'), e.get('speakerLane')) for e in _news(payload)]


# The bare surfaces that can carry a speaker, named by the user-facing call
# each one is reached from. Every entry lowers ONE freshly built object.
BARE_SURFACES = {
    'play(uc) -> convert_to_sc_payload':
        lambda obj: convert_to_sc_payload(obj),
    'plot(uc).play() -> animation events':
        lambda obj: (compositional_unit_to_sc_animation_events(obj)
                     if isinstance(obj, UC)
                     else temporal_container_to_sc_animation_events(obj)),
    'convert_to_sc_events (already guarded)':
        lambda obj: convert_to_sc_events(obj),
}


def _containers():
    return {
        'UC': lambda: unit(),
        'UTS': lambda: TemporalUnitSequence([unit()]),
        'BT': lambda: TemporalBlock([unit()]),
        'nested UTS[BT[UC]]':
            lambda: TemporalUnitSequence([TemporalBlock([unit()])]),
    }


class TestEveryBarePathRefuses:
    """No spelling of a track-less play may swallow a speaker label."""

    @pytest.mark.parametrize('shape', sorted(_containers()))
    @pytest.mark.parametrize('surface', sorted(BARE_SURFACES))
    def test_refused(self, surface, shape):
        obj = _containers()[shape]()
        with pytest.raises(ValueError) as excinfo:
            BARE_SURFACES[surface](obj)
        msg = str(excinfo.value)
        assert 'needs a Score' in msg
        assert "score.track('array', speakers=" in msg

    def test_the_refusal_names_the_offending_label(self):
        with pytest.raises(ValueError, match=r'speaker=1\b'):
            convert_to_sc_payload(unit(speakers=(1, 1, 1, 1)))


class TestNothingElseIsRefused:
    """A UC without a speaker must still play on every bare surface."""

    @pytest.mark.parametrize('shape', sorted(_containers()))
    @pytest.mark.parametrize('surface', sorted(BARE_SURFACES))
    def test_no_speaker_still_plays(self, surface, shape):
        # Rebuild the shape with speaker-less units.
        plain = {
            'UC': lambda: unit(speakers=None),
            'UTS': lambda: TemporalUnitSequence([unit(speakers=None)]),
            'BT': lambda: TemporalBlock([unit(speakers=None)]),
            'nested UTS[BT[UC]]': lambda: TemporalUnitSequence(
                [TemporalBlock([unit(speakers=None)])]),
        }[shape]()
        assert len(_news(BARE_SURFACES[surface](plain))) == 4


class TestTheScorePathIsUntouched:
    """The path that works today must keep working, byte for byte.

    This is the constraint the fix could most plausibly have broken: the
    guard refuses a speaker with no array, and a Score-routed voice has an
    array, so the refusal must not reach it.
    """

    def _score(self):
        s = Score().track('array', speakers=quad())
        s.add(unit(), name='x', track='array')
        return s

    def test_labels_still_resolve_to_lanes(self):
        assert _lanes(convert_score_to_sc_events(self._score())) == [
            (1, 0), (2, 1), (3, 2), (4, 3)]

    def test_the_animated_score_payload_routes_identically(self):
        assert (_lanes(convert_score_to_sc_animation_events(self._score()))
                == _lanes(convert_score_to_sc_events(self._score())))

    def test_the_spatial_meta_survives(self):
        meta = convert_score_to_sc_events(self._score())['meta']['spatial']
        assert meta['tracks'] == {'array': {'array': 'QUAD', 'width': 4}}

    def test_a_nested_container_in_a_score_still_routes(self):
        s = Score().track('array', speakers=quad())
        s.add(TemporalUnitSequence([unit()]), name='x', track='array')
        assert _lanes(convert_score_to_sc_events(s)) == [
            (1, 0), (2, 1), (3, 2), (4, 3)]

    def test_the_scores_own_refusals_are_unchanged(self):
        """An unknown label is still refused by the SCORE's message, not
        by the bare guard -- the two say different things and a caller
        needs the right one."""
        s = Score().track('array', speakers=quad())
        s.add(unit(speakers=(1, 2, 3, 99)), name='x', track='array')
        with pytest.raises(ValueError, match='no speaker labelled 99'):
            convert_score_to_sc_events(s)

    def test_a_score_track_with_no_array_still_gives_the_track_message(self):
        s = Score().track('plain')
        s.add(unit(), name='x', track='plain')
        with pytest.raises(ValueError) as excinfo:
            convert_score_to_sc_events(s)
        msg = str(excinfo.value)
        assert 'has no speaker array' in msg
        assert 'needs a Score' not in msg     # not the bare-path message
