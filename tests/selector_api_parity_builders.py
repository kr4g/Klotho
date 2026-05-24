"""Reusable builders for selector API parity tests (legacy vs fluent).

Each pair builds the same musical structure two ways so ``convert_to_sc_events``
can be compared byte-for-byte after canonicalization.
"""

from __future__ import annotations

import numpy as np

from klotho.chronos import TemporalBlock as BT
from klotho.chronos import TemporalUnitSequence as UTS
from klotho.thetos import CompositionalUnit as UC, ToneInstrument as JsInst
from klotho.tonos import Scale
from klotho.topos.collections.sequences import Pattern


def build_rt_preview_chronostasis_legacy():
    np.random.seed(0)
    tempus, beat, bpm, n_bars = "10/16", "1/16", 140, 4
    S1 = ((3, (1,) * 4), (4, (1,) * 6), (3, (1,) * 4))
    S2 = ((5, (1,) * 5),) * 2
    inst_pat_1 = Pattern(
        [
            JsInst.HatClosed(),
            [
                JsInst.HatClosed(),
                [
                    [JsInst.TomHigh(), JsInst.TomMid()],
                    [
                        JsInst.HatOpen(),
                        [JsInst.Ride(decay=0.2), JsInst.HatClosed()],
                    ],
                ],
            ],
        ]
    )
    uc1 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    uts1 = uc1.repeat(n_bars)
    for unit in uts1:
        unit.set_instrument(unit.leaves, inst_pat_1)
        unit.set_pfields(unit.leaves, vel=lambda: np.random.uniform(0.001, 0.25))
    inst_pat_2 = Pattern(
        [
            [
                [
                    JsInst.Kick("kick_punchy", punch=16),
                    JsInst.Kick("kick_pitchy", pitchDecay=0.05, decay=0.9),
                ],
                JsInst.Snare(),
            ],
            JsInst.Kick(),
        ]
    )
    uc2 = UC(tempus=tempus, prolatio=S2, beat=beat, bpm=bpm)
    uts2 = uc2.repeat(n_bars)
    for unit in uts2:
        unit.set_instrument(unit.leaves, inst_pat_2)
        unit.set_pfields(unit.leaves, vel=lambda: np.random.uniform(0.75, 0.9))
    return BT([uts1, uts2])


def build_rt_preview_chronostasis_fluent():
    np.random.seed(0)
    tempus, beat, bpm, n_bars = "10/16", "1/16", 140, 4
    S1 = ((3, (1,) * 4), (4, (1,) * 6), (3, (1,) * 4))
    S2 = ((5, (1,) * 5),) * 2
    inst_pat_1 = Pattern(
        [
            JsInst.HatClosed(),
            [
                JsInst.HatClosed(),
                [
                    [JsInst.TomHigh(), JsInst.TomMid()],
                    [
                        JsInst.HatOpen(),
                        [JsInst.Ride(decay=0.2), JsInst.HatClosed()],
                    ],
                ],
            ],
        ]
    )
    uc1 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    uts1 = uc1.repeat(n_bars)
    for unit in uts1:
        unit.leaves.set_instrument(inst_pat_1)
        unit.leaves.set_pfields(vel=lambda: np.random.uniform(0.001, 0.25))
    inst_pat_2 = Pattern(
        [
            [
                [
                    JsInst.Kick("kick_punchy", punch=16),
                    JsInst.Kick("kick_pitchy", pitchDecay=0.05, decay=0.9),
                ],
                JsInst.Snare(),
            ],
            JsInst.Kick(),
        ]
    )
    uc2 = UC(tempus=tempus, prolatio=S2, beat=beat, bpm=bpm)
    uts2 = uc2.repeat(n_bars)
    for unit in uts2:
        unit.leaves.set_instrument(inst_pat_2)
        unit.leaves.set_pfields(vel=lambda: np.random.uniform(0.75, 0.9))
    return BT([uts1, uts2])


