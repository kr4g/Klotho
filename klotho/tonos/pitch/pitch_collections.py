from __future__ import annotations

import math
from abc import ABC, abstractmethod
from fractions import Fraction
from typing import Iterable, List, Optional, Sequence, Union

import numpy as np

from .pitch import Pitch


def _interval_to_shift(interval):
    """Normalize a transposition interval to ``('ratio', Fraction)`` or
    ``('cents', float)``.

    Accepts the same domain as :meth:`Pitch.transpose` (Fraction, int,
    str, float, ``Ratio``, ``Cent``). Ratio-like inputs stay exact
    Fractions so ratio-mode degrees keep exact arithmetic.
    """
    from ..types import Cent, Ratio
    if isinstance(interval, Cent):
        return 'cents', float(interval.magnitude)
    if isinstance(interval, Ratio):
        mag = interval.magnitude
        return 'ratio', mag if isinstance(mag, Fraction) else Fraction(mag)
    return 'ratio', Fraction(interval)

IntervalType = Union[float, Fraction]
DegreeList = Union[List[float], List[Fraction], List[int], List[str]]
PitchList = Union[List[Pitch], List[str]]


MAX_EQUAVE_DENOMINATOR = 10 ** 6
"""Denominator ceiling when a float equave is turned into an exact ratio.

``Fraction(1.0594630943592953)`` is exact in binary and therefore enormous:
a 53-bit numerator over a 52-bit denominator. Reducing by such a ratio adds
about 105 bits per division, so a scale built on one becomes too large to
print long before it becomes slow to build. ``limit_denominator`` keeps the
equave compact; the cost is an error under 1e-12 relative, which is under a
millionth of a cent -- far below anything audible or notatable.
"""


def _resolve_equave(equave: Union[float, Fraction, int, str],
                    interval_type: str = 'ratios',
                    where: str = 'equave') -> Union[Fraction, float]:
    """Resolve an equave argument into the form *interval_type* works in.

    **The declared mode decides. Nothing is inferred from a Python type.**
    (Ryan, 2026-09-01.) ``Scale``, ``Chord``, ``Voicing`` and
    ``RelativePitchCollection`` all carry an explicit ``interval_type``
    selector, validated to be exactly ``'ratios'`` or ``'cents'``, so there
    is nothing here for a type to disambiguate:

    * In ``'ratios'`` mode the equave is a RATIO, in every spelling.
      ``2``, ``2.0``, ``Fraction(2, 1)`` and ``'2/1'`` are all the octave.
    * In ``'cents'`` mode the equave is a CENTS value. ``1200.0`` is the
      octave and ``1901.955`` the Bohlen-Pierce tritave. A plain ``int`` or
      ``float`` is fine; both are cents.
    * The one real category error is a FRACTION in cents mode -- a
      ``Fraction`` instance, or a string in fraction format such as
      ``'3/1'``. A ratio written in a field that means cents is a mistake,
      not an ambiguity, and it is refused with both readings spelled out
      rather than guessed at in either direction.

    Deciding this separately at each use site is what let a cents number be
    used directly as a ratio, and let a ratio equave be stored as that many
    cents. Resolve once, here, and no caller has to guess again.

    Parameters
    ----------
    equave : float, Fraction, int, or str
        The raw equave argument, before any mode-specific handling.
    interval_type : str, optional
        ``'ratios'`` or ``'cents'``. Default ``'ratios'``.
    where : str, optional
        Name of the caller, used in refusal messages (e.g. ``'Scale'``).

    Returns
    -------
    Fraction or float
        A ``Fraction`` ratio in ``'ratios'`` mode; a cents ``float`` in
        ``'cents'`` mode.

    Raises
    ------
    ValueError
        If the equave cannot be parsed; if it is not above the unison (an
        equave of 1 or less never walks a value into range, so the reduction
        loop would never end); or, in cents mode, if it is written as a
        fraction.

    Examples
    --------
    >>> _resolve_equave('3/1')
    Fraction(3, 1)
    >>> _resolve_equave(3)
    Fraction(3, 1)
    >>> _resolve_equave(3.0)
    Fraction(3, 1)
    >>> _resolve_equave(1901.955, 'cents')
    1901.955
    >>> _resolve_equave(3, 'cents')
    3.0
    """
    from ..utils.interval_normalization import (
        _refuse_degenerate_equave,
        _refuse_ratio_equave_in_cents_mode,
    )

    if interval_type == 'cents':
        if isinstance(equave, Fraction) or (isinstance(equave, str) and '/' in equave):
            raise _refuse_ratio_equave_in_cents_mode(where, equave)
        try:
            cents = float(equave)
        except (TypeError, ValueError):
            raise ValueError(f"Cannot parse equave value: {equave!r}")
        if not math.isfinite(cents) or cents <= 0.0:
            raise _refuse_degenerate_equave(where, equave)
        return cents

    if isinstance(equave, Fraction):
        ratio = equave
    elif isinstance(equave, bool):
        raise ValueError(f"Cannot parse equave value: {equave!r}")
    elif isinstance(equave, int):
        ratio = Fraction(equave, 1)
    elif isinstance(equave, float):
        if not math.isfinite(equave):
            raise _refuse_degenerate_equave(where, equave)
        # Bounded so the ratio stays compact; see MAX_EQUAVE_DENOMINATOR.
        # An equave that is already a tidy ratio (2.0, 1.5, 3.0) is exact
        # in binary and survives this untouched.
        ratio = Fraction(equave).limit_denominator(MAX_EQUAVE_DENOMINATOR)
    else:
        try:
            ratio = Fraction(equave)
        except (TypeError, ValueError, ZeroDivisionError):
            raise ValueError(f"Cannot parse equave value: {equave!r}")

    if ratio <= 1:
        raise _refuse_degenerate_equave(where, equave)
    return ratio


