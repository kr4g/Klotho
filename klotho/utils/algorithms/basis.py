from fractions import Fraction
from typing import Union, List, Tuple
import sympy as sp

from .ratios import validate_primes
from .factors import to_factors

__all__ = [
    'monzo_from_ratio',
    'ratio_from_monzo',
    'basis_matrix',
    'is_unimodular',
    'change_of_basis',
    'prime_to_generator_coords',
    'generator_to_prime_coords',
    'ratio_from_prime_coords',
    'ratio_from_generator_coords',
]


def monzo_from_ratio(ratio: Union[int, float, Fraction, str], primes: List[int]) -> sp.Matrix:
    """
    Convert a ratio to its monzo (prime exponent vector) representation.
    
    A monzo is a vector of prime exponents that represents a ratio.
    For primes [p1, p2, ..., pn] and ratio r = p1^e1 * p2^e2 * ... * pn^en,
    the monzo is [e1, e2, ..., en].
    
    Parameters
    ----------
    ratio : int, float, Fraction, or str
        The ratio to convert.
    primes : List[int]
        Ordered list of prime numbers defining the basis.

    Returns
    -------
    sympy.Matrix
        Column vector of prime exponents.

    Examples
    --------
    >>> monzo_from_ratio('3/2', [2, 3, 5])
    Matrix([
    [-1],
    [ 1],
    [ 0]])
    
    >>> monzo_from_ratio('5/4', [2, 3, 5])
    Matrix([
    [-2],
    [ 0],
    [ 1]])
    """
    ratio = Fraction(ratio)
    factors = to_factors(ratio)
    return sp.Matrix([factors.get(p, 0) for p in primes])


def ratio_from_monzo(monzo: Union[List[int], sp.Matrix], primes: List[int]) -> Fraction:
    """
    Convert a monzo (prime exponent vector) back to a ratio.
    
    Parameters
    ----------
    monzo : List[int] or sympy.Matrix
        Vector of prime exponents.
    primes : List[int]
        Ordered list of prime numbers defining the basis.

    Returns
    -------
    Fraction
        The ratio represented by the monzo.

    Examples
    --------
    >>> ratio_from_monzo([-1, 1, 0], [2, 3, 5])
    Fraction(3, 2)
    
    >>> ratio_from_monzo([-2, 0, 1], [2, 3, 5])
    Fraction(5, 4)
    """
    if isinstance(monzo, sp.Matrix):
        monzo = [int(v) for v in monzo]
    
    numerator = 1
    denominator = 1
    for exp, prime in zip(monzo, primes):
        exp = int(exp)
        if exp > 0:
            numerator *= prime ** exp
        elif exp < 0:
            denominator *= prime ** (-exp)
    return Fraction(numerator, denominator)


def basis_matrix(primes: List[int], generators: List[Union[int, float, Fraction, str]]) -> sp.Matrix:
    """
    Construct the change-of-basis matrix from generator monzos.
    
    The columns of the matrix are the monzos (prime exponent vectors)
    of the generators.
    
    Parameters
    ----------
    primes : List[int]
        Ordered list of prime numbers defining the prime basis.
    generators : List[Fraction-like]
        List of generator ratios. Length must equal len(primes).

    Returns
    -------
    sympy.Matrix
        Square matrix where column i is the monzo of generator i.

    Examples
    --------
    >>> A = basis_matrix([2, 3, 5], ['2/1', '5/4', '6/5'])
    >>> A
    Matrix([
    [ 1, -2,  1],
    [ 0,  0,  1],
    [ 0,  1, -1]])
    """
    generators = [Fraction(g) for g in generators]
    cols = [monzo_from_ratio(g, primes) for g in generators]
    return sp.Matrix.hstack(*cols)


def is_unimodular(matrix: sp.Matrix) -> bool:
    """
    Check if an integer matrix is unimodular (det = +/-1).
    
    A unimodular matrix has an integer inverse, meaning it represents
    a valid change of basis that spans the same lattice.
    
    Parameters
    ----------
    matrix : sympy.Matrix
        Square integer matrix to check.

    Returns
    -------
    bool
        True if the matrix is unimodular (det = +/-1), False otherwise.

    Examples
    --------
    >>> A = basis_matrix([2, 3, 5], ['2/1', '5/4', '6/5'])
    >>> is_unimodular(A)
    True
    
    >>> A = basis_matrix([2, 3, 5], ['2/1', '3/2', '5/4'])
    >>> is_unimodular(A)
    False
    """
    det = int(matrix.det())
    return det in (1, -1)


