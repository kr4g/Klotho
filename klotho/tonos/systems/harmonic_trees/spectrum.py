from klotho.tonos.utils.frequency_conversion import freq_to_pitchclass
from klotho.tonos.utils.harmonics import partial_to_fundamental
from klotho.tonos.pitch import Pitch
from typing import Union
from fractions import Fraction
# from klotho.topos.graphs.trees import Tree
from .harmonic_tree import HarmonicTree
import pandas as pd

class Spectrum():
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
        self._fundamental = (Pitch(*freq_to_pitchclass(fundamental)) 
                           if isinstance(fundamental, (int, float)) 
                           else fundamental)
        self._ht = HarmonicTree(self._fundamental.partial, partials)
        self._data = self._init_data()

    @property
    def fundamental(self):
        return self._fundamental

    @property
    def partials(self):
        return tuple(self._data['partial'])
    
    @property
    def data(self):
        return self._data
    
    @property
    def ht(self):
        return self._ht
    
    def __getitem__(self, key):
        """
        Get a Pitch by its partial number.
        
        Args:
            key: The partial number to retrieve
            
        Returns:
            The Pitch corresponding to the partial number
            
        Raises:
            KeyError: If the partial number doesn't exist in the spectrum
        """
        if key not in self.partials:
            raise KeyError(f"Partial {key} not found in spectrum")
            
        return self.data.loc[self.data['partial'] == key, 'pitch'].iloc[0]
    
    def _init_data(self):
        df_data = []
        for node in self._ht.nodes:
            harmonic = self._ht.graph.nodes[node]['harmonic']
            pitch = Pitch.from_freq(self._fundamental.freq * harmonic, harmonic)
            self._ht.graph.nodes[node]['pitch'] = pitch

            if node in self._ht.leaf_nodes:
                df_data.append({
                    'partial': harmonic,
                    'freq (Hz)': pitch.freq,
                    'pitch': pitch,
                    'cents_offset': pitch.cents_offset,
                    'node_id': node
                })
        return pd.DataFrame(df_data).sort_values('partial').reset_index(drop=True)

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
        if source_partial not in self.partials:
            raise ValueError(f"Source partial {source_partial} not found in spectrum")
        elif target_partial not in self.partials:
            raise ValueError(f"Target partial {target_partial} not found in spectrum")
        
        source_pitch = self.data.loc[self.data['partial'] == source_partial, 'pitch'].iloc[0]
        
        # Create a new Pitch with the target partial instead of trying to modify the existing one
        new_pitch = Pitch(
            source_pitch.pitchclass,
            source_pitch.octave,
            source_pitch.cents_offset,
            target_partial  # Use the target partial here
        )
        
        return Spectrum.from_target(new_pitch, self.partials)

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
        if partial not in self.partials:
            raise ValueError(f"Partial {partial} not found in spectrum")
        
        ratio = target.freq / self.data['freq (Hz)'][self.data['partial'] == partial].iloc[0]
        new_fundamental = self.fundamental.freq * ratio
        return Spectrum(new_fundamental, self.partials)

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
        if source_partial not in self.partials:
            raise ValueError(f"Source partial {source_partial} not found in source spectrum")
        if target_partial not in target.partials:
            raise ValueError(f"Target partial {target_partial} not found in target spectrum")
        
        source_pitch = self.data['pitch'][self.data['partial'] == source_partial].iloc[0]
        target_pitch = target.data['pitch'][target.data['partial'] == target_partial].iloc[0]
        ratio = target_pitch['frequency'] / source_pitch['frequency']
        new_fundamental = self.fundamental.freq * ratio
        return Spectrum(new_fundamental, self.partials)

    def __str__(self) -> str:
        df_str = str(self._data)
        width = max(len(line) for line in df_str.split('\n'))
        border = '-' * width
        
        fund_cents = f'({round(self.fundamental.cents_offset, 2):+} cents)' if round(self.fundamental.cents_offset, 2) != 0 else ''
        header = (
            f"{border}\n"
            f"Fundamental: {self.fundamental.freq} Hz | {self.fundamental.pitchclass}{self.fundamental.octave} {fund_cents}\n"
            # f"Freq. Range: {round(self.fundamental.freq, 2)} Hz - {round(self.fundamental.freq * max(self.partials), 2)} Hz\n"
            f"{border}\n"
        )
        return header + df_str + f"\n{border}\n"
    
    def __repr__(self):
        return self.__str__()

