"""Parity scenario (refactored): polyriddim using the new fluent selector API."""

import numpy as np

from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument


SEED = 3


def build():
    np.random.seed(SEED)
    inst_base = SynthDefInstrument.tri()
    inst_accent = SynthDefInstrument.saw()

    S = ((2, ((1, (1, 1, 1)), 1, 1)), (1, (1, 1, 1)))
    uc = UC(tempus='4/4', prolatio=S, beat='1/8', bpm=100)
    uc.root.set_instrument(inst_base)

    uc.sparsify(0.33)

    for branch in uc.at_depth(2):
        children = uc.successors(branch)
        if children:
            children[-1].set_instrument(inst_accent)
        leaves = uc.leaves_of(branch)
        if leaves:
            leaves.set_pfields(vel=lambda: float(np.random.uniform(0.2, 0.7)))

    return {"ucs": {"uc": uc}}
