"""Parity scenario: at_depth(1), successors, subtree_leaves, set_mfields with
context-reading callable freq.

Exercises nested mfield/pfield application where the freq callable reads
upstream mfields (idx, direction, offset) from its DistributionContext.
"""

import numpy as np

from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument


SEED = 17


def build():
    np.random.seed(SEED)
    inst = SynthDefInstrument.sine()

    S = ((3, (1, 1, 1)), (2, (1, 1)))
    uc = UC(tempus='5/8', prolatio=S, beat='1/8', bpm=120)
    uc.set_instrument(uc._rt.root, inst)

    limbs = uc._rt.at_depth(1)
    uc.set_mfields(limbs[0], idx=0, direction=1, offset=0)
    uc.set_mfields(limbs[1], idx=10, direction=-1, offset=0)

    def freq_from_ctx(c):
        m = c.mfields
        base = 220.0
        return base + float(m.get('offset') or 0) + float(m.get('direction') or 1) * c.index * 20.0

    for branch in uc._rt.at_depth(1):
        leaves = list(uc._rt.subtree_leaves(branch))
        uc.set_pfields(leaves, freq=freq_from_ctx)

    last_branch = limbs[-1]
    children = list(uc._rt.successors(last_branch))
    uc.set_mfields(children, offset=lambda c: c.total - c.index)

    return {"ucs": {"uc": uc}}
