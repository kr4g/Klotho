from fractions import Fraction
from sympy import factorint
from typing import Union, Dict

def to_factors(value: Union[int, Fraction, str]) -> Dict[int, int]:
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
    numerator = 1
    denominator = 1
    for prime, exp in factors.items():
        if exp > 0:
            numerator *= prime ** exp
        elif exp < 0:
            denominator *= prime ** (-exp)
    return Fraction(numerator, denominator)
