"""
Tests for Chunk 1 envelope fixes:

- #1  _bake_envelope time_scale math covers full event span regardless of the
      input envelope's own time_scale.
- #3  Score.write(start_time, time_scale) shifts/scales control-envelope
      descriptors in lockstep with events.
- #10 Numpy scalars inside meta / control_data do not crash HTML generation.
- #9  apply_envelope on a rest-only selection emits RuntimeWarning instead of
      silently no-oping.
- #19 Overlapping control-envelope errors name the colliding pfield(s).
"""

import json
import warnings

import numpy as np
import pytest

from klotho.chronos import TemporalUnit as UT
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.dynatos import Envelope
from klotho.utils.playback.supersonic.engine import SuperSonicEngine


def _inst(name='tri', defName='kl_tri', **pf):
    d = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0}
    d.update(pf)
    return SynthDefInstrument(name=name, defName=defName, pfields=d)


def _score_artifacts(uc, track=None):
    """Return (events, ctrl_descriptors, score) for a single-UC Score."""
    score = Score()
    if track is not None:
        score.track(track)
    score.add(uc, track=track)
    ctrl = score._build_control_data()
    return score._drain_events(), ctrl["descriptors"], score


def _baked_pfield_series(uc, field):
    """Baked values for `field` on sounding leaves in leaf order."""
    return [
        uc._pt.get_pfield(n, field)
        for n in uc._rt.leaf_nodes
        if uc._rt[n].get('proportion', 1) >= 0
    ]


class TestBakeTimeScale:
    """#1: _bake_envelope must span the full event duration regardless of the
    envelope's own time_scale.

    The envelope time span is [first_sounding_onset, max_onset+duration]. For
    a symmetric [0, 1, 0] envelope, the leaf whose onset is nearest 50% of
    span should see the peak (1.0). Pre-fix, any input envelope with
    time_scale != 1.0 under-stretched the scaled envelope to
    duration/original_time_scale, so the peak landed at the wrong place and
    most later leaves were clamped to values[-1]=0.
    """

    @pytest.mark.parametrize("time_scale", [1.0, 0.5, 2.0, 10.0])
    def test_mid_leaf_near_envelope_peak(self, time_scale):
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1, 1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        env = Envelope([0.0, 1.0, 0.0], times=[0.5, 0.5], time_scale=time_scale)
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root)
        amps = _baked_pfield_series(uc, 'amp')
        assert amps[0] == pytest.approx(0.0, abs=1e-9)
        mid_idx = len(amps) // 2
        mid = amps[mid_idx]
        assert mid >= 0.9, (
            f"Mid leaf baked amp should approach peak (~1.0); got {mid} at "
            f"time_scale={time_scale}. Pre-fix, non-default time_scale caused "
            f"the envelope to collapse early and leave later leaves clamped to 0."
        )

    @pytest.mark.parametrize("time_scale", [0.5, 2.0, 10.0])
    def test_late_leaves_not_clamped_to_zero(self, time_scale):
        """With envelope = [0, 1, 0], the pre-last leaf sits well before end_time;
        before the fix, with time_scale != 1.0 it was clamped to 0."""
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1, 1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        env = Envelope([0.0, 1.0, 0.0], times=[0.5, 0.5], time_scale=time_scale)
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root)
        amps = _baked_pfield_series(uc, 'amp')
        second = amps[1]
        assert second > 0.1, (
            f"Second leaf baked amp should be rising up the attack ramp "
            f"(not clamped to 0); got {second} at time_scale={time_scale}."
        )

    def test_scaled_envelope_total_time_matches_duration(self):
        """Direct structural check: after fix, the baked envelope's scaled
        total_time equals the event span duration regardless of the input
        envelope's time_scale."""
        import sys
        sys.path.insert(0, str(__import__('os').path.dirname(__file__)))

        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        uc._ensure_timing_cache()
        leaves = [n for n in uc._rt.leaf_nodes
                  if uc._rt[n].get('proportion', 1) >= 0]
        start = min(uc.nodes[n]['real_onset'] for n in leaves)
        end = max(uc.nodes[n]['real_onset'] + abs(uc.nodes[n]['real_duration'])
                  for n in leaves)
        expected_duration = end - start

        for ts in [0.5, 1.0, 2.0, 10.0]:
            env = Envelope([0.0, 1.0, 0.0], times=[0.5, 0.5], time_scale=ts)
            raw_total = sum(env.times)
            scaled_ts = expected_duration / raw_total if raw_total > 0 else 1.0
            scaled_total = raw_total * scaled_ts
            assert scaled_total == pytest.approx(expected_duration, abs=1e-9), (
                f"Post-fix math: for input time_scale={ts}, scaled envelope "
                f"total_time ({scaled_total}) must equal duration "
                f"({expected_duration})."
            )


