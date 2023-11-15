# ------------------------------------------------------------------------------------
# MUSIC TOPOLOGY TOOLS
# ------------------------------------------------------------------------------------
'''
The `topos` base module.
'''

from allopy.chronos import chronos
from allopy.aikous import aikous
from sympy.utilities.iterables import cartes

def isorhythm(color: list, talea: list, end=True, kwargs=None):
    '''
    **iso_pairs** (from the Greek for "the same rhythm") is a musical technique using a 
    repeating rhythmic pattern, called a *talea*, in at least one voice part throughout 
    a composition. *Taleae* are typically applied to one or more melodic patterns of 
    pitches or *colores*, which may be of the same or a different length from the *talea*.
    
    see: https://en.wikipedia.org/wiki/iso_pairs
    
    Args:
        color (list): a list of pitches
        talea (list): a list of durations
    '''
    color_len = len(color)
    talea_len = len(talea) 
    iso_len = color_len * talea_len
    min_amp = aikous.Dynamics.ppp
    max_amp = aikous.Dynamics.p
    
    start_time = 0.0
    rows_list = []
    for i in range(iso_len):
        i_color = i % color_len
        i_talea = i % talea_len
        
        # -----------
        amplitude = min_amp       # default amplitude
        if i % talea_len == 0:    # accent at each talea cycle
            amplitude = max_amp   # accent amplitude
            
        new_row = {
            'start'      : start_time,
            'dur'        : talea[i_talea],
            'synthName'  : 'PluckedString',
            'amplitude'  : amplitude,
            'frequency'  : color[i_color],
        }
        if kwargs:
            # kwargs['attackTime']  = talea[i_talea] * 0.05
            kwargs['releaseTime'] = talea[i_talea] * 3.47
            for key, value in kwargs.items():
                new_row[key] = value
        rows_list.append(new_row)
        # -----------
        start_time += talea[i_talea]

    # last note
    if end:
        new_row = {
            'start'      : start_time,
            'dur'        : max(talea),
            'synthName'  : 'PluckedString',
            'amplitude'  : amplitude,
            'frequency'  : color[0],
        }
        if kwargs:
            # kwargs['attackTime']  = talea[i_talea] * 0.01
            kwargs['releaseTime'] = talea[i_talea] * 6.23
            for key, value in kwargs.items():
                new_row[key] = value
        rows_list.append(new_row)
    
    return rows_list

def iso_pairs(l1: list, l2: list) -> list:
    '''
    Generates pairs of elements from two lists, l1 and l2, in a cyclic manner. 

    Creates a list of tuples where each element from l1 is paired with each 
    element from l2. The pairing continues cyclically until the length
    of the generated list equals the product of the lengths of l1 and l2. 
    Specifically, when the end of either list is reached, the iteration 
    continues from the beginning of that list, effectively cycling through 
    the shorter list until all pairings are created.
    
    This is a form of "cyclic pairing" or "modulo-based pairing" and is 
    different from computing the Cartesian product.

    Args:
        l1 (list): The first list.
        l2 (list): The second list.
    
    Returns:
        list: A list of tuples where each element from l1 is paired with each 
        element from l2.

    Example:
    >>> iso_pairs([1, 2], ['A', 'B', 'C'])
    [(1, 'A'), (2, 'B'), (1, 'C'), (2, 'A'), (1, 'B'), (2, 'C')]
    '''
    return [(l1[i % len(l1)], l2[i % len(l2)]) for i in range(len(l1) * len(l2))]

def ratio_pulse_pairs(metric_ratios: list, pulses: list, bpm: float = 60) -> list:
    '''
    Given a list of metric beat ratios and a list of pulses, generates a sequence of 
    events that cycles through combinations of each metric ratio repeated for each
    pulse in the pulse list.
    '''
    metric_ratio_cps = list(cartes(metric_ratios, metric_ratios))  # cartesian product of metric ratios
    # durations = []
    duration_pulse_pairs = []
    for i, (ratio_1, ratio_2) in enumerate(metric_ratio_cps):
        tempo = chronos.metric_modulation(bpm, ratio_1, ratio_2)
        duration = chronos.beat_duration(1/10, tempo)
        # durations.extend([duration] * pulses[i % len(pulses)])
        duration_pulse_pairs.append((duration, pulses[i % len(pulses)]))
    return duration_pulse_pairs

def cyclic_cartesian_pairs(l1: list, l2: list) -> list:
    '''
    Generates a sequence of pairs by first creating a Cartesian product of list l1 with itself,
    and then cycling through these pairs while pairing them with elements from list l2.
    Each pair from the Cartesian product of l1 is combined with an element from l2, 
    cycling through l2 as necessary.

    Args:
        l1 (list): The first list.
        l2 (list): The second list.
    
    Returns:
        list: A list of tuples, each containing a pair from the Cartesian product of l1 and an element from l2.

    Example:
    >>> cyclic_cartesian_pairs(['A', 'B'], [1, 2, 3])
    [('A', 'A', 1), ('B', 'A', 2), ('A', 'A', 3), ('B', 'B', 1), ('A', 'B', 2), ('B', 'B', 3)]
    '''
    return iso_pairs(list(cartes(l1, l1)), l2)
