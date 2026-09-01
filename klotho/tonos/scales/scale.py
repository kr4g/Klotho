from fractions import Fraction
from typing import Optional, Union, List, Sequence
from ..pitch import Pitch
from ..pitch.pitch_collections import (
    EquaveCyclicMixin,
    IntervalType,
    DegreeList,
    RelativePitchCollection,
    PitchCollectionBase,
    _resolve_equave,
    _convert_degree,
    _resolve_reference,
)
from ..utils.interval_normalization import (
    equave_reduce,
    check_reduction_cost,
    _refuse_degenerate_equave,
    _refuse_non_positive,
)
import numpy as np


class Scale(EquaveCyclicMixin, RelativePitchCollection):
    """
    A musical scale with automatic sorting, deduplication, and equave reduction.

    Scale represents a collection of pitch intervals that form a musical scale.
    It automatically sorts degrees, removes duplicates, equave-reduces intervals,
    and ensures the unison (1/1 or 0 cents) is present. Scales always use
    equave-cyclic indexing for accessing pitches in different octaves.

    Parameters
    ----------
    degrees : list of str, float, int, or Fraction
        Intervals as ratios (e.g., ``"5/4"``), decimals, or numbers.
    interval_type : str, optional
        ``"ratios"`` or ``"cents"``. Default is ``"ratios"``.
    equave : float, Fraction, int, or str, optional
        Interval of equivalence. Defaults to the octave, spelled to match
        the mode: ``Fraction(2, 1)`` in ``"ratios"``, ``1200.0`` in
        ``"cents"``. **``interval_type`` decides how this is read; its
        Python type does not.** In ``"ratios"`` mode it is a ratio in every spelling, so
        ``3``, ``3.0``, ``Fraction(3, 1)`` and ``'3/1'`` all give the
        Bohlen-Pierce tritave. In ``"cents"`` mode it is a cents value, so
        the tritave is ``equave=1901.955``; a fraction written there is
        refused as a category error rather than guessed at.
    reference_pitch : Pitch, str, or None, optional
        The root pitch. ``None`` (default) resolves to C4.

    Examples
    --------
    >>> scale = Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])
    >>> scale.degrees
    [Fraction(1, 1), Fraction(9, 8), Fraction(5, 4), Fraction(4, 3), Fraction(3, 2), Fraction(5, 3), Fraction(15, 8)]

    >>> scale[0]
    Pitch(C4, 261.63 Hz)

    >>> a_major = scale.root("A4")
    >>> a_major[0]
    Pitch(A4, 440.00 Hz)
    """
    
    def __init__(self, degrees: DegreeList = ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"],
                 interval_type: str = "ratios",
                 equave: Union[float, Fraction, int, str, None] = None,
                 reference_pitch: Union[Pitch, str, None] = None):
        if interval_type not in ["ratios", "cents"]:
            raise ValueError("interval_type must be 'ratios' or 'cents'")

        # The default is spelled per mode rather than as one literal. It used
        # to be the string "2/1", which reads as the octave in ratios mode and
        # as a ratio-written-in-a-cents-field in cents mode -- so the class's
        # own default would have been refused by its own rule.
        if equave is None:
            equave = 1200.0 if interval_type == "cents" else Fraction(2, 1)
        
        # The declared interval_type decides how the equave reads, and it is
        # resolved once, up front. The degrees used to be processed against
        # the RAW argument with each branch guessing its Python type: a cents
        # equave then reduced ratio degrees by a hardcoded octave while the
        # scale stored the tritave it was handed, or was used directly as a
        # ratio.
        resolved_equave = _resolve_equave(equave, interval_type, 'Scale')
        processed_degrees = self._process_scale_degrees(
            degrees, interval_type, resolved_equave)

        self._equave = resolved_equave
        self._equave_cyclic = True
        self._degrees = processed_degrees
        self._interval_type_mode = interval_type
        self._mode_cache = {}
        self._reference_pitch = _resolve_reference(reference_pitch)
        self._intervals = self._compute_scale_intervals()
    
    def _process_scale_degrees(self, degrees: DegreeList, interval_type: str,
                                equave: Union[float, Fraction]) -> List[IntervalType]:
        """Sort, reduce, dedupe and unison-anchor the degrees.

        *equave* arrives already resolved to the form this *interval_type*
        works in -- cents (float) for ``"cents"``, a ratio (Fraction) for
        ``"ratios"``. It is not the raw constructor argument, and this method
        must not try to infer the caller's intent from its type: doing that
        here is what made a cents equave reduce ratio degrees by an octave.
        """
        if not degrees:
            return []

        converted = [_convert_degree(d) for d in degrees]
        # Four copies of the reduction loop follow (two here, two in Chord),
        # and none of them is bounded. Price the work once, before any of it
        # runs, so an equave a hair above the unison refuses instead of
        # freezing the interpreter or building a scale too large to print.
        check_reduction_cost('Scale', equave, converted, interval_type)

        if interval_type == "cents":
            converted = [float(d) if isinstance(d, Fraction) else d for d in converted]
            equave_val = float(equave)

            reduced = []
            for d in converted:
                while d >= equave_val:
                    d -= equave_val
                while d < 0:
                    d += equave_val
                reduced.append(d)
            
            unique = []
            for d in reduced:
                if not any(abs(d - existing) < 1e-6 for existing in unique):
                    unique.append(d)
            unique.sort()
            
            if not unique or abs(unique[0]) >= 1e-6:
                unique.insert(0, 0.0)
        else:
            converted = [d if isinstance(d, Fraction) else Fraction(d) if isinstance(d, int) else d for d in converted]
            has_float = any(isinstance(d, float) for d in converted)
            if has_float:
                equave_val = float(equave)
                # This branch carries its own copy of the equave_reduce loop,
                # so it needs the same guards; without them a 0 degree froze
                # the interpreter here instead of raising. The equave check is
                # unreachable from the constructor now that _resolve_equave
                # refuses first; it stays because this method is callable on
                # its own and the loop below is unbounded without it.
                if equave_val <= 1:
                    raise _refuse_degenerate_equave('Scale', equave_val)
                reduced = []
                for d in converted:
                    val = float(d)
                    if val <= 0:
                        raise _refuse_non_positive('Scale', 'degree', val)
                    while val < 1:
                        val *= equave_val
                    while val >= equave_val:
                        val /= equave_val
                    reduced.append(val)
                unique = []
                for d in reduced:
                    if not any(abs(d - existing) < 1e-9 for existing in unique):
                        unique.append(d)
                unique.sort()
                if not unique or abs(unique[0] - 1.0) >= 1e-9:
                    unique.insert(0, 1.0)
            else:
                equave_val = Fraction(equave)
                reduced = [equave_reduce(d, equave_val) for d in converted]
                unique = sorted(list(set(reduced)))
                if not unique or unique[0] != Fraction(1, 1):
                    unique.insert(0, Fraction(1, 1))
        
        return unique
    
    def _compute_scale_intervals(self) -> List[IntervalType]:
        if not self._degrees or len(self._degrees) <= 1:
            return []
        
        result = []
        if self._interval_type_mode == "cents":
            for i in range(1, len(self._degrees)):
                result.append(self._degrees[i] - self._degrees[i-1])
            final = self._equave - self._degrees[-1]
            result.append(final)
        else:
            for i in range(1, len(self._degrees)):
                prev = self._degrees[i-1]
                if prev == 0 or (isinstance(prev, Fraction) and prev.numerator == 0):
                    result.append(Fraction(0, 1))
                else:
                    result.append(self._degrees[i] / prev)
            final = self._equave / self._degrees[-1]
            result.append(final)
        
        return result
    
    @property
    def intervals(self) -> List[IntervalType]:
        """list : Successive step intervals including the closing interval to the equave."""
        return self._intervals

    def root(self, pitch: Union[Pitch, str]) -> 'Scale':
        """
        Return a copy of this scale rooted at the given pitch.

        Parameters
        ----------
        pitch : Pitch or str
            The reference pitch.

        Returns
        -------
        Scale
        """
        return Scale(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            pitch
        )

    def transpose(self, interval) -> 'Scale':
        """
        Return a copy transposed by *interval*, carried in the reference pitch.

        Scale degrees are equave-reduced by construction, so the
        reference pitch carries the shift; note that a later
        :meth:`root` replaces the reference and therefore discards it.

        Parameters
        ----------
        interval : Fraction, int, float, str, Ratio, or Cent
            The transposition interval, as in :meth:`Pitch.transpose`.

        Returns
        -------
        Scale
        """
        return self.root(self._reference_pitch.transpose(interval))

    def mode(self, mode_number: int) -> 'Scale':
        """
        Return a modal rotation of this scale.

        Parameters
        ----------
        mode_number : int
            Zero-based mode index. ``0`` returns the original scale,
            ``1`` starts from the second degree, etc.

        Returns
        -------
        Scale
            A new Scale whose degrees are rotated to begin on the
            specified degree of the original.
        """
        if mode_number in self._mode_cache:
            return self._mode_cache[mode_number].root(self._reference_pitch)

        if mode_number == 0:
            return self
        
        size = len(self._degrees)
        if size == 0:
            return Scale([], self._interval_type_mode, self._equave, self._reference_pitch)
        
        start_index = mode_number % size
        if start_index < 0:
            start_index += size
        
        first_degree = self._degrees[start_index]
        modal_degrees = []
        
        if self._interval_type_mode == "cents":
            for i in range(size):
                current_idx = (start_index + i) % size
                if i == 0:
                    modal_degrees.append(0.0)
                else:
                    interval = self._degrees[current_idx] - first_degree
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, float) else 1200.0
                        interval += equave_value
                    modal_degrees.append(interval)
        else:
            for i in range(size):
                current_idx = (start_index + i) % size
                if i == 0:
                    modal_degrees.append(Fraction(1, 1))
                else:
                    interval = self._degrees[current_idx] / first_degree
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, Fraction) else Fraction.from_float(2 ** (self._equave / 1200))
                        interval *= equave_value
                    modal_degrees.append(interval)
        
        result = Scale(modal_degrees, self._interval_type_mode, self._equave, None)
        self._mode_cache[mode_number] = result
        return result.root(self._reference_pitch)
    
    def __invert__(self) -> 'Scale':
        """
        Mirror the scale about its own equave.

        Every degree ``d`` is replaced by ``equave / d`` (in cents, by
        ``equave - d``), so the step pattern is reversed and the unison is
        held fixed. Inversion is an involution: ``~~scale == scale``.

        The equave is the scale's own, not the octave. A tritave-equave
        scale inverts within the tritave, a Bohlen-Pierce scale within
        ``3/1``. (Before 2026-09-01 the ratios branch mirrored about a
        hardcoded 2 while the cents branch used the scale's equave, so
        non-octave scales inverted to the wrong notes with no error.)

        Returns
        -------
        Scale
            A new Scale with the mirrored degrees, keeping this scale's
            equave and reference pitch.
        """
        if self._interval_type_mode == "cents":
            inverted = [0.0 if abs(d) < 1e-6 else self._equave - d for d in self._degrees]
        else:
            equave = self._equave
            inverted = []
            for d in self._degrees:
                if isinstance(d, Fraction):
                    # `equave / d`; identical to the old `2 / d` when the
                    # equave is the octave.
                    inverted.append(Fraction(1, 1) if d == 1 else Fraction(equave) / d)
                else:
                    # _process_scale_degrees keeps degrees as floats when any
                    # input degree was a float, so this branch is reachable
                    # and used to raise AttributeError on `d.denominator`.
                    val = float(d)
                    inverted.append(1.0 if abs(val - 1.0) < 1e-9
                                    else float(equave) / val)

        return Scale(sorted(inverted), self._interval_type_mode, self._equave, self._reference_pitch)
    
    def __neg__(self) -> 'Scale':
        return self.__invert__()
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> Union[Pitch, IntervalType, PitchCollectionBase]:
        if isinstance(index, slice):
            return self._getitem_slice_scale(index)
        
        if hasattr(index, '__iter__') and not isinstance(index, str):
            flat_indices = self._flatten_indices(index)
            return self._getitem_sequence_scale(flat_indices)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        return self._getitem_single_scale(index)
    
    def _getitem_single_scale(self, index: int) -> Pitch:
        return self._calculate_pitch(index)
    
    def _getitem_slice_scale(self, index: slice) -> PitchCollectionBase:
        size = len(self._degrees)
        if size == 0:
            relative = RelativePitchCollection([], self._interval_type_mode, self._equave, self._reference_pitch)
            relative._equave_cyclic = False
            return relative
        
        start, stop, step = index.indices(size)
        use_cyclic = index.stop is not None and abs(index.stop) > size
        
        if use_cyclic:
            indices = list(range(index.start or 0, index.stop, step))
        else:
            indices = list(range(start, stop, step))
        
        selected_degrees = [
            self._calculate_degree_with_shift(*self._get_cyclic_index(i))
            if use_cyclic
            else self._degrees[i]
            for i in (indices if use_cyclic else range(start, stop, step))
        ]

        subset = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        subset._equave_cyclic = False
        return subset

    def _getitem_sequence_scale(self, indices: Sequence[int]) -> PitchCollectionBase:
        selected_degrees = []
        for i in indices:
            idx = int(i) if not isinstance(i, int) else i
            equave_shift, wrapped_index = self._get_cyclic_index(idx)
            degree = self._calculate_degree_with_shift(equave_shift, wrapped_index)
            selected_degrees.append(degree)
        subset = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        subset._equave_cyclic = False
        return subset
    
    @classmethod
    def n_edo(cls, n: int = 12, equave: float = 1200.0, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """
        Construct an equal-division-of-the-equave (EDO) scale.

        The scale is built in ``cents`` mode, so **``equave`` is a size in
        cents, not a ratio** -- the same unit the ``n`` steps are measured in.
        ``n_edo(12)`` divides 1200.0 cents into twelve 100-cent steps;
        ``n_edo(13, equave=1901.955)`` divides the Bohlen-Pierce tritave into
        thirteen. Writing that tritave as a fraction (``equave='3/1'`` or
        ``Fraction(3, 1)``) is refused, because a ratio in a cents field is a
        category error rather than a second reading of the same number.

        The step size and the stored equave are derived from the same value,
        so ``max(scale.degrees) + step == scale.equave`` holds at any equave,
        not only the default.

        Parameters
        ----------
        n : int, optional
            Number of equal divisions. Default is 12.
        equave : float, optional
            Size of the equave **in cents**. Default is 1200.0 (the octave).
        reference_pitch : Pitch, str, or None, optional
            Optional root pitch.

        Returns
        -------
        Scale

        Examples
        --------
        >>> Scale.n_edo(12).equave
        1200.0
        >>> [round(d, 3) for d in Scale.n_edo(13, equave=1901.955).degrees[:3]]
        [0.0, 146.304, 292.608]
        """
        # float() up front so the degrees below and the equave the constructor
        # stores are derived from ONE value in ONE unit. Passing the raw
        # argument to both while dividing it here as a raw cents number is
        # what made n_edo(13, equave=3) span 2.77 cents while reporting an
        # equave of 1901.955.
        equave_cents = _resolve_equave(equave, 'cents', 'Scale.n_edo')
        step_size = equave_cents / n
        degrees = [i * step_size for i in range(n)]
        return cls(degrees, 'cents', equave_cents, reference_pitch)
    
    @classmethod
    def ionian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Just-intonation major (ionian) scale — the parent of the seven modes."""
        return cls(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"], reference_pitch=reference_pitch)
    
    @classmethod
    def dorian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Dorian mode (mode 1 of the just ionian scale)."""
        return cls.ionian().mode(1).root(reference_pitch) if reference_pitch else cls.ionian().mode(1)
    
    @classmethod
    def phrygian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Phrygian mode (mode 2 of the just ionian scale)."""
        return cls.ionian().mode(2).root(reference_pitch) if reference_pitch else cls.ionian().mode(2)
    
    @classmethod
    def lydian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Lydian mode (mode 3 of the just ionian scale)."""
        return cls.ionian().mode(3).root(reference_pitch) if reference_pitch else cls.ionian().mode(3)
    
    @classmethod
    def mixolydian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Mixolydian mode (mode 4 of the just ionian scale)."""
        return cls.ionian().mode(4).root(reference_pitch) if reference_pitch else cls.ionian().mode(4)
    
    @classmethod
    def aeolian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Aeolian mode / natural minor (mode 5 of the just ionian scale)."""
        return cls.ionian().mode(5).root(reference_pitch) if reference_pitch else cls.ionian().mode(5)
    
    @classmethod
    def locrian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Locrian mode (mode 6 of the just ionian scale)."""
        return cls.ionian().mode(6).root(reference_pitch) if reference_pitch else cls.ionian().mode(6)

    @classmethod
    def octatonic(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Half–whole octatonic scale in 12-EDO cents. ``.mode(1)`` gives whole–half."""
        return cls([0, 100, 300, 400, 600, 700, 900, 1000],
                   interval_type='cents', reference_pitch=reference_pitch)

    @classmethod
    def hexatonic(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """The hexatonic (augmented) scale in 12-EDO cents."""
        return cls([0, 100, 400, 500, 800, 900],
                   interval_type='cents', reference_pitch=reference_pitch)

    @classmethod
    def wholetone(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """The whole-tone scale (6-EDO)."""
        return cls.n_edo(6, reference_pitch=reference_pitch)

    @classmethod
    def pentatonic(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Just-intonation major pentatonic scale."""
        return cls(["1/1", "9/8", "5/4", "3/2", "5/3"], reference_pitch=reference_pitch)

    @classmethod
    def harmonic_minor(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Just-intonation harmonic minor scale."""
        return cls(["1/1", "9/8", "6/5", "4/3", "3/2", "8/5", "15/8"],
                   reference_pitch=reference_pitch)

    @classmethod
    def melodic_minor(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Just-intonation melodic minor scale (ascending)."""
        return cls(["1/1", "9/8", "6/5", "4/3", "3/2", "5/3", "15/8"],
                   reference_pitch=reference_pitch)

    @classmethod
    def bagpipes(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """Just-intonation Great Highland bagpipe scale (10 degrees)."""
        return cls(
            ['1/1', '9/8', '5/4', '4/3', '27/20', '3/2', '5/3', '7/4', '16/9', '9/5'],
            reference_pitch=reference_pitch
        )

    @classmethod
    def janus(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        """12-degree just-intonation scale mixing 3-, 5-, 7-, and 11-limit degrees."""
        return cls(
            ['1/1', '33/32', '9/8', '7/6', '5/4', '21/16', '11/8', '3/2', '99/64', '5/3', '7/4', '15/8'],
            reference_pitch=reference_pitch
        )