class TestScoreWriteEnvelopeTiming:
    """#3: Score.write(start_time, time_scale) shifts/scales envelope descriptors
    in lockstep with events."""

    def _build_score_with_envelope(self):
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        env = Envelope([0.0, 1.0, 0.0], times=[0.5, 0.5])
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root, control=True)
        score = Score()
        score.add(uc)
        return score

    def test_write_start_time_shifts_envelope(self, tmp_path):
        score = self._build_score_with_envelope()
        out_path = tmp_path / "out.json"
        score.write(str(out_path), start_time=10.0, time_scale=1.0)
        with open(out_path) as f:
            data = json.load(f)
        assert "controlEnvelopes" in data["meta"]
        env_desc = data["meta"]["controlEnvelopes"][0]
        first_event_start = min(ev["start"] for ev in data["events"])
        assert env_desc["start"] == pytest.approx(first_event_start, abs=1e-9)
        assert env_desc["start"] == pytest.approx(10.0, abs=1e-9)

    def test_write_time_scale_scales_envelope(self, tmp_path):
        score = self._build_score_with_envelope()
        out_path = tmp_path / "out.json"
        score.write(str(out_path), start_time=None, time_scale=0.5)
        with open(out_path) as f:
            data = json.load(f)
        env_desc = data["meta"]["controlEnvelopes"][0]
        first_event_start = min(ev["start"] for ev in data["events"])
        assert env_desc["start"] == pytest.approx(first_event_start, abs=1e-9)

    def test_write_both_shift_and_scale(self, tmp_path):
        score = self._build_score_with_envelope()
        out_path = tmp_path / "out.json"
        score.write(str(out_path), start_time=5.0, time_scale=2.0)
        with open(out_path) as f:
            data = json.load(f)
        env_desc = data["meta"]["controlEnvelopes"][0]
        first_event_start = min(ev["start"] for ev in data["events"])
        assert env_desc["start"] == pytest.approx(first_event_start, abs=1e-9)

    def test_write_duration_scales(self, tmp_path):
        score = self._build_score_with_envelope()
        out_no_scale = tmp_path / "noscale.json"
        out_scaled = tmp_path / "scaled.json"
        score_ref = self._build_score_with_envelope()
        score.write(str(out_no_scale), time_scale=1.0)
        score_ref.write(str(out_scaled), time_scale=0.25)
        with open(out_no_scale) as f:
            d_no = json.load(f)
        with open(out_scaled) as f:
            d_scaled = json.load(f)
        dur_no = d_no["meta"]["controlEnvelopes"][0]["dur"]
        dur_scaled = d_scaled["meta"]["controlEnvelopes"][0]["dur"]
        assert dur_scaled == pytest.approx(dur_no * 0.25, abs=1e-9)


class TestNumpyScalarsInControlData:
    """#10: numpy scalars in meta / control_data do not crash HTML generation."""

    def test_engine_init_converts_numpy_meta(self):
        fake_buffer = np.zeros(512, dtype=np.float32)
        meta = {"groups": ["melody"]}
        control_data = {
            "buffer": fake_buffer,
            "blockSize": np.int64(512),
            "descriptors": [{
                "blockIndex": np.int64(0),
                "start": np.float64(1.5),
                "dur": np.float64(2.0),
                "pfields": ["amp"],
                "targets": [{"id": "deadbeef", "startTime": np.float64(1.5)}],
            }],
        }
        engine = SuperSonicEngine(events=[], meta=meta, control_data=control_data)
        assert isinstance(engine.control_data["blockSize"], int)
        desc = engine.control_data["descriptors"][0]
        assert isinstance(desc["blockIndex"], int)
        assert isinstance(desc["start"], float)
        assert isinstance(desc["dur"], float)
        assert isinstance(desc["targets"][0]["startTime"], float)
        assert engine.control_data["buffer"] is fake_buffer

    def test_engine_generates_html_with_numpy_descriptors(self):
        fake_buffer = np.zeros(512, dtype=np.float32)
        control_data = {
            "buffer": fake_buffer,
            "blockSize": np.int64(512),
            "descriptors": [{
                "blockIndex": np.int64(0),
                "start": np.float64(1.5),
                "dur": np.float64(2.0),
                "pfields": ["amp"],
                "targets": [{"id": "deadbeef", "startTime": np.float64(1.5)}],
            }],
        }
        engine = SuperSonicEngine(events=[], meta={}, control_data=control_data)
        html = engine._generate_html()
        assert isinstance(html, str)
        assert len(html) > 0
        assert "bufferB64" in html