def build_rt_preview_entertain_legacy():
    np.random.seed(1)
    tempus, beat, bpm, n_bars = "36/16", "1/8", 184, 2
    scale = Scale.phrygian().root("B3")
    S1 = ((20, ((5, (1,) * 5),) * 4), (15, ((3, (1,) * 3),) * 5))
    uc_mel = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=JsInst.Kalimba())
    limbs = uc_mel.at_depth(1)
    L0, L1 = limbs[0].id, limbs[-1].id
    uc_mel.set_mfields(limbs[0], idx=0, direction=1, offset=0)
    uc_mel.set_mfields(limbs[1], idx=len(scale), direction=-1, offset=0)
    uc_mel.set_mfields(uc_mel.successors(L1), offset=lambda c: c.total - c.index)
    for branch in uc_mel.at_depth(2):
        uc_mel.set_pfields(
            uc_mel.leaves_of(branch),
            freq=lambda c: scale[
                c.mfields["offset"] + c.mfields["idx"] + c.mfields["direction"] * c.index
            ].freq,
        )
    uc_ds = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    uc_ds.set_instrument(uc_ds.leaves_of(L0), Pattern([[JsInst.Kick(), JsInst.Snare()], JsInst.HatClosed()]))
    uc_ds.set_instrument(
        uc_ds.leaves_of(L1),
        lambda c: JsInst.HatOpen(vel=0.1) if c.index % 2 == 0 else JsInst.HatClosed(),
    )
    uc_bs = UC(
        tempus=tempus,
        prolatio=S1,
        beat=beat,
        bpm=bpm,
        inst=JsInst.Bassy(freq=scale[-len(scale) * 2].freq, vel=0.2),
    )
    bs_pat = Pattern([0, 0, [1, [3, [4, -3]]]])
    uc_bs.make_rest(limbs[-1].id)
    seq_bs = uc_bs.repeat(n_bars)
    for unit in seq_bs:
        unit.set_pfields(unit.leaves, freq=lambda: scale[next(bs_pat) - len(scale) * 2].freq)
    return BT([uc_mel.repeat(n_bars), uc_ds.repeat(n_bars), seq_bs])


def build_rt_preview_entertain_fluent():
    np.random.seed(1)
    tempus, beat, bpm, n_bars = "36/16", "1/8", 184, 2
    scale = Scale.phrygian().root("B3")
    S1 = ((20, ((5, (1,) * 5),) * 4), (15, ((3, (1,) * 3),) * 5))
    uc_mel = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=JsInst.Kalimba())
    limbs = uc_mel.at_depth(1)
    L0, L1 = limbs[0].id, limbs[-1].id
    limbs[0].set_mfields(idx=0, direction=1, offset=0)
    limbs[1].set_mfields(idx=len(scale), direction=-1, offset=0)
    uc_mel.successors(L1).set_mfields(offset=lambda c: c.total - c.index)
    for branch in uc_mel.at_depth(2):
        uc_mel.leaves_of(branch).set_pfields(
            freq=lambda c: scale[
                c.mfields["offset"] + c.mfields["idx"] + c.mfields["direction"] * c.index
            ].freq,
        )
    uc_ds = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    uc_ds.leaves_of(L0).set_instrument(Pattern([[JsInst.Kick(), JsInst.Snare()], JsInst.HatClosed()]))
    uc_ds.leaves_of(L1).set_instrument(
        lambda c: JsInst.HatOpen(vel=0.1) if c.index % 2 == 0 else JsInst.HatClosed(),
    )
    uc_bs = UC(
        tempus=tempus,
        prolatio=S1,
        beat=beat,
        bpm=bpm,
        inst=JsInst.Bassy(freq=scale[-len(scale) * 2].freq, vel=0.2),
    )
    bs_pat = Pattern([0, 0, [1, [3, [4, -3]]]])
    uc_bs.make_rest(limbs[-1].id)
    seq_bs = uc_bs.repeat(n_bars)
    for unit in seq_bs:
        unit.leaves.set_pfields(freq=lambda: scale[next(bs_pat) - len(scale) * 2].freq)
    return BT([uc_mel.repeat(n_bars), uc_ds.repeat(n_bars), seq_bs])


