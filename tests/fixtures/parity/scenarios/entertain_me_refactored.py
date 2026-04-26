"""Parity scenario (refactored): entertain_me using the new fluent selector API."""

import numpy as np

from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument


SEED = 17


def build():
    np.random.seed(SEED)
    inst = SynthDefInstrument.sine()

    S = ((3, (1, 1, 1)), (2, (1, 1)))
    uc = UC(tempus='5/8', prolatio=S, beat='1/8', bpm=120)
    uc.root.set_instrument(inst)

    limbs = uc.at_depth(1)
    limbs[0].set_mfields(idx=0, direction=1, offset=0)
    limbs[1].set_mfields(idx=10, direction=-1, offset=0)

    def freq_from_ctx(c):
        m = c.mfields
        base = 220.0
        return base + float(m.get('offset') or 0) + float(m.get('direction') or 1) * c.index * 20.0

    for branch in uc.at_depth(1):
        uc.leaves_of(branch).set_pfields(freq=freq_from_ctx)

    last_branch = limbs.last
    uc.successors(last_branch).set_mfields(offset=lambda c: c.total - c.index)

    return {"ucs": {"uc": uc}}
