"""Parity scenario (refactored): score_control_envs_3layer using the new fluent selector API."""

import numpy as np

from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC, Score, SynthDefInstrument


SEED = 11


def build():
    np.random.seed(SEED)
    inst = SynthDefInstrument.sine()

    S = ((2, (1, 1, 1)), (2, (1, 1)))
    uc = UC(tempus='4/4', prolatio=S, beat='1/4', bpm=90)
    uc.root.set_instrument(inst)
    uc.leaves.set_pfields(freq=220.0)

    uc.root.apply_envelope(
        Envelope([0.05, 0.4, 0.05], times=[0.4, 0.6], curve=[-2, 2]),
        'amp',
        control=True,
    )

    uc.successors(uc._rt.root).apply_envelope(
        Envelope([0.1, 0.6, 0.1], times=[0.5, 0.5]),
        'cutoff',
        scope='per_node',
        control=True,
    )

    uc.leaves.apply_envelope(
        Envelope([0.0, 0.3, 0.0], times=[0.5, 0.5]),
        'vib',
        scope='per_node',
        control=True,
    )

    s = Score()
    s.track('voice')
    s.add(uc, name='uc', track='voice')

    return {"score": s}
