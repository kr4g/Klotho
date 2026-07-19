from uuid import uuid4

from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.thetos.instruments.base import Effect
from klotho.thetos.instruments.base import Kit
from klotho.utils.playback._amplitude import single_voice_amplitude
from klotho.utils.playback._converter_base import (
    _merge_pfields,
    lower_event_ir_to_voice_events,
    freq_to_midi,
    coerce_sc_pfield_values,
)

SC_EVENT_PRIORITY = {'new': 0, 'set': 1, 'release': 2}

# Once-per-process dedupe for the "unknown pfield / unknown SynthDef" FYI
# notes printed during lowering. The engine still plays; these are purely
# informational.
_WARNED_UNKNOWN_PFIELDS: set = set()
_WARNED_UNKNOWN_DEFNAMES: set = set()

# Keys legitimately present in event pfields that are not SynthDef controls
# (synthetic/engine-level), so the unknown-pfield FYI must skip them.
_PFIELD_WARN_EXEMPT = frozenset({'note', 'out', 'gate', 'dur', 'duration'})


def _warn_unknown_pfields(def_name, pfields, manifest):
    """Print a one-line FYI for pfields the target SynthDef does not declare.

    Deduped per ``(defName, key)`` for the life of the process. Infra defs
    (``__``-prefixed) and empty names are skipped. An unknown defName gets
    its own one-time FYI instead of per-key checks.
    """
    if not def_name or def_name.startswith('__'):
        return
    controls = manifest.get(def_name)
    if controls is None:
        if def_name not in _WARNED_UNKNOWN_DEFNAMES:
            _WARNED_UNKNOWN_DEFNAMES.add(def_name)
            print(
                f"Klotho FYI: SynthDef '{def_name}' is not in the manifest; "
                f"its pfields cannot be checked (playback continues)."
            )
        return
    for key in pfields:
        if key in _PFIELD_WARN_EXEMPT or key in controls:
            continue
        tag = (def_name, key)
        if tag in _WARNED_UNKNOWN_PFIELDS:
            continue
        _WARNED_UNKNOWN_PFIELDS.add(tag)
        print(
            f"Klotho FYI: SynthDef '{def_name}' has no control '{key}'; "
            f"the value will be ignored during playback."
        )


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


def _resolve_instrument_controls(instrument, def_name, manifest):
    """Resolve the control set and gating for an event's instrument.

    Instrument objects carry their own pfields, which may deliberately
    drop controls (e.g. a sampler built with ``duration=None``). String
    and ``None`` instruments have no pfields, so their controls come from
    the manifest entry for the resolved defName (which includes
    runtime-registered Supriya defs).

    Returns ``(controls, has_gate, from_manifest)``. ``from_manifest``
    marks instruments that contribute no default pfields to the event, so
    any ``duration``/``dur`` already on the event is user-set and must
    win over injection. An unknown defName yields ``({}, True, False)``,
    preserving the legacy no-injection behavior.
    """
    pfields = getattr(instrument, 'pfields', None)
    if pfields is not None:
        return pfields, bool(getattr(instrument, 'has_gate', 'gate' in pfields)), False
    controls = manifest.get(def_name) if def_name else None
    if controls is None:
        return {}, True, False
    return controls, 'gate' in controls, True


