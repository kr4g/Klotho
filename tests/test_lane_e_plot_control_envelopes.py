"""Tests: ``plot(obj).play()`` renders control envelopes, like ``play(obj)``.

Two audition surfaces owe the same sound.  ``play(uc)`` lowers through
:func:`convert_to_sc_payload`, which harvests control-envelope descriptors;
the animated plot path used to return a bare event list, so the bridge saw
``controlData = null`` and the widget played the *baked onset value* of the
enveloped pfield.  For a ``0 -> 1 -> 0`` swell that onset value is ``0.0``,
so the swell auditioned as silence.

The assertion that matters here is not "the call does not raise" but
"the control data reaching the engine is the same on both surfaces".
"""

import pytest

from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import (
    TemporalBlock, TemporalUnit, TemporalUnitSequence,
)
from klotho.dynatos.envelopes import Envelope
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.utils.playback.supersonic.converters import (
    compositional_unit_to_sc_animation_events,
    convert_to_sc_payload,
    rhythm_tree_to_sc_animation_events,
    temporal_container_to_sc_animation_events,
    temporal_unit_to_sc_animation_events,
)
from klotho.utils.playback.supersonic.engine import serialize_control_data


def _swell_uc(bpm=60):
    """Ryan's single-note swell: one note, amp 0 -> 1 -> 0, ``control=True``."""
    uc = CompositionalUnit(
        tempus='1/4', prolatio=(1,), bpm=bpm,
        inst=SynthDefInstrument.from_manifest('kl_tri'),
    )
    uc.leaves.set_pfields(freq=440.0)
    uc.root.apply_envelope(Envelope([0.0, 1.0, 0.0]), pfields='amp', control=True)
    return uc


def _plain_uc(bpm=60):
    uc = CompositionalUnit(
        tempus='4/4', prolatio=(1, 1), bpm=bpm,
        inst=SynthDefInstrument.from_manifest('kl_tri'),
    )
    uc.leaves.set_pfields(freq=330.0, amp=0.4)
    return uc


def _baked_uc(bpm=60):
    """A ``control=False`` envelope: baked into the pfields, no descriptor."""
    uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=bpm)
    uc.leaves.set_pfields(freq=440.0)
    uc.root.apply_envelope(Envelope([0.1, 0.8]), pfields='amp', control=False)
    return uc


def _bare_control_data(obj):
    """The control data ``play(obj)`` hands the engine, JSON-serialized.

    ``player.play`` builds ``SuperSonicEngine(control_data=...)``, which
    serializes it exactly this way before it reaches the widget.
    """
    return serialize_control_data(convert_to_sc_payload(obj)["control_data"])


def _assert_control_data_equivalent(bare_payload, bare_cd, anim_payload):
    """Pin that both surfaces drive the same curve over the same notes.

    Event ids come from a process-local counter and are regenerated per
    lowering, so they are compared through the events they name rather
    than directly: every descriptor target must resolve to an event whose
    ``start`` matches the target's ``startTime``, in both payloads.
    """
    anim_cd = anim_payload["controlData"]

    assert anim_cd["blockSize"] == bare_cd["blockSize"]
    assert anim_cd["numFrames"] == bare_cd["numFrames"]
    # The sampled curve itself, byte for byte.
    assert anim_cd["bufferB64"] == bare_cd["bufferB64"]

    bare_descs = bare_cd["descriptors"]
    anim_descs = anim_cd["descriptors"]
    assert len(anim_descs) == len(bare_descs)

    bare_starts = {e["id"]: e["start"] for e in bare_payload["events"]}
    anim_starts = {e["id"]: e["start"] for e in anim_payload["events"]}

    for bare_desc, anim_desc in zip(bare_descs, anim_descs):
        assert anim_desc["blockIndex"] == bare_desc["blockIndex"]
        assert anim_desc["pfields"] == bare_desc["pfields"]
        assert anim_desc["start"] == pytest.approx(bare_desc["start"])
        assert anim_desc["dur"] == pytest.approx(bare_desc["dur"])

        bare_tgt = sorted(t["startTime"] for t in bare_desc["targets"])
        anim_tgt = sorted(t["startTime"] for t in anim_desc["targets"])
        assert anim_tgt == pytest.approx(bare_tgt)

        # Each target names a real event, at the time the descriptor claims.
        for tgt in bare_desc["targets"]:
            assert bare_starts[tgt["id"]] == pytest.approx(tgt["startTime"])
        for tgt in anim_desc["targets"]:
            assert anim_starts[tgt["id"]] == pytest.approx(tgt["startTime"])


