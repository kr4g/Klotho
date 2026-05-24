import numpy as np

from klotho.chronos import TemporalUnitSequence as UTS, TemporalBlock as BT
from klotho.thetos import CompositionalUnit as UC
from klotho.topos import Pattern
from klotho.dynatos import Envelope
from klotho.thetos import ToneInstrument as JsInst, SynthDefInstrument as ScInst
from klotho.utils.playback.tonejs.converters import (
    compositional_unit_to_events,
    temporal_sequence_to_events,
    temporal_block_to_events,
)
from klotho.utils.playback.supersonic.converters import temporal_sequence_to_sc_events
from klotho.semeios.notelists.supercollider import Scheduler


def test_uc_converter_smoke_with_instruments():
    np.random.seed(7)
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kick())
    inst_pat = Pattern([JsInst.Kick(), JsInst.Snare(), JsInst.HatClosed()])
    for leaf in uc.rt.leaf_nodes:
        uc.set_instrument(leaf, next(inst_pat))
        uc.set_pfields(leaf, vel=np.random.uniform(0.5, 0.9))
    payload = compositional_unit_to_events(uc)
    assert len(payload["events"]) == 4
    assert payload["instruments"]


def test_uts_and_bt_converter_smoke():
    uc1 = UC(tempus='10/16', prolatio=((3, (1,) * 4), (4, (1,) * 6), (3, (1,) * 4)), beat='1/16', bpm=140, inst=JsInst.Kick())
    uc2 = UC(tempus='10/16', prolatio=((5, (1,) * 5),) * 2, beat='1/16', bpm=140, inst=JsInst.Snare())
    uts1 = UTS([uc1, uc1.copy()])
    uts2 = UTS([uc2, uc2.copy()])
    bt = BT([uts1, uts2])

    seq_payload = temporal_sequence_to_events(uts1)
    block_payload = temporal_block_to_events(bt)

    assert len(seq_payload["events"]) > 0
    assert len(block_payload["events"]) >= len(seq_payload["events"])


def test_nested_bt_offsets_survive_temporal_sequence_conversion():
    uc1 = UC(tempus='1/4', prolatio='d', beat='1/4', bpm=60, inst=JsInst.Kick())
    uc2 = UC(tempus='1/4', prolatio='d', beat='1/4', bpm=60, inst=JsInst.Snare())

    seq = UTS()
    seq.append(BT([uc1]))
    seq.append(BT([uc2]))

    tone_starts = [ev["start"] for ev in temporal_sequence_to_events(seq)["events"]]
    sc_starts = [ev["start"] for ev in temporal_sequence_to_sc_events(seq)]
    assert tone_starts == [0.0, 1.0]
    assert sc_starts == [0.0, 1.0]

    seq._offset = 5.0
    seq._set_offsets()
    tone_shifted = [ev["start"] for ev in temporal_sequence_to_events(seq)["events"]]
    sc_shifted = [ev["start"] for ev in temporal_sequence_to_sc_events(seq)]
    assert tone_shifted == [0.0, 1.0]
    assert sc_shifted == [0.0, 1.0]


def test_scheduler_handles_uc_slur_and_env_overlay():
    uc = UC(tempus='4/4', prolatio=((2, (1, 1)), (2, (1, 1))), beat='1/4', bpm=120, inst=JsInst.Kalimba())
    inner_nodes = uc.rt.at_depth(1)
    uc.apply_slur(node=inner_nodes[0])
    uc.apply_envelope(envelope=Envelope([0.1, 0.8], times=[1.0]), pfields='vel', node=uc.rt.root)

    scheduler = Scheduler()
    scheduler.add(uc)
    assert scheduler.total_events > 0


def test_uc_copy_preserves_branch_leaf_assignments_after_subdivide():
    uc = UC(
        tempus="1/1",
        prolatio=(10, 4, 3, 2, 1),
        beat="1/8",
        bpm=62,
        inst=ScInst.blip(),
    )
    for leaf in uc.leaves:
        leaf.subdivide(leaf.proportion * 2)
    for branch in uc.at_depth(1):
        branch.leaves[0].set_pfields(freq=800, amp=0.9)
        branch.leaves[1:].set_pfields(freq=200, amp=0.2)

    copied = uc.copy()

    for branch in copied.at_depth(1):
        freqs = [copied.get_pfield(node_id, "freq") for node_id in branch.leaves.ids]
        amps = [copied.get_pfield(node_id, "amp") for node_id in branch.leaves.ids]
        assert freqs
        assert freqs[0] == 800
        assert all(value == 200 for value in freqs[1:])
        assert amps[0] == 0.9
        assert all(value == 0.2 for value in amps[1:])
