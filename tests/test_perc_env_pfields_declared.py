"""A bare rhythm play must not ship pfields the target SynthDef ignores.

``temporal_unit_to_sc_events`` built every percussion note with
``**perc_env_pfields(dur)`` -- ``attack``, ``decay``, ``sustain``,
``release`` -- and sent them to ``DEFAULT_RHYTHM_SYNTH``, which is
``kl_kicktone``.  ``kl_kicktone`` declares none of the four.  Measured
before the fix (2026-09-01), one note of ``play(TemporalUnit(...))``::

    shipped pfields : ['amp', 'attack', 'baseFreq', 'decay', 'dur',
                       'release', 'sustain']
    UNDECLARED      : ['attack', 'decay', 'release', 'sustain']
    values          : {"attack": 0.005, "decay": 0,
                       "release": 0.6666666666666667,
                       "sustain": 0.3283333333333333}

scsynth ignores an unknown control silently, so nothing broke and nothing
said anything -- but ``PERC_ATTACK``, ``PERC_BODY_RATIO`` and
``perc_env_pfields`` were in effect dead code, and a reader of
``temporal_unit_to_sc_events`` would reasonably conclude the percussion
envelope is shaped by the note's length.  It is not.

The fix filters the envelope block against what the synth DECLARES rather
than deleting the call.  That distinction is the point: a rhythm synth
that does declare these controls must still receive them, so the test
below drives the same code path against a def that declares ``release``
and shows exactly that one survives.
"""

import pytest

from klotho.chronos import TemporalUnit
from klotho.chronos.rhythm_trees import RhythmTree
from klotho.thetos.instruments._shared import load_ss_manifest
from klotho.utils.playback import _converter_base
from klotho.utils.playback._converter_base import perc_env_pfields
from klotho.utils.playback.supersonic import converters
from klotho.utils.playback.supersonic.converters import (
    DEFAULT_RHYTHM_SYNTH,
    convert_to_sc_events,
    rhythm_tree_to_sc_animation_events,
    temporal_unit_to_sc_animation_events,
)

PERC_ENV_KEYS = {'attack', 'decay', 'sustain', 'release'}

# Declares ``release`` and none of the other three -- so it separates
# "filtered against the declaration" from "the four names were deleted".
PARTIAL_DECLARER = 'chip_riser'


def _ut():
    return TemporalUnit(span=1, tempus='4/4', prolatio=(1, 1), beat='1/4',
                        bpm=120)


def _notes(events):
    events = events['events'] if isinstance(events, dict) else events
    return [e for e in events
            if e.get('type') == 'new' and e.get('defName') != '__rest__']


class TestTheDefaultRhythmSynthDeclaresWhatItGets:
    def test_kl_kicktone_still_declares_none_of_the_four(self):
        """Pin the premise. If a rebuild ever adds these controls to
        ``kl_kicktone``, this is the test that says so, and the filter
        will start shipping them again on its own."""
        declared = set(load_ss_manifest()[DEFAULT_RHYTHM_SYNTH])
        assert declared & PERC_ENV_KEYS == set()

    def test_no_undeclared_pfield_is_shipped(self):
        declared = set(load_ss_manifest()[DEFAULT_RHYTHM_SYNTH])
        for note in _notes(convert_to_sc_events(_ut())):
            assert set(note['pfields']) <= declared, sorted(
                set(note['pfields']) - declared)

    def test_the_pfields_that_do_land_are_unchanged(self):
        note = _notes(convert_to_sc_events(_ut()))[0]
        assert note['pfields'] == {'amp': 0.85, 'baseFreq': 110.0, 'dur': 1.0}

    @pytest.mark.parametrize('build', [
        pytest.param(lambda: convert_to_sc_events(_ut()), id='play(ut)'),
        pytest.param(lambda: convert_to_sc_events(RhythmTree(meas='4/4',
                                                             subdivisions=(1, 1))),
                     id='play(rt)'),
        pytest.param(lambda: temporal_unit_to_sc_animation_events(_ut()),
                     id='plot(ut).play()'),
        pytest.param(lambda: rhythm_tree_to_sc_animation_events(
            RhythmTree(meas='4/4', subdivisions=(1, 1))), id='plot(rt).play()'),
    ])
    def test_every_bare_rhythm_surface(self, build):
        declared = set(load_ss_manifest()[DEFAULT_RHYTHM_SYNTH])
        for note in _notes(build()):
            assert set(note['pfields']) & PERC_ENV_KEYS <= declared


class TestItIsAFilterNotADeletion:
    """A rhythm synth that declares these controls must still get them."""

    def test_a_declaring_synth_still_receives_its_control(self, monkeypatch):
        declared = set(load_ss_manifest()[PARTIAL_DECLARER])
        assert 'release' in declared           # premise of this test
        assert not (declared & {'attack', 'decay', 'sustain'})

        monkeypatch.setattr(converters, 'DEFAULT_RHYTHM_SYNTH',
                            PARTIAL_DECLARER)
        note = _notes(convert_to_sc_events(_ut()))[0]
        shipped = set(note['pfields']) & PERC_ENV_KEYS
        assert shipped == {'release'}
        assert note['pfields']['release'] == pytest.approx(1.0 * 2 / 3)

    def test_the_helper_keeps_every_field_when_no_declaration_is_given(self):
        """``controls=None`` means "cannot be checked", which must mean
        ship everything -- withholding a pfield because the manifest has
        not heard of a runtime-registered def would silence it for a
        bookkeeping reason."""
        assert set(perc_env_pfields(1.0)) == PERC_ENV_KEYS
        assert set(perc_env_pfields(1.0, controls=None)) == PERC_ENV_KEYS

    def test_the_helper_filters_against_the_mapping_it_is_given(self):
        got = perc_env_pfields(1.0, controls={'attack': 0.0, 'sustain': 0.0})
        assert set(got) == {'attack', 'sustain'}

    def test_filtering_does_not_change_the_values(self):
        full = perc_env_pfields(0.6)
        filtered = perc_env_pfields(0.6, controls={'sustain': 0.0,
                                                   'release': 0.0})
        assert filtered == {k: full[k] for k in ('sustain', 'release')}

    def test_the_envelope_math_is_untouched(self):
        """Regression fence around ``PERC_ATTACK`` / ``PERC_BODY_RATIO``:
        the filter must not become an excuse to change the shape."""
        assert _converter_base.PERC_ATTACK == 0.005
        assert _converter_base.PERC_BODY_RATIO == pytest.approx(1 / 3)
        assert perc_env_pfields(1.0) == {
            'attack': 0.005,
            'decay': 0,
            'sustain': pytest.approx(1 / 3 - 0.005),
            'release': pytest.approx(2 / 3),
        }