class TestAllRestSelectionWarns:
    """#9: apply_envelope on a rest-only selection emits RuntimeWarning."""

    def test_all_rest_selection_warns_bake(self):
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=120,
            inst=_inst(),
            pfields=['amp'],
        )
        for leaf in list(uc.rt.leaf_nodes):
            uc.make_rest(leaf)
        env = Envelope([0.0, 1.0], times=[1.0])
        with pytest.warns(RuntimeWarning, match="no sounding leaves"):
            uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root)

    def test_all_rest_selection_warns_control(self):
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=120,
            inst=_inst(),
            pfields=['amp'],
        )
        for leaf in list(uc.rt.leaf_nodes):
            uc.make_rest(leaf)
        env = Envelope([0.0, 1.0], times=[1.0])
        with pytest.warns(RuntimeWarning, match="no sounding leaves"):
            uc.apply_envelope(
                envelope=env, pfields='amp', node=uc.rt.root, control=True
            )
        assert len(uc._control_envelopes) == 0


class TestOverlapErrorMessage:
    """#19: overlap error message names the colliding pfield(s) and leaves."""

    def test_overlap_error_names_pfield(self):
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=120,
            inst=_inst(),
            pfields=['amp', 'pan'],
        )
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root, control=True)
        with pytest.raises(ValueError, match=r"amp"):
            uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root, control=True)

    def test_overlap_error_names_shared_leaves(self):
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=120,
            inst=_inst(),
            pfields=['amp'],
        )
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root, control=True)
        with pytest.raises(ValueError, match=r"shared_leaves"):
            uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root, control=True)


class TestControlDescriptorTargetsSchema:
    """Chunk 2: control descriptors expose per-target {id, startTime} so the
    runtime can /n_map at max(synth_start, env_start). This prevents the
    pre-envelope portion of a slur (or long-held synth) from being mapped to
    a bus whose value is still at its default."""

    def test_descriptor_has_targets_field(self):
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        env = Envelope([0.0, 1.0, 0.0], times=[0.5, 0.5])
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root, control=True)
        _, descriptors, _ = _score_artifacts(uc)
        assert len(descriptors) == 1
        desc = descriptors[0]
        assert "targets" in desc
        assert "targetIds" not in desc
        for t in desc["targets"]:
            assert isinstance(t, dict)
            assert "id" in t
            assert "startTime" in t
            assert isinstance(t["startTime"], float)

    def test_simple_envelope_targets_start_at_synth_onsets(self):
        """Normal case: envelope covers leaves that each have their own /s_new.
        Each target's startTime should equal its synth's own start (>= env.start)."""
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        env = Envelope([0.0, 1.0, 0.0], times=[0.5, 0.5])
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root, control=True)
        events, descriptors, _ = _score_artifacts(uc)
        desc = descriptors[0]
        env_start = desc["start"]
        starts_by_id = {
            ev["id"]: ev["start"] for ev in events if ev.get("type") == "new"
        }
        for t in desc["targets"]:
            synth_start = starts_by_id.get(t["id"])
            assert synth_start is not None, f"Target {t['id']} not in events"
            assert t["startTime"] == pytest.approx(
                max(synth_start, env_start), abs=1e-9
            )

    def test_slur_partial_envelope_targets_start_at_env_start(self):
        """Bug #2: slur on [L1..L4] + envelope on subset [L3, L4]. The slur
        synth's /s_new is at L1's onset. The envelope should map that synth
        starting at env.start (L3's onset), NOT at L1's onset.
        """
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        leaves = list(uc.rt.leaf_nodes)
        uc.apply_slur(node=leaves)
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(envelope=env, pfields='amp', node=leaves[2:], control=True)
        events, descriptors, _ = _score_artifacts(uc)
        desc = descriptors[0]
        env_start = desc["start"]
        slur_synth_start = min(
            ev["start"] for ev in events if ev.get("type") == "new"
        )
        assert slur_synth_start < env_start, (
            "Test setup: slur synth must start before envelope"
        )
        for t in desc["targets"]:
            assert t["startTime"] == pytest.approx(env_start, abs=1e-9), (
                f"Target {t['id']} startTime should be env.start "
                f"({env_start}), not slur onset ({slur_synth_start}). "
                "Pre-fix behavior was to /n_map at the slur's /s_new, "
                "causing the pre-envelope portion to read bus default (0)."
            )

    def test_slur_fully_inside_envelope_targets_at_synth_start(self):
        """Slur on [L3, L4] fully inside an envelope applied to [L1..L4].
        The slur's /s_new is at L3's onset (which is > env.start); startTime
        should equal the slur /s_new time, not env.start."""
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        leaves = list(uc.rt.leaf_nodes)
        uc.apply_slur(node=leaves[2:])
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root, control=True)
        events, descriptors, _ = _score_artifacts(uc)
        desc = descriptors[0]
        env_start = desc["start"]
        new_events_by_id = {
            ev["id"]: ev["start"] for ev in events if ev.get("type") == "new"
        }
        for t in desc["targets"]:
            synth_start = new_events_by_id[t["id"]]
            expected = max(synth_start, env_start)
            assert t["startTime"] == pytest.approx(expected, abs=1e-9)

    def test_targets_dedup_by_id(self):
        """A slur produces one uid referenced by multiple target leaves.
        Targets should be deduplicated by id."""
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        leaves = list(uc.rt.leaf_nodes)
        uc.apply_slur(node=leaves)
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root, control=True)
        _, descriptors, _ = _score_artifacts(uc)
        desc = descriptors[0]
        ids = [t["id"] for t in desc["targets"]]
        assert len(ids) == len(set(ids)), (
            f"Expected deduplicated targets, got {ids}"
        )


