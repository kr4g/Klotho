from enum import Enum, EnumMeta
import numpy as np

class DirectValueEnumMeta(EnumMeta):
  def __getattribute__(cls, name):
    member = super().__getattribute__(name)
    if isinstance(member, cls):
      return member.value
    return member

class MinMaxEnum(Enum):
    @property
    def min(self):
        return self.value[0]

    @property
    def max(self):
        return self.value[1]
    
    def __repr__(self):
        return repr(self.value)
    
    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return (self.min * other, self.max * other)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)
    
    def __call__(self):
        return np.random.uniform(self.min, self.max)