def build_rt_preview_poly_legacy():
    np.random.seed(2)
    S1 = (
        (1, ((6, (1,) * 7), (8, (1,) * 11))),
        (
            1,
            (
                (6, ((3, (1,) * 4), 1, (2, (1,) * 3))),
                (8, ((3, (1,) * 4), (3, (1,) * 4), (5, (1,) * 5))),
            ),
        ),
        (
            1,
            (
                (6, (2, (3, (1,) * 4), (2, (1,) * 4))),
                (8, ((2, (1,) * 3), (2, (1,) * 4), (2, (1,) * 5), (2, (1,) * 5))),
            ),
        ),
        (1, ((6, ((2, (1,) * 3), (2, (1,) * 3), (2, (1,) * 3))), (8, (5, (6, (1,) * 11))))),
    )
    S2 = ((7, ((3, (1,) * 3), (4, (1,) * 4))),) * 4
    tempus, beat, bpm, n_bars = "28/16", "1/16", 122.5, 2
    inst1_pat = Pattern(
        [
            [
                JsInst.Kick(),
                [
                    [
                        JsInst.Kick("kick_punch", punch=9, click=0.6),
                        JsInst.Snare("snare_body", body=0.8),
                    ],
                    JsInst.TomMid(),
                ],
            ],
            [
                JsInst.Kick("kick_click", click=0.8),
                [[JsInst.Snare(), JsInst.TomHigh(punch=8, decay=0.9)], JsInst.TomLow()],
            ],
        ]
    )
    uc1 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    uts1 = uc1.repeat(n_bars)
    for unit in uts1:
        unit.sparsify(0.33)
        unit.set_instrument(unit.leaves, inst1_pat)
        unit.set_pfields(unit.leaves, vel=lambda: np.random.uniform(0.25, 0.85))
    uc2 = UC(tempus=tempus, prolatio=S2, beat=beat, bpm=bpm)
    uts2 = uc2.repeat(n_bars)
    for unit in uts2:
        for branch in unit.at_depth(2):
            unit.set_instrument(branch, JsInst.HatClosed())
            unit.set_instrument(unit.successors(branch)[-1], JsInst.HatOpen())
            unit.set_pfields(unit.leaves_of(branch), vel=lambda: np.random.uniform(0.05, 0.25))
    scale = Scale.locrian().root("Eb2")
    scl_pat = Pattern([[0, -1, [0, -3]], [1, [3, 4]]])
    uc3 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=JsInst.Bassy())
    uts3 = uc3.repeat(n_bars)
    for unit in uts3:
        unit.sparsify(0.67)
        unit.set_pfields(
            unit.leaves,
            freq=lambda: scale[next(scl_pat)].freq,
            vel=lambda: np.random.uniform(0.1, 0.5),
        )
    return BT([uts1, uts2, uts3])


