import math

from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, Sonority, ChordSequence
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
    'equaves', 'beat', 'bpm', 'mode', 'amp', 'ring_time',
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
