"""Parity scenario (refactored): score_demo_multi using the new fluent selector API."""

import numpy as np

from klotho.thetos import (
    CompositionalUnit as UC,
    Score,
    SynthDefInstrument,
    SynthDefFX,
)
from klotho.topos.collections.sequences import Pattern


SEED = 7


def build():
    np.random.seed(SEED)
    tri = SynthDefInstrument.tri()
    saw = SynthDefInstrument.saw()

    mel = UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120, inst=tri)
    mel.leaves.set_pfields(freq=Pattern([261.63, 293.66, 329.63, 349.23]))
    mel.root.set_pfields(amp=0.3)

    bass = UC(tempus='4/4', prolatio=(1, 1), bpm=120, inst=saw)
    bass.leaves.set_pfields(freq=Pattern([65.4, 98.0]))
    bass.root.set_pfields(amp=0.5)

    reverb = SynthDefFX('kl_reverb', mix=0.3, room=0.7)

    s = Score()
    s.track('melody', inserts=[reverb])
    s.track('bass')
    s.add(mel, name='mel', track='melody')
    s.add(bass, name='bass', track='bass')

    return {"score": s}
