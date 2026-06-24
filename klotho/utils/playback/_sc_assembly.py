from uuid import uuid4

from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.thetos.instruments.base import Effect
from klotho.thetos.instruments.base import Kit
from klotho.utils.playback._amplitude import single_voice_amplitude
from klotho.utils.playback._converter_base import (
    _merge_pfields,
    lower_event_ir_to_voice_events,
    freq_to_midi,
)

SC_EVENT_PRIORITY = {'new': 0, 'set': 1, 'release': 2}


def sort_sc_assembly_events(events):
    indexed = list(enumerate(events))
    indexed.sort(
        key=lambda item: (
            item[1].get("start", 0.0),
            SC_EVENT_PRIORITY.get(item[1].get("type"), 3),
            item[0],
        )
    )
    return [event for _, event in indexed]


def _normalize_sc_pfields(pfields):
    normalized = dict(pfields)
    if 'freq' in normalized and 'note' not in normalized:
        freq = normalized['freq']
        normalized['note'] = freq_to_midi(freq) if isinstance(freq, (int, float)) else freq
    if 'amp' not in normalized:
        freq = normalized.get('freq', 440.0)
        normalized['amp'] = single_voice_amplitude(freq) if isinstance(freq, (int, float)) else 0.5
    return normalized


def _resolve_event_synth(instrument, default_synth):
    if isinstance(instrument, str):
        return instrument
    if isinstance(instrument, SynthDefInstrument):
        return instrument.defName or default_synth
    if instrument is not None and hasattr(instrument, 'defName'):
        return instrument.defName or default_synth
    return default_synth


def _has_gate(instrument):
    if instrument is None:
        return True
    return bool(getattr(instrument, 'has_gate', True))


def _wants_duration_pfield(instrument):
    """True if a non-gated instrument declares a ``duration`` control.

    Such synths (e.g. Supriya/SC one-shots that self-free via an
    ``Env.linen(0, duration, ...)`` envelope) need the leaf's time
    duration injected as the ``duration`` pfield so their internal
    envelope length tracks the rhythmic value.
    """
    pfields = getattr(instrument, 'pfields', None)
    if pfields is None:
        return False
    try:
        return 'duration' in pfields
    except TypeError:
        return False


def _attach_poly_meta(event_record, voice_event):
    event_record["_polyGroupId"] = voice_event["poly_group_id"]
    event_record["_logicalStepId"] = voice_event["logical_step_id"]
    event_record["_polyVoiceIndex"] = voice_event["poly_voice_index"]
    event_record["_polyVoiceCount"] = voice_event["poly_voice_count"]
    event_record["_polyLeader"] = voice_event["poly_is_leader"]
    event_record["_animate"] = voice_event["animate"]
    if voice_event["step_index"] is not None:
        event_record["_stepIndex"] = voice_event["step_index"]
    return event_record


def _is_insert_instrument(instrument):
    return isinstance(instrument, Effect)


