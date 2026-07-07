"""Regression: the ``inst`` playback argument.

``play(obj, inst=...)`` and ``plot(obj).play(inst=...)`` accept a
SynthDef name string (exact match only, including runtime-registered
Supriya defs) or a ``SynthDefInstrument``. Time-structured classes
(RT/UT/UTS/BT/UC) silently ignore it, like ``dur``.
"""
import pytest

from klotho.tonos import Pitch, Scale, Chord
from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice
from klotho.chronos.rhythm_trees import RhythmTree
from klotho.chronos.temporal_units import TemporalUnit
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.utils.playback._converter_base import resolve_instrument
from klotho.utils.playback.supersonic.converters import convert_to_sc_events
from klotho.utils.playback.supersonic.registry import (
    register_compiled, clear_runtime,
)


def _new_events(events):
    return [e for e in events if e.get("type") == "new"]


class TestResolveInstrument:
    def test_none(self):
        assert resolve_instrument(None) == (None, {}, True)

    def test_exact_string(self):
        def_name, pfields, has_gate = resolve_instrument("kl_saw")
        assert def_name == "kl_saw"
        assert isinstance(pfields, dict)

    def test_no_prefix_fallback(self):
        clear_runtime()
        with pytest.raises(ValueError, match="exactly"):
            resolve_instrument("saw")

    def test_unknown_name_lists_available(self):
        with pytest.raises(ValueError, match="Available:"):
            resolve_instrument("definitely_not_a_synth")

    def test_instrument_instance(self):
        inst = SynthDefInstrument.from_manifest("kl_saw", attackTime=0.7)
        def_name, pfields, has_gate = resolve_instrument(inst)
        assert def_name == "kl_saw"
        assert pfields.get("attackTime") == 0.7

    def test_object_without_defname_raises(self):
        with pytest.raises(TypeError):
            resolve_instrument(object())

    def test_runtime_registered_exact_name_wins(self):
        try:
            register_compiled("saw", b"\x00fake", {"freq": 440.0, "amp": 0.1, "gate": 1})
            def_name, pfields, has_gate = resolve_instrument("saw")
            assert def_name == "saw"
            assert has_gate
        finally:
            clear_runtime()


class TestConverterInst:
    def test_pitch_string(self):
        events = convert_to_sc_events(Pitch("C4"), inst="kl_saw")
        assert {e["defName"] for e in _new_events(events)} == {"kl_saw"}

    def test_pitch_instance(self):
        inst = SynthDefInstrument.from_manifest("kl_saw")
        events = convert_to_sc_events(Pitch("C4"), inst=inst)
        assert {e["defName"] for e in _new_events(events)} == {"kl_saw"}

    def test_inst_never_a_pfield(self):
        events = convert_to_sc_events(Pitch("C4"), inst="kl_saw")
        assert all("inst" not in e["pfields"] for e in _new_events(events))

    def test_scale_and_chord(self):
        scale = Scale(["1/1", "9/8", "5/4"]).root("C4")
        events = convert_to_sc_events(scale, inst="kl_sine")
        assert {e["defName"] for e in _new_events(events)} == {"kl_sine"}
        chord = Chord(["1/1", "5/4", "3/2"]).root("C4")
        events = convert_to_sc_events(chord, inst="kl_sine")
        assert {e["defName"] for e in _new_events(events)} == {"kl_sine"}

    def test_default_unchanged_without_inst(self):
        events = convert_to_sc_events(Pitch("C4"))
        assert {e["defName"] for e in _new_events(events)} == {"kl_tri"}

    def test_instrument_defaults_below_user_kwargs(self):
        inst = SynthDefInstrument.from_manifest("kl_saw", attackTime=0.9)
        events = convert_to_sc_events(Chord(["1/1", "5/4"]).root("C4"), inst=inst)
        assert events[0]["pfields"]["attackTime"] == 0.9
        events = convert_to_sc_events(Chord(["1/1", "5/4"]).root("C4"),
                                      inst=inst, attackTime=0.1)
        assert events[0]["pfields"]["attackTime"] == 0.1

    def test_event_freq_amp_not_clobbered_by_inst(self):
        inst = SynthDefInstrument.from_manifest("kl_saw", freq=111.0, amp=0.999)
        events = convert_to_sc_events(Pitch("A4"), inst=inst)
        pf = events[0]["pfields"]
        assert abs(pf["freq"] - 440.0) < 1e-6
        assert pf["amp"] != 0.999

    def test_ignored_for_rhythm_tree_and_temporal_unit(self):
        rt = RhythmTree(span=1, meas="4/4", subdivisions=(1, 1, 1, 1))
        events = convert_to_sc_events(rt, inst="kl_saw")
        assert {e["defName"] for e in _new_events(events)} == {"kl_kicktone"}
        assert all("inst" not in e["pfields"] for e in _new_events(events))
        tu = TemporalUnit.from_rt(rt)
        events = convert_to_sc_events(tu, inst="kl_saw")
        assert {e["defName"] for e in _new_events(events)} == {"kl_kicktone"}


class TestRuntimeRegistration:
    def test_runtime_def_resolves_and_ships_assets(self):
        try:
            register_compiled("test_def_xyz", b"\x00fakebytes",
                              {"freq": 440.0, "amp": 0.1, "gate": 1})
            events = convert_to_sc_events(Pitch("C4"), inst="test_def_xyz")
            assert {e["defName"] for e in _new_events(events)} == {"test_def_xyz"}

            from klotho.utils.playback.supersonic import SuperSonicEngine
            engine = SuperSonicEngine(events)
            assert "test_def_xyz" in engine.synthdef_assets
        finally:
            clear_runtime()

    def test_non_gated_runtime_def_gets_dur_pfield(self):
        try:
            register_compiled("test_oneshot", b"\x00fakebytes",
                              {"freq": 440.0, "amp": 0.1, "dur": 1.0})
            events = convert_to_sc_events(Pitch("C4"), inst="test_oneshot", dur=2.5)
            pf = events[0]["pfields"]
            assert pf["dur"] == 2.5
        finally:
            clear_runtime()


class TestPlotPlayback:
    def test_path_payload_uses_inst(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        tl = ToneLattice.from_generators((3, 5), resolution=2, equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True,
                            path=[(0, 0), (1, 0), (1, 1)], inst="kl_saw")
        synths = {e["defName"] for e in fig.audio_payload["events"]
                  if e.get("type") == "new"}
        assert synths == {"kl_saw"}
        html = fig.to_html()
        assert '"defName": "kl_saw"' in html or '"defName":"kl_saw"' in html
        assert "kl_saw" in html

    def test_bare_preview_uses_inst(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        from klotho.semeios.visualization._animation import ClickPreviewFigure
        tl = ToneLattice.from_generators((3, 5), resolution=2, equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True, inst="kl_saw")
        assert isinstance(fig, ClickPreviewFigure)
        assert fig.def_name == "kl_saw"
        html = fig.to_html()
        assert '"defName": "kl_saw"' in html or '"defName":"kl_saw"' in html

    def test_defname_kwarg_still_wins(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        tl = ToneLattice.from_generators((3, 5), resolution=2, equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True,
                            inst="kl_saw", defName="kl_sine")
        assert fig.def_name == "kl_sine"

    def test_playback_kwargs_include_inst(self):
        from klotho.semeios.visualization._dispatch._klotho_plot import _PLAYBACK_KWARGS
        assert "inst" in _PLAYBACK_KWARGS
        assert "defName" in _PLAYBACK_KWARGS
