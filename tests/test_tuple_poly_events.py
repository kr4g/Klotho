from mido import MidiFile

from klotho import CompositionalUnit
from klotho.semeios.notelists.supercollider import Scheduler
from klotho.thetos.instruments.instrument import ToneInstrument, MidiInstrument
from klotho.utils.playback._converter_base import lower_event_ir_to_voice_events, lower_poly_pfields_to_voices
from klotho.utils.playback.midi_player import _create_midi_from_compositional_unit
from klotho.utils.playback._sc_assembly import sort_sc_assembly_events
from klotho.utils.playback.supersonic.converters import compositional_unit_to_sc_events
from klotho.utils.playback.tonejs.converters import compositional_unit_to_events


class _FakeRT:
    def __init__(self, leaf_nodes):
        self.leaf_nodes = leaf_nodes


class _FakeEvent:
    def __init__(self, node_id, start, duration, pfields=None, mfields=None, is_rest=False):
        self.node_id = node_id
        self._node_id = node_id
        self.start = start
        self.duration = duration
        self.end = start + duration
        self.is_rest = is_rest
        self.pfields = pfields or {}
        self._mfields = mfields or {}

    @property
    def mfields(self):
        return dict(self._mfields)

    def get_parameter(self, key, default=None):
        if key in self.pfields:
            return self.pfields[key]
        if key in self._mfields:
            return self._mfields[key]
        return default


class _FakeCU:
    def __init__(self, events, instrument):
        self._events = list(events)
        self._instrument = instrument
        self._rt = _FakeRT([ev.node_id for ev in self._events])

    def __iter__(self):
        return iter(self._events)

    def get_instrument(self, node_id):
        return self._instrument


class _SimpleSCInstrument:
    def __init__(self, defName="test-synth", release_mode="gate"):
        self.defName = defName
        self.release_mode = release_mode
        self.name = defName
        self.pfields = {}


def _collect_note_on_events_with_ticks(midi_file):
    events = []
    for track in midi_file.tracks:
        tick = 0
        for msg in track:
            tick += msg.time
            if msg.type == "note_on" and getattr(msg, "velocity", 0) > 0:
                events.append((tick, msg.note, msg.velocity))
    events.sort(key=lambda item: item[0])
    return events


def test_expand_poly_pfields_loops_shorter_tuples():
    expanded, tuple_expanded = lower_poly_pfields_to_voices({
        "note": (60, 64, 67),
        "velocity": (100, 80),
        "gate": 1,
    })
    assert tuple_expanded is True
    assert len(expanded) == 3
    assert expanded[0]["note"] == 60 and expanded[0]["velocity"] == 100
    assert expanded[1]["note"] == 64 and expanded[1]["velocity"] == 80
    assert expanded[2]["note"] == 67 and expanded[2]["velocity"] == 100
    assert all(item["gate"] == 1 for item in expanded)


def test_expand_event_poly_voices_signed_strum_and_non_tuple_behavior():
    event = _FakeEvent(
        node_id=10,
        start=4.0,
        duration=2.0,
        pfields={"note": (60, 64, 67)},
        mfields={"strum": -0.5},
    )
    expanded = lower_event_ir_to_voice_events(event, step_index=3)
    starts = [round(v["start"], 6) for v in expanded]
    assert starts == [4.666667, 4.333333, 4.0]
    leaders = [v["poly_is_leader"] for v in expanded]
    assert leaders == [False, False, True]
    assert all(v["step_index"] == 3 for v in expanded)

    scalar_event = _FakeEvent(
        node_id=11,
        start=1.25,
        duration=0.5,
        pfields={"note": 60},
        mfields={"strum": 1.0},
    )
    scalar_expanded = lower_event_ir_to_voice_events(scalar_event)
    assert len(scalar_expanded) == 1
    assert scalar_expanded[0]["start"] == 1.25