class TestPayloadShape:
    """Every animation converter answers with the same payload shape."""

    def test_uc_payload_is_dict(self):
        payload = compositional_unit_to_sc_animation_events(_swell_uc())
        assert isinstance(payload, dict)
        assert set(payload) == {"events", "controlData"}
        assert isinstance(payload["events"], list)

    @pytest.mark.parametrize('factory', [
        lambda: TemporalUnitSequence([_swell_uc(), _plain_uc()]),
        lambda: TemporalBlock([_swell_uc(), _plain_uc()], sort_rows=False),
    ])
    def test_container_payload_is_dict(self, factory):
        payload = temporal_container_to_sc_animation_events(factory())
        assert isinstance(payload, dict)
        assert set(payload) == {"events", "controlData"}

    def test_temporal_unit_and_rhythm_tree_answer_alike(self):
        """A UT/RT carries no control envelopes, but answers in the same
        shape -- a caller must not have to switch on the object type."""
        ut = temporal_unit_to_sc_animation_events(
            TemporalUnit(tempus='4/4', prolatio=(1, 1, -1, 2), bpm=72))
        rt = rhythm_tree_to_sc_animation_events(
            RhythmTree(meas='4/4', subdivisions=(1, 1)), beat='1/4', bpm=60)
        for payload in (ut, rt):
            assert set(payload) == {"events", "controlData"}
            assert payload["controlData"]["descriptors"] == []
            assert payload["controlData"]["bufferB64"] is None


class TestSwellIsNotSilent:
    """The defect itself: the swell must not audition as silence."""

    def test_plot_path_carries_the_swell(self):
        uc = _swell_uc()
        payload = compositional_unit_to_sc_animation_events(uc)

        # The baked onset value IS 0.0 -- that is correct and by design;
        # it is what the widget played when the curve went missing.
        amps = [e.get("pfields", {}).get("amp")
                for e in payload["events"] if e.get("type") == "new"]
        assert amps == [0.0]

        # ...so the curve has to arrive, or the note is silent.
        cd = payload["controlData"]
        assert len(cd["descriptors"]) == 1
        assert cd["descriptors"][0]["pfields"] == ["amp"]
        assert cd["bufferB64"] is not None
        assert cd["numFrames"] > 0

    def test_curve_actually_rises(self):
        """Decode the buffer: a 0 -> 1 -> 0 swell must peak above zero."""
        import base64
        import numpy as np

        cd = compositional_unit_to_sc_animation_events(_swell_uc())["controlData"]
        samples = np.frombuffer(base64.b64decode(cd["bufferB64"]), dtype=np.float32)
        assert len(samples) == cd["numFrames"]
        assert samples[0] == pytest.approx(0.0, abs=1e-6)
        # 512 samples across the curve land just shy of the true apex.
        assert samples.max() > 0.99
        assert samples[-1] == pytest.approx(0.0, abs=1e-6)


class TestBothSurfacesOweTheSameSound:
    """The pin that counts: play(obj) and plot(obj).play() agree."""

    def test_single_note_swell(self):
        uc = _swell_uc()
        bare_payload = convert_to_sc_payload(uc)
        bare_cd = serialize_control_data(bare_payload["control_data"])
        anim = compositional_unit_to_sc_animation_events(uc)
        _assert_control_data_equivalent(bare_payload, bare_cd, anim)

    def test_multi_leaf_envelope(self):
        uc = CompositionalUnit(
            tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60,
            inst=SynthDefInstrument.from_manifest('kl_tri'),
        )
        uc.leaves.set_pfields(freq=440.0)
        uc.root.apply_envelope(Envelope([0.0, 1.0, 0.0]), pfields='amp',
                               control=True)
        bare_payload = convert_to_sc_payload(uc)
        anim = compositional_unit_to_sc_animation_events(uc)
        assert len(anim["controlData"]["descriptors"][0]["targets"]) == 4
        _assert_control_data_equivalent(
            bare_payload, serialize_control_data(bare_payload["control_data"]), anim)

    def test_sequence_of_swells(self):
        seq = TemporalUnitSequence([_plain_uc(), _swell_uc(), _swell_uc()])
        bare_payload = convert_to_sc_payload(seq)
        assert len(bare_payload["control_data"]["descriptors"]) == 2
        anim = temporal_container_to_sc_animation_events(seq)
        _assert_control_data_equivalent(
            bare_payload, serialize_control_data(bare_payload["control_data"]), anim)

    def test_block_of_swells(self):
        blk = TemporalBlock([_swell_uc(), _plain_uc(), _swell_uc()],
                            sort_rows=False)
        bare_payload = convert_to_sc_payload(blk)
        assert len(bare_payload["control_data"]["descriptors"]) == 2
        anim = temporal_container_to_sc_animation_events(blk)
        _assert_control_data_equivalent(
            bare_payload, serialize_control_data(bare_payload["control_data"]), anim)

    def test_nested_container(self):
        blk = TemporalBlock(
            [TemporalUnitSequence([_plain_uc(), _swell_uc()]),
             TemporalUnit(tempus='3/4', prolatio=(1, 1, 1), bpm=90)],
            sort_rows=False,
        )
        bare_payload = convert_to_sc_payload(blk)
        anim = temporal_container_to_sc_animation_events(blk)
        assert len(anim["controlData"]["descriptors"]) == 1
        _assert_control_data_equivalent(
            bare_payload, serialize_control_data(bare_payload["control_data"]), anim)


