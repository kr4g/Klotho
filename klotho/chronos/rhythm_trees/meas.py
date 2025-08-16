from fractions import Fraction
from math import gcd
from numbers import Rational

class Meas:
    '''
    Time signature class that preserves unreduced fractions.
    Similar to Python's Fraction class, but for musical time signatures.
    '''
    def __init__(self, numerator, denominator=None):
        match (numerator, denominator):
            case (Meas() as m, None):
                self._numerator, self._denominator = m.numerator, m.denominator
            case (Fraction() as f, None):
                self._numerator, self._denominator = f.numerator, f.denominator
            case (int() as n, None):
                self._numerator, self._denominator = n, 1
            case (float() as f, None):
                frac = Fraction(f).limit_denominator()
                self._numerator, self._denominator = frac.numerator, frac.denominator
            case (str() as s, None):
                try:
                    num, den = map(int, s.replace('//', '/').split('/'))
                    self._numerator, self._denominator = num, den
                except ValueError:
                    raise ValueError('Invalid time signature format')
            case (int() as num, int() as den):
                self._numerator, self._denominator = num, den
            case _:
                raise ValueError('Invalid time signature arguments')

        if self._denominator == 0:
            raise ValueError('Time signature denominator cannot be zero')

    @property
    def numerator(self):
        return self._numerator

    @property
    def denominator(self):
        return self._denominator
    
    def __add__(self, other):
        match other:
            case Meas() | Fraction():
                common_denominator = self._denominator * other.denominator
                new_numerator = (self._numerator * other.denominator) + (other.numerator * self._denominator)
                divisor = gcd(self._denominator, other.denominator)
                new_numerator = new_numerator // divisor
                common_denominator = common_denominator // divisor
                return Meas(new_numerator, common_denominator)
            case int():
                return Meas(self._numerator + (other * self._denominator), self._denominator)
            case float():
                return self + Meas(other)
            case str():
                try:
                    return self + Meas(other)
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        match other:
            case Meas() | Fraction():
                common_denominator = self._denominator * other.denominator
                new_numerator = (self._numerator * other.denominator) - (other.numerator * self._denominator)
                divisor = gcd(self._denominator, other.denominator)
                new_numerator = new_numerator // divisor
                common_denominator = common_denominator // divisor
                return Meas(new_numerator, common_denominator)
            case int():
                return Meas(self._numerator - (other * self._denominator), self._denominator)
            case float():
                return self - Meas(other)
            case str():
                try:
                    return self - Meas(other)
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __rsub__(self, other):
        match other:
            case int():
                return Meas((other * self._denominator) - self._numerator, self._denominator)
            case float():
                return Meas(other) - self
            case str():
                try:
                    return Meas(other) - self
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __mul__(self, other):
        match other:
            case Meas() | Fraction():
                new_numerator = self._numerator * other.numerator
                new_denominator = self._denominator * other.denominator
                divisor = gcd(new_numerator, new_denominator)
                return Meas(new_numerator // divisor, new_denominator // divisor)
            case int():
                new_numerator = self._numerator * other
                divisor = gcd(new_numerator, self._denominator)
                return Meas(new_numerator // divisor, self._denominator // divisor)
            case float():
                return self * Meas(other)
            case str():
                try:
                    return self * Meas(other)
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        match other:
            case Meas() | Fraction():
                if other.numerator == 0:
                    raise ZeroDivisionError("division by zero")
                new_numerator = self._numerator * other.denominator
                new_denominator = self._denominator * other.numerator
                divisor = gcd(new_numerator, new_denominator)
                return Meas(new_numerator // divisor, new_denominator // divisor)
            case int():
                if other == 0:
                    raise ZeroDivisionError("division by zero")
                new_denominator = self._denominator * other
                divisor = gcd(self._numerator, new_denominator)
                return Meas(self._numerator // divisor, new_denominator // divisor)
            case float():
                if other == 0:
                    raise ZeroDivisionError("division by zero")
                return self / Meas(other)
            case str():
                try:
                    return self / Meas(other)
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __rtruediv__(self, other):
        if self._numerator == 0:
            raise ZeroDivisionError("division by zero")
        match other:
            case int():
                new_numerator = other * self._denominator
                divisor = gcd(new_numerator, self._numerator)
                return Meas(new_numerator // divisor, self._numerator // divisor)
            case float():
                return Meas(other) / self
            case str():
                try:
                    return Meas(other) / self
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __eq__(self, other):
        """Strict equality - exact same time signature representation"""
        match other:
            case Meas() | Fraction():
                return (self._numerator == other.numerator and 
                       self._denominator == other.denominator)
            case int():
                return self._numerator == other * self._denominator
            case float():
                try:
                    return self == Meas(other)
                except ValueError:
                    return False
            case str():
                try:
                    return self == Meas(other)
                except ValueError:
                    return False
            case _:
                return NotImplemented
    
    def __abs__(self):
        return Meas(abs(self._numerator), abs(self._denominator))
    
    def __neg__(self):
        return Meas(-self._numerator, self._denominator)

    def is_equivalent(self, other) -> bool:
        """Check if two time signatures represent the same metric proportion"""
        match other:
            case Meas() | Fraction():
                return (self._numerator * other.denominator == 
                       other.numerator * self._denominator)
            case str():
                try:
                    return self.is_equivalent(Meas(other))
                except ValueError:
                    return False
            case _:
                return False

    def to_fraction(self):
        return Fraction(self._numerator, self._denominator)

    def _as_fraction(self):
        """Special method that Fraction constructor looks for"""
        return Fraction(self._numerator, self._denominator)

    def reduced(self):
        """Return a new Meas with reduced form"""
        return Meas(self.to_fraction().limit_denominator())
    
    def __str__(self):
        return f'{self._numerator}/{self._denominator}'

    def __repr__(self) -> str:
        return self.__str__()
    
    def __float__(self):
        return self._numerator / self._denominator


Rational.register(Meas)
    