import json
from pathlib import Path

from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes
from klotho.utils.playback._converter_base import iter_group_sequence


_SS_MANIFEST_PATH = Path(__file__).resolve().parent / "supersonic" / "assets" / "manifest.json"
_SS_RELEASE_MODE_CACHE = None


def normalize_animation_payload_for_engine(audio_payload, engine):
    return audio_payload


def _release_mode_for_synth(def_name):
    global _SS_RELEASE_MODE_CACHE
    if _SS_RELEASE_MODE_CACHE is None:
        _SS_RELEASE_MODE_CACHE = {}
        try:
            data = json.loads(_SS_MANIFEST_PATH.read_text())
            synths = data.get("synths", {})
            for name, meta in synths.items():
                mode = (meta.get("releaseMode") or "gate").lower()
                _SS_RELEASE_MODE_CACHE[name] = mode if mode in ("gate", "free") else "gate"
        except Exception:
            _SS_RELEASE_MODE_CACHE = {}
    return _SS_RELEASE_MODE_CACHE.get(def_name, "gate")


def _synth_needs_release(def_name):
    return _release_mode_for_synth(def_name) == "gate"


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


def _tone_payload_from_plan(plan, extra_pfields=None, pause=0.0):
    events = []
    for ev in plan:
        pfields = _merged_pfields(
            {"freq": ev["freq"], "vel": ev["amp"]},
            extra_pfields,
            protected={"freq"},
        )
        events.append({
            "start": ev["start"],
            "duration": ev["duration"],
            "instrument": ev["instrument"],
            "pfields": pfields,
            "_stepIndex": ev["step"],
        })
    return {"events": events, "instruments": {}, "_engine": "tone", "pause": max(0.0, float(pause or 0.0))}


def _supersonic_payload_from_plan(plan, extra_pfields=None, pause=0.0):
    events = []
    counter = 0

    for ev in plan:
        uid = f"a{counter}"
        counter += 1
        synth = "kl_kicktone" if ev["instrument"] == "membrane" else "kl_tri"

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
            "pfields": pfields,
            "_stepIndex": ev["step"],
            "_animate": True,
        })

        if _synth_needs_release(synth):
            events.append({
                "type": "release",
                "id": uid,
                "start": ev["start"] + ev["duration"],
                "_stepIndex": ev["step"],
                "_animate": True,
            })

    events.sort(key=lambda e: e["start"])
    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(events, animation=True)
    return {"events": events, "_engine": "supersonic", "pause": max(0.0, float(pause or 0.0))}


def build_path_audio_events(freqs, dur, amp=None):
    plan = _plan_from_path(freqs, dur, amp=amp, pause=0.0)
    return _tone_payload_from_plan(plan, extra_pfields=None, pause=0.0)


def build_shape_audio_events(freq_groups, dur, arp=False, strum=0, direction='u', amp=None):
    plan = _plan_from_shape(freq_groups, dur, arp=arp, strum=strum, direction=direction, amp=amp, pause=0.25)
    return _tone_payload_from_plan(plan, extra_pfields=None, pause=0.25)


def build_path_engine_payload(freqs, dur, engine, amp=None, extra_pfields=None, pause=0.0):
    plan = _plan_from_path(freqs, dur, amp=amp, pause=pause)
    if engine == "supersonic":
        return _supersonic_payload_from_plan(plan, extra_pfields=extra_pfields, pause=pause)
    return _tone_payload_from_plan(plan, extra_pfields=extra_pfields, pause=pause)


def build_shape_engine_payload(freq_groups, dur, engine, arp=False, strum=0, direction='u', amp=None, extra_pfields=None, pause=0.25):
    plan = _plan_from_shape(freq_groups, dur, arp=arp, strum=strum, direction=direction, amp=amp, pause=pause)
    if engine == "supersonic":
        return _supersonic_payload_from_plan(plan, extra_pfields=extra_pfields, pause=pause)
    return _tone_payload_from_plan(plan, extra_pfields=extra_pfields, pause=pause)
