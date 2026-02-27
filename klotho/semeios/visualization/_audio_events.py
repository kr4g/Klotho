from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes


def build_path_audio_events(freqs, dur, amp=None):
    events = []
    for i, freq in enumerate(freqs):
        events.append({
            "start": round(i * dur, 6),
            "duration": round(dur * 0.9, 6),
            "instrument": "synth",
            "pfields": {
                "freq": round(freq, 4),
                "vel": round(single_voice_amplitude(freq, amp), 4),
            },
            "_stepIndex": i,
        })
    return {"events": events, "instruments": {}}


def build_shape_audio_events(freq_groups, dur, arp=False, strum=0, direction='u', amp=None):
    events = []
    current_time = 0.0

    for gi, freqs in enumerate(freq_groups):
        if direction.lower() == 'd':
            freqs = list(reversed(freqs))

        if arp:
            n = len(freqs)
            voice_dur = dur / max(1, n)
            for i, freq in enumerate(freqs):
                events.append({
                    "start": round(current_time + i * voice_dur, 6),
                    "duration": round(voice_dur * 0.9, 6),
                    "instrument": "synth",
                    "pfields": {
                        "freq": round(freq, 4),
                        "vel": round(single_voice_amplitude(freq, amp), 4),
                    },
                    "_stepIndex": gi,
                })
            current_time += dur
        else:
            num_notes = len(freqs)
            voice_amps = compute_voice_amplitudes(freqs, amp)
            strum_val = max(0, min(1, strum))
            for i, freq in enumerate(freqs):
                start_offset = (strum_val * dur * i) / num_notes if num_notes > 1 else 0
                events.append({
                    "start": round(current_time + start_offset, 6),
                    "duration": round((dur * 0.95) - start_offset, 6),
                    "instrument": "synth",
                    "pfields": {
                        "freq": round(freq, 4),
                        "vel": round(voice_amps[i], 4),
                    },
                    "_stepIndex": gi,
                })
            current_time += dur

    return {"events": events, "instruments": {}}
