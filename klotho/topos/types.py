"""
Base class for typed musical units with NumPy integration.
"""

import numbers
import numpy as np
from fractions import Fraction

__all__ = ['Unit', '_to_fraction_array']


def _to_fraction_array(value):
    """
    Convert a value to Fraction(s), preserving shape. Accepts int, Fraction, str,
    or array-like of those. Returns ndarray with dtype=object (0-d for scalar).
    """
    if isinstance(value, (list, tuple, np.ndarray)):
        arr = np.asarray(value)
        out = np.array([Fraction(x) for x in arr.flat], dtype=object)
        return out.reshape(arr.shape)
    return np.array(Fraction(value), dtype=object)


class Unit:
    """
    Base class for typed musical units with NumPy integration.

    Wraps a numeric magnitude with unit metadata, supporting transparent
    NumPy array operations via ``__array__`` and ``__array_ufunc__``.

    Parameters
    ----------
    magnitude : scalar or array-like
        The numeric value(s) of the unit.
    unit_type : str
        Identifier for the unit type (e.g., 'frequency', 'amplitude').
    unit_symbol : str, optional
        Display symbol for the unit (default is ``""``).
    """
    def __init__(self, magnitude, unit_type, unit_symbol=""):
        self.magnitude = np.asarray(magnitude)
        self.unit_type = unit_type
        self.unit_symbol = unit_symbol

    def __array__(self):
        return self.magnitude

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        magnitudes = []
        for input_ in inputs:
            if hasattr(input_, 'magnitude'):
                magnitudes.append(input_.magnitude)
            else:
                magnitudes.append(input_)

        result_magnitude = ufunc(*magnitudes, **kwargs)
        return type(self)(result_magnitude)

    def __float__(self):
        return float(self.magnitude)

    def __int__(self):
        return int(self.magnitude)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"{self.magnitude} {self.unit_symbol}"

    def __getitem__(self, key):
        return type(self)(self.magnitude[key])
