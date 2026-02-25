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
    A harmonic spectrum built from a fundamental frequency and partial numbers.

    Manages a collection of pitches derived from a fundamental and a list of
    partial numbers (harmonic or non-harmonic). Provides operations for
    reinterpreting, retargeting, and modulating the spectrum.

    Parameters
    ----------
    fundamental : int, float, or Pitch
        The fundamental frequency (Hz) or a Pitch object.
    partials : list of int, float, or Fraction
        Partial numbers defining the spectrum.

    Examples
    --------
    >>> spectrum = Spectrum(Pitch('A', 4), [1, 2, 3, 4])
    >>> spectrum = Spectrum.from_target(Pitch('A', 4, partial=3), [1, 2, 3, 4])
    """
    def __init__(self, fundamental: Union[int, float, Pitch], partials: list[Union[int, float, Fraction]]):
        self._fundamental = (Pitch(*freq_to_pitchclass(fundamental)) 
                           if isinstance(fundamental, (int, float)) 
                           else fundamental)
        self._ht = HarmonicTree(self._fundamental.partial, partials)
        self._data = self._init_data()

    @property
    def fundamental(self):
        """Pitch : The fundamental pitch of the spectrum."""
        return self._fundamental

    @property
    def partials(self):
        """tuple : The partial numbers present in the spectrum."""
        return tuple(self._data['partial'])
    
    @property
    def data(self):
        """pandas.DataFrame : Tabular data with partial, frequency, pitch, and offset columns."""
        return self._data
    
    @property
    def ht(self):
        """HarmonicTree : The underlying harmonic tree structure."""
        return self._ht
    
    def __getitem__(self, key):
        """
        Get a Pitch by its partial number.

        Parameters
        ----------
        key : int or float
            The partial number to retrieve.

        Returns
        -------
        Pitch
            The Pitch corresponding to the partial number.

        Raises
        ------
        KeyError
            If the partial number does not exist in the spectrum.
        """
        if key not in self.partials:
            raise KeyError(f"Partial {key} not found in spectrum")
            
        return self.data.loc[self.data['partial'] == key, 'pitch'].iloc[0]
    
    def _init_data(self):
        df_data = []
        for node in self._ht.nodes:
            harmonic = self._ht[node]['harmonic']
            pitch = Pitch.from_freq(self._fundamental.freq * harmonic, harmonic)
            self._ht[node]['pitch'] = pitch

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
        Create a Spectrum where *target* is a known partial rather than the fundamental.

        The fundamental is back-calculated from the target pitch and its
        partial number.

        Parameters
        ----------
        target : Pitch
            A Pitch whose ``partial`` attribute identifies which partial it
            represents.
        partials : list of int, float, or Fraction
            Partial numbers to include.

        Returns
        -------
        Spectrum

        Raises
        ------
        ValueError
            If the target's partial number is not in *partials*.
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
        Reinterpret a partial as a different partial number, adjusting the fundamental.

        Parameters
        ----------
        source_partial : int or float
            The partial number to reinterpret.
        target_partial : int or float
            The new partial number to assign.

        Returns
        -------
        Spectrum
            A new Spectrum with the adjusted fundamental.

        Raises
        ------
        ValueError
            If either partial is not in the spectrum.
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
        Adjust the spectrum so that the given partial matches *target*.

        Parameters
        ----------
        partial : int or float
            The partial number to adjust.
        target : Pitch
            The target pitch to match.

        Returns
        -------
        Spectrum
            A new Spectrum with the adjusted fundamental.

        Raises
        ------
        ValueError
            If the partial is not in the spectrum.
        """
        if partial not in self.partials:
            raise ValueError(f"Partial {partial} not found in spectrum")
        
        ratio = target.freq / self.data['freq (Hz)'][self.data['partial'] == partial].iloc[0]
        new_fundamental = self.fundamental.freq * ratio
        return Spectrum(new_fundamental, self.partials)

    def modulate(self, target: 'Spectrum', source_partial: Union[int, float], target_partial: Union[int, float]) -> 'Spectrum':
        """
        Adjust this spectrum so that *source_partial* aligns with *target_partial* in another spectrum.

        Parameters
        ----------
        target : Spectrum
            The target spectrum to align with.
        source_partial : int or float
            Partial number from this spectrum to adjust.
        target_partial : int or float
            Partial number from the target spectrum to match.

        Returns
        -------
        Spectrum
            A new Spectrum with the adjusted fundamental.

        Raises
        ------
        ValueError
            If either partial is not found in its respective spectrum.
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