def test_supersonic_compositional_unit_poly_strum_animation_metadata():
    event = _FakeEvent(
        node_id=1,
        start=10.0,
        duration=4.0,
        pfields={"note": (60, 64, 67), "velocity": 90},
        mfields={"strum": 0.6},
    )
    cu = _FakeCU([event], _SimpleSCInstrument())
    sc_events = compositional_unit_to_sc_events(cu, animation=True)
    new_events = [ev for ev in sc_events if ev["type"] == "new" and ev["defName"] != "__rest__"]
    release_events = [ev for ev in sc_events if ev["type"] == "release"]

    assert len(new_events) == 3
    assert len(release_events) == 3
    assert [round(ev["start"], 6) for ev in new_events] == [0.0, 0.8, 1.6]
    assert {round(ev["start"], 6) for ev in release_events} == {4.0}
    assert all(ev["_stepIndex"] == 0 for ev in new_events)
    assert sum(1 for ev in new_events if ev["_animate"] is True) == 1
    assert len({ev["_polyGroupId"] for ev in new_events}) == 1


def test_tonejs_compositional_unit_poly_strum_animation_metadata():
    event = _FakeEvent(
        node_id=2,
        start=8.0,
        duration=3.0,
        pfields={"freq": (220.0, 330.0, 440.0), "vel": (0.4, 0.6)},
        mfields={"strum": 0.5},
    )
    cu = _FakeCU([event], ToneInstrument(name="poly", tonejs_class="Synth", pfields={"vel": 0.5}))
    payload = compositional_unit_to_events(cu, animation=True)
    events = payload["events"]

    assert len(events) == 3
    assert [round(ev["start"], 6) for ev in events] == [0.0, 0.5, 1.0]
    assert [round(ev["duration"], 6) for ev in events] == [3.0, 2.5, 2.0]
    assert all(ev["_stepIndex"] == 0 for ev in events)
    assert sum(1 for ev in events if ev["_animate"] is True) == 1
    assert len({ev["_polyGroupId"] for ev in events}) == 1


def test_midi_compositional_unit_expands_tuple_voices_with_strum():
    event = _FakeEvent(
        node_id=3,
        start=5.0,
        duration=2.0,
        pfields={"note": (60, 64, 67), "velocity": (100, 90, 80)},
        mfields={"strum": -0.5},
    )
    cu = _FakeCU([event], MidiInstrument(name="mid", prgm=1, is_Drum=False))
    midi_file = _create_midi_from_compositional_unit(cu, max_channels=32)
    assert isinstance(midi_file, MidiFile)

    note_ons = _collect_note_on_events_with_ticks(midi_file)
    assert len(note_ons) == 3
    assert note_ons[0][1] == 67
    assert len({tick for tick, _, _ in note_ons}) == 3


def test_sort_sc_events_orders_type_priority_at_same_start():
    unsorted_events = [
        {"type": "release", "start": 1.0, "id": "a"},
        {"type": "set", "start": 1.0, "id": "a", "pfields": {"note": 62}},
        {"type": "new", "start": 1.0, "id": "a", "defName": "custom", "pfields": {"note": 60}},
    ]
    sorted_events = sort_sc_assembly_events(unsorted_events)
    assert [event["type"] for event in sorted_events] == ["new", "set", "release"]


def test_scheduler_accepts_arbitrary_def_name_from_uc():
    uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), pfields={"note": 60, "amp": 0.2}, mfields={"group": "default"})
    leaves = tuple(uc._rt.leaf_nodes)
    uc.set_pfields(leaves[0], defName='custom_poly_synth', note=(60, 64), amp=0.25)
    uc.set_pfields(leaves[1], defName='custom_poly_synth', note=67, amp=0.2)

    scheduler = Scheduler()
    scheduler.add(uc)
    scheduled_events = [event for *_, event in scheduler.events]
    new_events = [event for event in scheduled_events if event["type"] == "new"]

    assert any(event.get("defName") == 'custom_poly_synth' for event in new_events)


def test_slur_markers_live_in_mfields_not_pfields():
    uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), pfields={"note": 60, "amp": 0.2})
    leaves = tuple(uc._rt.leaf_nodes)
    uc.apply_slur(leaves)

    events = list(uc)
    first_event = events[0]
    second_event = events[1]

    assert first_event.get_mfield('_slur_start') == 1
    assert first_event.get_mfield('_slur_end') == 0
    assert second_event.get_mfield('_slur_start') == 0
    assert second_event.get_mfield('_slur_end') == 1
    assert first_event.get_mfield('_slur_id') is not None
    assert second_event.get_mfield('_slur_id') == first_event.get_mfield('_slur_id')

    assert '_slur_start' not in first_event.pfields
    assert '_slur_end' not in first_event.pfields
    assert '_slur_id' not in first_event.pfields
