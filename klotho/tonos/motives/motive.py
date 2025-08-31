import numpy as np
from typing import Union, List, Sequence, overload
from collections.abc import Iterable

class Motive:
    """
    A musical motive represented as a sequence of integer indices.
    
    Motive provides arithmetic operations that enable transposition and combination
    of melodic patterns. It behaves like a numpy array for mathematical operations
    but ensures all elements remain standard Python integers.
    
    Args:
        values: Sequence of integers representing the motive
        
    Examples:
        >>> motive = Motive([6, 2, 4, 0])
        >>> motive + [0, 3, 1, -7, -3, 7]  # Transpose by each value
        Motive([6, 2, 4, 0, 9, 5, 7, 3, 7, 3, 5, 1, -1, -5, -3, -7, 3, -1, 1, -3, 13, 9, 11, 7])
        
        >>> [1, -1, 0] + motive  # Add each motive value to the list
        Motive([7, 1, 3, -1, 1, -3, -1, -5, 4, 0, 2, -2])
        
        >>> motive * 2  # Scalar multiplication
        Motive([12, 4, 8, 0])
        
        >>> motive + 1  # Scalar addition (transpose)
        Motive([7, 3, 5, 1])
    """
    
    def __init__(self, values: Union[List[int], Sequence[int], np.ndarray, 'Motive']):
        if isinstance(values, Motive):
            self._values = values._values.copy()
        elif isinstance(values, np.ndarray):
            self._values = [int(v) for v in values.flatten()]
        elif isinstance(values, (list, tuple)):
            self._values = [int(v) for v in values]
        else:
            raise TypeError("Motive values must be a sequence of integers")
    
    @property
    def values(self) -> List[int]:
        """Return the motive values as a list of integers."""
        return self._values.copy()
    
    def __len__(self) -> int:
        return len(self._values)
    
    def __getitem__(self, index: Union[int, slice, Sequence[int]]) -> Union[int, 'Motive']:
        if isinstance(index, slice):
            return Motive(self._values[index])
        elif isinstance(index, int):
            return self._values[index]
        elif hasattr(index, '__iter__') and not isinstance(index, str):
            return Motive([self._values[int(i)] for i in index])
        else:
            raise TypeError("Index must be an integer, slice, or sequence of integers")
    
    def __iter__(self):
        return iter(self._values)
    
    def __add__(self, other: Union[int, List[int], Sequence[int], np.ndarray, 'Motive']) -> 'Motive':
        if isinstance(other, (int, float)):
            return Motive([v + int(other) for v in self._values])
        elif isinstance(other, (list, tuple, np.ndarray, Motive)):
            if isinstance(other, Motive):
                other_values = other._values
            elif isinstance(other, np.ndarray):
                other_values = [int(v) for v in other.flatten()]
            else:
                other_values = [int(v) for v in other]
            
            result = []
            for transpose in other_values:
                result.extend([v + transpose for v in self._values])
            return Motive(result)
        else:
            return NotImplemented
    
    def __radd__(self, other: Union[int, List[int], Sequence[int], np.ndarray]) -> 'Motive':
        if isinstance(other, (int, float)):
            return Motive([int(other) + v for v in self._values])
        elif isinstance(other, (list, tuple, np.ndarray)):
            if isinstance(other, np.ndarray):
                other_values = [int(v) for v in other.flatten()]
            else:
                other_values = [int(v) for v in other]
            
            result = []
            for motive_value in self._values:
                result.extend([transpose + motive_value for transpose in other_values])
            return Motive(result)
        else:
            return NotImplemented
    
    def __sub__(self, other: Union[int, List[int], Sequence[int], np.ndarray, 'Motive']) -> 'Motive':
        if isinstance(other, (int, float)):
            return Motive([v - int(other) for v in self._values])
        elif isinstance(other, (list, tuple, np.ndarray, Motive)):
            if isinstance(other, Motive):
                other_values = other._values
            elif isinstance(other, np.ndarray):
                other_values = [int(v) for v in other.flatten()]
            else:
                other_values = [int(v) for v in other]
            
            result = []
            for subtract in other_values:
                result.extend([v - subtract for v in self._values])
            return Motive(result)
        else:
            return NotImplemented
    
    def __rsub__(self, other: Union[int, List[int], Sequence[int], np.ndarray]) -> 'Motive':
        if isinstance(other, (int, float)):
            return Motive([int(other) - v for v in self._values])
        elif isinstance(other, (list, tuple, np.ndarray)):
            if isinstance(other, np.ndarray):
                other_values = [int(v) for v in other.flatten()]
            else:
                other_values = [int(v) for v in other]
            
            result = []
            for motive_value in self._values:
                result.extend([transpose - motive_value for transpose in other_values])
            return Motive(result)
        else:
            return NotImplemented
    
    def __mul__(self, other: Union[int, float]) -> 'Motive':
        if isinstance(other, (int, float)):
            return Motive([int(v * other) for v in self._values])
        else:
            return NotImplemented
    
    def __rmul__(self, other: Union[int, float]) -> 'Motive':
        return self.__mul__(other)
    
    def __truediv__(self, other: Union[int, float]) -> 'Motive':
        if isinstance(other, (int, float)) and other != 0:
            return Motive([int(v / other) for v in self._values])
        else:
            raise ValueError("Cannot divide by zero or non-numeric value")
    
    def __floordiv__(self, other: Union[int, float]) -> 'Motive':
        if isinstance(other, (int, float)) and other != 0:
            return Motive([int(v // other) for v in self._values])
        else:
            raise ValueError("Cannot divide by zero or non-numeric value")
    
    def __mod__(self, other: Union[int, float]) -> 'Motive':
        if isinstance(other, (int, float)) and other != 0:
            return Motive([int(v % other) for v in self._values])
        else:
            raise ValueError("Cannot modulo by zero or non-numeric value")
    
    def __neg__(self) -> 'Motive':
        return Motive([-v for v in self._values])
    
    def __abs__(self) -> 'Motive':
        return Motive([abs(v) for v in self._values])
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Motive):
            return self._values == other._values
        elif isinstance(other, (list, tuple)):
            return self._values == list(other)
        else:
            return False
    
    def __repr__(self) -> str:
        values_str = ', '.join(str(v) for v in self._values)
        return f"Motive([{values_str}])"
    
    def __str__(self) -> str:
        values_str = ', '.join(str(v) for v in self._values)
        return f"Motive([{values_str}])"
    
    def copy(self) -> 'Motive':
        """Return a copy of this motive."""
        return Motive(self._values)
    
    def reverse(self) -> 'Motive':
        """Return a reversed copy of this motive."""
        return Motive(self._values[::-1])
    
    def invert(self, axis: int = 0) -> 'Motive':
        """Return an inverted copy of this motive around the given axis."""
        return Motive([2 * axis - v for v in self._values])
    
    def retrograde(self) -> 'Motive':
        """Return the retrograde (reverse) of this motive."""
        return self.reverse()
    
    def inversion(self) -> 'Motive':
        """Return the inversion of this motive (same as motive * -1)."""
        return Motive([-v for v in self._values])
    
    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array(self._values, dtype=int)
    
    def flatten(self) -> 'Motive':
        """Return a flattened copy (no-op for Motive, included for compatibility)."""
        return self.copy()