def lower_compositional_ir_to_sc_assembly(
    obj,
    extra_pfields=None,
    animation=False,
    default_synth='kl_tri',
    normalize_sc_pfields=True,
    sort_output=True,
    return_node_map=False,
    include_ungated_release=None,  # deprecated no-op; lifecycle-release emission moved to schedulers
):
    events = []
    node_to_event_ids = {}
    uid_first_start: dict = {}
    last_event_index_by_uid: dict = {}
    leaf_nodes = obj._rt.leaf_nodes if animation else None
    node_to_step = ({nid: idx for idx, nid in enumerate(leaf_nodes)} if animation else None)
    events_iterable = tuple(obj)
    slur_end_events = {}
    sustain_param_cache = {}

    def _record(node_id, uid, synth_start):
        if uid not in uid_first_start:
            uid_first_start[uid] = synth_start
        node_to_event_ids.setdefault(node_id, []).append((uid, uid_first_start[uid]))

    def _track_event(uid):
        last_event_index_by_uid[uid] = len(events) - 1

    def _mark_terminal(uid, terminal_time=None):
        idx = last_event_index_by_uid.get(uid)
        if idx is None:
            return
        ev = events[idx]
        ev["releaseAfter"] = True
        if terminal_time is not None:
            new_dur = terminal_time - ev.get("start", 0.0)
            if new_dur > 0:
                ev["dur"] = new_dur

    for event in events_iterable:
        if event.is_rest:
            continue
        slur_id = event.get_mfield('_slur_id')
        if slur_id is None:
            continue
        if event.get_mfield('_slur_end', 0):
            slur_end_events[slur_id] = event

    time_offset = 0.0
    if animation:
        sounding = [ev for ev in events_iterable if not ev.is_rest]
        time_offset = min(ev.start for ev in sounding) if sounding else 0.0

    slur_voice_uids: dict = {}

    for event in events_iterable:
        step_idx = node_to_step.get(event.node_id, None) if animation else None
        if event.is_rest:
            if animation:
                rest = {
                    "type": "new",
                    "id": uuid4().hex,
                    "defName": "__rest__",
                    "start": event.start - time_offset,
                    "pfields": {},
                }
                if step_idx is not None:
                    rest["_stepIndex"] = step_idx
                events.append(rest)
            continue

        instrument = obj.get_instrument(event.node_id)

        if _is_insert_instrument(instrument):
            voice_events = lower_event_ir_to_voice_events(event, step_index=step_idx)
            for voice_event in voice_events:
                voice_start = voice_event["start"] - time_offset if animation else voice_event["start"]
                voice_pfields = {
                    k: v for k, v in voice_event["pfields"].items()
                    if k != 'group'
                }
                if normalize_sc_pfields:
                    voice_pfields = _normalize_sc_pfields(voice_pfields)
                merged_pfields = _merge_pfields(voice_pfields, extra_pfields)
                set_event = {
                    "type": "set",
                    "id": instrument.uid,
                    "start": voice_start,
                    "pfields": merged_pfields,
                }
                events.append(_attach_poly_meta(set_event, voice_event))
                _record(event.node_id, instrument.uid, 0.0)
            continue

        resolved_instrument = instrument
        if isinstance(instrument, Kit):
            selector_val = event.get_pfield(instrument.selector)
            resolved_instrument = instrument._resolve(selector_val)

        def_name = _resolve_event_synth(resolved_instrument, default_synth)
        has_gate = _has_gate(resolved_instrument)
        inject_duration = (not has_gate) and _wants_duration_pfield(resolved_instrument)
        group = event.get_mfield('group')
        is_slur_start = event.get_mfield('_slur_start', 0)
        is_slur_end = event.get_mfield('_slur_end', 0)
        slur_id = event.get_mfield('_slur_id')
        voice_events = lower_event_ir_to_voice_events(event, step_index=step_idx)

        if slur_id is not None and not is_slur_start:
            base_start = float(event.start)
            base_end = base_start + abs(float(event.duration))
            for ve in voice_events:
                ve["start"] = base_start
                ve["end"] = base_end

        _kit_selector = instrument.selector if isinstance(instrument, Kit) else None
        active_uids = slur_voice_uids.setdefault(slur_id, []) if slur_id is not None else None

        # Mid-slur: voice count drops. The dropped voice's most recent event
        # becomes terminal (releaseAfter=true) with dur set so it fires at the
        # transition point.
        if (slur_id is not None and not is_slur_start
                and active_uids is not None and len(active_uids) > len(voice_events)):
            transition_time = (float(event.start)) - (time_offset if animation else 0.0)
            for vi in range(len(voice_events), len(active_uids)):
                uid = active_uids[vi]
                if uid is None:
                    continue
                _mark_terminal(uid, terminal_time=transition_time)
                active_uids[vi] = None
            while active_uids and active_uids[-1] is None:
                active_uids.pop()
        for voice_event in voice_events:
            voice_start = voice_event["start"] - time_offset if animation else voice_event["start"]
            voice_end = voice_event["end"] - time_offset if animation else voice_event["end"]
            voice_dur = max(0.0, voice_end - voice_start)
            voice_index = voice_event["poly_voice_index"]
            voice_pfields = {
                k: v for k, v in voice_event["pfields"].items()
                if k != 'group' and k != _kit_selector
            }

            if not has_gate:
                instrument_id = id(resolved_instrument) if resolved_instrument is not None else None
                sustain_param = sustain_param_cache.get(instrument_id)
                if instrument_id is not None and instrument_id not in sustain_param_cache:
                    sustain_param = None
                    lower_to_key = {k.lower(): k for k in resolved_instrument.pfields.keys()}
                    for param in ('sustaintime', 'releasetime'):
                        if param in lower_to_key:
                            sustain_param = lower_to_key[param]
                            break
                    sustain_param_cache[instrument_id] = sustain_param
                if sustain_param and is_slur_start:
                    end_event = slur_end_events.get(slur_id)
                    if end_event is not None:
                        voice_pfields[sustain_param] = end_event.end - voice_event["start"]

            if normalize_sc_pfields:
                voice_pfields = _normalize_sc_pfields(voice_pfields)

            merged_pfields = _merge_pfields(voice_pfields, extra_pfields)

            if inject_duration:
                merged_pfields = dict(merged_pfields)
                merged_pfields['duration'] = voice_dur

            if is_slur_start:
                slur_uid = uuid4().hex
                new_event = {
                    "type": "new",
                    "id": slur_uid,
                    "defName": def_name,
                    "start": voice_start,
                    "dur": voice_dur,
                    "releaseAfter": False,
                    "pfields": merged_pfields,
                }
                if group is not None:
                    new_event["group"] = group
                events.append(_attach_poly_meta(new_event, voice_event))
                _track_event(slur_uid)
                while len(active_uids) <= voice_index:
                    active_uids.append(None)
                active_uids[voice_index] = slur_uid
                _record(event.node_id, slur_uid, voice_start)
                continue

            if slur_id is not None:
                if voice_index < len(active_uids) and active_uids[voice_index] is not None:
                    target_uid = active_uids[voice_index]
                    set_event = {
                        "type": "set",
                        "id": target_uid,
                        "start": voice_start,
                        "dur": voice_dur,
                        "releaseAfter": False,
                        "pfields": merged_pfields,
                    }
                    events.append(_attach_poly_meta(set_event, voice_event))
                    _track_event(target_uid)
                    _record(event.node_id, target_uid, voice_start)
                else:
                    slur_uid = uuid4().hex
                    new_event = {
                        "type": "new",
                        "id": slur_uid,
                        "defName": def_name,
                        "start": voice_start,
                        "dur": voice_dur,
                        "releaseAfter": False,
                        "pfields": merged_pfields,
                    }
                    if group is not None:
                        new_event["group"] = group
                    events.append(_attach_poly_meta(new_event, voice_event))
                    _track_event(slur_uid)
                    while len(active_uids) <= voice_index:
                        active_uids.append(None)
                    active_uids[voice_index] = slur_uid
                    _record(event.node_id, slur_uid, voice_start)
                continue

            # Non-slur leaf: terminal immediately.
            uid = uuid4().hex
            new_event = {
                "type": "new",
                "id": uid,
                "defName": def_name,
                "start": voice_start,
                "dur": voice_dur,
                "releaseAfter": True,
                "pfields": merged_pfields,
            }
            if group is not None:
                new_event["group"] = group
            events.append(_attach_poly_meta(new_event, voice_event))
            _track_event(uid)
            _record(event.node_id, uid, voice_start)

        # End-of-slur: the most recent event for each still-active uid is the
        # terminal one. Mark releaseAfter=true; dur already reflects this leaf.
        if slur_id is not None and is_slur_end:
            for vi, uid in enumerate(active_uids or []):
                if uid is None:
                    continue
                _mark_terminal(uid)
            if slur_id in slur_voice_uids:
                del slur_voice_uids[slur_id]

    result = sort_sc_assembly_events(events) if sort_output else events
    if return_node_map:
        return result, node_to_event_ids
    return result
