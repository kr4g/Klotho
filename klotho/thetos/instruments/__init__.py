from .base import Instrument, InsertBase
from .synthdef import SynthDefInstrument, Insert
from .midi import MidiInstrument
from .tone import ToneInstrument

__all__ = ['Instrument', 'InsertBase', 'SynthDefInstrument', 'Insert', 'MidiInstrument', 'ToneInstrument']