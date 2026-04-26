"""Parity scenario: chord tuples via set_pfields(leaf, freq=(a,b,c)) + per-leaf pan bake envelope."""

import numpy as np

from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument


SEED = 23


def build():
    np.random.seed(SEED)
    inst = SynthDefInstrument.sqr()

    uc = UC(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=60)
    uc.set_instrument(uc._rt.root, inst)

    leaves = list(uc._rt.leaf_nodes)
    uc.set_pfields(leaves[0], freq=(220.0, 277.0, 330.0))
    uc.set_pfields(leaves[1], freq=(247.0, 294.0, 370.0))
    uc.set_pfields(leaves[2], freq=(262.0, 330.0, 392.0))

    uc.set_pfields(uc._rt.root, width=0.3, amp=0.2)

    uc.apply_envelope(
        Envelope([-0.8, 0.8, -0.3], times=[0.5, 0.5]),
        pfields='pan',
        node=uc._rt.root,
    )

    return {"ucs": {"uc": uc}}
