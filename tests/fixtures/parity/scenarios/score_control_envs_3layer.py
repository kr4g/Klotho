"""Parity scenario: three envelope layers (root span, per-phrase per_node, per-leaf per_node) all control=True."""

import numpy as np

from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC, Score, SynthDefInstrument


SEED = 11


def build():
    np.random.seed(SEED)
    inst = SynthDefInstrument.sine()

    S = ((2, (1, 1, 1)), (2, (1, 1)))
    uc = UC(tempus='4/4', prolatio=S, beat='1/4', bpm=90)
    uc.set_instrument(uc._rt.root, inst)
    uc.set_pfields(list(uc._rt.leaf_nodes), freq=220.0)

    uc.apply_envelope(
        Envelope([0.05, 0.4, 0.05], times=[0.4, 0.6], curve=[-2, 2]),
        pfields='amp',
        node=uc._rt.root,
        control=True,
    )

    branches = list(uc._rt.successors(uc._rt.root))
    uc.apply_envelope(
        Envelope([0.1, 0.6, 0.1], times=[0.5, 0.5]),
        pfields='cutoff',
        node=branches,
        scope='per_node',
        control=True,
    )

    uc.apply_envelope(
        Envelope([0.0, 0.3, 0.0], times=[0.5, 0.5]),
        pfields='vib',
        node=list(uc._rt.leaf_nodes),
        scope='per_node',
        control=True,
    )

    s = Score()
    s.track('voice')
    s.add(uc, name='uc', track='voice')

    return {"score": s}
