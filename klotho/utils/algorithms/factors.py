from fractions import Fraction
from sympy import factorint, prime as sympy_prime, isprime
from typing import Union, Dict, List, Optional
from functools import lru_cache
import numpy as np

def to_factors(value: Union[int, Fraction, str]) -> Dict[int, int]:
    """
    Convert a numeric value to its prime factorization representation.
    
    Decompose a rational number into its prime factors, returning a dictionary
    mapping prime numbers to their exponents. Negative exponents represent
    factors in the denominator.

    Parameters
    ----------
    value : int, Fraction, or str
        The value to factorize. Can be an integer, Fraction object, or
        string representation of a fraction (e.g., '3/2').

    Returns
    -------
    Dict[int, int]
        Dictionary mapping prime numbers to their exponents. Positive
        exponents represent factors in the numerator, negative exponents
        represent factors in the denominator.

    Raises
    ------
    TypeError
        If input type is not supported.

    Examples
    --------
    Factor an integer:
    
    >>> to_factors(12)
    {2: 2, 3: 1}
    
    Factor a fraction:
    
    >>> to_factors(Fraction(3, 2))
    {2: -1, 3: 1}
    
    Factor from string representation:
    
    >>> to_factors('5/4')
    {2: -2, 5: 1}
    """
    match value:
        case int() as i:
            ratio = Fraction(i, 1)
        case Fraction() as f:
            ratio = f
        case str() as s:
            ratio = Fraction(s)
        case _:
            raise TypeError("Unsupported type")
    num_factors = factorint(ratio.numerator)
    den_factors = factorint(ratio.denominator)
    for p, e in den_factors.items():
        num_factors[p] = num_factors.get(p, 0) - e
    return num_factors

def from_factors(factors: Dict[int, int]) -> Fraction:
    """
    Reconstruct a fraction from its prime factorization.
    
    Convert a dictionary of prime factors back to a Fraction object.
    Positive exponents contribute to the numerator, negative exponents
    contribute to the denominator.

    Parameters
    ----------
    factors : Dict[int, int]
        Dictionary mapping prime numbers to their exponents. Positive
        exponents represent factors in the numerator, negative exponents
        represent factors in the denominator.

    Returns
    -------
    Fraction
        The reconstructed fraction from the prime factorization.

    Examples
    --------
    Reconstruct from prime factors:
    
    >>> from_factors({2: 2, 3: 1})
    Fraction(12, 1)
    
    Handle negative exponents:
    
    >>> from_factors({2: -1, 3: 1})
    Fraction(3, 2)
    
    Empty factorization returns 1:
    
    >>> from_factors({})
    Fraction(1, 1)
    """
    numerator = 1
    denominator = 1
    for prime, exp in factors.items():
        if exp > 0:
            numerator *= prime ** exp
        elif exp < 0:
            denominator *= prime ** (-exp)
    return Fraction(numerator, denominator)

@lru_cache(maxsize=256)
def nth_prime(prime: int) -> int:
    """
    Find the index (position) of a prime number in the sequence of primes.
    
    Determine which position a given prime number occupies in the ordered
    sequence of all prime numbers (2 is 1st, 3 is 2nd, 5 is 3rd, etc.).

    Parameters
    ----------
    prime : int
        The prime number to find the index for. Must be a valid prime number.
    
    Returns
    -------
    int
        The 1-based index of the prime in the sequence of all primes.

    Raises
    ------
    ValueError
        If the input number is not prime.

    Examples
    --------
    Find index of small primes:
    
    >>> nth_prime(2)
    1
    
    >>> nth_prime(3)
    2
    
    >>> nth_prime(7)
    4
    
    >>> nth_prime(11)
    5
    """
    if not isprime(prime):
        raise ValueError(f"{prime} is not a prime number")
    
    nth = 1
    while sympy_prime(nth) != prime:
        nth += 1
    return nth

def factors_to_lattice_vector(factors: Dict[int, int], vector_size: Optional[int] = None) -> np.ndarray:
    """
    Convert prime factors dictionary to lattice vector representation.
    
    Transform a dictionary of prime factors into a vector in prime number space.
    This function is more efficient when you already have the factors computed
    and want to avoid recomputing them.

    Parameters
    ----------
    factors : Dict[int, int]
        Dictionary mapping prime numbers to their exponents.
    vector_size : int, optional
        Target size for the output vector. Must be at least as large as
        needed to represent the largest prime factor. If None, uses the
        minimum required size. Default is None.

    Returns
    -------
    numpy.ndarray
        Immutable vector of prime exponents with optional zero-padding to 
        specified size. Position i corresponds to the (i+1)th prime number.
        Supports mathematical vector operations (addition, subtraction, etc.).

    Raises
    ------
    ValueError
        If vector_size is smaller than required to represent the factors.

    Examples
    --------
    Convert factors to minimal vector:
    
    >>> factors = {2: 1, 3: 1, 5: -1}
    >>> factors_to_lattice_vector(factors)
    array([ 1,  1, -1])
    
    Convert with padding:
    
    >>> factors_to_lattice_vector(factors, vector_size=5)
    array([ 1,  1, -1,  0,  0])

    Notes
    -----
    Returned arrays are immutable to preserve mathematical integrity.
    Vector addition corresponds to ratio multiplication:
    lattice_vector(a) + lattice_vector(b) = lattice_vector(a * b)
    """
    if not factors:
        arr = np.zeros(vector_size or 1, dtype=int)
        arr.setflags(write=False)
        return arr
    
    max_prime = max(factors.keys())
    min_size = nth_prime(max_prime)
    
    if vector_size is not None and vector_size < min_size:
        raise ValueError(f"vector_size ({vector_size}) must be at least {min_size} to represent prime {max_prime}")
    
    target_size = vector_size or min_size
    primes = [sympy_prime(i) for i in range(1, target_size + 1)]
    arr = np.array([factors.get(p, 0) for p in primes], dtype=int)
    arr.setflags(write=False)
    return arr

