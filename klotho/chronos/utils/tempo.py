from typing import Union
from fractions import Fraction
from klotho.utils.data_structures.enums import MinMaxEnum

__all__ = [
    'TEMPO',
    'metric_modulation',
    'tempo_for_duration',
    'beat_for_duration',
]

class TEMPO(MinMaxEnum):
  '''
  Enum for musical tempo markings mapped to beats per minute (bpm).

  Each tempo marking is associated with a range of beats per minute. 
  This enumeration returns a tuple representing the minimum and maximum bpm for each tempo.

  ----------------|----------------------|----------------
  Name            | Tempo Marking        | BPM Range
  ----------------|----------------------|----------------
  Larghissimo     | extremely slow       | (12 - 24 bpm)
  Adagissimo_Grave | very slow, solemn   | (24 - 40 bpm)
  Largo           | slow and broad       | (40 - 66 bpm)
  Larghetto       | rather slow and broad| (44 - 66 bpm)
  Adagio          | slow and expressive  | (44 - 68 bpm)
  Adagietto       | slower than andante  | (46 - 80 bpm)
  Lento           | slow                 | (52 - 108 bpm)
  Andante         | walking pace         | (56 - 108 bpm)
  Andantino       | slightly faster than andante | (80 - 108 bpm)
  Marcia_Moderato | moderate march       | (66 - 80 bpm)
  Andante_Moderato | between andante and moderato | (80 - 108 bpm)
  Moderato        | moderate speed       | (108 - 120 bpm)
  Allegretto      | moderately fast      | (112 - 120 bpm)
  Allegro_Moderato | slightly less than allegro | (116 - 120 bpm)
  Allegro         | fast, bright         | (120 - 156 bpm)
  Molto_Allegro_Allegro_Vivace | slightly faster than allegro | (124 - 156 bpm)
  Vivace          | lively, fast         | (156 - 176 bpm)
  Vivacissimo_Allegrissimo | very fast, bright | (172 - 176 bpm)
  Presto          | very fast            | (168 - 200 bpm)
  Prestissimo     | extremely fast       | (200 - 300 bpm)
  ----------------|----------------------|----------------

  Example use:
  `>>> Tempo.Adagio.min`
  '''  
  Larghissimo                  = (12, 24)
  Adagissimo_Grave             = (24, 40)
  Largo                        = (40, 66)
  Larghetto                    = (44, 66)
  Adagio                       = (44, 68)
  Adagietto                    = (46, 80)
  Lento                        = (52, 108)
  Andante                      = (56, 108)
  Andantino                    = (80, 108)
  Marcia_Moderato              = (66, 80)
  Andante_Moderato             = (80, 108)
  Moderato                     = (108, 120)
  Allegretto                   = (112, 120)
  Allegro_Moderato             = (116, 120)
  Allegro                      = (120, 156)
  Molto_Allegro_Allegro_Vivace = (124, 156)
  Vivace                       = (156, 176)
  Vivacissimo_Allegrissimo     = (172, 176)
  Presto                       = (168, 200)
  Prestissimo                  = (200, 300)
  
def metric_modulation(current_tempo:float, current_beat_value:Union[Fraction,str,float], new_beat_value:Union[Fraction,str,float]) -> float:
  '''
  Determine the new tempo (in BPM) for a metric modulation from one metric value to another.

  Metric modulation is calculated by maintaining the duration of a beat constant while changing
  the note value that represents the beat, effectively changing the tempo.
  
  see:  https://en.wikipedia.org/wiki/Metric_modulation

  Args:
  current_tempo (float): The original tempo in beats per minute.
  current_beat_value (float): The note value (as a fraction of a whole note) representing one beat before modulation.
  new_beat_value (float): The note value (as a fraction of a whole note) representing one beat after modulation.

  Returns:
  float: The new tempo in beats per minute after the metric modulation.
  '''
  current_beat_value = Fraction(current_beat_value)
  new_beat_value = Fraction(new_beat_value)
  current_duration = 60 / current_tempo * current_beat_value
  new_tempo = 60 / current_duration * new_beat_value
  return float(new_tempo)

def tempo_for_duration(metric_ratio: Union[Fraction, str, float], reference_beat: Union[Fraction, str, float], duration: float) -> float:
    '''
    Calculate the tempo (BPM) required for a given metric ratio to last a specified duration.
    
    Args:
        metric_ratio: The metric ratio representing the total duration (e.g., '4/4', '3/4')
        reference_beat: The beat value that defines the tempo (e.g., '1/4' for quarter note)
        duration: The desired duration in seconds
    
    Returns:
        float: The tempo in beats per minute
    '''
    metric_ratio = Fraction(metric_ratio)
    reference_beat = Fraction(reference_beat)
    
    beats_in_metric = metric_ratio / reference_beat
    bpm = float(beats_in_metric * 60 / duration)
    
    return bpm

def beat_for_duration(metric_ratio: Union[Fraction, str, float], bpm: float, duration: float) -> Fraction:
    '''
    Calculate the reference beat value required for a given metric ratio at a specified tempo to last a desired duration.
    
    Args:
        metric_ratio: The metric ratio representing the total duration (e.g., '4/4', '3/4')
        bpm: The tempo in beats per minute
        duration: The desired duration in seconds
    
    Returns:
        Fraction: The reference beat value as a fraction
    '''
    metric_ratio = Fraction(metric_ratio)
    reference_beat = Fraction(metric_ratio * 60) / Fraction(bpm * duration)
    
    return reference_beat