def _duration_inject_key(controls, has_gate, from_manifest, event_pfields):
    """Pfield to fill with the event's real duration, or ``None``.

    A synth declaring a control named exactly ``duration`` always gets
    the event duration (e.g. one-shots that self-free via an
    ``Env.linen(0, duration, ...)`` envelope, so their internal envelope
    tracks the rhythmic value). A ``dur`` control gets it only on
    non-gated synths.
    """
    if 'duration' in controls:
        key = 'duration'
    elif (not has_gate) and 'dur' in controls:
        key = 'dur'
    else:
        return None
    if from_manifest and key in event_pfields:
        return None
    return key


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
    use_absolute_time=False,
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

    if extra_pfields:
        extra_pfields = coerce_sc_pfield_values(extra_pfields)

    from klotho.thetos.instruments._shared import load_ss_manifest
    manifest = load_ss_manifest()

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
    if animation and not use_absolute_time:
        time_offset = min((ev.start for ev in events_iterable), default=0.0)

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
                voice_pfields = coerce_sc_pfield_values(voice_pfields)
                _warn_unknown_pfields(
                    getattr(instrument, 'defName', None), voice_pfields, manifest
                )
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
        kit_tuple_selector = False
        if isinstance(instrument, Kit):
            selector_val = event.get_pfield(instrument.selector)
            kit_tuple_selector = isinstance(selector_val, tuple)
            resolved_instrument = instrument._resolve(selector_val)

        def_name = _resolve_event_synth(resolved_instrument, default_synth)
        controls, has_gate, controls_from_manifest = _resolve_instrument_controls(
            resolved_instrument, def_name, manifest
        )
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

            # A tuple selector expands per voice, so Kit members (and hence
            # defName/gating) must be re-resolved from the voice's own
            # selector value, not once per event.
            voice_resolved = resolved_instrument
            voice_def_name = def_name
            voice_controls = controls
            voice_has_gate = has_gate
            voice_from_manifest = controls_from_manifest
            if _kit_selector is not None:
                voice_sel = voice_event["pfields"].get(_kit_selector)
                if not isinstance(voice_sel, tuple):
                    voice_resolved = instrument._resolve(voice_sel)
                    voice_def_name = _resolve_event_synth(voice_resolved, default_synth)
                    voice_controls, voice_has_gate, voice_from_manifest = (
                        _resolve_instrument_controls(voice_resolved, voice_def_name, manifest)
                    )

            voice_pfields = {
                k: v for k, v in voice_event["pfields"].items()
                if k != 'group' and k != _kit_selector
            }

            # A tuple selector merges defaults across members whose key
            # sets may differ; keep only what THIS voice's member (or the
            # engine) understands so e.g. a gated member's `gate` never
            # leaks onto a one-shot sampler voice.
            if kit_tuple_selector and voice_resolved is not None:
                member_keys = set(voice_controls.keys())
                voice_pfields = {
                    k: v for k, v in voice_pfields.items()
                    if k in member_keys or k in ('note', 'out')
                }

            if not voice_has_gate:
                instrument_id = id(voice_resolved) if voice_resolved is not None else None
                sustain_param = sustain_param_cache.get(instrument_id)
                if instrument_id is not None and instrument_id not in sustain_param_cache:
                    sustain_param = None
                    lower_to_key = {k.lower(): k for k in voice_controls.keys()}
                    for param in ('sustaintime', 'releasetime'):
                        if param in lower_to_key:
                            sustain_param = lower_to_key[param]
                            break
                    sustain_param_cache[instrument_id] = sustain_param
                if sustain_param and is_slur_start:
                    end_event = slur_end_events.get(slur_id)
                    if end_event is not None:
                        voice_pfields[sustain_param] = end_event.end - voice_event["start"]

            voice_pfields = coerce_sc_pfield_values(voice_pfields)
            _warn_unknown_pfields(voice_def_name, voice_pfields, manifest)

            if normalize_sc_pfields:
                voice_pfields = _normalize_sc_pfields(voice_pfields)

            merged_pfields = _merge_pfields(voice_pfields, extra_pfields)

            inject_key = _duration_inject_key(
                voice_controls, voice_has_gate, voice_from_manifest, voice_pfields
            )
            if inject_key is not None:
                merged_pfields = dict(merged_pfields)
                merged_pfields[inject_key] = voice_dur

            if is_slur_start:
                slur_uid = uuid4().hex
                new_event = {
                    "type": "new",
                    "id": slur_uid,
                    "defName": voice_def_name,
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
                        "defName": voice_def_name,
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
                "defName": voice_def_name,
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
