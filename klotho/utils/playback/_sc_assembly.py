from uuid import uuid4

from klotho.thetos.instruments.instrument import SynthDefInstrument
from klotho.utils.playback._amplitude import single_voice_amplitude
from klotho.utils.playback._converter_base import (
    _merge_pfields,
    lower_event_ir_to_voice_events,
    freq_to_midi,
)

GATED_ENV_TYPES = ('sustained', 'sus', 'asr', 'adsr', '')
UNGATED_ENV_TYPES = ('standard', 'std', 'perc', 'linen')
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


def _resolve_event_synth(event, instrument, default_synth):
    explicit = event.get_parameter('synth_name') or event.get_parameter('synthName')
    if explicit:
        return explicit
    if isinstance(instrument, SynthDefInstrument):
        return getattr(instrument, 'synth_name', None) or getattr(instrument, 'name', None) or default_synth
    if instrument is not None:
        return getattr(instrument, 'synth_name', None) or getattr(instrument, 'name', None) or default_synth
    return default_synth


def _env_type(instrument):
    if instrument is None:
        return ''
    return (getattr(instrument, 'env_type', '') or '').lower()


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


def lower_compositional_ir_to_sc_assembly(
    obj,
    extra_pfields=None,
    animation=False,
    default_synth='sonic-pi-beep',
    include_ungated_release=True,
    normalize_sc_pfields=True,
    sort_output=True,
):
    events = []
    leaf_nodes = obj._rt.leaf_nodes if animation else None
    node_to_step = ({nid: idx for idx, nid in enumerate(leaf_nodes)} if animation else None)
    events_iterable = tuple(obj)
    slur_end_events = {}
    sustain_param_cache = {}

    for event in events_iterable:
        if event.is_rest:
            continue
        slur_id = event.get_parameter('_slur_id')
        if slur_id is None:
            continue
        if event.get_parameter('_slur_end', 0):
            slur_end_events[slur_id] = event

    time_offset = 0.0
    if animation:
        sounding = [ev for ev in events_iterable if not ev.is_rest]
        time_offset = min(ev.start for ev in sounding) if sounding else 0.0

    slur_uids = {}

    for event in events_iterable:
        step_idx = node_to_step.get(event.node_id, None) if animation else None
        if event.is_rest:
            if animation:
                rest = {
                    "type": "new",
                    "id": uuid4().hex,
                    "synthName": "__rest__",
                    "start": event.start - time_offset,
                    "pfields": {},
                }
                if step_idx is not None:
                    rest["_stepIndex"] = step_idx
                events.append(rest)
            continue

        instrument = obj.get_instrument(event.node_id)
        synth_name = _resolve_event_synth(event, instrument, default_synth)
        env_type = _env_type(instrument)
        is_gated = env_type in GATED_ENV_TYPES
        is_ungated = env_type in UNGATED_ENV_TYPES
        group = event.get_parameter('group')
        is_slur_start = event.get_parameter('_slur_start', 0)
        is_slur_end = event.get_parameter('_slur_end', 0)
        slur_id = event.get_parameter('_slur_id')
        voice_events = lower_event_ir_to_voice_events(event, step_index=step_idx)

        for voice_event in voice_events:
            voice_start = voice_event["start"] - time_offset if animation else voice_event["start"]
            voice_end = voice_event["end"] - time_offset if animation else voice_event["end"]
            voice_pfields = {
                k: v for k, v in voice_event["pfields"].items()
                if k not in ('synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id')
            }

            if is_ungated:
                instrument_id = id(instrument) if instrument is not None else None
                sustain_param = sustain_param_cache.get(instrument_id)
                if instrument_id is not None and instrument_id not in sustain_param_cache:
                    sustain_param = None
                    lower_to_key = {k.lower(): k for k in instrument.keys()}
                    for param in ('sustaintime', 'releasetime'):
                        if param in lower_to_key:
                            sustain_param = lower_to_key[param]
                            break
                    sustain_param_cache[instrument_id] = sustain_param
                if sustain_param and is_slur_start:
                    end_event = slur_end_events.get(slur_id)
                    if end_event is not None:
                        voice_pfields[sustain_param] = end_event.end - event.start

            if normalize_sc_pfields:
                voice_pfields = _normalize_sc_pfields(voice_pfields)

            merged_pfields = _merge_pfields(voice_pfields, extra_pfields)
            voice_slur_key = (slur_id, voice_event["poly_voice_index"])

            if is_slur_start:
                slur_uid = uuid4().hex
                new_event = {
                    "type": "new",
                    "id": slur_uid,
                    "synthName": synth_name,
                    "start": voice_start,
                    "pfields": merged_pfields,
                }
                if group is not None:
                    new_event["group"] = group
                events.append(_attach_poly_meta(new_event, voice_event))
                slur_uids[voice_slur_key] = slur_uid
                if is_slur_end and is_gated:
                    release_event = {
                        "type": "release",
                        "id": slur_uid,
                        "start": voice_end,
                    }
                    events.append(_attach_poly_meta(release_event, voice_event))
                continue

            if slur_id is not None and (voice_slur_key in slur_uids or (slur_id, 0) in slur_uids):
                target_uid = slur_uids.get(voice_slur_key, slur_uids.get((slur_id, 0)))
                set_event = {
                    "type": "set",
                    "id": target_uid,
                    "start": voice_start,
                    "pfields": merged_pfields,
                }
                events.append(_attach_poly_meta(set_event, voice_event))
                if is_slur_end and is_gated:
                    release_event = {
                        "type": "release",
                        "id": target_uid,
                        "start": voice_end,
                    }
                    events.append(_attach_poly_meta(release_event, voice_event))
                continue

            uid = uuid4().hex
            new_event = {
                "type": "new",
                "id": uid,
                "synthName": synth_name,
                "start": voice_start,
                "pfields": merged_pfields,
            }
            if group is not None:
                new_event["group"] = group
            events.append(_attach_poly_meta(new_event, voice_event))

            if is_gated or include_ungated_release:
                release_event = {
                    "type": "release",
                    "id": uid,
                    "start": voice_end,
                }
                events.append(_attach_poly_meta(release_event, voice_event))

    return sort_sc_assembly_events(events) if sort_output else events
