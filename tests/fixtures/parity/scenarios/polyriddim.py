"""Parity scenario: sparsify(float), nested at_depth loop, successors(branch)[-1].

Exercises float-probability sparsify (deterministic under np.random.seed) plus
iteration at a deeper level of the tree with successors-based node targeting.
"""

import numpy as np

from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument


SEED = 3


def build():
    np.random.seed(SEED)
    inst_base = SynthDefInstrument.tri()
    inst_accent = SynthDefInstrument.saw()

    S = ((2, ((1, (1, 1, 1)), 1, 1)), (1, (1, 1, 1)))
    uc = UC(tempus='4/4', prolatio=S, beat='1/8', bpm=100)
    uc.set_instrument(uc._rt.root, inst_base)

    uc.sparsify(0.33)

    for branch in uc._rt.at_depth(2):
        children = list(uc._rt.successors(branch))
        if children:
            uc.set_instrument(children[-1], inst_accent)
        leaves = list(uc._rt.subtree_leaves(branch))
        if leaves:
            uc.set_pfields(leaves, vel=lambda: float(np.random.uniform(0.2, 0.7)))

    return {"ucs": {"uc": uc}}
