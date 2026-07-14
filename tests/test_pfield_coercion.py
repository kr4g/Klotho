"""Tests for pfield value coercion (set-time and lowering) and FYI warnings."""

from fractions import Fraction

import numpy as np
import pytest

from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.tonos import Pitch, Scale
from klotho.tonos.chords.chord import Chord
from klotho.topos.collections.sequences import Pattern
from klotho.utils.playback._converter_base import (
    coerce_sc_pfield_value,
    coerce_sc_pfield_values,
)
from klotho.utils.playback.supersonic.converters import (
    compositional_unit_to_sc_events,
)


def _uc(prolatio=(1, 1, 1, 1)):
    return CompositionalUnit(
        tempus='4/4', prolatio=prolatio, bpm=60,
        inst=SynthDefInstrument.from_manifest('kl_tri'),
    )


def _new_events(uc):
    return [e for e in compositional_unit_to_sc_events(uc) if e['type'] == 'new']


class TestSetTimeCoercion:
    def test_freq_string_stored_as_pitch(self):
        uc = _uc()
        uc.leaves.set_pfields(freq='F#3')
        stored = uc.get_pfield(uc._rt.leaf_nodes[0], 'freq')
        assert isinstance(stored, Pitch)
        assert stored.freq == pytest.approx(184.997, rel=1e-3)

    def test_freq_bad_string_fails_early(self):
        uc = _uc()
        with pytest.raises(ValueError, match="Invalid pitch class"):
            uc.leaves.set_pfields(freq='notapitch')

    def test_freq_pitch_stored_as_is(self):
        uc = _uc()
        p = Pitch('A4')
        uc.leaves.set_pfields(freq=p)
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'freq') is p

    def test_freq_chord_becomes_tuple_of_pitches(self):
        uc = _uc()
        uc.leaves.set_pfields(freq=Chord(['1/1', '5/4', '3/2']).root('A4'))
        stored = uc.get_pfield(uc._rt.leaf_nodes[0], 'freq')
        assert isinstance(stored, tuple)
        assert len(stored) == 3
        assert all(isinstance(p, Pitch) for p in stored)
        assert stored[0].freq == pytest.approx(440.0)

    def test_freq_pitch_collection_rejected_with_hint(self):
        from klotho.tonos import PitchCollection
        pc = PitchCollection.from_degrees(['1/1', '9/8', '5/4'])
        uc = _uc()
        with pytest.raises(TypeError, match="ambiguous"):
            uc.leaves.set_pfields(freq=pc)

    def test_freq_tuple_of_strings_coerced_elementwise(self):
        uc = _uc()
        uc.leaves.set_pfields(freq=('C4', 'E4', 'G4'))
        stored = uc.get_pfield(uc._rt.leaf_nodes[0], 'freq')
        assert all(isinstance(p, Pitch) for p in stored)

    def test_numpy_scalar_normalized(self):
        uc = _uc()
        uc.leaves.set_pfields(freq=np.int64(440), amp=np.float32(0.5))
        n = uc._rt.leaf_nodes[0]
        assert type(uc.get_pfield(n, 'freq')) is int
        assert type(uc.get_pfield(n, 'amp')) is float

    def test_numpy_array_rejected(self):
        uc = _uc()
        with pytest.raises(TypeError, match="numpy array"):
            uc.leaves.set_pfields(freq=np.array([440.0, 550.0]))

    def test_pattern_resolved_strings_coerced(self):
        uc = _uc()
        uc.leaves.set_pfields(freq=Pattern(['C4', 'E4', 'G4', 'C5']))
        vals = [uc.get_pfield(n, 'freq') for n in uc._rt.leaf_nodes]
        assert all(isinstance(v, Pitch) for v in vals)

    def test_callable_resolved_string_coerced(self):
        uc = _uc()
        uc.leaves.set_pfields(freq=lambda: 'D4')
        assert isinstance(uc.get_pfield(uc._rt.leaf_nodes[0], 'freq'), Pitch)

    def test_list_passes_through_at_set_time(self):
        uc = _uc()
        uc.leaves.set_pfields(freq=[440.0, 550.0])
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'freq') == [440.0, 550.0]

    def test_non_freq_string_untouched(self):
        uc = _uc()
        uc.leaves.set_pfields(voice='snare')
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'voice') == 'snare'