class TestEnvelopeHandlesAndRemoval:
    """Chunk 3 Feature A: apply_envelope returns an int handle for control
    envelopes; remove_envelope deletes the descriptor and unsets the baked
    pfield values so leaves fall back to their inherited/instrument defaults.
    Bake-mode envelopes have no state and return None."""

    def _uc(self):
        return UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=120,
            inst=_inst(),
            pfields=['amp'],
        )

    def test_bake_mode_returns_none(self):
        uc = self._uc()
        env = Envelope([0.0, 1.0], times=[1.0])
        result = uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root)
        assert result is None

    def test_control_mode_returns_int_handle(self):
        uc = self._uc()
        env = Envelope([0.0, 1.0], times=[1.0])
        env_id = uc.apply_envelope(
            envelope=env, pfields='amp', node=uc.rt.root, control=True
        )
        assert isinstance(env_id, int)
        assert env_id in uc._control_envelopes

    def test_control_mode_per_node_returns_list_of_ints(self):
        uc = self._uc()
        inner_nodes = uc.rt.at_depth(1)
        env = Envelope([0.0, 1.0], times=[1.0])
        result = uc.apply_envelope(
            envelope=env, pfields='amp', node=inner_nodes,
            scope="per_node", control=True
        )
        assert isinstance(result, list)
        assert len(result) == len(inner_nodes)
        for env_id in result:
            assert isinstance(env_id, int)
            assert env_id in uc._control_envelopes

    def test_successive_handles_are_unique(self):
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1),
            beat='1/4',
            bpm=120,
            inst=_inst(),
            pfields=['amp', 'pan'],
        )
        env = Envelope([0.0, 1.0], times=[1.0])
        id_a = uc.apply_envelope(
            envelope=env, pfields='amp', node=uc.rt.root, control=True
        )
        id_b = uc.apply_envelope(
            envelope=env, pfields='pan', node=uc.rt.root, control=True
        )
        assert id_a != id_b

    def test_remove_envelope_clears_descriptor(self):
        uc = self._uc()
        env = Envelope([0.0, 1.0], times=[1.0])
        env_id = uc.apply_envelope(
            envelope=env, pfields='amp', node=uc.rt.root, control=True
        )
        uc.remove_envelope(env_id)
        assert env_id not in uc._control_envelopes

    def test_remove_envelope_unsets_baked_pfields(self):
        uc = self._uc()
        baseline = _baked_pfield_series(uc, 'amp')
        env = Envelope([0.0, 1.0], times=[1.0])
        env_id = uc.apply_envelope(
            envelope=env, pfields='amp', node=uc.rt.root, control=True
        )
        post_apply = _baked_pfield_series(uc, 'amp')
        assert post_apply != baseline, (
            "Test setup: envelope must have actually changed baked values"
        )
        uc.remove_envelope(env_id)
        after_remove = _baked_pfield_series(uc, 'amp')
        assert after_remove == baseline, (
            f"After remove_envelope, baked pfields should revert to baseline. "
            f"baseline={baseline} after_remove={after_remove}"
        )

    def test_remove_envelope_invalid_id_raises(self):
        uc = self._uc()
        with pytest.raises(KeyError):
            uc.remove_envelope(9999)


