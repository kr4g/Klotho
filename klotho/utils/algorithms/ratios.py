import numbers
from fractions import Fraction
from typing import Union, List
from sympy import isprime

__all__ = [
    'is_superparticular',
    'superparticular_base',
    'validate_primes',
]


def _as_whole_number(value) -> int:
    """Coerce ``value`` to ``int``, refusing anything that is not exactly whole.

    ``int(2.5)`` is ``2``, so coercing first and validating afterwards turns a
    non-integer into a perfectly plausible prime. This checks first.
    Integral types (including numpy integers) pass straight through; every
    other value goes via ``Fraction``, which keeps the string and
    ``Fraction`` inputs that already worked.
    """
    if isinstance(value, numbers.Integral):
        return int(value)
    try:
        as_fraction = Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        raise ValueError(f"primes must be whole numbers, got {value!r}") from None
    if as_fraction.denominator != 1:
        raise ValueError(f"primes must be whole numbers, got {value!r}")
    return int(as_fraction)


def is_superparticular(ratio: Union[int, float, Fraction, str]) -> bool:
    """
    Check if a ratio is superparticular.
    
    A superparticular ratio has the form (n+1)/n where n is a positive integer.
    Examples: 2/1, 3/2, 4/3, 5/4, 6/5, 9/8, 10/9, etc.
    
    Parameters
    ----------
    ratio : int, float, Fraction, or str
        The ratio to check. Can be an integer, Fraction object, or
        string representation of a fraction (e.g., '3/2').

    Returns
    -------
    bool
        True if the ratio is superparticular, False otherwise.

    Examples
    --------
    >>> is_superparticular('3/2')
    True
    
    >>> is_superparticular(Fraction(5, 4))
    True
    
    >>> is_superparticular('5/3')
    False
    
    >>> is_superparticular('8/9')  # Subparticular (inverse)
    True
    """
    ratio = Fraction(ratio)
    p, q = ratio.numerator, ratio.denominator
    return abs(p - q) == 1


def superparticular_base(ratio: Union[int, float, Fraction, str]) -> int:
    """
    Get the base n of a superparticular ratio.
    
    For a superparticular ratio (n+1)/n, returns n.
    For a subparticular ratio n/(n+1), also returns n.
    
    Parameters
    ----------
    ratio : int, float, Fraction, or str
        The ratio to analyze. Should be superparticular.

    Returns
    -------
    int
        The base n of the superparticular ratio.

    Examples
    --------
    >>> superparticular_base('3/2')
    2
    
    >>> superparticular_base('5/4')
    4
    
    >>> superparticular_base('9/8')
    8
    
    >>> superparticular_base('2/3')  # Subparticular
    2

    Notes
    -----
    This function does not validate that the input is superparticular.
    For non-superparticular ratios, returns the smaller of numerator
    and denominator, which may not be meaningful.
    """
    ratio = Fraction(ratio)
    p, q = ratio.numerator, ratio.denominator
    return min(p, q)


def validate_primes(primes: List[Union[int, float]]) -> List[int]:
    """
    Validate and normalize a list of prime numbers.
    
    Ensures all values in the list are unique prime integers.
    
    Parameters
    ----------
    primes : List[int or float]
        List of values to validate as primes.

    Returns
    -------
    List[int]
        List of validated prime integers.

    Raises
    ------
    ValueError
        If any value is not a whole number, is not prime, or if there are
        duplicates.

    Notes
    -----
    A float is accepted only when it is exactly a whole number, so
    ``2.0 -> 2`` still works while ``2.5`` is refused. The truncation used
    to happen *before* validation, which let ``[2.5, 3.7]`` "validate" as
    ``[2, 3]`` -- two primes the caller never asked for, silently
    substituted for two values that are not integers at all.

    Examples
    --------
    >>> validate_primes([2, 3, 5])
    [2, 3, 5]

    >>> validate_primes([2.0, 3.0, 5.0])
    [2, 3, 5]

    >>> validate_primes([2, 3, 4])  # 4 is not prime
    Traceback (most recent call last):
        ...
    ValueError: all entries in primes must be prime

    >>> validate_primes([2, 3, 3])  # duplicate
    Traceback (most recent call last):
        ...
    ValueError: primes must be unique

    >>> validate_primes([2.5])  # not a whole number
    Traceback (most recent call last):
        ...
    ValueError: primes must be whole numbers, got 2.5
    """
    primes = [_as_whole_number(p) for p in primes]
    if len(set(primes)) != len(primes):
        raise ValueError("primes must be unique")
    if any(not isprime(p) for p in primes):
        raise ValueError("all entries in primes must be prime")
    return primes
