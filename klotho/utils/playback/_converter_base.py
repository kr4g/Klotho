import math
from uuid import uuid4

from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, ChordSequence
from klotho.tonos.scales.scale import Scale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes

DEFAULT_NOTE_DURATION = 0.5
DEFAULT_CHORD_DURATION = 2.0
DEFAULT_SPECTRUM_DURATION = 3.0
DEFAULT_DRUM_FREQ = 110.0

KNOWN_KWARGS = frozenset({
    'dur', 'duration', 'arp', 'strum', 'dir', 'direction',
    'equaves', 'beat', 'bpm', 'mode', 'amp', 'ring_time', 'pause',
})


def freq_to_midi(freq):
    if not isinstance(freq, (int, float)) or freq <= 0:
        return 69.0
    return 69.0 + 12.0 * math.log2(freq / 440.0)


def _get_addressed_collection(obj):
    if hasattr(obj, 'freq'):
        return obj
    if hasattr(obj, 'is_instanced') and obj.is_instanced:
        return obj
    if hasattr(obj, 'is_relative') and not obj.is_relative:
        return obj
    return obj.root("C4")


def _merge_pfields(base, extra):
    if not extra:
        return base
    merged = dict(extra)
    merged.update(base)
    return merged


def scale_pitch_sequence(obj, equaves=1):
    addressed = _get_addressed_collection(obj)
    if equaves == 0:
        equaves = 1
    scale_len = len(addressed)
    abs_equaves = abs(equaves)
    going_up = equaves > 0

    all_pitches = []
    if going_up:
        for idx in range(abs_equaves * scale_len + 1):
            all_pitches.append(addressed[idx])
        pitches_down = list(reversed(all_pitches[:-1]))
        all_pitches = all_pitches + pitches_down
    else:
        for i in range(abs_equaves * scale_len + 1):
            all_pitches.append(addressed[-i])
        pitches_up = list(reversed(all_pitches[:-1]))
        all_pitches = all_pitches + pitches_up
    return all_pitches


def extract_convert_kwargs(kwargs):
    extra = {k: v for k, v in kwargs.items() if k not in KNOWN_KWARGS}
    return {
        'duration': kwargs.get('dur', kwargs.get('duration', None)),
        'arp': kwargs.get('arp', False),
        'mode': kwargs.get('mode', None),
        'strum': kwargs.get('strum', 0),
        'direction': kwargs.get('dir', 'u'),
        'equaves': kwargs.get('equaves', 1),
        'beat': kwargs.get('beat', None),
        'bpm': kwargs.get('bpm', None),
        'amp': kwargs.get('amp', None),
        'pause': kwargs.get('pause', None),
        'extra_pfields': extra if extra else None,
    }


PERC_ATTACK = 0.005
PERC_BODY_RATIO = 1 / 3


def perc_env_pfields(dur):
    body = dur * PERC_BODY_RATIO
    attack = min(PERC_ATTACK, body * 0.5)
    return {
        "attack": attack,
        "decay": 0,
        "sustain": max(0, body - attack),
        "release": max(0, dur - body),
    }


def _is_tuple_value(value):
    return isinstance(value, tuple) and len(value) > 0


def _normalized_strum_value(raw_strum):
    if not isinstance(raw_strum, (int, float)):
        return 0.0
    return max(-1.0, min(1.0, float(raw_strum)))


def lower_poly_pfields_to_voices(pfields):
    tuple_fields = {k: v for k, v in pfields.items() if _is_tuple_value(v)}
    if not tuple_fields:
        return [dict(pfields)], False

    voice_count = max(len(v) for v in tuple_fields.values())
    expanded = []
    for voice_index in range(voice_count):
        voice_pfields = {}
        for key, value in pfields.items():
            if key in tuple_fields:
                seq = tuple_fields[key]
                voice_pfields[key] = seq[voice_index % len(seq)]
            else:
                voice_pfields[key] = value
        expanded.append(voice_pfields)
    return expanded, True


def lower_event_ir_to_voice_events(event, step_index=None):
    base_pfields = dict(event.pfields)
    expanded_pfields, tuple_expanded = lower_poly_pfields_to_voices(base_pfields)
    voice_count = len(expanded_pfields)
    base_start = float(event.start)
    duration = abs(float(event.duration))
    mfields = event.mfields if hasattr(event, "mfields") else {}
    strum_raw = mfields.get("strum", 0.0)
    strum_value = _normalized_strum_value(strum_raw)
    apply_strum = tuple_expanded and voice_count > 1 and strum_value != 0.0
    logical_step_id = uuid4().hex
    voices = []

    for voice_index, voice_pfields in enumerate(expanded_pfields):
        if apply_strum:
            order_index = voice_index if strum_value >= 0 else (voice_count - 1 - voice_index)
            start_offset = (abs(strum_value) * duration * order_index) / voice_count
            is_leader = order_index == 0
        else:
            start_offset = 0.0
            is_leader = voice_index == 0

        voices.append({
            "node_id": event.node_id,
            "start": base_start + start_offset,
            "duration": max(0.0, duration - start_offset),
            "end": (base_start + start_offset) + max(0.0, duration - start_offset),
            "pfields": voice_pfields,
            "mfields": dict(mfields),
            "step_index": step_index,
            "poly_group_id": logical_step_id,
            "logical_step_id": logical_step_id,
            "poly_voice_index": voice_index,
            "poly_voice_count": voice_count,
            "poly_is_leader": is_leader,
            "animate": bool(is_leader),
            "tuple_expanded": tuple_expanded,
        })

    return voices


def iter_group_sequence(groups, dur, arp=False, strum=0, direction='u', pause=0.0):
    current_time = 0.0
    for gi, group in enumerate(groups):
        values = list(group)
        if direction.lower() == 'd':
            values = list(reversed(values))

        if arp:
            n = len(values)
            voice_dur = dur / max(1, n)
            for i, value in enumerate(values):
                yield gi, i, current_time + i * voice_dur, voice_dur, value
        else:
            strum_val = max(0, min(1, strum))
            num = len(values)
            for i, value in enumerate(values):
                start_offset = (strum_val * dur * i) / num if num > 1 else 0
                yield gi, i, current_time + start_offset, dur - start_offset, value

        current_time += dur + max(0.0, pause)
