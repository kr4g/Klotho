"""
Thetos: A specialized module for working with musical parameters and instruments.

From the Greek "θέτος" (thetos) meaning "placed" or "set," this module
deals with the placement and configuration of musical parameters and instruments.
"""

from . import instruments
from . import parameters
from . import composition

from .parameters import ParameterTree, ParameterField
from .instruments import Instrument, Effect, SynthDefInstrument, SynthDefFX, MidiInstrument, ToneInstrument, Kit, SynthDefKit, Ensemble
from .composition import CompositionalUnit, Parametron, Score
from .types import frequency, cent, midicent, midi, amplitude, decibel, real_onset, real_duration, metric_onset, metric_duration

__all__ = [
    'instruments',
    'parameters',
    'composition',
    'ParameterTree',
    'ParameterField',
    'Instrument',
    'Effect',
    'SynthDefFX',
    'Kit',
    'SynthDefKit',
    'Ensemble',
    'CompositionalUnit',
    'Parametron',
    'Score',
    'frequency', 
    'cent', 
    'midicent', 
    'midi',
    'amplitude', 
    'decibel', 
    'real_onset', 
    'real_duration',
    'metric_onset',
    'metric_duration',
] 