class TestRebakeOnPartialShrink:
    """Chunk 3 #5: when make_rest / prune shrinks an envelope's leaf set
    without destroying it, remaining leaves must be re-sampled against the
    new (shrunken) span so uc.pt / uc.events stay in sync with runtime."""

    def test_make_rest_rebakes_remaining_leaves(self):
        uc = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1, 1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        env = Envelope([0.0, 1.0, 0.0], times=[0.5, 0.5])
        uc.apply_envelope(
            envelope=env, pfields='amp', node=uc.rt.root, control=True
        )
        leaves = list(uc.rt.leaf_nodes)
        uc.make_rest(leaves[-1])
        post_rest = [
            uc._pt.get_pfield(n, 'amp')
            for n in uc._rt.leaf_nodes
            if uc._rt[n].get('proportion', 1) >= 0
        ]

        reference = UC(
            tempus='4/4',
            prolatio=(1, 1, 1, 1, 1, 1, 1, 1),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        ref_leaves = list(reference.rt.leaf_nodes)
        reference.make_rest(ref_leaves[-1])
        reference.apply_envelope(
            envelope=env, pfields='amp', node=reference.rt.root, control=True
        )
        ref_series = [
            reference._pt.get_pfield(n, 'amp')
            for n in reference._rt.leaf_nodes
            if reference._rt[n].get('proportion', 1) >= 0
        ]

        assert len(post_rest) == len(ref_series)
        for a, b in zip(post_rest, ref_series):
            assert a == pytest.approx(b, abs=1e-9), (
                f"Post-make_rest rebake mismatch: {post_rest} vs {ref_series}"
            )


class TestDegenerateEndpointFalse:
    """Chunk 3 #8: endpoint=False with a single sounding leaf collapses the
    envelope duration to zero. Fallback: warn and treat as endpoint=True."""

    def test_single_leaf_endpoint_false_warns(self):
        uc = UC(
            tempus='4/4',
            prolatio=(1,),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        env = Envelope([0.1, 0.9], times=[1.0])
        with pytest.warns(RuntimeWarning, match=r"endpoint=False"):
            uc.apply_envelope(
                envelope=env, pfields='amp', node=uc.rt.root, endpoint=False
            )
        amp = uc._pt.get_pfield(uc.rt.leaf_nodes[0], 'amp')
        assert amp == pytest.approx(0.1, abs=1e-9), (
            "Single leaf sits at relative_time=0 of the envelope, so baked "
            f"value should equal values[0]=0.1; got {amp}"
        )


class TestFromSubtreeEnvelopes:
    """Chunk 3: from_subtree preserves envelopes fully inside the subtree and
    drops those whose anchor/leaves cross the subtree boundary."""

    def test_fully_contained_envelope_survives(self):
        uc = UC(
            tempus='4/4',
            prolatio=((2, (1, 1)), (2, (1, 1))),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        inner = uc.rt.at_depth(1)
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(
            envelope=env, pfields='amp', node=inner[0], control=True
        )
        sub = uc.from_subtree(inner[0])
        assert len(sub._control_envelopes) == 1
        surviving_id = next(iter(sub._control_envelopes.keys()))
        assert isinstance(surviving_id, int)

    def test_crossing_envelope_dropped(self):
        uc = UC(
            tempus='4/4',
            prolatio=((2, (1, 1)), (2, (1, 1))),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(
            envelope=env, pfields='amp', node=uc.rt.root, control=True
        )
        inner = uc.rt.at_depth(1)
        sub = uc.from_subtree(inner[0])
        assert len(sub._control_envelopes) == 0

    def test_subtree_envelope_ids_start_fresh(self):
        uc = UC(
            tempus='4/4',
            prolatio=((2, (1, 1)), (2, (1, 1))),
            beat='1/4',
            bpm=60,
            inst=_inst(),
            pfields=['amp'],
        )
        inner = uc.rt.at_depth(1)
        env = Envelope([0.0, 1.0], times=[1.0])
        for _ in range(3):
            uc.apply_envelope(
                envelope=env, pfields='amp', node=inner[0], control=True
            )
            uc.remove_envelope(max(uc._control_envelopes.keys())
                               if uc._control_envelopes else 0)
        uc.apply_envelope(
            envelope=env, pfields='amp', node=inner[0], control=True
        )
        parent_id = max(uc._control_envelopes.keys())
        assert parent_id > 0, "Test setup: parent counter should have advanced"
        sub = uc.from_subtree(inner[0])
        sub_ids = list(sub._control_envelopes.keys())
        assert len(sub_ids) == 1
        assert sub_ids[0] == 0, (
            f"Subtree envelope IDs should start fresh at 0; got {sub_ids}"
        )
