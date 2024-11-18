from klotho.chronos import seconds_to_hmsms
from klotho.tonos import fold_interval, fold_freq
from klotho.tonos.harmonic_trees import HarmonicTree as HT
from klotho.chronos.rhythm_trees import Meas
from klotho.chronos.rhythm_pairs import RhythmPair as RP
from klotho.chronos.temporal_units import TemporalUnit as UT, TemporalUnitSequence as UTSeq

from sympy import isprime
from math import log2, log

def is_power_of_2(n):
        return n > 0 and log2(n).is_integer()

def is_power_of_3(n):
    return n > 0 and (log(n, 3).is_integer())

def rewrite_system(data):
    if isinstance(data, int):
        # Rewrite integer into a (D, S) tuple based on rules
        match data:
            case n if is_power_of_2(n):
                return (n, (n + 5, n + 4))
            case n if is_power_of_3(n):
                return (n, (n + 5, n + 7, n + 3))
            case n if n % 2 == 0:
                return (n, (7 * n, 3 * n))
            case n if n % 2 != 0:
                return (n, (3 * n, 7 * n, 5 * n))
            case _:
                return (n, (n + 3, n + 2))
    elif isinstance(data, tuple):
        # Recurse into the S part of (D, S) tuples
        match data:
            case (d, s) if isinstance(d, int) and isinstance(s, tuple):
                return (d, tuple(rewrite_system(item) for item in s))
            case _:
                # Top-level input tuple of integers
                return tuple(rewrite_system(item) for item in data)
    else:
        raise ValueError("Invalid input. Must be an integer or a tuple.")

def iterate_rewrite(data, max_iterations=5):
    iterations = 0
    current = data
    while iterations < max_iterations:
        rewritten = rewrite_system(current)
        if rewritten == current:
            break
        current = rewritten
        iterations += 1
        # print(f'i: {iterations} -> {current}')
    return current, iterations

# nested_tuple = RP((3, 5, 7), subdivs=True).measures
# print(nested_tuple)
# nested_tuple = (3,5)
# print(f'Axiom: {nested_tuple}\n')

# rewritten, iterations = iterate_rewrite(nested_tuple)
# print(f'Rewritten: {rewritten}')
# print(f'Total Iterations: {iterations}')

# print('-' * 80)

S = (3, 5, 7)
ut = UT(duration=30, tempus=Meas((1, 1)), prolatio=RP(S, subdivs=False).measures, tempo=54, beat='1/8')
print(ut)
print('-' * 80)
utseq = ut.decompose([m[1] for m in RP(S, subdivs=True).measures])

for ut in utseq:
    print(ut, end='')
    print('Ratios: ', ', '.join(str(r) for r in ut.ratios), end='\n\n')
print(seconds_to_hmsms(utseq.time))

# from klotho.aikous.messaging import Scheduler
# from itertools import cycle
# from sympy import prime

# import json
# output_data = []
# for i, ut in enumerate(utseq):
#     partials = HT(1, ut.prolationis).partials
#     ratios = cycle(partials)
    
#     prolat_ratios = [str(r) for r in ut.ratios]
    
#     fund = 333.0 * fold_interval(float(ut.tempus))
#     output_data.append({
#         "ut_number": i,
#         "tempus": str(ut.tempus),
#         "prolat_ratios": prolat_ratios,
#         "partials": [str(p) for p in partials]
#     })

#     for j, event in enumerate(ut):
#         duration = event['duration']
#         ratio = next(ratios)

# with open('ut_data.json', 'w') as f:
#     json.dump(output_data, f, indent=2)