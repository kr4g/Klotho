"""``play(container, amp=...)`` must not throw the amplitude away.

``amp`` is reserved in ``_converter_base.KNOWN_KWARGS``, so
``extract_convert_kwargs`` CONSUMES it -- it never survives into
``extra_pfields`` either.  For a bare :class:`TemporalUnit` the dispatch
adapter forwarded it and everything worked; for a
:class:`TemporalUnitSequence` / :class:`TemporalBlock` the adapter dropped
it on the floor and the events were built at the hardcoded 0.85 default.

Measured before the fix (2026-09-01)::

    play(ut,  amp=0.2) -> [0.2]     # single unit already worked
    play(uts, amp=0.2) -> [0.85]    # value evaporated
    play(bt,  amp=0.2) -> [0.85]    # value evaporated
    plot(uts, amp=0.2) -> [0.2]     # the animation path already honoured it

0.85 against a requested 0.2 is 12.6 dB between two spellings of the same
request, with no exception and no warning to notice it by.

Scope note: ``amp`` reaches bare ``TemporalUnit`` members only.  A
:class:`CompositionalUnit` carries its own parameter layer and sources
``amp`` from there, so it ignores the kwarg on BOTH paths -- this file
pins that asymmetry so the two paths cannot drift apart again.
"""

import math

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.utils.playback.supersonic.converters import (
    convert_to_sc_events,
    convert_to_sc_payload,
    temporal_container_to_sc_animation_events,
)


def _ut(prolatio=(1, 1, 1, 1)):
    return TemporalUnit(span=1, tempus='4/4', prolatio=prolatio,
                        beat='1/4', bpm=120)


def _amps(events):
    return sorted({
        ev['pfields'].get('amp')
        for ev in events
        if ev.get('type') == 'new' and ev.get('defName') != '__rest__'
    })


@pytest.fixture
def seq():
    return TemporalUnitSequence([_ut(), _ut((1, 1))])


@pytest.fixture
def block():
    return TemporalBlock([_ut(), _ut((1, 1))])


class TestAmpReachesContainers:
    """The three bare-playback surfaces must agree on ``amp``."""

    def test_single_unit_reference_implementation(self):
        assert _amps(convert_to_sc_events(_ut(), amp=0.2)) == [0.2]

    def test_sequence_events(self, seq):
        assert _amps(convert_to_sc_events(seq, amp=0.2)) == [0.2]

    def test_block_events(self, block):
        assert _amps(convert_to_sc_events(block, amp=0.2)) == [0.2]

    def test_sequence_payload(self, seq):
        assert _amps(convert_to_sc_payload(seq, amp=0.2)['events']) == [0.2]

    def test_block_payload(self, block):
        assert _amps(convert_to_sc_payload(block, amp=0.2)['events']) == [0.2]

    def test_nested_container(self):
        nested = TemporalUnitSequence([
            _ut(),
            TemporalUnitSequence([_ut((1, 1))]),
            TemporalBlock([_ut((1, 1, 1))]),
        ])
        assert _amps(convert_to_sc_events(nested, amp=0.2)) == [0.2]
        assert _amps(convert_to_sc_payload(nested, amp=0.2)['events']) == [0.2]


class TestPathsAgree:
    """``play`` and ``plot(...).play()`` must lower the same amplitude."""

    def test_play_matches_plot_sequence(self, seq):
        play_amps = _amps(convert_to_sc_events(seq, amp=0.2))
        plot_amps = _amps(
            temporal_container_to_sc_animation_events(seq, amp=0.2)['events'])
        assert play_amps == plot_amps == [0.2]

    def test_play_matches_plot_block(self, block):
        play_amps = _amps(convert_to_sc_events(block, amp=0.2))
        plot_amps = _amps(
            temporal_container_to_sc_animation_events(block, amp=0.2)['events'])
        assert play_amps == plot_amps == [0.2]

    def test_payload_matches_events(self, seq):
        assert (_amps(convert_to_sc_payload(seq, amp=0.2)['events'])
                == _amps(convert_to_sc_events(seq, amp=0.2)))


class TestDefaultUnchanged:
    """Omitting ``amp`` must keep the historical 0.85 default."""

    def test_sequence_default(self, seq):
        assert _amps(convert_to_sc_events(seq)) == [0.85]

    def test_block_default(self, block):
        assert _amps(convert_to_sc_payload(block)['events']) == [0.85]

    def test_amp_zero_is_honoured_not_treated_as_missing(self, seq):
        """``amp=0`` is a real request for silence, not a missing value."""
        assert _amps(convert_to_sc_events(seq, amp=0.0)) == [0.0]


class TestCompositionalUnitStillSourcesItsOwnAmp:
    """A UC member owns its amplitude; the kwarg must not override it."""

    def test_uc_member_ignores_amp_on_both_paths(self):
        from klotho.thetos.composition.compositional import CompositionalUnit
        uc = CompositionalUnit.from_ut(_ut((1, 1)), pfields={'amp': 0.44})
        container = TemporalUnitSequence([uc])
        for events in (convert_to_sc_events(container, amp=0.2),
                       convert_to_sc_payload(container, amp=0.2)['events'],
                       temporal_container_to_sc_animation_events(
                           container, amp=0.2)['events']):
            amps = _amps(events)
            assert all(not math.isclose(a, 0.2) for a in amps), amps
