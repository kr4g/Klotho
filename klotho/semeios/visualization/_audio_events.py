from klotho.utils.playback.animation_events import (
    build_path_audio_events as _build_path_audio_events,
    build_shape_audio_events as _build_shape_audio_events,
)


def build_path_audio_events(freqs, dur, amp=None):
    return _build_path_audio_events(freqs, dur, amp=amp)


def build_shape_audio_events(freq_groups, dur, arp=False, strum=0, direction='u', amp=None):
    return _build_shape_audio_events(freq_groups, dur, arp=arp, strum=strum, direction=direction, amp=amp)
