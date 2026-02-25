from enum import Enum, EnumMeta
import numpy as np

class DirectValueEnumMeta(EnumMeta):
  """
  Metaclass that returns member values directly on attribute access.

  When accessing a member through the class, the raw value is returned
  instead of the enum member instance.
  """

  def __getattribute__(cls, name):
    member = super().__getattribute__(name)
    if isinstance(member, cls):
      return member.value
    return member

class MinMaxEnum(Enum):
    """
    Enum whose members store ``(min, max)`` tuples and support arithmetic.

    Provides ``min`` and ``max`` properties for convenient access, scalar
    multiplication, and callable random sampling from the uniform
    distribution over the range.

    Examples
    --------
    >>> class Dynamics(MinMaxEnum):
    ...     pp = (0.1, 0.3)
    ...     ff = (0.7, 0.9)
    >>> Dynamics.pp.min
    0.1
    >>> Dynamics.pp.max
    0.3
    """

    @property
    def min(self):
        """float : Lower bound of the range."""
        return self.value[0]

    @property
    def max(self):
        """float : Upper bound of the range."""
        return self.value[1]
    
    def __repr__(self):
        """Return a string representation of the range tuple."""
        return repr(self.value)
    
    def __mul__(self, other):
        """
        Scale both bounds by a numeric factor.

        Parameters
        ----------
        other : int or float
            Scalar multiplier.

        Returns
        -------
        tuple of float
            ``(min * other, max * other)``.
        """
        if isinstance(other, (int, float)):
            return (self.min * other, self.max * other)
        return NotImplemented

    def __rmul__(self, other):
        """Support ``scalar * member`` via :meth:`__mul__`."""
        return self.__mul__(other)
    
    def __call__(self):
        """
        Sample a random value uniformly from ``[min, max]``.

        Returns
        -------
        float
            A random value in the range.
        """
        return np.random.uniform(self.min, self.max)
