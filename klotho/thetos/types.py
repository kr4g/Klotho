import numpy as np
from typing import Union, List, Tuple, TypeVar, Any

from ..tonos.utils.frequency_conversion import freq_to_midicents, midicents_to_freq
from ..topos.graphs.graphs import Graph
from ..topos.graphs.fields import Field
from ..topos.graphs.trees.trees import Tree
from ..dynatos.expression.dynamics import ampdb, dbamp

T = TypeVar('T', bound='float')
Collection = Union[List[float], Tuple[float, ...], np.ndarray]

class frequency(float):
    def __new__(cls, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            return type(value)(cls(x) for x in value)
        return super().__new__(cls, value)
    
    def to_midicent(self):
        return midicent(freq_to_midicents(float(self)))
    
    def to_midi(self):
        return midi(self.to_midicent() / 100)

class midi(float):
    def __new__(cls, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            return type(value)(cls(x) for x in value)
        return super().__new__(cls, value)
    
    def to_frequency(self):
        return frequency(midicents_to_freq(float(self) * 100))
    
    def to_midicent(self):
        return midicent(float(self) * 100)

class midicent(float):
    def __new__(cls, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            return type(value)(cls(x) for x in value)
        return super().__new__(cls, value)
    
    def to_midi(self):
        return midi(float(self) / 100)
    
    def to_frequency(self):
        return frequency(midicents_to_freq(float(self)))

class cent(float):
    def __new__(cls, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            return type(value)(cls(x) for x in value)
        return super().__new__(cls, value)
    
    def to_frequency_ratio(self):
        return 2.0 ** (float(self) / 1200.0)

class amplitude(float):
    def __new__(cls, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            return type(value)(cls(x) for x in value)
        return super().__new__(cls, value)
    
    def to_decibel(self):
        return decibel(ampdb(float(self)))

class decibel(float):
    def __new__(cls, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            return type(value)(cls(x) for x in value)
        return super().__new__(cls, value)
    
    def to_amplitude(self):
        return amplitude(dbamp(float(self)))

class onset(float):
    def __new__(cls, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            return type(value)(cls(x) for x in value)
        return super().__new__(cls, value)

class duration(float):
    def __new__(cls, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            return type(value)(cls(x) for x in value)
        return super().__new__(cls, value) 