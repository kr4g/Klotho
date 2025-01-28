from ..spectrum import Spectrum
from ...tonos import Pitch
from typing import Union

def pivot(spectrum: Spectrum, source_partial: Union[int, float], target_partial: Union[int, float]) -> Spectrum:
    """Reinterpret a partial as a different partial number, adjusting the spectrum accordingly."""
    if source_partial not in spectrum.partials:
        raise ValueError(f"Source partial {source_partial} not found in spectrum")
    elif target_partial not in spectrum.partials:
        raise ValueError(f"Target partial {target_partial} not found in spectrum")
    
    pitch_to_pivot = spectrum.data['partials'][source_partial]
    pitch_to_pivot.partial = target_partial
    new_fundamental = pitch_to_pivot.virtual_fundamental
    return Spectrum(new_fundamental, spectrum.partials)

def retarget(spectrum: Spectrum, partial: Union[int, float], target: Pitch) -> Spectrum:
    """Adjust spectrum so the given partial matches the target pitch."""
    if partial not in spectrum.partials:
        raise ValueError(f"Partial {partial} not found in spectrum")
    
    ratio = target.freq / spectrum.data['partials'][partial].freq
    new_fundamental = spectrum.fundamental.freq * ratio
    return Spectrum(new_fundamental, spectrum.partials)

def modulate(source: Spectrum, target: Spectrum, source_partial: Union[int, float], target_partial: Union[int, float]) -> Spectrum:
    """Adjust target spectrum to align source_partial with target_partial."""
    if source_partial not in source.partials:
        raise ValueError(f"Source partial {source_partial} not found in source spectrum")
    if target_partial not in target.partials:
        raise ValueError(f"Target partial {target_partial} not found in target spectrum")
    
    source_pitch = source.data['partials'][source_partial]
    ratio = source_pitch.freq / target.data['partials'][target_partial].freq
    new_fundamental = target.fundamental.freq * ratio
    return Spectrum(new_fundamental, target.partials)