def _convert_degree(value: Union[float, Fraction, int, str]) -> Union[float, Fraction]:
    """
    Convert a scale degree value to a float or Fraction.

    Parameters
    ----------
    value : float, Fraction, int, or str
        The degree value to convert. Strings containing ``'/'`` are
        interpreted as fractions.

    Returns
    -------
    float or Fraction
        The converted degree value.

    Raises
    ------
    ValueError
        If the value cannot be converted.
    """
    if isinstance(value, float):
        return value
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str) and '/' in value:
        return Fraction(value)
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"Cannot convert {value} to either a float or Fraction")


_DEFAULT_REFERENCE = 'C4'


def _resolve_reference(reference_pitch: Union[Pitch, str, None]) -> Pitch:
    """Resolve a reference-pitch argument, defaulting ``None`` to C4.

    Relative collections always carry a reference pitch; ``None`` in a
    constructor signature means "use the default root," not "rootless."
    """
    if reference_pitch is None:
        return Pitch(_DEFAULT_REFERENCE)
    return Pitch(reference_pitch) if isinstance(reference_pitch, str) else reference_pitch


class PitchCollectionBase(ABC):
    """
    Abstract base class for all pitch collections.

    Defines the common interface for both relative (interval-based) and
    absolute (pitch-based) collections, including properties for degrees,
    pitches, intervals, equave, and indexing operations.
    """

    @property
    @abstractmethod
    def is_relative(self) -> bool:
        """bool : True when degrees are intervals relative to the reference pitch."""
        raise NotImplementedError

    @property
    @abstractmethod
    def reference_pitch(self) -> Optional[Pitch]:
        """Pitch : The pitch anchoring this collection (defaults to C4)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def equave(self) -> Union[float, Fraction]:
        """Fraction or float : The interval of equivalence (ratio or cents)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def equave_cyclic(self) -> bool:
        """bool : Whether out-of-range indexing wraps through equaves."""
        raise NotImplementedError

    @property
    @abstractmethod
    def degrees(self) -> List[Union[Pitch, IntervalType]]:
        """list : The defining degrees (intervals when relative, pitches when absolute)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def pitches(self) -> List[Pitch]:
        """list of Pitch : Concrete pitches resolved at the reference pitch."""
        raise NotImplementedError

    @property
    @abstractmethod
    def intervals(self) -> List[IntervalType]:
        """list : Successive intervals between adjacent degrees."""
        raise NotImplementedError

    @abstractmethod
    def __len__(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]):
        raise NotImplementedError

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def __call__(self, index: Union[int, Sequence[int]]):
        return self[index]

    @property
    def freqs(self) -> tuple:
        """tuple of float : Concrete frequencies of the collection's pitches.

        A tuple, so ``freq=coll.freqs`` produces a simultaneity (chord)
        when assigned to the ``freq`` pfield; wrap in ``Pattern(...)`` to
        cycle the frequencies across events instead.
        """
        return tuple(float(p.freq) for p in self.pitches)

    def equave_shift(self, n: int):
        """
        Return a copy of this collection shifted by *n* equaves.

        Delegates to :meth:`transpose` with the collection's own equave,
        so the shift carrier follows the type: the degrees for
        ``Voicing`` and plain relative collections, the reference pitch
        for ``Chord`` and ``Scale`` (whose degrees stay equave-reduced),
        and the pitches themselves for absolute collections.

        Parameters
        ----------
        n : int
            Number of equaves to shift (negative shifts down).

        Returns
        -------
        Same type as ``self``
        """
        equave = self.equave
        if isinstance(equave, float):
            from ..types import cent
            return self.transpose(cent(n * equave))
        return self.transpose(Fraction(equave) ** n)

    def _flatten_indices(self, index: Iterable) -> List[int]:
        result: List[int] = []
        for item in index:
            if hasattr(item, '__iter__') and not isinstance(item, (str, int)):
                result.extend(self._flatten_indices(item))
            else:
                result.append(int(item))
        return result

    def index(self, value: Union[Pitch, float, Fraction, int, str], start: int = 0, stop: Optional[int] = None) -> int:
        """
        Return the index of the first occurrence of *value* in the collection.

        Parameters
        ----------
        value : Pitch, float, Fraction, int, or str
            The value to search for. Interpreted as a degree for relative
            collections without a reference pitch, or as a Pitch otherwise.
        start : int, optional
            Index at which to begin the search. Default is 0.
        stop : int or None, optional
            Index at which to stop searching. Default is None (end).

        Returns
        -------
        int
            The index of the matching element.

        Raises
        ------
        ValueError
            If the value is not found in the collection.
        """
        if self.is_relative and not isinstance(value, Pitch):
            try:
                target = _convert_degree(value)
            except ValueError:
                target = None
            if target is not None:
                degrees = self.degrees
                if degrees:
                    if isinstance(target, Fraction) and isinstance(degrees[0], float):
                        target = float(target)
                    elif isinstance(target, float) and isinstance(degrees[0], Fraction):
                        target = Fraction.from_float(target)
                for i, degree in enumerate(degrees):
                    if i < start:
                        continue
                    if stop is not None and i >= stop:
                        break
                    if isinstance(degree, float):
                        if abs(degree - target) < 1e-6:
                            return i
                    else:
                        if degree == target:
                            return i
                raise ValueError(f"Value {value} not found in collection")
        target_pitch = value if isinstance(value, Pitch) else Pitch(value)
        for i, pitch in enumerate(self.pitches):
            if i < start:
                continue
            if stop is not None and i >= stop:
                break
            if abs(pitch.freq - target_pitch.freq) < 1e-6:
                return i
        raise ValueError(f"Value {value} not found in collection")


class EquaveCyclicMixin:
    """Mixin that enables equave-cyclic indexing by default."""

    _equave_cyclic_enabled = True


class RelativePitchCollection(PitchCollectionBase):
    """
    A collection of pitches defined by interval degrees relative to a root.

    Degrees are stored as ratios (``Fraction``) or cents (``float``) and are
    always anchored to a reference pitch (default C4) that resolves concrete
    ``Pitch`` objects. ``.degrees`` is the interval structure; ``.pitches``
    / ``.freqs`` are the realization. Supports equave-cyclic indexing when
    enabled.

    Parameters
    ----------
    degrees : list of float, Fraction, int, or str
        Scale/chord degrees as ratios or cent values.
    interval_type : str, optional
        ``"ratios"`` or ``"cents"``. Default is ``"ratios"``.
    equave : float, Fraction, int, str, or None, optional
        Interval of equivalence. When provided, equave-cyclic indexing
        is enabled. **The mode decides how it is read, not its Python
        type.** In ``"ratios"`` mode it is a ratio in every spelling, so
        ``3``, ``3.0``, ``Fraction(3, 1)`` and ``'3/1'`` are all the
        tritave. In ``"cents"`` mode it is a cents value, so the tritave is
        ``1901.955``; a fraction there is refused.
    reference_pitch : Pitch, str, or None, optional
        The root pitch. ``None`` (default) resolves to C4.

    Examples
    --------
    >>> coll = RelativePitchCollection(["1/1", "5/4", "3/2"])
    >>> coll.degrees
    [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]
    >>> coll[0]
    Pitch(C4, 261.63 Hz)
    """
    _equave_cyclic_enabled: Optional[bool] = None

    def __init__(
        self,
        degrees: DegreeList,
        interval_type: str = "ratios",
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ):
        if interval_type not in ["ratios", "cents"]:
            raise ValueError("interval_type must be 'ratios' or 'cents'")

        equave_cyclic = equave is not None
        equave_value: Union[float, Fraction]
        if equave is None:
            equave_value = 1200.0 if interval_type == "cents" else Fraction(2, 1)
        else:
            # The declared mode decides, and it decides once. Guessing the
            # raw type separately per branch used to turn a ratio equave into
            # a cents value of the same number -- equave=3 stored as 3 cents.
            equave_value = _resolve_equave(equave, interval_type, type(self).__name__)
        converted = [_convert_degree(d) for d in degrees] if degrees else []

        if interval_type == "cents":
            converted = [float(d) if isinstance(d, Fraction) else float(d) for d in converted]
        else:
            converted = [
                d if isinstance(d, Fraction)
                else Fraction(d) if isinstance(d, int)
                else d
                for d in converted
            ]

        if self._equave_cyclic_enabled is not None:
            equave_cyclic = self._equave_cyclic_enabled

        self._equave = equave_value
        self._equave_cyclic = equave_cyclic
        self._degrees = converted
        self._interval_type_mode = interval_type
        self._reference_pitch = _resolve_reference(reference_pitch)
        self._intervals = self._compute_intervals_relative()

    @classmethod
    def from_degrees(
        cls,
        degrees: DegreeList,
        interval_type: str = "ratios",
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ) -> "RelativePitchCollection":
        """
        Construct from an explicit list of cumulative degrees.

        Parameters
        ----------
        degrees : list
            Cumulative degree values (ratios or cents).
        interval_type : str, optional
            ``"ratios"`` or ``"cents"``.
        equave : float, Fraction, int, str, or None, optional
            Interval of equivalence.
        reference_pitch : Pitch, str, or None, optional
            Optional root pitch.

        Returns
        -------
        RelativePitchCollection
        """
        return cls(degrees, interval_type, equave, reference_pitch)

    @classmethod
    def from_intervals(
        cls,
        intervals: DegreeList,
        interval_type: str = "ratios",
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ) -> "RelativePitchCollection":
        """
        Construct from successive intervals (step sizes) rather than cumulative degrees.

        Parameters
        ----------
        intervals : list
            Successive interval values (ratios or cents).
        interval_type : str, optional
            ``"ratios"`` or ``"cents"``.
        equave : float, Fraction, int, str, or None, optional
            Interval of equivalence.
        reference_pitch : Pitch, str, or None, optional
            Optional root pitch.

        Returns
        -------
        RelativePitchCollection
        """
        if not intervals:
            return cls.from_degrees([], interval_type, equave, reference_pitch)

        degrees: List[IntervalType] = []
        if interval_type == "cents":
            current = 0.0
            degrees = [current]
            for interval in intervals:
                current += float(_convert_degree(interval))
                degrees.append(current)
        else:
            current = Fraction(1, 1)
            degrees = [current]
            for interval in intervals:
                val = _convert_degree(interval)
                current = current * val
                degrees.append(current)

        return cls.from_degrees(degrees, interval_type, equave, reference_pitch)

    @classmethod
    def from_setclass(
        cls,
        pcs: List[int],
        mod: int = 12,
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ) -> "RelativePitchCollection":
        """
        Construct from pitch-class integers in an equal-tempered system.

        Parameters
        ----------
        pcs : list of int
            Pitch-class integers (e.g., ``[0, 4, 7]`` for a major triad
            in 12-TET).
        mod : int, optional
            Number of divisions per equave. Default is 12.
        equave : float, Fraction, int, str, or None, optional
            Override equave in cents. Defaults to ``mod * 100``.
        reference_pitch : Pitch, str, or None, optional
            Optional root pitch.

        Returns
        -------
        RelativePitchCollection
        """
        equave_cents = float(mod * 100)
        step_size = equave_cents / mod
        degrees = [float(pc * step_size) for pc in pcs]
        target_equave = equave if equave is not None else equave_cents
        return cls.from_degrees(degrees, "cents", target_equave, reference_pitch)

    def _compute_intervals_relative(self) -> List[IntervalType]:
        if not self._degrees or len(self._degrees) <= 1:
            return []
        result: List[IntervalType] = []
        if self._interval_type_mode == "cents":
            for i in range(1, len(self._degrees)):
                result.append(self._degrees[i] - self._degrees[i - 1])
        else:
            for i in range(1, len(self._degrees)):
                prev_degree = self._degrees[i - 1]
                if prev_degree == 0 or (isinstance(prev_degree, Fraction) and prev_degree.numerator == 0):
                    result.append(Fraction(0, 1))
                else:
                    result.append(self._degrees[i] / prev_degree)
        return result

    @property
    def is_relative(self) -> bool:
        """bool : Always True for relative collections."""
        return True

    @property
    def reference_pitch(self) -> Pitch:
        """Pitch : The reference pitch anchoring the collection."""
        return self._reference_pitch

    @property
    def equave(self) -> Union[float, Fraction]:
        """float or Fraction : The interval of equivalence."""
        return self._equave

    @property
    def equave_cyclic(self) -> bool:
        """bool : Whether indexing wraps around the equave."""
        return self._equave_cyclic

    @property
    def degrees(self) -> List[IntervalType]:
        """list : The cumulative degree values (ratios or cents)."""
        return list(self._degrees)

    @property
    def pitches(self) -> List[Pitch]:
        """list of Pitch : Concrete pitches resolved from degrees and the
        reference pitch.

        Memoized on the identity of the degree list and reference pitch
        (both are only ever rebound, never mutated — ``root()`` shallow-
        copies and rebinds the reference, which invalidates naturally).
        Pitch objects are immutable, so sharing them across accesses is
        safe; a fresh outer list is returned each call.
        """
        cached = self.__dict__.get('_pitches_cache')
        if (cached is not None and cached[0] is self._degrees
                and cached[1] is self._reference_pitch):
            return list(cached[2])
        value = [self._calculate_pitch(i) for i in range(len(self._degrees))]
        self.__dict__['_pitches_cache'] = (self._degrees, self._reference_pitch, value)
        return list(value)

    @property
    def intervals(self) -> List[IntervalType]:
        """list : Successive intervals between adjacent degrees."""
        return self._intervals

    @property
    def degree_dtype(self) -> Optional[type]:
        """type or None : The Python type of the stored degrees (float or Fraction)."""
        if self._degrees:
            return type(self._degrees[0])
        return None

    def root(self, pitch: Union[Pitch, str]) -> "RelativePitchCollection":
        """
        Return a copy of this collection rooted at the given pitch.

        Parameters
        ----------
        pitch : Pitch or str
            The pitch to use as the reference root.

        Returns
        -------
        RelativePitchCollection
        """
        rooted = RelativePitchCollection(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            pitch,
        )
        rooted._equave_cyclic = self._equave_cyclic
        return rooted

    def transpose(self, interval) -> "RelativePitchCollection":
        """
        Return a copy transposed by *interval*, carried in the degrees.

        The reference pitch is unchanged: every degree is multiplied by
        the interval (ratios mode) or offset by it (cents mode), so the
        register survives a later :meth:`root`. ``Chord`` and ``Scale``
        override this with reference-pitch transposition, since their
        degrees stay equave-reduced. A cents interval on a ratios-mode
        collection converts the degrees to floats.

        Parameters
        ----------
        interval : Fraction, int, float, str, Ratio, or Cent
            The transposition interval, as in :meth:`Pitch.transpose`.

        Returns
        -------
        Same type as ``self``
        """
        kind, value = _interval_to_shift(interval)
        if self._interval_type_mode == "cents":
            delta = value if kind == 'cents' else 1200.0 * math.log2(float(value))
            new_degrees = [d + delta for d in self._degrees]
        else:
            factor = value if kind == 'ratio' else 2.0 ** (value / 1200.0)
            new_degrees = [d * factor for d in self._degrees]
        out = type(self)(new_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        out._equave_cyclic = self._equave_cyclic
        return out

    def as_voicing(self):
        """
        Convert to a :class:`~klotho.tonos.chords.chord.Voicing`.

        Sorts the degrees but does NOT equave-reduce, so multi-octave
        spreads survive. The reference pitch carries over.

        Duplicate degrees are removed, EXCEPT when ``self`` is itself a
        ``Voicing`` built with ``dedupe=False``: that voicing's stored
        policy is carried, so a deliberately doubled voice survives the
        conversion. A collection with no such policy (this base class,
        ``Chord``, a slice) gets ``Voicing``'s documented default.

        Returns
        -------
        Voicing
        """
        from klotho.tonos.chords.chord import Voicing
        # getattr rather than isinstance(self, Voicing): "has a stored
        # policy" is the question, and it is the same question for every
        # collection that grows one later. Absent policy == the default,
        # which is what every non-Voicing source here already got.
        return Voicing(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            self._reference_pitch,
            dedupe=getattr(self, '_dedupe', True),
        )

    def _get_cyclic_index(self, index: int) -> tuple:
        if not self._equave_cyclic:
            return 0, index
        size = len(self)
        if size == 0:
            raise IndexError("Cannot index an empty collection")
        return index // size, index % size

    def _calculate_degree_with_shift(self, equave_shift: int, wrapped_index: int) -> IntervalType:
        degree = self._degrees[wrapped_index]
        if self._interval_type_mode == "cents":
            equave_cents = self._equave if isinstance(self._equave, float) else 1200.0
            return degree + (equave_shift * equave_cents)
        equave_ratio = self._equave if isinstance(self._equave, Fraction) else Fraction(2, 1)
        return degree * (equave_ratio ** equave_shift)

    def _calculate_pitch(self, index: int) -> Pitch:
        if self._equave_cyclic:
            equave_shift, wrapped_index = self._get_cyclic_index(index)
            degree = self._calculate_degree_with_shift(equave_shift, wrapped_index)
        else:
            degree = self._degrees[index]
        if self._interval_type_mode == "cents":
            freq = self._reference_pitch.freq * (2 ** (float(degree) / 1200))
            partial = 2 ** (float(degree) / 1200)
        else:
            freq = self._reference_pitch.freq * float(degree)
            partial = degree
        # exact frequency preserved: from_freq would re-derive it from the
        # symbolic name rounded to 4 decimals, discarding the exact value
        return Pitch._from_exact_freq(freq, partial)

    def __len__(self) -> int:
        return len(self._degrees)

    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]):
        if isinstance(index, slice):
            return self._getitem_slice(index)
        if hasattr(index, '__iter__') and not isinstance(index, str):
            flat_indices = self._flatten_indices(index)
            return self._getitem_sequence(flat_indices)
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        return self._getitem_single(index)

    def _getitem_single(self, index: int) -> Pitch:
        return self._calculate_pitch(index)

    def _getitem_slice(self, index: slice):
        size = len(self)
        if size == 0:
            empty = RelativePitchCollection([], self._interval_type_mode, self._equave, self._reference_pitch)
            empty._equave_cyclic = False
            return empty
        start, stop, step = index.indices(size)
        use_cyclic = self._equave_cyclic and index.stop is not None and abs(index.stop) > size
        if use_cyclic:
            indices = list(range(index.start or 0, index.stop, step))
            selected_degrees = [
                self._calculate_degree_with_shift(*self._get_cyclic_index(i))
                for i in indices
            ]
        else:
            selected_degrees = [self._degrees[i] for i in range(start, stop, step)]
        subset = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        subset._equave_cyclic = False
        return subset

    def _getitem_sequence(self, indices: Sequence[int]):
        selected_degrees = []
        for i in indices:
            idx = int(i) if not isinstance(i, int) else i
            if self._equave_cyclic:
                selected_degrees.append(self._calculate_degree_with_shift(*self._get_cyclic_index(idx)))
            else:
                selected_degrees.append(self._degrees[idx])
        subset = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        subset._equave_cyclic = False
        return subset

    def __repr__(self) -> str:
        size = len(self._degrees)
        degrees_str = ", ".join(str(d) for d in self._degrees[:8])
        if size > 8:
            degrees_str += ", ..."
        ref = self._reference_pitch
        if abs(ref.cents_offset) > 0.01:
            root_str = f"{ref.pitchclass}{ref.octave} ({ref.cents_offset:+.1f}¢)"
        else:
            root_str = f"{ref.pitchclass}{ref.octave}"
        return f"{self.__class__.__name__}([{degrees_str}], equave={self._equave}, root={root_str})"


class AbsolutePitchCollection(PitchCollectionBase):
    """
    A collection defined by concrete ``Pitch`` objects rather than intervals.

    Intervals are derived from successive pitch frequencies rather than
    stored directly. Supports equave-cyclic indexing when an equave is
    provided.

    Parameters
    ----------
    pitches : list of Pitch or str
        The pitches in the collection.
    equave : float, Fraction, int, str, or None, optional
        Interval of equivalence for cyclic indexing, as a RATIO in every
        spelling -- ``2``, ``2.0``, ``Fraction(2, 1)`` and ``'2/1'`` are all
        the octave. This class has no ``interval_type`` selector, so there is
        no cents reading of the argument here.
    reference_pitch : Pitch, str, or None, optional
        Optional reference pitch for partial calculations.
    """

    def __init__(
        self,
        pitches: PitchList,
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ):
        # AbsolutePitchCollection has no interval_type selector, so it is one
        # of the mode-less surfaces where a bare equave is a RATIO -- the same
        # convention as equave_reduce(), ToneLattice and Tonnetz. Resolving it
        # here rather than storing the raw argument is what keeps as_voicing()
        # able to hand a cents-mode Voicing a cents number (see below): the
        # stored value now has one known meaning instead of two.
        self._equave = (_resolve_equave(equave, 'ratios', 'AbsolutePitchCollection')
                        if equave is not None else Fraction(2, 1))
        self._equave_cyclic = equave is not None
        self._reference_pitch = Pitch(reference_pitch) if isinstance(reference_pitch, str) else reference_pitch

        self._pitches: List[Pitch] = []
        for p in pitches:
            if isinstance(p, str):
                self._pitches.append(Pitch(p))
            elif isinstance(p, Pitch):
                self._pitches.append(p)
            else:
                raise TypeError(f"Expected Pitch or str, got {type(p)}")

        if self._reference_pitch is not None:
            self._pitches = [p.with_partial(p.freq / self._reference_pitch.freq) for p in self._pitches]

        self._intervals = self._compute_intervals_absolute()

    def _compute_intervals_absolute(self) -> List[float]:
        if len(self._pitches) <= 1:
            return []
        return [self._pitches[i].cents_difference(self._pitches[i - 1]) for i in range(1, len(self._pitches))]

    @property
    def is_relative(self) -> bool:
        """bool : Always False for absolute collections."""
        return False

    @property
    def reference_pitch(self) -> Optional[Pitch]:
        """Pitch or None : The reference pitch."""
        return self._reference_pitch

    @property
    def equave(self) -> Union[float, Fraction]:
        """float or Fraction : The interval of equivalence."""
        return self._equave

    @property
    def equave_cyclic(self) -> bool:
        """bool : Whether indexing wraps around the equave."""
        return self._equave_cyclic

    @property
    def degrees(self) -> List[float]:
        """list of float : Cents of each pitch relative to the reference
        pitch (or the first pitch when no reference is set).

        Degrees are always raw interval values; use ``pitches`` / ``freqs``
        for the concrete realization.
        """
        if not self._pitches:
            return []
        ref = self._reference_pitch if self._reference_pitch is not None else self._pitches[0]
        return [p.cents_difference(ref) for p in self._pitches]

    @property
    def degree_dtype(self) -> Optional[type]:
        """type or None : Absolute collections express degrees in cents (float)."""
        return float if self._pitches else None

    @property
    def pitches(self) -> List[Pitch]:
        """list of Pitch : The stored pitch objects."""
        return list(self._pitches)

    @property
    def intervals(self) -> List[float]:
        """list of float : Successive intervals in cents between adjacent pitches."""
        return self._intervals

    def as_voicing(self):
        """
        Convert to a :class:`~klotho.tonos.chords.chord.Voicing` (cents
        degrees relative to the reference or first pitch; dedupe + sort,
        no equave reduction).

        Returns
        -------
        Voicing
        """
        from klotho.tonos.chords.chord import Voicing
        # The Voicing is built in CENTS, while this collection stores its
        # equave as a RATIO. Handing the ratio straight across would ask a
        # cents-mode constructor to read a fraction, which it refuses; before
        # the refusal existed it silently stored the octave as 2 cents.
        # Convert at the seam so the Voicing carries the same interval.
        equave_cents = 1200.0 * math.log2(float(self._equave))
        if not self._pitches:
            return Voicing([], 'cents', equave_cents, self._reference_pitch)
        ref = self._reference_pitch if self._reference_pitch is not None else self._pitches[0]
        return Voicing(self.degrees, 'cents', equave_cents, ref)

    def root(self, pitch: Union[Pitch, str]) -> "AbsolutePitchCollection":
        """
        Return a copy with a different reference pitch.

        Parameters
        ----------
        pitch : Pitch or str
            The new reference pitch.

        Returns
        -------
        AbsolutePitchCollection
        """
        rooted = AbsolutePitchCollection(list(self._pitches), self._equave, pitch)
        rooted._equave_cyclic = self._equave_cyclic
        return rooted

    def transpose(self, interval) -> "AbsolutePitchCollection":
        """
        Return a copy with every pitch transposed by *interval*.

        The reference pitch, when set, is transposed too, so partial
        relationships are preserved.

        Parameters
        ----------
        interval : Fraction, int, float, str, Ratio, or Cent
            The transposition interval, as in :meth:`Pitch.transpose`.

        Returns
        -------
        AbsolutePitchCollection
        """
        new_pitches = [p.transpose(interval) for p in self._pitches]
        new_ref = (self._reference_pitch.transpose(interval)
                   if self._reference_pitch is not None else None)
        out = AbsolutePitchCollection(new_pitches, self._equave, new_ref)
        out._equave_cyclic = self._equave_cyclic
        return out

    def __len__(self) -> int:
        return len(self._pitches)

    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]):
        if isinstance(index, slice):
            return self._getitem_slice(index)
        if hasattr(index, '__iter__') and not isinstance(index, str):
            flat_indices = self._flatten_indices(index)
            return self._getitem_sequence(flat_indices)
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        return self._getitem_single(index)

    def _getitem_single(self, index: int) -> Pitch:
        if self._equave_cyclic:
            size = len(self)
            if size == 0:
                raise IndexError("Cannot index an empty collection")
            _, wrapped_index = index // size, index % size
            return self._pitches[wrapped_index]
        return self._pitches[index]

    def _getitem_slice(self, index: slice):
        size = len(self)
        if size == 0:
            sliced = AbsolutePitchCollection([], self._equave, self._reference_pitch)
            sliced._equave_cyclic = self._equave_cyclic
            return sliced
        start, stop, step = index.indices(size)
        use_cyclic = self._equave_cyclic and index.stop is not None and abs(index.stop) > size
        if use_cyclic:
            indices = list(range(index.start or 0, index.stop, step))
            selected = [self._getitem_single(i) for i in indices]
        else:
            selected = [self._pitches[i] for i in range(start, stop, step)]
        sliced = AbsolutePitchCollection(selected, self._equave, self._reference_pitch)
        sliced._equave_cyclic = self._equave_cyclic
        return sliced

    def _getitem_sequence(self, indices: Sequence[int]):
        selected = [self._getitem_single(int(i) if not isinstance(i, int) else i) for i in indices]
        sliced = AbsolutePitchCollection(selected, self._equave, self._reference_pitch)
        sliced._equave_cyclic = self._equave_cyclic
        return sliced

    def __repr__(self) -> str:
        pitches = []
        for pitch in self._pitches[:8]:
            if abs(pitch.cents_offset) > 0.01:
                pitches.append(f"{pitch.pitchclass}{pitch.octave} ({pitch.cents_offset:+.1f}¢)")
            else:
                pitches.append(f"{pitch.pitchclass}{pitch.octave}")
        if len(self._pitches) > 8:
            pitches.append("...")
        pitches_str = ", ".join(pitches)
        return f"{self.__class__.__name__}([{pitches_str}])"


class PitchCollection:
    """
    Factory class providing unified constructors for pitch collections.

    All methods are classmethods that delegate to ``RelativePitchCollection``
    or ``AbsolutePitchCollection`` depending on the input format. Use this
    class when you want a single entry point for creating collections from
    degrees, intervals, set classes, pitches, MIDI notes, MIDI cents, or
    frequencies.
    """

    @classmethod
    def from_degrees(
        cls,
        degrees: DegreeList,
        mode: str = "ratios",
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
        mod: int = 12,
    ) -> RelativePitchCollection:
        """
        Create a relative collection from cumulative degree values.

        Parameters
        ----------
        degrees : list
            Degree values as ratios, cents, or pitch-class integers.
        mode : str, optional
            ``"ratios"``, ``"cents"``, or ``"setclass"``. Default is ``"ratios"``.
        equave : float, Fraction, int, str, or None, optional
            Interval of equivalence.
        reference_pitch : Pitch, str, or None, optional
            Optional root pitch.
        mod : int, optional
            Divisions per equave when *mode* is ``"setclass"``. Default is 12.

        Returns
        -------
        RelativePitchCollection
        """
        if mode == "setclass":
            return RelativePitchCollection.from_setclass(
                [int(pc) for pc in degrees], mod, equave, reference_pitch
            )
        return RelativePitchCollection.from_degrees(degrees, mode, equave, reference_pitch)

    @classmethod
    def from_intervals(
        cls,
        intervals: DegreeList,
        mode: str = "ratios",
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
        mod: int = 12,
    ) -> RelativePitchCollection:
        """
        Create a relative collection from successive interval sizes.

        Parameters
        ----------
        intervals : list
            Successive interval values.
        mode : str, optional
            ``"ratios"``, ``"cents"``, or ``"setclass"``. Default is ``"ratios"``.
        equave : float, Fraction, int, str, or None, optional
            Interval of equivalence.
        reference_pitch : Pitch, str, or None, optional
            Optional root pitch.
        mod : int, optional
            Divisions per equave when *mode* is ``"setclass"``. Default is 12.

        Returns
        -------
        RelativePitchCollection
        """
        if mode == "setclass":
            step_size = float(mod * 100) / mod
            interval_cents = [float(i) * step_size for i in intervals]
            return RelativePitchCollection.from_intervals(
                interval_cents,
                "cents",
                float(mod * 100),
                reference_pitch,
            )
        return RelativePitchCollection.from_intervals(intervals, mode, equave, reference_pitch)

    @classmethod
    def from_setclass(
        cls,
        pcs: List[int],
        mod: int = 12,
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ) -> RelativePitchCollection:
        """
        Create a relative collection from pitch-class integers.

        Parameters
        ----------
        pcs : list of int
            Pitch-class integers.
        mod : int, optional
            Divisions per equave. Default is 12.
        equave : float, Fraction, int, str, or None, optional
            Interval of equivalence.
        reference_pitch : Pitch, str, or None, optional
            Optional root pitch.

        Returns
        -------
        RelativePitchCollection
        """
        return RelativePitchCollection.from_setclass(pcs, mod, equave, reference_pitch)

    @classmethod
    def from_pitch(
        cls,
        pitches: PitchList,
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ) -> AbsolutePitchCollection:
        """
        Create an absolute collection from Pitch objects or pitch strings.

        Parameters
        ----------
        pitches : list of Pitch or str
            The pitches to include.
        equave : float, Fraction, int, str, or None, optional
            Interval of equivalence for cyclic indexing.
        reference_pitch : Pitch, str, or None, optional
            Optional reference pitch.

        Returns
        -------
        AbsolutePitchCollection
        """
        return AbsolutePitchCollection(pitches, equave, reference_pitch)

    @classmethod
    def from_midi(
        cls,
        midi_notes: List[float],
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ) -> AbsolutePitchCollection:
        """
        Create an absolute collection from MIDI note numbers.

        Parameters
        ----------
        midi_notes : list of float
            MIDI note numbers.
        equave : float, Fraction, int, str, or None, optional
            Interval of equivalence.
        reference_pitch : Pitch, str, or None, optional
            Optional reference pitch.

        Returns
        -------
        AbsolutePitchCollection
        """
        pitches = [Pitch.from_midi(midi) for midi in midi_notes]
        return AbsolutePitchCollection(pitches, equave, reference_pitch)

    @classmethod
    def from_midicent(
        cls,
        midicents: List[float],
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ) -> AbsolutePitchCollection:
        """
        Create an absolute collection from MIDI cent values.

        Parameters
        ----------
        midicents : list of float
            MIDI cent values.
        equave : float, Fraction, int, str, or None, optional
            Interval of equivalence.
        reference_pitch : Pitch, str, or None, optional
            Optional reference pitch.

        Returns
        -------
        AbsolutePitchCollection
        """
        pitches = [Pitch.from_midicent(midicent) for midicent in midicents]
        return AbsolutePitchCollection(pitches, equave, reference_pitch)

    @classmethod
    def from_freq(
        cls,
        frequencies: List[float],
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ) -> AbsolutePitchCollection:
        """
        Create an absolute collection from frequencies in Hertz.

        Parameters
        ----------
        frequencies : list of float
            Frequencies in Hertz.
        equave : float, Fraction, int, str, or None, optional
            Interval of equivalence.
        reference_pitch : Pitch, str, or None, optional
            Optional reference pitch.

        Returns
        -------
        AbsolutePitchCollection
        """
        pitches = [Pitch.from_freq(freq) for freq in frequencies]
        return AbsolutePitchCollection(pitches, equave, reference_pitch)
