from klotho.chronos import beat_duration, seconds_to_hmsms


rhy = [
    1/4,
    1/20,
    1/20,
    1/20,
    1/20,
    1/8,
    1/8,
    1/6,
    1/6,
]

for r in rhy:
    print(seconds_to_hmsms(beat_duration(r, bpm=60, beat_ratio='1/4')))
    
from klotho.chronos.temporal_units import TemporalUnit as UT

print('-'*60)

beat = '1/4'
bpm = 60
rhy = [
    UT(tempus='1/4', prolatio='d', beat=beat, tempo=bpm),
    UT(tempus='4/20', prolatio='p', beat=beat, tempo=bpm),
    UT(tempus='1/4', prolatio=(1,1), beat=beat, tempo=bpm),
    UT(tempus='2/6', prolatio=(1,1), beat=beat, tempo=bpm),
]

for ut in rhy:
    for d in ut.durations:
        print(seconds_to_hmsms(d))