class TestLoweringCoercion:
    def test_coerce_helper_matrix(self):
        assert coerce_sc_pfield_value(440) == 440
        assert coerce_sc_pfield_value(0.5) == 0.5
        assert coerce_sc_pfield_value(True) is True
        assert coerce_sc_pfield_value(Pitch('A4')) == pytest.approx(440.0)
        assert coerce_sc_pfield_value(Fraction(1, 2)) == 0.5
        assert type(coerce_sc_pfield_value(np.int64(3))) is float
        got = coerce_sc_pfield_value((Pitch('A4'), Fraction(3, 2)))
        assert got == pytest.approx((440.0, 1.5))

    def test_coerce_values_dict(self):
        out = coerce_sc_pfield_values({'freq': Pitch('A4'), 'amp': Fraction(1, 4)})
        assert out['freq'] == pytest.approx(440.0)
        assert out['amp'] == 0.25

    def test_pitch_freq_lowers_to_float(self):
        uc = _uc()
        uc.leaves.set_pfields(freq='A4')
        events = _new_events(uc)
        assert all(e['pfields']['freq'] == pytest.approx(440.0) for e in events)
        assert all(e['pfields']['note'] == pytest.approx(69.0) for e in events)

    def test_fraction_freq_lowers_to_float(self):
        uc = _uc()
        uc.leaves.set_pfields(freq=440 * Fraction(1, 2))
        events = _new_events(uc)
        assert all(e['pfields']['freq'] == pytest.approx(220.0) for e in events)

    def test_chord_lowers_to_poly_voices(self):
        uc = _uc(prolatio=(1,))
        uc.leaves.set_pfields(freq=Chord(['1/1', '5/4', '3/2']).root('A4'))
        events = _new_events(uc)
        assert len(events) == 3
        freqs = sorted(e['pfields']['freq'] for e in events)
        assert freqs == pytest.approx([440.0, 550.0, 660.0])

    def test_list_fails_validation_with_hint(self):
        from klotho.utils.playback._sc_validate import AssemblyValidationError
        uc = _uc()
        uc.leaves.set_pfields(freq=[440.0, 550.0])
        with pytest.raises(AssemblyValidationError, match="tuple for a chord"):
            compositional_unit_to_sc_events(uc)


class TestUnknownPfieldFYI:
    def _reset_warned(self):
        from klotho.utils.playback import _sc_assembly
        _sc_assembly._WARNED_UNKNOWN_PFIELDS.clear()
        _sc_assembly._WARNED_UNKNOWN_DEFNAMES.clear()

    def test_unknown_pfield_warns_once(self, capsys):
        self._reset_warned()
        uc = _uc()
        uc.leaves.set_pfields(freq=440.0, atackTime=0.01)
        compositional_unit_to_sc_events(uc)
        compositional_unit_to_sc_events(uc)
        out = capsys.readouterr().out
        assert out.count("no control 'atackTime'") == 1
        assert "kl_tri" in out

    def test_known_and_exempt_keys_silent(self, capsys):
        self._reset_warned()
        uc = _uc()
        uc.leaves.set_pfields(freq=440.0, amp=0.3)
        compositional_unit_to_sc_events(uc)
        assert "Klotho FYI" not in capsys.readouterr().out

    def test_unknown_defname_warns_once(self, capsys):
        self._reset_warned()
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=60)
        uc.set_instrument(uc._rt.root, 'no_such_def')
        uc.leaves.set_pfields(freq=440.0)
        compositional_unit_to_sc_events(uc)
        compositional_unit_to_sc_events(uc)
        out = capsys.readouterr().out
        assert out.count("not in the manifest") == 1

    def test_engine_still_produces_events(self, capsys):
        self._reset_warned()
        uc = _uc()
        uc.leaves.set_pfields(freq=440.0, bogusParam=1.0)
        events = _new_events(uc)
        assert len(events) == 4
        assert all(e['pfields']['bogusParam'] == 1.0 for e in events)


class TestEndToEndScalePattern:
    def test_scale_pattern_workflow_still_works(self):
        scale = Scale.ionian().root('C4')
        uc = _uc()
        uc.leaves.set_pfields(
            freq=Pattern([scale[i].freq for i in [0, 2, 4, 7]]), amp=0.4
        )
        events = _new_events(uc)
        assert len(events) == 4
        assert events[0]['pfields']['freq'] == pytest.approx(scale[0].freq)