def change_of_basis(
    primes: List[int], 
    generators: List[Union[int, float, Fraction, str]]
) -> Tuple[sp.Matrix, sp.Matrix]:
    """
    Compute the change-of-basis matrices for a generator set.
    
    Given a set of generators, returns both the forward transformation
    matrix A and its inverse A^-1 for converting between prime coordinates
    and generator coordinates.
    
    Parameters
    ----------
    primes : List[int]
        Ordered list of prime numbers defining the prime basis.
    generators : List[Fraction-like]
        List of generator ratios. Must form a unimodular basis.

    Returns
    -------
    Tuple[sympy.Matrix, sympy.Matrix]
        (A, A_inv) where:
        - A converts generator coords to prime coords: x = A @ y
        - A_inv converts prime coords to generator coords: y = A_inv @ x

    Raises
    ------
    ValueError
        If the generators do not form a unimodular basis.

    Examples
    --------
    >>> primes = [2, 3, 5]
    >>> generators = ['2/1', '5/4', '6/5']
    >>> A, A_inv = change_of_basis(primes, generators)
    >>> is_unimodular(A)
    True
    """
    primes = validate_primes(primes)
    generators = [Fraction(g) for g in generators]
    
    A = basis_matrix(primes, generators)
    det = int(A.det())
    
    if det not in (1, -1):
        raise ValueError(f"generator set is not unimodular (det={det})")
    
    return A, A.inv()


def prime_to_generator_coords(
    prime_coords: Union[List[int], sp.Matrix], 
    A_inv: sp.Matrix
) -> List[int]:
    """
    Convert prime coordinates to generator coordinates.
    
    Given a ratio expressed in prime coordinates (monzo), compute
    its representation in the generator basis.
    
    Parameters
    ----------
    prime_coords : List[int] or sympy.Matrix
        Prime exponent vector (monzo).
    A_inv : sympy.Matrix
        Inverse of the basis matrix (from change_of_basis).

    Returns
    -------
    List[int]
        Generator exponent vector.

    Raises
    ------
    ValueError
        If the result contains non-integer values (shouldn't happen
        for valid unimodular bases).

    Examples
    --------
    >>> A, A_inv = change_of_basis([2, 3, 5], ['2/1', '5/4', '6/5'])
    >>> prime_to_generator_coords([-2, 0, 1], A_inv)  # monzo of 5/4
    [0, 1, 0]
    """
    x = sp.Matrix([int(v) for v in prime_coords])
    y = A_inv * x
    
    if any(sp.denom(v) != 1 for v in y):
        raise ValueError("non-integer result (unexpected for unimodular bases)")
    
    return [int(v) for v in y]


def generator_to_prime_coords(
    gen_coords: Union[List[int], sp.Matrix], 
    A: sp.Matrix
) -> List[int]:
    """
    Convert generator coordinates to prime coordinates.
    
    Given a ratio expressed in the generator basis, compute
    its representation in prime coordinates (monzo).
    
    Parameters
    ----------
    gen_coords : List[int] or sympy.Matrix
        Generator exponent vector.
    A : sympy.Matrix
        The basis matrix (from change_of_basis).

    Returns
    -------
    List[int]
        Prime exponent vector (monzo).

    Raises
    ------
    ValueError
        If the result contains non-integer values (shouldn't happen
        for integer inputs).

    Examples
    --------
    >>> A, A_inv = change_of_basis([2, 3, 5], ['2/1', '5/4', '6/5'])
    >>> generator_to_prime_coords([0, 1, 0], A)  # 5/4 in generator coords
    [-2, 0, 1]
    """
    y = sp.Matrix([int(v) for v in gen_coords])
    x = A * y
    
    if any(sp.denom(v) != 1 for v in x):
        raise ValueError("non-integer result (unexpected)")
    
    return [int(v) for v in x]


def ratio_from_prime_coords(
    primes: List[int], 
    prime_coords: Union[List[int], sp.Matrix]
) -> Fraction:
    """
    Compute a ratio from its prime coordinates (monzo).
    
    This is an alias for ratio_from_monzo for clarity in coordinate
    conversion contexts.
    
    Parameters
    ----------
    primes : List[int]
        Ordered list of prime numbers defining the prime basis.
    prime_coords : List[int] or sympy.Matrix
        Prime exponent vector (monzo).

    Returns
    -------
    Fraction
        The ratio represented by the coordinates.

    Examples
    --------
    >>> ratio_from_prime_coords([2, 3, 5], [-2, 0, 1])
    Fraction(5, 4)
    """
    primes = validate_primes(primes)
    return ratio_from_monzo(prime_coords, primes)


def ratio_from_generator_coords(
    generators: List[Union[int, float, Fraction, str]], 
    gen_coords: Union[List[int], sp.Matrix]
) -> Fraction:
    """
    Compute a ratio from its generator coordinates.
    
    Parameters
    ----------
    generators : List[Fraction-like]
        The generator ratios defining the basis.
    gen_coords : List[int] or sympy.Matrix
        Generator exponent vector.

    Returns
    -------
    Fraction
        The ratio represented by the coordinates.

    Examples
    --------
    >>> generators = ['2/1', '5/4', '6/5']
    >>> ratio_from_generator_coords(generators, [0, 1, 1])
    Fraction(3, 2)
    """
    generators = [Fraction(g) for g in generators]
    
    if isinstance(gen_coords, sp.Matrix):
        gen_coords = [int(v) for v in gen_coords]
    
    result = Fraction(1, 1)
    for g, e in zip(generators, gen_coords):
        e = int(e)
        if e != 0:
            result *= g ** e
    
    return result
