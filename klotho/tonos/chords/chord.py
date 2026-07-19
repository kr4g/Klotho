from fractions import Fraction
from typing import Optional, Union, List, Sequence
from ..pitch import Pitch
from ..pitch.pitch_collections import (
    AbsolutePitchCollection,
    EquaveCyclicMixin,
    IntervalType,
    DegreeList,
    RelativePitchCollection,
    PitchCollectionBase,
    _parse_equave,
    _convert_degree,
    _resolve_reference,
)
from ..utils.interval_normalization import equave_reduce
import numpy as np


class Chord(EquaveCyclicMixin, RelativePitchCollection):
    """
    A musical chord with automatic sorting and deduplication.

    Chord represents a collection of pitch intervals that form a musical chord.
    It automatically sorts degrees, removes duplicates, and equave-reduces intervals,
    but unlike Scale, it does NOT enforce the presence of unison. Chords always use
    equave-cyclic indexing for accessing chord tones in different octaves.

    Parameters
    ----------
    degrees : list of str, float, int, or Fraction
        Intervals as ratios (e.g., ``"5/4"``), decimals, or numbers.
    interval_type : str, optional
        ``"ratios"`` or ``"cents"``. Default is ``"ratios"``.
    equave : float, Fraction, int, or str, optional
        Interval of equivalence. Default is ``"2/1"`` (octave).
    reference_pitch : Pitch, str, or None, optional
        The root pitch. ``None`` (default) resolves to C4.

    Examples
    --------
    >>> chord = Chord(["1/1", "5/4", "3/2"])
    >>> chord.degrees
    [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]

    >>> chord[0]
    Pitch(C4, 261.63 Hz)

    >>> a_major = chord.root("A4")
    >>> a_major[0]
    Pitch(A4, 440.00 Hz)
    """
    
    def __init__(self, degrees: DegreeList = ["1/1", "5/4", "3/2"],
                 interval_type: str = "ratios",
                 equave: Union[float, Fraction, int, str] = "2/1",
                 reference_pitch: Union[Pitch, str, None] = None):
        if interval_type not in ["ratios", "cents"]:
            raise ValueError("interval_type must be 'ratios' or 'cents'")
        
        parsed_equave = _parse_equave(equave)
        processed_degrees = self._process_chord_degrees(degrees, interval_type, parsed_equave)
        
        if interval_type == "cents":
            if isinstance(parsed_equave, Fraction):
                parsed_equave = 1200.0 if parsed_equave == Fraction(2, 1) else float(parsed_equave)
        else:
            if isinstance(parsed_equave, float):
                parsed_equave = Fraction.from_float(2 ** (parsed_equave / 1200))
        
        self._equave = parsed_equave
        self._equave_cyclic = True
        self._degrees = processed_degrees
        self._interval_type_mode = interval_type
        self._reference_pitch = _resolve_reference(reference_pitch)
        self._intervals = self._compute_chord_intervals()
    
    def _process_chord_degrees(self, degrees: DegreeList, interval_type: str,
                                equave: Union[float, Fraction]) -> List[IntervalType]:
        if not degrees:
            return []
        
        converted = [_convert_degree(d) for d in degrees]
        
        if interval_type == "cents":
            converted = [float(d) if isinstance(d, Fraction) else d for d in converted]
            equave_val = equave if isinstance(equave, float) else 1200.0
            
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
        else:
            converted = [d if isinstance(d, Fraction) else Fraction(d) if isinstance(d, int) else d for d in converted]
            has_float = any(isinstance(d, float) for d in converted)
            if has_float:
                equave_val = float(equave) if not isinstance(equave, float) else equave
                reduced = []
                for d in converted:
                    val = float(d)
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
            else:
                equave_val = equave if isinstance(equave, Fraction) else Fraction(2, 1)
                reduced = [equave_reduce(d, equave_val) for d in converted]
                unique = sorted(list(set(reduced)))
        
        return unique
    
    def _compute_chord_intervals(self) -> List[IntervalType]:
        if not self._degrees or len(self._degrees) <= 1:
            return []
        
        result = []
        if self._interval_type_mode == "cents":
            for i in range(1, len(self._degrees)):
                result.append(self._degrees[i] - self._degrees[i-1])
        else:
            for i in range(1, len(self._degrees)):
                prev = self._degrees[i-1]
                if prev == 0 or (isinstance(prev, Fraction) and prev.numerator == 0):
                    result.append(Fraction(0, 1))
                else:
                    result.append(self._degrees[i] / prev)
        
        return result
    
    @property
    def intervals(self) -> List[IntervalType]:
        """list : Successive intervals between adjacent chord tones."""
        return self._intervals

    @property
    def freq(self) -> tuple:
        """tuple of float : Frequencies of the chord's pitches.

        A tuple, so ``freq=chord.freq`` assigns the whole chord as one
        simultaneity when used as the ``freq`` pfield (alias of
        :attr:`freqs`).
        """
        return self.freqs

    def root(self, pitch: Union[Pitch, str]) -> 'Chord':
        """
        Return a copy of this chord rooted at the given pitch.

        Parameters
        ----------
        pitch : Pitch or str
            The reference pitch.

        Returns
        -------
        Chord
        """
        return Chord(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            pitch
        )

    def transpose(self, interval) -> 'Chord':
        """
        Return a copy transposed by *interval*, carried in the reference pitch.

        Chord degrees are equave-reduced by construction, so the
        reference pitch carries the shift; note that a later
        :meth:`root` replaces the reference and therefore discards it.

        Parameters
        ----------
        interval : Fraction, int, float, str, Ratio, or Cent
            The transposition interval, as in :meth:`Pitch.transpose`.

        Returns
        -------
        Chord
        """
        return self.root(self._reference_pitch.transpose(interval))

    def normalized(self) -> 'Chord':
        """
        Transpose the chord so the lowest degree is the unison (1/1 or 0 cents).

        Returns
        -------
        Chord
        """
        if not self._degrees:
            return Chord([], self._interval_type_mode, self._equave, self._reference_pitch)
        
        lowest = self._degrees[0]
        
        if self._interval_type_mode == "cents":
            normalized_degrees = [d - lowest for d in self._degrees]
        else:
            normalized_degrees = [d / lowest for d in self._degrees]
        
        return Chord(normalized_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
    
    def voicing(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> 'Voicing':
        """
        Extract a Voicing from this chord by selecting tones with cyclic indexing.

        Unlike slicing (which returns a ``RelativePitchCollection``), this
        preserves multi-octave spread by using cyclic degree lookup without
        equave reduction.

        Parameters
        ----------
        index : int, slice, or sequence of int
            Indices into the chord (cyclic).

        Returns
        -------
        Voicing
        """
        if isinstance(index, slice):
            size = len(self._degrees)
            if size == 0:
                return Voicing([], self._interval_type_mode, self._equave, self._reference_pitch)
            
            start, stop, step = index.indices(size)
            use_cyclic = index.stop is not None and abs(index.stop) > size
            
            if use_cyclic:
                indices = list(range(index.start or 0, index.stop, step))
                selected = [self._get_degree_cyclic(i) for i in indices]
            else:
                selected = [self._degrees[i] for i in range(start, stop, step)]
            
            return Voicing(selected, self._interval_type_mode, self._equave, self._reference_pitch)
        
        if hasattr(index, '__iter__') and not isinstance(index, str):
            selected = [self._get_degree_cyclic(int(i) if not isinstance(i, int) else i) for i in index]
            return Voicing(selected, self._interval_type_mode, self._equave, self._reference_pitch)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        degree = self._get_degree_cyclic(index)
        return Voicing([degree], self._interval_type_mode, self._equave, self._reference_pitch)
    
    def _get_degree_cyclic(self, index: int) -> IntervalType:
        equave_shift, wrapped_index = self._get_cyclic_index(index)
        return self._calculate_degree_with_shift(equave_shift, wrapped_index)
    
    def __invert__(self) -> 'Chord':
        if len(self._degrees) <= 1:
            return Chord(list(self._degrees), self._interval_type_mode, self._equave, self._reference_pitch)
        
        if self._interval_type_mode == "cents":
            new_degrees = [self._degrees[0]]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_diff = self._degrees[i] - self._degrees[i-1]
                new_degrees.append(new_degrees[-1] + interval_diff)
        else:
            new_degrees = [self._degrees[0]]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_ratio = self._degrees[i] / self._degrees[i-1]
                new_degrees.append(new_degrees[-1] * interval_ratio)
        
        return Chord(new_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
    
    def __neg__(self) -> 'Chord':
        return self.__invert__()
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> Union[Pitch, IntervalType, PitchCollectionBase]:
        if isinstance(index, slice):
            return self._getitem_slice_chord(index)
        
        if hasattr(index, '__iter__') and not isinstance(index, str):
            flat_indices = self._flatten_indices(index)
            return self._getitem_sequence_chord(flat_indices)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        return self._getitem_single_chord(index)
    
    def _getitem_single_chord(self, index: int) -> Pitch:
        return self._calculate_pitch(index)
    
    def _getitem_slice_chord(self, index: slice) -> PitchCollectionBase:
        size = len(self._degrees)
        if size == 0:
            relative = RelativePitchCollection([], self._interval_type_mode, self._equave, self._reference_pitch)
            relative._equave_cyclic = False
            return relative
        
        start, stop, step = index.indices(size)
        use_cyclic = index.stop is not None and abs(index.stop) > size
        
        if use_cyclic:
            indices = list(range(index.start or 0, index.stop, step))
            selected_degrees = [self._get_degree_cyclic(i) for i in indices]
        else:
            selected_degrees = [self._degrees[i] for i in range(start, stop, step)]

        subset = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        subset._equave_cyclic = False
        return subset

    def _getitem_sequence_chord(self, indices: Sequence[int]) -> PitchCollectionBase:
        selected_degrees = [self._get_degree_cyclic(int(i) if not isinstance(i, int) else i) for i in indices]
        subset = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        subset._equave_cyclic = False
        return subset
    
    @classmethod
    def from_collection(cls, collection: PitchCollectionBase, equave: Union[float, Fraction, int, str, None] = None) -> 'Chord':
        """
        Construct a Chord from an existing relative pitch collection.

        Parameters
        ----------
        collection : PitchCollectionBase
            A relative pitch collection to convert.
        equave : float, Fraction, int, str, or None, optional
            Override equave. Defaults to the collection's equave.

        Returns
        -------
        Chord

        Raises
        ------
        ValueError
            If the collection is absolute (not relative).
        """
        if not collection.is_relative:
            raise ValueError("Cannot create Chord from absolute collection")
        target_equave = equave if equave is not None else (collection.equave if collection.equave is not None else Fraction(2, 1))
        return cls(
            list(collection._degrees),
            collection._interval_type_mode,
            target_equave,
            collection._reference_pitch
        )


class Voicing(RelativePitchCollection):
    """
    A musical voicing with no equave reduction, removing only exact duplicates.

    Voicing represents a "frozen" set of intervals that preserves exact pitch
    relationships without equave cycling. Unlike Chord, it does not reduce
    intervals to within an equave, allowing voicings that span multiple octaves.
    Exact duplicates are removed, but the same pitch-class in different octaves
    is allowed.

    Parameters
    ----------
    degrees : list of str, float, int, or Fraction
        Intervals as ratios, decimals, or numbers.
    interval_type : str, optional
        ``"ratios"`` or ``"cents"``. Default is ``"ratios"``.
    equave : float, Fraction, int, or str, optional
        Interval of equivalence. Default is ``"2/1"``.
    reference_pitch : Pitch, str, or None, optional
        The root pitch. ``None`` (default) resolves to C4.

    Examples
    --------
    >>> voicing = Voicing(["1/2", "1/1", "3/2", "5/2"])
    >>> voicing.degrees
    [Fraction(1, 2), Fraction(1, 1), Fraction(3, 2), Fraction(5, 2)]

    >>> voicing = Voicing(["1/1", "1/1", "3/2"])
    >>> voicing.degrees
    [Fraction(1, 1), Fraction(3, 2)]
    """
    
    def __init__(self, degrees: DegreeList = ["1/1", "5/4", "3/2"],
                 interval_type: str = "ratios",
                 equave: Union[float, Fraction, int, str] = "2/1",
                 reference_pitch: Union[Pitch, str, None] = None):
        if interval_type not in ["ratios", "cents"]:
            raise ValueError("interval_type must be 'ratios' or 'cents'")
        
        parsed_equave = _parse_equave(equave)
        processed_degrees = self._process_sonority_degrees(degrees, interval_type, parsed_equave)
        
        if interval_type == "cents":
            if isinstance(parsed_equave, Fraction):
                parsed_equave = 1200.0 if parsed_equave == Fraction(2, 1) else float(parsed_equave)
        else:
            if isinstance(parsed_equave, float):
                parsed_equave = Fraction.from_float(2 ** (parsed_equave / 1200))
        
        self._equave = parsed_equave
        self._equave_cyclic = False
        self._degrees = processed_degrees
        self._interval_type_mode = interval_type
        self._reference_pitch = _resolve_reference(reference_pitch)
        self._intervals = self._compute_sonority_intervals()
    
    def _process_sonority_degrees(self, degrees: DegreeList, interval_type: str,
                                   equave: Union[float, Fraction]) -> List[IntervalType]:
        if not degrees:
            return []
        
        converted = [_convert_degree(d) for d in degrees]
        
        if interval_type == "cents":
            converted = [float(d) if isinstance(d, Fraction) else d for d in converted]
            
            unique = []
            for d in converted:
                if not any(abs(d - existing) < 1e-6 for existing in unique):
                    unique.append(d)
            unique.sort()
        else:
            converted = [d if isinstance(d, Fraction) else Fraction(d) if isinstance(d, int) else d for d in converted]
            has_float = any(isinstance(d, float) for d in converted)
            if has_float:
                converted = [float(d) for d in converted]
                unique = []
                for d in converted:
                    if not any(abs(d - existing) < 1e-9 for existing in unique):
                        unique.append(d)
                unique.sort()
            else:
                unique = sorted(list(set(converted)))
        
        return unique
    
    def _compute_sonority_intervals(self) -> List[IntervalType]:
        if not self._degrees or len(self._degrees) <= 1:
            return []
        
        result = []
        if self._interval_type_mode == "cents":
            for i in range(1, len(self._degrees)):
                result.append(self._degrees[i] - self._degrees[i-1])
        else:
            for i in range(1, len(self._degrees)):
                prev = self._degrees[i-1]
                if prev == 0 or (isinstance(prev, Fraction) and prev.numerator == 0):
                    result.append(Fraction(0, 1))
                else:
                    result.append(self._degrees[i] / prev)
        
        return result
    
    @property
    def intervals(self) -> List[IntervalType]:
        """list : Successive intervals between adjacent voicing tones."""
        return self._intervals

    @property
    def freq(self) -> tuple:
        """tuple of float : Frequencies of the voicing's pitches.

        A tuple, so ``freq=voicing.freq`` assigns the whole voicing as one
        simultaneity when used as the ``freq`` pfield (alias of
        :attr:`freqs`).
        """
        return self.freqs

    def root(self, pitch: Union[Pitch, str]) -> 'Voicing':
        """
        Return a copy rooted at the given pitch.

        Parameters
        ----------
        pitch : Pitch or str
            The reference pitch.

        Returns
        -------
        Voicing
        """
        return Voicing(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            pitch
        )
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> Union[Pitch, IntervalType, PitchCollectionBase]:
        if isinstance(index, slice):
            return self._getitem_slice_sonority(index)
        
        if hasattr(index, '__iter__') and not isinstance(index, str):
            flat_indices = self._flatten_indices(index)
            return self._getitem_sequence_sonority(flat_indices)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        return self._getitem_single_sonority(index)
    
    def _getitem_single_sonority(self, index: int) -> Pitch:
        return self._calculate_pitch(index)

    def _getitem_slice_sonority(self, index: slice) -> PitchCollectionBase:
        selected_degrees = self._degrees[index]
        subset = RelativePitchCollection(list(selected_degrees), self._interval_type_mode, self._equave, self._reference_pitch)
        subset._equave_cyclic = False
        return subset

    def _getitem_sequence_sonority(self, indices: Sequence[int]) -> PitchCollectionBase:
        selected_degrees = [self._degrees[int(i) if not isinstance(i, int) else i] for i in indices]
        subset = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        subset._equave_cyclic = False
        return subset
    
    @classmethod
    def from_collection(cls, collection: PitchCollectionBase, equave: Union[float, Fraction, int, str, None] = None) -> 'Voicing':
        """
        Construct a Voicing from an existing relative pitch collection.

        Parameters
        ----------
        collection : PitchCollectionBase
            A relative pitch collection to convert.
        equave : float, Fraction, int, str, or None, optional
            Override equave. Defaults to the collection's equave.

        Returns
        -------
        Voicing

        Raises
        ------
        ValueError
            If the collection is absolute (not relative).
        """
        if not collection.is_relative:
            raise ValueError("Cannot create Voicing from absolute collection")
        target_equave = equave if equave is not None else (collection.equave if collection.equave is not None else Fraction(2, 1))
        return cls(
            list(collection._degrees),
            collection._interval_type_mode,
            target_equave,
            collection._reference_pitch
        )


class ChordSequence:
    """
    An ordered sequence of Chord or Voicing objects.

    Provides a container for chord progressions or harmonic sequences.

    Parameters
    ----------
    chords : list of Chord or Voicing, optional
        The chord objects in the sequence.

    Examples
    --------
    >>> chord1 = Chord(["1/1", "5/4", "3/2"])
    >>> chord2 = Chord(["1/1", "6/5", "3/2"])
    >>> sequence = ChordSequence([chord1, chord2])
    >>> len(sequence)
    2
    """
    
    def __init__(self, chords: List[Union[Chord, Voicing]] = None):
        self._chords = chords if chords is not None else []
    
    @property
    def chords(self) -> List[Union[Chord, Voicing]]:
        """list : A copy of the chord objects in this sequence."""
        return self._chords.copy()
    
    def __len__(self) -> int:
        return len(self._chords)
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> Union[Chord, Voicing, 'ChordSequence']:
        if isinstance(index, slice):
            return ChordSequence(self._chords[index])
        if hasattr(index, '__iter__') and not isinstance(index, str):
            flat = self._flatten_indices(index)
            return ChordSequence([self._chords[i] for i in flat])
        return self._chords[index]

    @staticmethod
    def _flatten_indices(index) -> List[int]:
        result: List[int] = []
        for item in index:
            if hasattr(item, '__iter__') and not isinstance(item, (str, int)):
                result.extend(ChordSequence._flatten_indices(item))
            else:
                result.append(int(item))
        return result
    
    def __iter__(self):
        return iter(self._chords)

    def voicing(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> 'ChordSequence':
        """
        Return a new sequence with the same voicing applied to every chord.

        Elements that are already :class:`Voicing` are first reduced to
        their underlying :class:`Chord` form, so the passed voicing
        *replaces* any existing one.

        Parameters
        ----------
        index : int, slice, or sequence of int
            Voicing indices, as in :meth:`Chord.voicing` (cyclic indices
            reach other equaves).

        Returns
        -------
        ChordSequence
        """
        voiced = []
        for ch in self._chords:
            base = ch if isinstance(ch, Chord) else Chord.from_collection(ch)
            voiced.append(base.voicing(index))
        return ChordSequence(voiced)

    def root(self, pitch: Union[Pitch, str]) -> 'ChordSequence':
        """
        Return a new sequence with every chord rooted at the given pitch.

        Parameters
        ----------
        pitch : Pitch or str
            The reference pitch.

        Returns
        -------
        ChordSequence
        """
        return ChordSequence([ch.root(pitch) for ch in self._chords])

    def transpose(self, interval) -> 'ChordSequence':
        """
        Return a new sequence with every chord transposed by *interval*.

        Each element keeps its own carrier semantics: Chords move their
        reference pitch, Voicings shift their degrees.

        Parameters
        ----------
        interval : Fraction, int, float, str, Ratio, or Cent
            The transposition interval, as in :meth:`Pitch.transpose`.

        Returns
        -------
        ChordSequence
        """
        return ChordSequence([ch.transpose(interval) for ch in self._chords])

    def equave_shift(self, n: int) -> 'ChordSequence':
        """
        Return a new sequence with every chord shifted by *n* equaves.

        Parameters
        ----------
        n : int
            Number of equaves to shift (negative shifts down).

        Returns
        -------
        ChordSequence
        """
        return ChordSequence([ch.equave_shift(n) for ch in self._chords])

    def folded(self, lo=None, hi=None) -> 'ChordSequence':
        """
        Return a new sequence with each chord folded into ``[lo, hi]``.

        Parameters
        ----------
        lo, hi : optional
            Register bounds, as in :func:`~klotho.tonos.chords.voice_leading.fold`.

        Returns
        -------
        ChordSequence
        """
        from .voice_leading import fold
        return ChordSequence([fold(chord, lo, hi) for chord in self._chords])

    def voice_led(self, lo=None, hi=None) -> 'ChordSequence':
        """
        Return a new sequence voice-led with minimal per-voice movement.

        Parameters
        ----------
        lo, hi : optional
            Register bounds, as in :func:`~klotho.tonos.chords.voice_leading.voice_lead`.

        Returns
        -------
        ChordSequence
        """
        from .voice_leading import voice_lead
        return ChordSequence(voice_lead(self._chords, lo, hi))

    def __repr__(self) -> str:
        return f"ChordSequence({len(self._chords)} chords)"
    
    def __str__(self) -> str:
        return f"ChordSequence({len(self._chords)} chords)"