class TestNoFalsePositives:
    """A guard must not change behaviour for input that never had a bug."""

    def test_no_envelope_gives_empty_control_data(self):
        payload = compositional_unit_to_sc_animation_events(_plain_uc())
        assert payload["controlData"]["descriptors"] == []
        assert payload["controlData"]["bufferB64"] is None

    def test_baked_envelope_produces_no_descriptor(self):
        """``control=False`` bakes the curve into the pfields; both
        surfaces already agreed, and neither grows a descriptor."""
        uc = _baked_uc()
        assert convert_to_sc_payload(uc)["control_data"]["descriptors"] == []
        anim = compositional_unit_to_sc_animation_events(uc)
        assert anim["controlData"]["descriptors"] == []
        # The curve is already in the pfields: a rising ramp per leaf.
        amps = [e["pfields"]["amp"] for e in sorted(
            (e for e in anim["events"] if e.get("type") == "new"),
            key=lambda e: e["start"])]
        assert amps[0] == pytest.approx(0.1)
        assert amps == sorted(amps)
        assert amps[-1] > amps[0]


class TestRebaseKeepsCurveOnTheNote:
    """The animation payload starts at zero; the curve must move with it."""

    def test_descriptor_shifts_with_its_events(self):
        seq = TemporalUnitSequence([_plain_uc(), _swell_uc()])
        payload = temporal_container_to_sc_animation_events(seq)
        events, cd = payload["events"], payload["controlData"]

        assert min(e["start"] for e in events) == pytest.approx(0.0)
        desc = cd["descriptors"][0]
        starts = {e["id"]: e["start"] for e in events}
        # The swell sits on the SECOND unit: its descriptor must land at
        # 4.0s (the first unit's length at bpm=60), not back at zero.
        assert desc["start"] == pytest.approx(4.0)
        for tgt in desc["targets"]:
            assert starts[tgt["id"]] == pytest.approx(tgt["startTime"])

    def test_offset_container_rebases_events_and_curve_together(self):
        """Same rebase, one level up: a container handed to plot() with an
        offset of its own. Shifting the events without shifting the
        descriptors would fire each swell 4 seconds after its note."""
        inner = TemporalUnitSequence([_swell_uc(), _swell_uc()])
        outer = TemporalUnitSequence([_plain_uc(), inner])
        member = outer[1]
        assert member._offset == pytest.approx(4.0)

        payload = temporal_container_to_sc_animation_events(member)
        events, cd = payload["events"], payload["controlData"]
        assert min(e["start"] for e in events) == pytest.approx(0.0)
        assert [d["start"] for d in cd["descriptors"]] == pytest.approx([0.0, 1.0])

        bare_payload = convert_to_sc_payload(member)
        _assert_control_data_equivalent(
            bare_payload, serialize_control_data(bare_payload["control_data"]),
            payload)

    def test_offset_unit_rebases_events_and_curve_together(self):
        """A UC carrying its own offset rebases to zero on the plot path;
        the descriptor has to travel the same distance or the swell fires
        on a note that is no longer there."""
        # A sequence copies its members and places them, so the member
        # handle -- not the one passed in -- is the one carrying an offset.
        seq = TemporalUnitSequence([_plain_uc(), _swell_uc()])
        uc = seq[1]
        assert uc._offset > 0

        payload = compositional_unit_to_sc_animation_events(uc)
        events, cd = payload["events"], payload["controlData"]
        assert min(e["start"] for e in events) == pytest.approx(0.0)
        desc = cd["descriptors"][0]
        assert desc["start"] == pytest.approx(0.0)
        starts = {e["id"]: e["start"] for e in events}
        for tgt in desc["targets"]:
            assert starts[tgt["id"]] == pytest.approx(tgt["startTime"])
