from ..tonos import Pitch, freq_to_pitchclass, partial_to_fundamental
from typing import Union
from fractions import Fraction

class Spectrum:
    """
    A class representing a harmonic spectrum based on a fundamental frequency and its partials.

    The Spectrum class manages a collection of pitches derived from a fundamental frequency
    and a list of partial numbers (harmonic or non-harmonic). It provides methods for
    manipulating and transforming the spectrum through various operations.

    Attributes:
        fundamental (Pitch): The fundamental frequency of the spectrum
        partials (list): List of partial numbers (can be integers, floats, or Fractions)
        data (dict): Dictionary containing the fundamental and all calculated partial pitches

    Example:
        >>> spectrum = Spectrum(Pitch('A', 4), [1, 2, 3, 4])  # Creates spectrum with A4 fundamental
        >>> spectrum = Spectrum.from_target(Pitch('A', 4, partial=3), [1, 2, 3, 4])  # Creates spectrum where A4 is 3rd partial
    """
    def __init__(self, fundamental: Union[int, float, Pitch], partials: list[Union[int, float, Fraction]]):
        self._fundamental = Pitch(*freq_to_pitchclass(fundamental)) if isinstance(fundamental, (int, float)) else fundamental
        self._partials = partials
        self._data = self._init_data()

    @property
    def fundamental(self):
        return self._fundamental

    @property
    def partials(self):
        return self._partials
    
    @property
    def data(self):
        return self._data

    def _init_data(self):
        sonority = {}
        sonority['fundamental'] = self._fundamental
        sonority['partials'] = {
            p: Pitch(*freq_to_pitchclass(self._fundamental.freq * p), partial = p) for p in self._partials
        }
        return sonority
    
    @classmethod
    def from_target(cls, target: Pitch, partials: list[Union[int, float, Fraction]]):
        """
        Create a Spectrum from a target pitch and list of partials.
        
        Args:
            target: A Pitch object representing a partial in the spectrum
            partials: List of partial numbers to include
            
        Returns:
            A new Spectrum instance with the calculated fundamental
        
        Raises:
            ValueError: If target's partial number is not in the partials list
        """
        if target.partial not in partials:
            raise ValueError(f"Target partial {target.partial} must be in the list of partials")
            
        fund_pc, fund_oct, fund_cents = partial_to_fundamental(
            target.pitchclass, 
            target.octave, 
            target.partial, 
            target.cents_offset
        )
        fundamental = Pitch(fund_pc, fund_oct, fund_cents)
        
        return cls(fundamental, partials)

    def pivot(self, source_partial: Union[int, float], target_partial: Union[int, float]) -> 'Spectrum':
        """
        Reinterpret a partial as a different partial number, adjusting the spectrum accordingly.
        
        Args:
            source_partial: The partial number to reinterpret
            target_partial: The new partial number to use
            
        Returns:
            A new Spectrum with the adjusted fundamental
            
        Raises:
            ValueError: If either partial is not in the spectrum
        """
        if source_partial not in self._partials:
            raise ValueError(f"Source partial {source_partial} not found in spectrum")
        elif target_partial not in self._partials:
            raise ValueError(f"Target partial {target_partial} not found in spectrum")
        
        pitch_to_pivot = self._data['partials'][source_partial]
        pitch_to_pivot.partial = target_partial
        new_fundamental = pitch_to_pivot.virtual_fundamental
        return Spectrum(new_fundamental, self._partials)

    def retarget(self, partial: Union[int, float], target: Pitch) -> 'Spectrum':
        """
        Adjust spectrum so the given partial matches the target pitch.
        
        Args:
            partial: The partial number to adjust
            target: The target pitch to match
            
        Returns:
            A new Spectrum with the adjusted fundamental
            
        Raises:
            ValueError: If the partial is not in the spectrum
        """
        if partial not in self._partials:
            raise ValueError(f"Partial {partial} not found in spectrum")
        
        ratio = target.freq / self._data['partials'][partial].freq
        new_fundamental = self._fundamental.freq * ratio
        return Spectrum(new_fundamental, self._partials)

    def modulate(self, target: 'Spectrum', source_partial: Union[int, float], target_partial: Union[int, float]) -> 'Spectrum':
        """
        Adjusts spectrum so that its source_partial matches target_partial in the target spectrum.
        
        Args:
            target: The target spectrum to align with
            source_partial: The partial number from this spectrum to adjust
            target_partial: The partial number from the target spectrum to match
            
        Returns:
            A new Spectrum with the adjusted fundamental
            
        Raises:
            ValueError: If either partial is not in its respective spectrum
        """
        if source_partial not in self._partials:
            raise ValueError(f"Source partial {source_partial} not found in source spectrum")
        if target_partial not in target.partials:
            raise ValueError(f"Target partial {target_partial} not found in target spectrum")
        
        source_pitch = self._data['partials'][source_partial]
        target_pitch = target.data['partials'][target_partial]
        ratio = target_pitch.freq / source_pitch.freq
        new_fundamental = self._fundamental.freq * ratio
        return Spectrum(new_fundamental, self._partials)

    def __str__(self):
        cents_offset = f'({self._fundamental.cents_offset:+0.2f} cents)' if round(self._fundamental.cents_offset, 2) != 0 else ''
        return (
            f'Fundamental: {self._fundamental.pitchclass}{self._fundamental.octave} {cents_offset}\n'
            f'Partials:    {self._partials}\n'
            f'Freq. Range: {round(self._fundamental.freq, 2)} Hz - {round(self._fundamental.freq * max(self._partials), 2)} Hz\n'
        )
    
    def __repr__(self):
        return self.__str__()

