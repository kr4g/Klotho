"""Parity scenario (refactored): build_uc_helper using the new fluent selector API."""

import numpy as np

from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument
from klotho.topos.collections.sequences import Pattern


SEED = 29


def build():
    np.random.seed(SEED)
    inst = SynthDefInstrument.tri()

    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1, 1, 1), beat='1/4', bpm=110)
    uc.root.set_instrument(inst)

    freqs = [220.0, 247.0, 262.0, 294.0, 330.0, 370.0]
    leaves = uc.leaves
    for i in range(len(leaves)):
        leaves[i].set_pfields(freq=freqs[i], amp=0.3)

    leaves.set_mfields(strum=Pattern([0.0, 0.3, -0.3, 0.5]))

    leaves[[2, 5]].make_rest()

    leaves[0:2].apply_slur()
    leaves[3:5].apply_slur()

    return {"ucs": {"uc": uc}}
