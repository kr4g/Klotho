from ..tonos import Pitch, freq_to_pitchclass, partial_to_fundamental
from typing import Union
from fractions import Fraction

class Spectrum:
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

    def __str__(self):
        cents_offset = f'({self._fundamental.cents_offset:+0.2f} cents)' if round(self._fundamental.cents_offset, 2) != 0 else ''
        return (
            f'Fundamental: {self._fundamental.pitchclass}{self._fundamental.octave} {cents_offset}\n'
            f'Partials:    {self._partials}\n'
            f'Freq. Range: {round(self._fundamental.freq, 2)} Hz - {round(self._fundamental.freq * max(self._partials), 2)} Hz\n'
        )
    
    def __repr__(self):
        return self.__str__()
