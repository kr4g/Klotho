"""Tests: control envelopes flow through bare (non-Score) play lowering."""

import pytest

from klotho.chronos.temporal_units.temporal import TemporalUnitSequence
from klotho.dynatos.envelopes import Envelope
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.utils.playback.supersonic.converters import (
    convert_score_to_sc_events,
    convert_to_sc_events,
    convert_to_sc_payload,
)
from klotho.utils.playback.supersonic.engine import SuperSonicEngine


def _uc_with_ctrl_env(bpm=60):
    uc = CompositionalUnit(
        tempus='4/4', prolatio=(1, 1, 1, 1), bpm=bpm,
        inst=SynthDefInstrument.from_manifest('kl_tri'),
    )
    uc.leaves.set_pfields(freq=440.0)
    uc.root.apply_envelope(Envelope([0.1, 0.8]), pfields='amp', control=True)
    return uc


class TestBareUCPayload:
    def test_payload_shape(self):
        payload = convert_to_sc_payload(_uc_with_ctrl_env())
        assert set(payload.keys()) == {"events", "control_data"}
        cd = payload["control_data"]
        assert len(cd["descriptors"]) == 1
        assert cd["buffer"] is not None

    def test_descriptor_targets_reference_event_ids(self):
        payload = convert_to_sc_payload(_uc_with_ctrl_env())
        event_ids = {e["id"] for e in payload["events"] if e["type"] == "new"}
        desc = payload["control_data"]["descriptors"][0]
        assert len(desc["targets"]) == 4
        for tgt in desc["targets"]:
            assert tgt["id"] in event_ids

    def test_descriptor_matches_score_path_timing(self):
        uc = _uc_with_ctrl_env()
        bare = convert_to_sc_payload(uc)["control_data"]["descriptors"][0]

        s = Score()
        s.track('voice')
        s.add(uc, track='voice')
        score = convert_score_to_sc_events(s)["control_data"]["descriptors"][0]

        assert bare["start"] == pytest.approx(score["start"])
        assert bare["dur"] == pytest.approx(score["dur"])
        assert bare["pfields"] == score["pfields"]
        bare_starts = sorted(t["startTime"] for t in bare["targets"])
        score_starts = sorted(t["startTime"] for t in score["targets"])
        assert bare_starts == pytest.approx(score_starts)

    def test_no_envelope_gives_empty_control_data(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=60)
        uc.leaves.set_pfields(freq=440.0)
        payload = convert_to_sc_payload(uc)
        assert payload["control_data"]["descriptors"] == []
        assert payload["control_data"]["buffer"] is None

    def test_events_match_convert_to_sc_events(self):
        uc = _uc_with_ctrl_env()
        payload_events = convert_to_sc_payload(uc)["events"]
        plain_events = convert_to_sc_events(uc)
        assert len(payload_events) == len(plain_events)
        per_run_keys = {'id', '_polyGroupId', '_logicalStepId'}
        strip = lambda evs: [
            {k: v for k, v in e.items() if k not in per_run_keys} for e in evs
        ]
        assert strip(payload_events) == strip(plain_events)


class TestUTSShiftSync:
    def test_uts_descriptor_shifted_with_events(self):
        uc_a = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=60)
        uc_a.leaves.set_pfields(freq=330.0)
        uc_b = _uc_with_ctrl_env()
        seq = TemporalUnitSequence([uc_a, uc_b])

        payload = convert_to_sc_payload(seq)
        events = payload["events"]
        descs = payload["control_data"]["descriptors"]

        assert len(descs) == 1
        assert min(e["start"] for e in events) == pytest.approx(0.0)

        # uc_b starts after uc_a (4s at bpm=60); the descriptor must sit on
        # the same rebased timeline as its target events.
        desc = descs[0]
        target_ids = {t["id"] for t in desc["targets"]}
        target_events = [e for e in events if e["id"] in target_ids]
        assert len(target_events) == 4
        assert desc["start"] == pytest.approx(min(e["start"] for e in target_events))
        for tgt in desc["targets"]:
            ev = next(e for e in events if e["id"] == tgt["id"])
            assert tgt["startTime"] == pytest.approx(ev["start"])

    def test_uts_events_match_plain_converter(self):
        uc = _uc_with_ctrl_env()
        seq = TemporalUnitSequence([uc, uc])
        payload_events = convert_to_sc_payload(seq)["events"]
        plain_events = convert_to_sc_events(seq)
        assert len(payload_events) == len(plain_events)
        assert [e["start"] for e in payload_events] == pytest.approx(
            [e["start"] for e in plain_events]
        )


class TestConvertToScEventsUnchanged:
    def test_still_returns_plain_list(self):
        events = convert_to_sc_events(_uc_with_ctrl_env())
        assert isinstance(events, list)
        assert all(isinstance(e, dict) for e in events)


class TestEngineHTML:
    def test_bare_control_data_loads_score_scheduler(self):
        payload = convert_to_sc_payload(_uc_with_ctrl_env())
        eng = SuperSonicEngine(
            payload["events"], control_data=payload["control_data"]
        )
        html = eng._generate_html()
        assert "setupControlEnvelopes" in html
        assert "__klEnvCtrl" in html

    def test_plain_events_skip_score_scheduler(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=60)
        uc.leaves.set_pfields(freq=440.0)
        payload = convert_to_sc_payload(uc)
        eng = SuperSonicEngine(
            payload["events"], control_data=payload["control_data"]
        )
        html = eng._generate_html()
        assert "setupControlEnvelopes = " not in html


class TestTracklessScoreRegression:
    def test_trackless_score_control_envelopes_reach_widget(self):
        s = Score()
        s.add(_uc_with_ctrl_env())
        payload = convert_score_to_sc_events(s)
        assert len(payload["control_data"]["descriptors"]) == 1

        eng = SuperSonicEngine(
            payload["events"],
            meta=payload["meta"],
            control_data=payload["control_data"],
        )
        html = eng._generate_html()
        # Score has no tracks (meta empty) but descriptors exist: the
        # score scheduler must still be loaded so the ramp plays.
        assert "setupControlEnvelopes" in html
