from __future__ import annotations

from abc import ABC, abstractmethod
from fractions import Fraction
from typing import Iterable, List, Optional, Sequence, Union

import numpy as np

from .pitch import Pitch

IntervalType = Union[float, Fraction]
DegreeList = Union[List[float], List[Fraction], List[int], List[str]]
PitchList = Union[List[Pitch], List[str]]


def _parse_equave(equave: Union[float, Fraction, int, str]) -> Union[float, Fraction]:
    """
    Parse an equave value into a float or Fraction.

    Parameters
    ----------
    equave : float, Fraction, int, or str
        The equave (interval of equivalence) to parse.

    Returns
    -------
    float or Fraction
        The parsed equave value.

    Raises
    ------
    ValueError
        If the value cannot be parsed.
    """
    if isinstance(equave, float):
        return equave
    if isinstance(equave, Fraction):
        return equave
    if isinstance(equave, int):
        return Fraction(equave, 1)
    if isinstance(equave, str) and '/' in equave:
        return Fraction(equave)
    try:
        return float(equave)
    except ValueError:
        raise ValueError(f"Cannot parse equave value: {equave}")


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
        raise NotImplementedError

    @property
    @abstractmethod
    def is_instanced(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def reference_pitch(self) -> Optional[Pitch]:
        raise NotImplementedError

    @property
    @abstractmethod
    def equave(self) -> Union[float, Fraction]:
        raise NotImplementedError

    @property
    @abstractmethod
    def equave_cyclic(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def degrees(self) -> List[Union[Pitch, IntervalType]]:
        raise NotImplementedError

    @property
    @abstractmethod
    def pitches(self) -> List[Pitch]:
        raise NotImplementedError

    @property
    @abstractmethod
    def intervals(self) -> List[IntervalType]:
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
        if self.is_relative and not self.is_instanced:
            target = _convert_degree(value)
            if isinstance(target, Fraction) and isinstance(self.degrees[0], float):
                target = float(target)
            elif isinstance(target, float) and isinstance(self.degrees[0], Fraction):
                target = Fraction.from_float(target)
            for i, degree in enumerate(self.degrees):
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

    Degrees are stored as ratios (``Fraction``) or cents (``float``) and can
    optionally be anchored to a reference pitch to resolve concrete ``Pitch``
    objects. Supports equave-cyclic indexing when enabled.

    Parameters
    ----------
    degrees : list of float, Fraction, int, or str
        Scale/chord degrees as ratios or cent values.
    interval_type : str, optional
        ``"ratios"`` or ``"cents"``. Default is ``"ratios"``.
    equave : float, Fraction, int, str, or None, optional
        Interval of equivalence. When provided, equave-cyclic indexing
        is enabled.
    reference_pitch : Pitch, str, or None, optional
        If given, the collection is *instanced* at this pitch and indexing
        returns ``Pitch`` objects.

    Examples
    --------
    >>> coll = RelativePitchCollection(["1/1", "5/4", "3/2"])
    >>> coll.degrees
    [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]
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
            equave_value = _parse_equave(equave)
        converted = [_convert_degree(d) for d in degrees] if degrees else []

        if interval_type == "cents":
            converted = [float(d) if isinstance(d, Fraction) else float(d) for d in converted]
            if isinstance(equave_value, Fraction):
                equave_value = 1200.0 if equave_value == Fraction(2, 1) else float(equave_value)
        else:
            converted = [
                d if isinstance(d, Fraction)
                else Fraction(d) if isinstance(d, int)
                else d
                for d in converted
            ]
            if isinstance(equave_value, float):
                equave_value = Fraction.from_float(2 ** (equave_value / 1200))

        if self._equave_cyclic_enabled is not None:
            equave_cyclic = self._equave_cyclic_enabled

        self._equave = equave_value
        self._equave_cyclic = equave_cyclic
        self._degrees = converted
        self._interval_type_mode = interval_type
        self._reference_pitch = Pitch(reference_pitch) if isinstance(reference_pitch, str) else reference_pitch
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
    def is_instanced(self) -> bool:
        """bool : True if a reference pitch has been assigned."""
        return self._reference_pitch is not None

    @property
    def reference_pitch(self) -> Optional[Pitch]:
        """Pitch or None : The reference pitch anchoring the collection."""
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
        """
        list of Pitch : Concrete pitches resolved from degrees and reference pitch.

        Raises
        ------
        ValueError
            If no reference pitch has been set.
        """
        if not self.is_instanced:
            raise ValueError("Cannot resolve pitches without a reference pitch")
        return [self._calculate_pitch(i) for i in range(len(self._degrees))]

    @property
    def intervals(self) -> List[IntervalType]:
        """list : Successive intervals between adjacent degrees."""
        return self._intervals

    @property
    def interval_type(self) -> Optional[type]:
        """type or None : The Python type of the stored degrees (float or Fraction)."""
        if self._degrees:
            return type(self._degrees[0])
        return None

    def root(self, pitch: Union[Pitch, str]) -> "RootedPitchCollection":
        """
        Return a copy of this collection rooted at the given pitch.

        Parameters
        ----------
        pitch : Pitch or str
            The pitch to use as the reference root.

        Returns
        -------
        RootedPitchCollection
        """
        return RootedPitchCollection(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            pitch,
        )

    def relative(self) -> "RelativePitchCollection":
        """
        Return a rootless copy retaining only the interval structure.

        Returns
        -------
        RelativePitchCollection
        """
        if not self.is_instanced:
            return self
        relative = RelativePitchCollection(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            None,
        )
        relative._equave_cyclic = self._equave_cyclic
        return relative

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
        return Pitch.from_freq(freq, partial)

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

    def _getitem_single(self, index: int) -> Union[Pitch, IntervalType]:
        if self.is_instanced:
            return self._calculate_pitch(index)
        if self._equave_cyclic:
            equave_shift, wrapped_index = self._get_cyclic_index(index)
            return self._calculate_degree_with_shift(equave_shift, wrapped_index)
        return self._degrees[index]

    def _getitem_slice(self, index: slice):
        size = len(self)
        if size == 0:
            return RelativePitchCollection([], self._interval_type_mode, self._equave, False, self._reference_pitch)
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
        if self.is_instanced:
            rooted = RootedPitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
            rooted._equave_cyclic = False
            return rooted
        relative = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        relative._equave_cyclic = False
        return relative

    def _getitem_sequence(self, indices: Sequence[int]):
        selected_degrees = []
        for i in indices:
            idx = int(i) if not isinstance(i, int) else i
            if self._equave_cyclic:
                selected_degrees.append(self._calculate_degree_with_shift(*self._get_cyclic_index(idx)))
            else:
                selected_degrees.append(self._degrees[idx])
        if self.is_instanced:
            rooted = RootedPitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
            rooted._equave_cyclic = False
            return rooted
        relative = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, None)
        relative._equave_cyclic = False
        return relative

    def __repr__(self) -> str:
        size = len(self._degrees)
        if self.is_instanced:
            pitches = []
            for i in range(min(size, 8)):
                pitch = self._calculate_pitch(i)
                if abs(pitch.cents_offset) > 0.01:
                    pitches.append(f"{pitch.pitchclass}{pitch.octave} ({pitch.cents_offset:+.1f}¢)")
                else:
                    pitches.append(f"{pitch.pitchclass}{pitch.octave}")
            if size > 8:
                pitches.append("...")
            pitches_str = ", ".join(pitches)
            return f"{self.__class__.__name__}([{pitches_str}], root={self._reference_pitch.pitchclass}{self._reference_pitch.octave})"
        degrees_str = ", ".join(str(d) for d in self._degrees[:8])
        if size > 8:
            degrees_str += ", ..."
        return f"{self.__class__.__name__}([{degrees_str}], equave={self._equave})"


class RootedPitchCollection(RelativePitchCollection):
    """
    A ``RelativePitchCollection`` that always carries a reference pitch.

    Slicing or sequence-indexing a ``RelativePitchCollection`` with a
    reference pitch produces a ``RootedPitchCollection`` so that the
    root information is preserved through subsetting.
    """

    def root(self, pitch: Union[Pitch, str]) -> "RootedPitchCollection":
        """
        Return a copy rooted at a different pitch.

        Parameters
        ----------
        pitch : Pitch or str
            The new reference pitch.

        Returns
        -------
        RootedPitchCollection
        """
        return RootedPitchCollection(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            pitch,
        )

    def relative(self) -> "RelativePitchCollection":
        relative = RelativePitchCollection(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            None,
        )
        relative._equave_cyclic = self._equave_cyclic
        return relative


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
        Interval of equivalence for cyclic indexing.
    reference_pitch : Pitch, str, or None, optional
        Optional reference pitch for partial calculations.
    """

    def __init__(
        self,
        pitches: PitchList,
        equave: Union[float, Fraction, int, str, None] = None,
        reference_pitch: Union[Pitch, str, None] = None,
    ):
        self._equave = _parse_equave(equave) if equave is not None else Fraction(2, 1)
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
    def is_instanced(self) -> bool:
        """bool : True if a reference pitch has been assigned."""
        return self._reference_pitch is not None

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
    def degrees(self) -> List[Pitch]:
        """list of Pitch : The pitches (same as ``pitches`` for absolute collections)."""
        return list(self._pitches)

    @property
    def pitches(self) -> List[Pitch]:
        """list of Pitch : The stored pitch objects."""
        return list(self._pitches)

    @property
    def intervals(self) -> List[float]:
        """list of float : Successive intervals in cents between adjacent pitches."""
        return self._intervals

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
