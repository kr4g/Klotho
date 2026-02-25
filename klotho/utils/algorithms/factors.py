from fractions import Fraction
from sympy import factorint, prime as sympy_prime, isprime
from typing import Union, Dict, List, Optional, Sequence
from functools import lru_cache
import numpy as np
import sympy as sp

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
    Convert a prime-factor dictionary to a prime-coordinate vector.
    
    Transform a dictionary of prime factors into a vector in prime basis space.
    This is efficient when factors are already available and factorization work
    can be skipped.

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
        Immutable vector of prime exponents with optional zero-padding.
        Position ``i`` corresponds to the ``(i+1)``th prime.

    Raises
    ------
    ValueError
        If ``vector_size`` is too small to represent the highest prime.

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
    Returned arrays are immutable.
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

def ratio_to_coordinate(
    ratio: Union[int, Fraction, str],
    vector_size: Optional[int] = None,
    generators: Optional[Sequence[Union[int, Fraction, str]]] = None,
    basis_primes: Optional[Sequence[int]] = None,
) -> np.ndarray:
    """
    Convert a ratio to a coordinate vector.

    Behavior depends on ``generators``:

    - If ``generators`` is ``None``, return prime coordinates (monzo-style) in
      the canonical prime basis.
    - If ``generators`` is provided, solve for integer generator coordinates
      using ``basis_primes`` and a linear Diophantine system.

    Parameters
    ----------
    ratio : int | Fraction | str
        Ratio to convert.
    vector_size : int, optional
        Output length. If larger than required, result is zero-padded.
        If smaller, raises ``ValueError``.
    generators : sequence[int | Fraction | str], optional
        Generator basis used for coordinates. Floats are not accepted.
    basis_primes : sequence[int], optional
        Prime basis used to express generator monzos. If omitted, inferred from
        the generator factorizations.

    Returns
    -------
    numpy.ndarray
        Immutable integer coordinate vector.

    Raises
    ------
    TypeError
        If generator values include floats.
    ValueError
        If the basis is invalid, if representation is not unique/integer, or if
        ``vector_size`` is inconsistent.
    """
    ratio_fraction = Fraction(ratio)
    if generators is None:
        factors = to_factors(ratio_fraction)
        return factors_to_lattice_vector(factors, vector_size)

    parsed_generators: List[Fraction] = []
    for g in generators:
        if isinstance(g, float):
            raise TypeError("generators must be int, Fraction, or str; floats are not supported")
        parsed_generators.append(Fraction(g))
    if not parsed_generators:
        raise ValueError("generators must not be empty")

    if basis_primes is None:
        all_primes = set()
        for g in parsed_generators:
            all_primes.update(to_factors(g).keys())
        primes = sorted(all_primes)
    else:
        primes = [int(p) for p in basis_primes]
    if len(set(primes)) != len(primes):
        raise ValueError("basis_primes must be unique")
    if any(not isprime(p) for p in primes):
        raise ValueError("basis_primes must contain only prime numbers")

    ratio_factors = to_factors(ratio_fraction)
    missing_primes = [p for p, e in ratio_factors.items() if e != 0 and p not in primes]
    if missing_primes:
        raise ValueError(
            f"ratio contains primes not present in basis_primes: {sorted(missing_primes)}"
        )

    A = sp.Matrix(
        [
            [to_factors(g).get(p, 0) for g in parsed_generators]
            for p in primes
        ]
    )
    x = sp.Matrix([ratio_factors.get(p, 0) for p in primes])
    y_symbols = sp.symbols(f"y0:{len(parsed_generators)}", integer=True)
    solutions = sp.linsolve((A, x), y_symbols)
    if not solutions:
        raise ValueError("ratio is not representable with provided generators")
    solution = next(iter(solutions))
    if any(expr.free_symbols for expr in solution):
        raise ValueError("ratio does not have a unique integer coordinate in provided generators")
    y = sp.Matrix(solution)
    if any(sp.denom(v) != 1 for v in y):
        raise ValueError("ratio is not representable with integer generator coordinates")

    coord = [int(v) for v in y]
    if vector_size is not None:
        if vector_size < len(coord):
            raise ValueError(
                f"vector_size ({vector_size}) must be at least {len(coord)} for provided generators"
            )
        if vector_size > len(coord):
            coord = coord + [0] * (vector_size - len(coord))
    arr = np.array(coord, dtype=int)
    arr.setflags(write=False)
    return arr


def ratios_to_coordinates(
    ratios: Sequence[Union[int, Fraction, str]],
    vector_size: Optional[int] = None,
    generators: Optional[Sequence[Union[int, Fraction, str]]] = None,
    basis_primes: Optional[Sequence[int]] = None,
) -> List[np.ndarray]:
    """
    Convert multiple ratios to coordinate vectors.

    This is the batch companion to ``ratio_to_coordinate`` and preserves input
    order in the returned list.

    Parameters
    ----------
    ratios : sequence[int | Fraction | str]
        Ratios to convert.
    vector_size : int, optional
        Target output length for each coordinate vector.
    generators : sequence[int | Fraction | str], optional
        Generator basis for conversion. If omitted, prime coordinates are used.
    basis_primes : sequence[int], optional
        Prime basis used with ``generators``.

    Returns
    -------
    list[numpy.ndarray]
        Immutable coordinate vectors aligned with input order.
    """
    ratios_list = list(ratios)
    if generators is None and vector_size is None:
        all_factors = [to_factors(Fraction(ratio)) for ratio in ratios_list]
        all_primes = set()
        for factors in all_factors:
            all_primes.update(factors.keys())
        if all_primes:
            max_prime = max(all_primes)
            inferred_size = nth_prime(max_prime)
        else:
            inferred_size = 1
        return [
            ratio_to_coordinate(
                ratio=ratio,
                vector_size=inferred_size,
                generators=generators,
                basis_primes=basis_primes,
            )
            for ratio in ratios_list
        ]
    return [
        ratio_to_coordinate(
            ratio=ratio,
            vector_size=vector_size,
            generators=generators,
            basis_primes=basis_primes,
        )
        for ratio in ratios_list
    ]
