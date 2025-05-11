# Klotho/klotho/tonos/__init__.py
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

from .pitch import Pitch
from .pitch_collection import PitchCollection, AddressedPitchCollection
from .scales import Scale
from .chords import Chord
from .systems.combination_product_sets import CombinationProductSet
from .systems.harmonic_trees import HarmonicTree
from .systems.harmonic_trees.spectrum import Spectrum

__all__ = [
    'Pitch',
    'PitchCollection', 
    'AddressedPitchCollection',
    'Scale',
    'Chord',
    'CombinationProductSet',
    'HarmonicTree',
    'Spectrum',
]

__version__ = '2.0.0'