@lru_cache(maxsize=128)
def ratio_to_lattice_vector(ratio: Union[int, Fraction, str], vector_size: Optional[int] = None) -> np.ndarray:
    """
    Convert a ratio to its prime lattice vector representation.
    
    Transform a rational number into a vector in prime number space,
    where each dimension corresponds to a prime number and the value
    represents the exponent of that prime in the factorization.
    
    This is a convenience function that combines factorization and vector
    conversion. For efficiency with multiple ratios, consider using
    ratios_to_lattice_vectors() instead.

    Parameters
    ----------
    ratio : int, Fraction, or str
        The ratio to convert to prime lattice form. Can be an integer,
        Fraction object, or string representation of a fraction.
    vector_size : int, optional
        Target size for the output vector. Must be at least as large as
        needed to represent the largest prime factor. If None, uses the
        minimum required size. Default is None.

    Returns
    -------
    numpy.ndarray
        Immutable vector of prime exponents, where position i corresponds 
        to the (i+1)th prime number. Zero-padded to vector_size if specified.
        Supports mathematical vector operations.

    Raises
    ------
    ValueError
        If vector_size is smaller than required to represent the ratio.

    Examples
    --------
    Simple ratio to prime lattice:
    
    >>> ratio_to_lattice_vector(3)
    array([0, 1])
    
    Fraction with padding:
    
    >>> ratio_to_lattice_vector('6/5', vector_size=4)
    array([ 1,  1, -1,  0])
    
    Higher primes with padding:
    
    >>> ratio_to_lattice_vector('7/4', vector_size=6)
    array([-2,  0,  0,  1,  0,  0])

    Notes
    -----
    The prime lattice representation enables geometric operations on
    musical intervals and harmonic relationships. Vector addition 
    corresponds to ratio multiplication, and subtraction corresponds
    to ratio division.
    
    Vectors are returned as immutable NumPy arrays to preserve mathematical
    integrity while enabling proper mathematical operations.
    """
    factors = to_factors(Fraction(ratio))
    return factors_to_lattice_vector(factors, vector_size)

def ratios_to_lattice_vectors(ratios: List[Union[int, Fraction, str]], 
                             vector_size: Optional[int] = None) -> Dict[Union[int, Fraction, str], np.ndarray]:
    """
    Convert multiple ratios to prime lattice vectors efficiently.
    
    Process a collection of ratios to their lattice vector representations.
    This function is more efficient than calling ratio_to_lattice_vector()
    multiple times because it computes factors only once per ratio and
    can automatically determine optimal vector size for uniform output.

    Parameters
    ----------
    ratios : List[Union[int, Fraction, str]]
        List of ratios to convert to prime lattice form.
    vector_size : int, optional
        Target size for all output vectors. If None, automatically
        determines the minimum size needed to represent all ratios.
        Default is None.

    Returns
    -------
    Dict[Union[int, Fraction, str], numpy.ndarray]
        Dictionary mapping each input ratio to its corresponding immutable
        prime lattice vector. All vectors have the same size and support
        mathematical operations.

    Examples
    --------
    Convert multiple ratios with automatic sizing:
    
    >>> ratios = ['3/2', '5/4', '7/4']
    >>> vectors = ratios_to_lattice_vectors(ratios)
    >>> print(vectors)
    {'3/2': array([-1,  1,  0,  0]), '5/4': array([-2,  0,  1,  0]), '7/4': array([-2,  0,  0,  1])}
    
    Convert with specified size:
    
    >>> vectors = ratios_to_lattice_vectors(['3/2', '5/4'], vector_size=5)
    >>> print(vectors)  
    {'3/2': array([-1,  1,  0,  0,  0]), '5/4': array([-2,  0,  1,  0,  0])}

    Notes
    -----
    This function is optimal for batch processing as it avoids redundant
    factorization calls and ensures uniform vector sizes across all outputs.
    
    Vectors are returned as immutable NumPy arrays to preserve mathematical
    integrity while enabling proper mathematical operations like addition
    (which corresponds to ratio multiplication).
    """
    all_factors = [to_factors(Fraction(ratio)) for ratio in ratios]
    
    if vector_size is None:
        all_primes = set()
        for factors in all_factors:
            all_primes.update(factors.keys())
        
        if all_primes:
            max_prime = max(all_primes)
            vector_size = nth_prime(max_prime)
        else:
            vector_size = 1
    
    vectors = [factors_to_lattice_vector(factors, vector_size) for factors in all_factors]
    return dict(zip(ratios, vectors))
