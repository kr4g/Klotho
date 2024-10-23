from klotho.chronos.rhythm_pairs import RhythmPair as RP
from klotho.chronos.rhythm_trees import RhythmTree as RT
from klotho.chronos.temporal_units import TemporalUnit as UT, TemporalUnitSequence as UTSeq
from klotho.tonos.combination_product_sets.nkany import *

from klotho.topos.sequences import Pattern
import numpy as np

rp = RP((3,5,7,11))

def add_tuples(tup: tuple[int]) -> tuple[int]:
    result = ()
    def _add_tuple(elem: int) -> tuple[int]:
        if elem > 2 and np.random.uniform() > 0.5:
            return (elem, (1,) * np.random.randint(2,7))
        else:
            return elem
        
    for elem in tup:
        result += _add_tuple(elem),
    
    return result

subdivs = rp.beats
# subdivs = add_tuples(rp.beats)
rt = RT(duration=16, meas='4/4', subdivisions=subdivs)
ut = UT.from_tree(rt, 66, '1/8')
print(ut.time)
print('-'*20)

ratios = Pattern(Hexany().ratios)

from klotho.aikous.messaging import Scheduler
sch = Scheduler()

synths = {
    'kicks': ['kick','kick2','softKick','ghostKick'],
    'snares': ['snare','rim','rim2'],
    'percs': ['perc','clap1'],
    'jingles': ['jingle','jingle2'],
    'pings': ['ping','reverseKey'],
    'lasers': ['laser','laser2','laser3'],
    # 'metal': ['metal1','metal2','metal3'],
    'vocals': ['vocal1','vocal2'],
    'buzzes': ['buzz1','buzz2'],
    'other': ['fizz','chirps','fsk1','fsk2']
}

rand_synths = lambda key: np.random.choice(synths[key])

pat = Pattern([[rand_synths(np.random.choice(list(synths.keys()))) for _ in range(np.random.randint(1,6))] for _ in range(3)])
# print(pat)

for event in ut:
    synth = next(pat)
    freq_ratio = next(ratios)
    if np.random.uniform(1.0) > 0.33:
        freq_ratio = 1.0 / freq_ratio
    if synth == 'fizz':
        fund = 333.0
        equave = (np.random.randint(0,2))
    else:
        fund = 166.5
        equave = (np.random.randint(0,4))
    sch.new_event(
        synth_name = synth,
        start      = event['start'],
        duration   = event['duration'],
        freq       = (freq_ratio * fund) ** equave,
        ratio      = freq_ratio
)

sch.run()