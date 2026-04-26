"""Parity scenario (refactored): chronostasis using the new fluent selector API.

Must produce byte-identical serialize output vs the verbose chronostasis.py
golden-master fixture.
"""

import numpy as np

from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument
from klotho.topos.collections.sequences import Pattern


SEED = 42


def build():
    np.random.seed(SEED)
    inst = SynthDefInstrument.tri()

    S1 = ((3, (1, 1, 1, 1)), (4, (1, 1, 1)), (3, (1, 1, 1, 1)))
    uc1 = UC(tempus='10/16', prolatio=S1, beat='1/16', bpm=140)
    uc1.leaves.set_instrument(inst)
    uc1.leaves.set_pfields(
        freq=Pattern([220.0, 440.0, 660.0]),
        vel=lambda c: float(np.random.uniform(0.1, 0.5)),
    )

    S2 = ((5, (1, 1, 1)),) * 2
    uc2 = UC(tempus='10/16', prolatio=S2, beat='1/16', bpm=140)
    uc2.leaves.set_instrument(inst)
    uc2.leaves.set_pfields(
        freq=Pattern([110.0, 220.0]),
        vel=lambda c: float(np.random.uniform(0.6, 0.9)),
    )

    return {"ucs": {"uc1": uc1, "uc2": uc2}}
