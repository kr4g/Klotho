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
        match data:
            # case n if isprime(n) and n > 2:
            #     return (n, (2, 1, 3, 2))
            case n if is_power_of_2(n):
                return (n, (n + 5, n + 4))
            case n if is_power_of_3(n):
                return (n, (n + 5, n + 7, n + 3))
            case n if n % 2 == 0:
                return (n, (7 * n, 3 * n))
            case n if n % 3 == 0:
                return (n, (3 * n, 7 * n, 5 * n))
            case _:
                return data
    elif isinstance(data, tuple):
        match data:
            # case (n, (m1, m2, m3)):
            #     return (n, (3 * m1, 2 * m2, 5 * m3))
            # case (n, (m1, m2)):
            #     return (n, (5 * m1, 2 * m2))
            case tuple(items):
                return tuple(rewrite_system(item[1]) if isinstance(item, tuple) else rewrite_system(item) for item in items)

def iterate_rewrite(data, max_iterations=2):
    iterations = 0
    current = data
    while iterations < max_iterations:
        rewritten = rewrite_system(current)
        if rewritten == current:
            break
        current = rewritten
        iterations += 1
    return current, iterations

# nested_tuple = RP((3, 5, 7)).measures
nested_tuple = 3
print(f'Axiom: {nested_tuple}\n')

# rewritten, iterations = iterate_rewrite(nested_tuple)
# print(f'Rewritten: {rewritten}')
# print(f'Total Iterations: {iterations}')

p = (3, 5, 7)
rp = RP(p)
S = rp.measures
ut = UT(duration=30, tempus=Meas((1, 1)), prolatio=S, tempo=54, beat='1/4')
print(ut)
utseq = ut.decompose('s')
print(seconds_to_hmsms(utseq.time))
print(utseq.uts)

from klotho.aikous.messaging import Scheduler
scheduler = Scheduler()

uid = scheduler.new_event_with_id('vosim', 0, trigFreq = 66.0, amp = 0.1)
for i, ut in enumerate(utseq):
    fund = 166.5 if i % 2 == 0 else 333.0
    fund = fund * fold_interval(float(ut.tempus), 2, 1)
    ht = HT(1, (n + i * 3 for n in S))
    # atk = min(ut.durations) / 2
    for j, event in enumerate(ut):
        ratio = ht.partials[j] if i % 2 == 0 else 1 / ht.partials[j]
        freq = fund * ratio
        duration = event['duration']
        atk = duration / 2
        scheduler.set_synth(uid         = uid,
                            start       = event['start'],
                            lag         = duration * 0.25,
                            trigFreq    = fund / 2,
                            freq        = freq * 8)
scheduler.send_events()
