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
    """
    Enum for musical tempo markings mapped to beats per minute (bpm).

    Each tempo marking is associated with a range of beats per minute.
    This enumeration returns a tuple representing the minimum and maximum
    bpm for each tempo.

    .. list-table:: Tempo Markings
       :header-rows: 1

       * - Name
         - Tempo Marking
         - BPM Range
       * - Larghissimo
         - extremely slow
         - 12 -- 24
       * - Adagissimo_Grave
         - very slow, solemn
         - 24 -- 40
       * - Largo
         - slow and broad
         - 40 -- 66
       * - Larghetto
         - rather slow and broad
         - 44 -- 66
       * - Adagio
         - slow and expressive
         - 44 -- 68
       * - Adagietto
         - slower than andante
         - 46 -- 80
       * - Lento
         - slow
         - 52 -- 108
       * - Andante
         - walking pace
         - 56 -- 108
       * - Andantino
         - slightly faster than andante
         - 80 -- 108
       * - Marcia_Moderato
         - moderate march
         - 66 -- 80
       * - Andante_Moderato
         - between andante and moderato
         - 80 -- 108
       * - Moderato
         - moderate speed
         - 108 -- 120
       * - Allegretto
         - moderately fast
         - 112 -- 120
       * - Allegro_Moderato
         - slightly less than allegro
         - 116 -- 120
       * - Allegro
         - fast, bright
         - 120 -- 156
       * - Molto_Allegro_Allegro_Vivace
         - slightly faster than allegro
         - 124 -- 156
       * - Vivace
         - lively, fast
         - 156 -- 176
       * - Vivacissimo_Allegrissimo
         - very fast, bright
         - 172 -- 176
       * - Presto
         - very fast
         - 168 -- 200
       * - Prestissimo
         - extremely fast
         - 200 -- 300

    Examples
    --------
    >>> TEMPO.Adagio.min
    44
    >>> TEMPO.Adagio.max
    68
    """
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
    """
    Determine the new tempo for a metric modulation between two beat values.

    A metric modulation holds the underlying NOTE-VALUE GRID steady and
    changes which note value is counted as the beat. The pivot note value
    keeps the duration it already had; because a different note value now
    carries the pulse, the tempo number changes. (The beat's duration is
    exactly what does NOT stay constant -- if it did, the tempo could not
    change.)

    So a shorter new beat value gives a faster tempo: at quarter = 120 an
    eighth lasts 0.25 s, and counting that eighth as the beat is 240 bpm.
    The relation is ``T' = T * b / b'``.

    See: https://en.wikipedia.org/wiki/Metric_modulation

    Parameters
    ----------
    current_tempo : float
        The original tempo in beats per minute.
    current_beat_value : Fraction, str, or float
        The note value (as a fraction of a whole note) representing one beat
        before modulation.
    new_beat_value : Fraction, str, or float
        The note value (as a fraction of a whole note) representing one beat
        after modulation.

    Returns
    -------
    float
        The new tempo in beats per minute after the metric modulation.

    Examples
    --------
    >>> metric_modulation(120, '1/4', '1/8')
    240.0
    """
    current_beat_value = Fraction(current_beat_value)
    new_beat_value = Fraction(new_beat_value)
    # The invariant is the grid, expressed as the whole note's duration:
    # one beat of value b lasts 60/T seconds and lasts W*b, so W = 60/(T*b).
    # Both steps DIVIDE by the beat value; multiplying inverted the result
    # (it returned T*b'/b, i.e. 60.0 for the example above, not 240.0).
    whole_note_duration = 60 / current_tempo / current_beat_value
    new_tempo = 60 / whole_note_duration / new_beat_value
    return float(new_tempo)

def tempo_for_duration(metric_ratio: Union[Fraction, str, float], reference_beat: Union[Fraction, str, float], duration: float) -> float:
    """
    Calculate the tempo required for a metric ratio to last a specified duration.

    Parameters
    ----------
    metric_ratio : Fraction, str, or float
        The metric ratio representing the total duration (e.g., ``'4/4'``).
    reference_beat : Fraction, str, or float
        The beat value that defines the tempo (e.g., ``'1/4'`` for a
        quarter note).
    duration : float
        The desired duration in seconds.

    Returns
    -------
    float
        The tempo in beats per minute.

    Examples
    --------
    >>> tempo_for_duration('4/4', '1/4', 2.0)
    120.0
    """
    metric_ratio = Fraction(metric_ratio)
    reference_beat = Fraction(reference_beat)
    
    beats_in_metric = metric_ratio / reference_beat
    bpm = float(beats_in_metric * 60 / duration)
    
    return bpm

def beat_for_duration(metric_ratio: Union[Fraction, str, float], bpm: float, duration: float) -> Fraction:
    """
    Calculate the reference beat value for a metric ratio at a given tempo and duration.

    Parameters
    ----------
    metric_ratio : Fraction, str, or float
        The metric ratio representing the total duration (e.g., ``'4/4'``).
    bpm : float
        The tempo in beats per minute.
    duration : float
        The desired duration in seconds.

    Returns
    -------
    Fraction
        The reference beat value as a fraction.

    Examples
    --------
    >>> beat_for_duration('4/4', 120, 2.0)
    Fraction(1, 4)
    """
    metric_ratio = Fraction(metric_ratio)
    reference_beat = Fraction(metric_ratio * 60) / Fraction(bpm * duration)
    
    return reference_beat