def build_rt_preview_poly_fluent():
    np.random.seed(2)
    S1 = (
        (1, ((6, (1,) * 7), (8, (1,) * 11))),
        (
            1,
            (
                (6, ((3, (1,) * 4), 1, (2, (1,) * 3))),
                (8, ((3, (1,) * 4), (3, (1,) * 4), (5, (1,) * 5))),
            ),
        ),
        (
            1,
            (
                (6, (2, (3, (1,) * 4), (2, (1,) * 4))),
                (8, ((2, (1,) * 3), (2, (1,) * 4), (2, (1,) * 5), (2, (1,) * 5))),
            ),
        ),
        (1, ((6, ((2, (1,) * 3), (2, (1,) * 3), (2, (1,) * 3))), (8, (5, (6, (1,) * 11))))),
    )
    S2 = ((7, ((3, (1,) * 3), (4, (1,) * 4))),) * 4
    tempus, beat, bpm, n_bars = "28/16", "1/16", 122.5, 2
    inst1_pat = Pattern(
        [
            [
                JsInst.Kick(),
                [
                    [
                        JsInst.Kick("kick_punch", punch=9, click=0.6),
                        JsInst.Snare("snare_body", body=0.8),
                    ],
                    JsInst.TomMid(),
                ],
            ],
            [
                JsInst.Kick("kick_click", click=0.8),
                [[JsInst.Snare(), JsInst.TomHigh(punch=8, decay=0.9)], JsInst.TomLow()],
            ],
        ]
    )
    uc1 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    uts1 = uc1.repeat(n_bars)
    for unit in uts1:
        unit.sparsify(0.33)
        unit.leaves.set_instrument(inst1_pat)
        unit.leaves.set_pfields(vel=lambda: np.random.uniform(0.25, 0.85))
    uc2 = UC(tempus=tempus, prolatio=S2, beat=beat, bpm=bpm)
    uts2 = uc2.repeat(n_bars)
    for unit in uts2:
        for branch in unit.at_depth(2):
            branch.set_instrument(JsInst.HatClosed())
            unit.successors(branch)[-1].set_instrument(JsInst.HatOpen())
            unit.leaves_of(branch).set_pfields(vel=lambda: np.random.uniform(0.05, 0.25))
    scale = Scale.locrian().root("Eb2")
    scl_pat = Pattern([[0, -1, [0, -3]], [1, [3, 4]]])
    uc3 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=JsInst.Bassy())
    uts3 = uc3.repeat(n_bars)
    for unit in uts3:
        unit.sparsify(0.67)
        unit.leaves.set_pfields(
            freq=lambda: scale[next(scl_pat)].freq,
            vel=lambda: np.random.uniform(0.1, 0.5),
        )
    return BT([uts1, uts2, uts3])


def build_uc_uts_helper_legacy(
    tempus,
    prolatio,
    freqs,
    amp=0.25,
    rests=None,
    slur_spans=None,
    strum_values=None,
):
    uc = UC(
        tempus=tempus,
        prolatio=prolatio,
        bpm=108,
        pfields={"freq": 440.0, "amp": amp},
        mfields={"group": "default"},
    )
    leaves = tuple(uc._rt.leaf_nodes)
    for i, leaf in enumerate(leaves):
        uc.set_pfields(leaf, freq=freqs[i % len(freqs)], amp=amp)
    if strum_values is not None:
        for i, leaf in enumerate(leaves):
            uc.set_mfields(leaf, strum=strum_values[i % len(strum_values)])
    if rests:
        for ridx in rests:
            if 0 <= ridx < len(leaves):
                uc.make_rest(leaves[ridx])
    if slur_spans:
        for start_idx, span_len in slur_spans:
            stop_idx = start_idx + span_len
            if span_len >= 2 and 0 <= start_idx < len(leaves) and stop_idx <= len(leaves):
                nodes = leaves[start_idx:stop_idx]
                uc.apply_slur(node=nodes)
    return uc


def build_uc_uts_helper_fluent(
    tempus,
    prolatio,
    freqs,
    amp=0.25,
    rests=None,
    slur_spans=None,
    strum_values=None,
):
    uc = UC(
        tempus=tempus,
        prolatio=prolatio,
        bpm=108,
        pfields={"freq": 440.0, "amp": amp},
        mfields={"group": "default"},
    )
    leaves = tuple(uc._rt.leaf_nodes)
    for i, leaf in enumerate(leaves):
        uc.select(leaf).set_pfields(freq=freqs[i % len(freqs)], amp=amp)
    if strum_values is not None:
        for i, leaf in enumerate(leaves):
            uc.select(leaf).set_mfields(strum=strum_values[i % len(strum_values)])
    if rests:
        for ridx in rests:
            if 0 <= ridx < len(leaves):
                uc.make_rest(leaves[ridx])
    if slur_spans:
        for start_idx, span_len in slur_spans:
            stop_idx = start_idx + span_len
            if span_len >= 2 and 0 <= start_idx < len(leaves) and stop_idx <= len(leaves):
                nodes = leaves[start_idx:stop_idx]
                uc.select(*nodes).apply_slur()
    return uc
