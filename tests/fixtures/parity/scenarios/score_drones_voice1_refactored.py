"""Parity scenario (refactored): score_drones_voice1 using the new fluent selector API."""

import numpy as np

from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument


SEED = 23


def build():
    np.random.seed(SEED)
    inst = SynthDefInstrument.sqr()

    uc = UC(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=60)
    uc.root.set_instrument(inst)

    leaves = uc.leaves
    leaves[0].set_pfields(freq=(220.0, 277.0, 330.0))
    leaves[1].set_pfields(freq=(247.0, 294.0, 370.0))
    leaves[2].set_pfields(freq=(262.0, 330.0, 392.0))

    uc.root.set_pfields(width=0.3, amp=0.2)

    uc.root.apply_envelope(
        Envelope([-0.8, 0.8, -0.3], times=[0.5, 0.5]),
        'pan',
    )

    return {"ucs": {"uc": uc}}
