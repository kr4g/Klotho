"""Parity scenario: make_rest(leaves[i]), apply_slur(node=leaves[start:stop]), strum mfield Pattern."""

import numpy as np

from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument
from klotho.topos.collections.sequences import Pattern


SEED = 29


def build():
    np.random.seed(SEED)
    inst = SynthDefInstrument.tri()

    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1, 1, 1), beat='1/4', bpm=110)
    uc.set_instrument(uc._rt.root, inst)

    freqs = [220.0, 247.0, 262.0, 294.0, 330.0, 370.0]
    leaves = list(uc._rt.leaf_nodes)
    for i, leaf in enumerate(leaves):
        uc.set_pfields(leaf, freq=freqs[i], amp=0.3)

    uc.set_mfields(leaves, strum=Pattern([0.0, 0.3, -0.3, 0.5]))

    for ridx in [2, 5]:
        uc.make_rest(leaves[ridx])

    uc.apply_slur(node=leaves[0:2])
    uc.apply_slur(node=leaves[3:5])

    return {"ucs": {"uc": uc}}
