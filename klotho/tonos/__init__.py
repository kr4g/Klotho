'''
--------------------------------------------------------------------------------------

`Tonos` is a specialized module for working with pitch and frequency in music.

In Ancient Greek, "τόνος" (tonos) originally meant "tension," "tone," or "pitch." This 
word has contributed to various terms in modern languages, especially in the fields of 
music, literature, and medicine.

In music, "tonos" is the origin of the word "tone," which is used to describe both a
musical interval and a musical quality. That is, both the phonemenon of pitch and the
perception of "tone-quality" also known as *timbre*.

"Any tone can succeed any other tone, any tone can sound simultaneously with any other
tone or tones, and any group of tones can be followed by any other group of tones, just
as any degree of tension or nuance can occur in any medium under and kind of stress or
duration.  Successful projection will depend upon the contextual and formal conditions
that prevail, and upon the skill and the soul of the composer." 
  — Vincent Persichetti, from "Twentieth-Century Harmony: Creative Aspects and Practice", 
    Chapter One: Intervals

--------------------------------------------------------------------------------------
'''
from . import utils
from . import systems
from . import scales
from . import chords
from . import motives
from . import pitch

combination_product_sets = systems.combination_product_sets
harmonic_trees = systems.harmonic_trees

from .pitch import Pitch, PitchCollection, EquaveCyclicCollection, AddressedPitchCollection
from .scales import Scale
from .chords import Chord, Sonority, ChordSequence
from .motives import Motive
from .systems.combination_product_sets import CombinationProductSet, Hexany, Dekany, Pentadekany, Eikosany
from .systems.harmonic_trees import HarmonicTree
from .systems.harmonic_trees.spectrum import Spectrum
from .systems.tone_lattices import ToneLattice
from .scales.scale import AddressedScale
from .chords.chord import AddressedChord, AddressedSonority

from .utils.intervals import ratio_to_cents, cents_to_ratio, cents_to_setclass, ratio_to_setclass
from .utils.intervals import split_interval, harmonic_mean, arithmetic_mean, logarithmic_distance
from .utils.intervals import interval_cost, n_tet, ratios_n_tet

from .utils.frequency_conversion import freq_to_midicents, midicents_to_freq
from .utils.frequency_conversion import midicents_to_pitchclass, freq_to_pitchclass, pitchclass_to_freq
from .utils.frequency_conversion import A4_Hz, A4_MIDI, PITCH_CLASSES

from .utils.harmonics import partial_to_fundamental, first_equave

from .utils.interval_normalization import equave_reduce, reduce_interval, reduce_interval_relative
from .utils.interval_normalization import reduce_sequence_relative, fold_interval, reduce_freq

__all__ = [
    # Modules
    'utils',
    'systems',
    'scales',
    'chords',
    'motives',
    'pitch',
    'combination_product_sets',
    'harmonic_trees',
    
    # Classes
    'Pitch',
    'PitchCollection', 
    'EquaveCyclicCollection',
    'AddressedPitchCollection',
    'Scale',
    'Chord',
    'Sonority',
    'ChordSequence',
    'Motive',
    'CombinationProductSet',
    'Hexany',
    'Dekany',
    'Pentadekany',
    'Eikosany',
    'HarmonicTree',
    'Spectrum',
    'ToneLattice',
    'AddressedScale',
    'AddressedChord',
    'AddressedSonority',
    
    # Interval utilities
    'ratio_to_cents',
    'cents_to_ratio',
    'cents_to_setclass',
    'ratio_to_setclass',
    'split_interval',
    'harmonic_mean',
    'arithmetic_mean',
    'logarithmic_distance',
    'interval_cost',
    'n_tet',
    'ratios_n_tet',
    
    # Frequency conversion utilities
    'freq_to_midicents',
    'midicents_to_freq',
    'midicents_to_pitchclass',
    'freq_to_pitchclass',
    'pitchclass_to_freq',
    'A4_Hz',
    'A4_MIDI',
    'PITCH_CLASSES',
    
    # Harmonics utilities
    'partial_to_fundamental',
    'first_equave',
    
    # Interval normalization utilities
    'equave_reduce',
    'reduce_interval',
    'reduce_interval_relative',
    'reduce_sequence_relative',
    'fold_interval',
    'reduce_freq',
]
