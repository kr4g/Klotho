import numpy as np
from typing import Union, List, Sequence

class Contour:
    """
    A pitch contour represented as a 1-D numpy array of integers.
    
    Contour provides element-wise arithmetic operations and an outer sum method
    for Cartesian sum (chord multiplication). All operations return new Contour
    instances (immutable design).
    
    A contour represents the shape of pitch motion as a sequence of scale degree
    indices. It can be used to index into pitch collections (Scale, Chord, etc.)
    to retrieve actual pitches.
    
    Args:
        values: Sequence of integers representing the contour
        
    Examples:
        >>> contour = Contour([6, 2, 4, 0])
        
        >>> contour + 1  # Scalar addition (transpose)
        Contour([7, 3, 5, 1])
        
        >>> contour * 2  # Scalar multiplication (scale)
        Contour([12, 4, 8, 0])
        
        >>> contour + Contour([1, 2, 3, 4])  # Element-wise addition
        Contour([7, 4, 7, 4])
        
        >>> Contour.outer([6, 2, 4, 0], [0, 3, 1])  # Cartesian sum
        Contour([6, 9, 7, 2, 5, 3, 4, 7, 5, 0, 3, 1])
        
        >>> scale = Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])
        >>> scale[contour]  # Index into a scale with a contour
        PitchCollection([...])
    """
    
    def __init__(self, values: Union[List[int], Sequence[int], np.ndarray, 'Contour']):
        if isinstance(values, Contour):
            self._values = values._values.copy()
        else:
            self._values = np.asarray(values, dtype=int).flatten()
    
    @classmethod
    def outer(cls, a: Union['Contour', Sequence[int], np.ndarray], 
              b: Union['Contour', Sequence[int], np.ndarray]) -> 'Contour':
        """
        Compute the outer sum (Cartesian sum) of two sequences.
        
        This operation is also known as "chord multiplication" in set-theoretic
        music theory (Boulez). For each element in `a`, adds all elements of `b`,
        returning a flattened result.
        
        Args:
            a: First sequence (Contour, list, or array)
            b: Second sequence (Contour, list, or array)
            
        Returns:
            New Contour containing the flattened outer sum
            
        Examples:
            >>> Contour.outer([0, 1, 2], [4, 0])
            Contour([4, 0, 5, 1, 6, 2])
            
            >>> Contour.outer(Contour([6, 2, 4, 0]), [0, 3, 1])
            Contour([6, 9, 7, 2, 5, 3, 4, 7, 5, 0, 3, 1])
        """
        a_arr = a._values if isinstance(a, cls) else np.asarray(a, dtype=int)
        b_arr = b._values if isinstance(b, cls) else np.asarray(b, dtype=int)
        return cls(np.add.outer(a_arr, b_arr).flatten())
    
    @classmethod
    def concat(cls, contours: List['Contour']) -> 'Contour':
        """
        Concatenate multiple contours into one flat contour.
        
        Args:
            contours: List of Contour instances to concatenate
            
        Returns:
            New Contour containing all values from input contours in sequence
            
        Examples:
            >>> c1 = Contour([0, 2, 4])
            >>> c2 = Contour([1, 3, 5])
            >>> Contour.concat([c1, c2])
            Contour([0, 2, 4, 1, 3, 5])
        """
        return cls([v for c in contours for v in c])
    
    @property
    def values(self) -> List[int]:
        """Return the contour values as a list of integers."""
        return self._values.tolist()
    
    def __len__(self) -> int:
        return len(self._values)
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> Union[int, 'Contour']:
        result = self._values[index]
        if isinstance(result, np.ndarray):
            return Contour(result)
        return int(result)
    
    def __iter__(self):
        return iter(self._values)
    
    def __add__(self, other: Union[int, float, 'Contour', Sequence[int], np.ndarray]) -> 'Contour':
        if isinstance(other, Contour):
            return Contour(self._values + other._values)
        elif isinstance(other, (int, float, np.integer, np.floating)):
            return Contour(self._values + int(other))
        elif isinstance(other, (list, tuple, np.ndarray)):
            return Contour(self._values + np.asarray(other, dtype=int))
        return NotImplemented
    
    def __radd__(self, other: Union[int, float, Sequence[int], np.ndarray]) -> 'Contour':
        if isinstance(other, (int, float, np.integer, np.floating)):
            return Contour(int(other) + self._values)
        elif isinstance(other, (list, tuple, np.ndarray)):
            return Contour(np.asarray(other, dtype=int) + self._values)
        return NotImplemented
    
    def __sub__(self, other: Union[int, float, 'Contour', Sequence[int], np.ndarray]) -> 'Contour':
        if isinstance(other, Contour):
            return Contour(self._values - other._values)
        elif isinstance(other, (int, float, np.integer, np.floating)):
            return Contour(self._values - int(other))
        elif isinstance(other, (list, tuple, np.ndarray)):
            return Contour(self._values - np.asarray(other, dtype=int))
        return NotImplemented
    
    def __rsub__(self, other: Union[int, float, Sequence[int], np.ndarray]) -> 'Contour':
        if isinstance(other, (int, float, np.integer, np.floating)):
            return Contour(int(other) - self._values)
        elif isinstance(other, (list, tuple, np.ndarray)):
            return Contour(np.asarray(other, dtype=int) - self._values)
        return NotImplemented
    
    def __mul__(self, other: Union[int, float, 'Contour', Sequence[int], np.ndarray]) -> 'Contour':
        if isinstance(other, Contour):
            return Contour(self._values * other._values)
        elif isinstance(other, (int, float, np.integer, np.floating)):
            return Contour((self._values * other).astype(int))
        elif isinstance(other, (list, tuple, np.ndarray)):
            return Contour(self._values * np.asarray(other, dtype=int))
        return NotImplemented
    
    def __rmul__(self, other: Union[int, float, Sequence[int], np.ndarray]) -> 'Contour':
        if isinstance(other, (int, float, np.integer, np.floating)):
            return Contour((other * self._values).astype(int))
        elif isinstance(other, (list, tuple, np.ndarray)):
            return Contour(np.asarray(other, dtype=int) * self._values)
        return NotImplemented
    
    def __truediv__(self, other: Union[int, float, 'Contour', Sequence[int], np.ndarray]) -> 'Contour':
        if isinstance(other, Contour):
            if np.any(other._values == 0):
                raise ValueError("Cannot divide by zero")
            return Contour((self._values / other._values).astype(int))
        elif isinstance(other, (int, float, np.integer, np.floating)):
            if other == 0:
                raise ValueError("Cannot divide by zero")
            return Contour((self._values / other).astype(int))
        elif isinstance(other, (list, tuple, np.ndarray)):
            other_arr = np.asarray(other, dtype=int)
            if np.any(other_arr == 0):
                raise ValueError("Cannot divide by zero")
            return Contour((self._values / other_arr).astype(int))
        return NotImplemented
    
    def __rtruediv__(self, other: Union[int, float, Sequence[int], np.ndarray]) -> 'Contour':
        if np.any(self._values == 0):
            raise ValueError("Cannot divide by zero")
        if isinstance(other, (int, float, np.integer, np.floating)):
            return Contour((other / self._values).astype(int))
        elif isinstance(other, (list, tuple, np.ndarray)):
            return Contour((np.asarray(other, dtype=int) / self._values).astype(int))
        return NotImplemented
    
    def __floordiv__(self, other: Union[int, float, 'Contour', Sequence[int], np.ndarray]) -> 'Contour':
        if isinstance(other, Contour):
            if np.any(other._values == 0):
                raise ValueError("Cannot floor divide by zero")
            return Contour(self._values // other._values)
        elif isinstance(other, (int, float, np.integer, np.floating)):
            if other == 0:
                raise ValueError("Cannot floor divide by zero")
            return Contour(self._values // int(other))
        elif isinstance(other, (list, tuple, np.ndarray)):
            other_arr = np.asarray(other, dtype=int)
            if np.any(other_arr == 0):
                raise ValueError("Cannot floor divide by zero")
            return Contour(self._values // other_arr)
        return NotImplemented
    
    def __rfloordiv__(self, other: Union[int, float, Sequence[int], np.ndarray]) -> 'Contour':
        if np.any(self._values == 0):
            raise ValueError("Cannot floor divide by zero")
        if isinstance(other, (int, float, np.integer, np.floating)):
            return Contour(int(other) // self._values)
        elif isinstance(other, (list, tuple, np.ndarray)):
            return Contour(np.asarray(other, dtype=int) // self._values)
        return NotImplemented
    
    def __mod__(self, other: Union[int, float]) -> 'Contour':
        """
        Musical modulo operation that preserves sign.
        
        Unlike standard Python mod which always returns non-negative values,
        this preserves the sign of the input to maintain musical semantics
        where negative indices indicate pitches below the root.
        
        Examples:
            >>> Contour([13, -13, -1, -12, 0]) % 12
            Contour([1, -1, -1, 0, 0])
        """
        if isinstance(other, (int, float, np.integer, np.floating)) and other != 0:
            mod_val = int(other)
            return Contour(np.sign(self._values) * (np.abs(self._values) % mod_val))
        raise ValueError("Cannot modulo by zero or non-numeric value")
    
    def __neg__(self) -> 'Contour':
        return Contour(-self._values)
    
    def __abs__(self) -> 'Contour':
        return Contour(np.abs(self._values))
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Contour):
            return np.array_equal(self._values, other._values)
        elif isinstance(other, (list, tuple, np.ndarray)):
            return np.array_equal(self._values, np.asarray(other))
        return False
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __str__(self) -> str:
        values_str = ', '.join(str(v) for v in self._values)
        return f"Contour([{values_str}])"
    
    def copy(self) -> 'Contour':
        """Return a copy of this contour."""
        return Contour(self._values.copy())
    
    def invert(self, axis: int = 0) -> 'Contour':
        """
        Return an inverted copy of this contour around the given axis.
        
        Reflects each value around the axis point using the formula: 2 * axis - value.
        With the default axis=0, this is equivalent to negation (-contour).
        
        Args:
            axis: The pitch value to reflect around (default: 0)
            
        Returns:
            New Contour with inverted values
        """
        return Contour(2 * axis - self._values)
    
    def retrograde(self) -> 'Contour':
        """Return the retrograde (reversed order) of this contour."""
        return Contour(self._values[::-1])
    
    def rotate(self, n: int) -> 'Contour':
        """
        Circular shift of contour values.
        
        Args:
            n: Number of positions to shift. Positive shifts right,
               negative shifts left.
               
        Returns:
            New Contour with rotated values
            
        Examples:
            >>> Contour([0, 1, 2, 3]).rotate(1)
            Contour([3, 0, 1, 2])
            
            >>> Contour([0, 1, 2, 3]).rotate(-1)
            Contour([1, 2, 3, 0])
        """
        return Contour(np.roll(self._values, n))
    
    def normalized(self, start: int = 0) -> 'Contour':
        """
        Shift contour so minimum value equals start.
        
        Args:
            start: The value that the minimum should equal (default: 0)
            
        Returns:
            New Contour shifted to start at the given value
            
        Examples:
            >>> Contour([5, 3, 7, 4]).normalize()
            Contour([2, 0, 4, 1])
            
            >>> Contour([5, 3, 7, 4]).normalize(1)
            Contour([3, 1, 5, 2])
        """
        return Contour(self._values - np.min(self._values) + start)
    
    def zeroed(self, start: int = 0) -> 'Contour':
        """
        Shift contour so the first value equals start.
        
        Args:
            start: The value that the first element should equal (default: 0)
            
        Returns:
            New Contour with values shifted relative to the first element
            
        Examples:
            >>> Contour([5, 3, 7, 4]).zeroed()
            Contour([0, -2, 2, -1])
            
            >>> Contour([5, 3, 7, 4]).zeroed(1)
            Contour([1, -1, 3, 0])
        """
        return Contour(self._values - self._values[0] + start)
    
    def to_numpy(self) -> np.ndarray:
        """Return a copy of the internal numpy array."""
        return self._values.copy()
