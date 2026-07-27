"""Engine-independent multi-voice (tuple-pfield) expansion tests.

Ported from the removed test_tuple_poly_events.py (whose MIDI/Tone.js
halves went away with those engines in 10.12); Phase 4 of the refactor
plan extends this file with slur-driven ``voice_count=`` override tests.
"""
from klotho.thetos import CompositionalUnit
from klotho.utils.playback._converter_base import (
    lower_event_ir_to_voice_events,
    lower_poly_pfields_to_voices,
)
from klotho.utils.playback._sc_assembly import sort_sc_assembly_events
from klotho.utils.playback.supersonic.converters import compositional_unit_to_sc_events


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

    def get_pfield(self, key, default=None):
        if key in self.pfields:
            return self.pfields[key]
        return default

    def get_mfield(self, key, default=None):
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
    def __init__(self, defName="test-synth", has_gate=True):
        self.defName = defName
        self.has_gate = has_gate
        self.name = defName
        self.pfields = {}


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

    # The lowering layer no longer emits explicit type:release events;
    # instead each terminal new carries releaseAfter=true. The scheduler
    # schedules /n_set gate=0 at start+dur at fire time when the synthdef
    # has a 'gate' control.
    assert all(ev["type"] != "release" for ev in sc_events)
    assert len(new_events) == 3
    assert [round(ev["start"], 6) for ev in new_events] == [0.0, 0.8, 1.6]
    # Every voice is terminal (single leaf), so all carry releaseAfter=true.
    assert all(ev.get("releaseAfter") is True for ev in new_events)
    # The scheduler will fire gate-off at start + dur for each.
    assert {round(ev["start"] + ev.get("dur", 0), 6) for ev in new_events} == {4.0}
    assert all(ev["_stepIndex"] == 0 for ev in new_events)
    assert sum(1 for ev in new_events if ev["_animate"] is True) == 1
    assert len({ev["_polyGroupId"] for ev in new_events}) == 1


def test_voice_count_override_expands_scalars_without_tuple_flag():
    expanded, tuple_expanded = lower_poly_pfields_to_voices(
        {"freq": 440.0, "amp": 0.5}, voice_count=3)
    assert tuple_expanded is False
    assert len(expanded) == 3
    assert all(v == {"freq": 440.0, "amp": 0.5} for v in expanded)


def test_voice_count_override_cycles_smaller_tuples():
    expanded, tuple_expanded = lower_poly_pfields_to_voices(
        {"freq": (440.0, 550.0), "amp": 0.5}, voice_count=5)
    assert tuple_expanded is True
    assert [v["freq"] for v in expanded] == [440.0, 550.0, 440.0, 550.0, 440.0]
    assert all(v["amp"] == 0.5 for v in expanded)


def test_voice_count_override_never_shrinks():
    expanded, _ = lower_poly_pfields_to_voices(
        {"freq": (440.0, 550.0, 660.0)}, voice_count=2)
    assert len(expanded) == 3


def test_event_voice_count_override_updates_poly_metadata():
    event = _FakeEvent(node_id=7, start=1.0, duration=1.0,
                       pfields={"freq": 440.0})
    voices = lower_event_ir_to_voice_events(event, voice_count=4)
    assert len(voices) == 4
    assert all(v["poly_voice_count"] == 4 for v in voices)
    assert sum(1 for v in voices if v["poly_is_leader"]) == 1
    # force-expansion does not enable strum even with a strum mfield
    strummed = _FakeEvent(node_id=8, start=0.0, duration=1.0,
                          pfields={"freq": 440.0}, mfields={"strum": 0.9})
    voices = lower_event_ir_to_voice_events(strummed, voice_count=3)
    assert {v["start"] for v in voices} == {0.0}


def test_sort_sc_events_orders_type_priority_at_same_start():
    unsorted_events = [
        {"type": "release", "start": 1.0, "id": "a"},
        {"type": "set", "start": 1.0, "id": "a", "pfields": {"note": 62}},
        {"type": "new", "start": 1.0, "id": "a", "defName": "custom", "pfields": {"note": 60}},
    ]
    sorted_events = sort_sc_assembly_events(unsorted_events)
    assert [event["type"] for event in sorted_events] == ["new", "set", "release"]


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
