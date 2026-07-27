from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes
from klotho.utils.playback._converter_base import iter_group_sequence


def _plan_from_path(freqs, dur, amp=None, pause=0.0):
    plan = []
    cursor = 0.0
    for i, freq in enumerate(freqs):
        plan.append({
            "start": round(cursor, 6),
            "duration": dur,
            "instrument": "synth",
            "freq": round(freq, 4),
            "amp": round(single_voice_amplitude(freq, amp), 4),
            "step": i,
        })
        cursor += dur + max(0.0, pause)
    return plan


def _plan_from_shape(freq_groups, dur, arp=False, strum=0, direction='u', amp=None, pause=0.25):
    plan = []
    group_voice_amps = [
        compute_voice_amplitudes(group, amp) for group in freq_groups
    ]
    for gi, vi, start_time, voice_dur, freq in iter_group_sequence(
        freq_groups, dur, arp=arp, strum=strum, direction=direction, pause=pause
    ):
        amp_value = single_voice_amplitude(freq, amp) if arp else group_voice_amps[gi][vi]
        plan.append({
            "start": round(start_time, 6),
            "duration": voice_dur,
            "instrument": "synth",
            "freq": round(freq, 4),
            "amp": round(amp_value, 4),
            "step": gi,
        })

    return plan


def _merged_pfields(base, extra, protected):
    merged = dict(extra or {})
    merged.update(base)
    for key in protected:
        if key in base:
            merged[key] = base[key]
    return merged


def _supersonic_payload_from_plan(plan, extra_pfields=None, pause=0.0, def_name=None):
    events = []
    counter = 0

    for ev in plan:
        uid = f"a{counter}"
        counter += 1
        synth = "kl_kicktone" if ev["instrument"] == "membrane" else (def_name or "kl_tri")

        if ev["instrument"] == "membrane":
            pfields = _merged_pfields(
                {"baseFreq": ev["freq"], "amp": ev["amp"], "dur": ev["duration"]},
                extra_pfields,
                protected={"baseFreq", "dur"},
            )
        else:
            pfields = _merged_pfields(
                {"freq": ev["freq"], "amp": ev["amp"]},
                extra_pfields,
                protected={"freq"},
            )

        events.append({
            "type": "new",
            "id": uid,
            "defName": synth,
            "start": ev["start"],
            "dur": ev["duration"],
            "releaseAfter": True,
            "pfields": pfields,
            "_stepIndex": ev["step"],
            "_animate": True,
        })

    events.sort(key=lambda e: e["start"])
    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(events, animation=True)
    return {"events": events, "_engine": "supersonic", "pause": max(0.0, float(pause or 0.0))}


def build_path_payload(freqs, dur, amp=None, extra_pfields=None, pause=0.0, def_name=None):
    plan = _plan_from_path(freqs, dur, amp=amp, pause=pause)
    return _supersonic_payload_from_plan(plan, extra_pfields=extra_pfields, pause=pause, def_name=def_name)


def build_shape_payload(freq_groups, dur, arp=False, strum=0, direction='u', amp=None, extra_pfields=None, pause=0.25, def_name=None):
    plan = _plan_from_shape(freq_groups, dur, arp=arp, strum=strum, direction=direction, amp=amp, pause=pause)
    return _supersonic_payload_from_plan(plan, extra_pfields=extra_pfields, pause=pause, def_name=def_name)
