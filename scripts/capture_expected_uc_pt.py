"""
Capture expected UC/PT structure and events from REMOTE klotho.

To capture baseline from origin/main (use remote code only):
  PYTHONPATH=.worktree-remote python scripts/capture_expected_uc_pt.py 2>/dev/null > tests/expected_uc_pt.json

Requires .worktree-remote checked out to origin/main:
  git worktree add .worktree-remote origin/main

Captures for each UC:
- RT: node_data, successors, descendants, ancestors, parent, subtree_leaves,
      leaf_nodes, at_depth, durations, onsets, depth, span, meas
- PT: items(node), get_pfield(node,k), get_mfield(node,k), get_instrument(node)
      for every node
- Events: full pfields/mfields per event
"""

import json
import sys

sys.path.insert(0, ".")
import numpy as np
from fractions import Fraction

from klotho.chronos import TemporalUnitSequence as UTS, TemporalBlock as BT
from klotho.thetos import CompositionalUnit as UC, ToneInstrument as ToneInst
from klotho.tonos import Scale
from klotho.topos import Pattern


def _jsonable(obj):
    if obj is None:
        return None
    if isinstance(obj, Fraction):
        return str(obj)
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if isinstance(obj, (int, float, str, bool)):
        return obj
    return obj


def _node_tuple(g, node):
    d = g[node]
    return (d.get("proportion"), str(d["metric_duration"]), str(d["metric_onset"]))


def _serialize_instrument(inst):
    if inst is None:
        return None
    try:
        if hasattr(inst, "pfields"):
            d = {str(k): _jsonable(v) for k, v in inst.pfields.items()}
            if hasattr(inst, "name"):
                d["_name"] = inst.name
            if hasattr(inst, "tonejs_class"):
                d["_tonejs_class"] = inst.tonejs_class
            if hasattr(inst, "defName"):
                d["_defName"] = inst.defName
            return d
        if hasattr(inst, "keys"):
            return {str(k): _jsonable(inst[k]) for k in inst.keys()}
    except Exception:
        pass
    return {"_repr": str(inst)[:200]}


def capture_rt_full(rt):
    return {
        "num_nodes": len(list(rt.nodes)),
        "depth": rt.depth,
        "span": rt.span,
        "meas": str(rt.meas),
        "root": rt.root,
        "leaf_nodes": list(rt.leaf_nodes),
        "durations": [str(d) for d in rt.durations],
        "onsets": [str(o) for o in rt.onsets],
        "node_data": {
            str(n): {
                "proportion": rt[n].get("proportion"),
                "metric_duration": str(rt[n]["metric_duration"]),
                "metric_onset": str(rt[n]["metric_onset"]),
            }
            for n in rt.nodes
        },
        "successors": {str(n): list(rt.successors(n)) for n in rt.nodes},
        "descendants": {
            str(n): sorted([list(_node_tuple(rt, d)) for d in rt.descendants(n)])
            for n in rt.nodes
        },
        "ancestors": {
            str(n): list(rt.ancestors(n)) if n != rt.root else []
            for n in rt.nodes
        },
        "parent": {
            str(n): rt.parent(n) for n in rt.nodes if n != rt.root
        },
        "subtree_leaves": {
            str(n): sorted([list(_node_tuple(rt, l)) for l in rt.subtree_leaves(n)])
            for n in rt.nodes
        },
        "at_depth": [
            sorted([list(_node_tuple(rt, n)) for n in rt.at_depth(d)])
            for d in range(rt.depth + 1)
        ],
    }


def capture_pt_full(pt):
    pfields = pt.pfields
    mfields = pt.mfields
    out = {
        "pfields_registry": list(pfields),
        "mfields_registry": list(mfields),
        "node_items": {str(n): _jsonable(pt.items(n)) for n in pt.nodes},
        "node_pfields": {
            str(n): {k: _jsonable(pt.get_pfield(n, k)) for k in pfields}
            for n in pt.nodes
        },
        "node_mfields": {
            str(n): {k: _jsonable(pt.get_mfield(n, k)) for k in mfields}
            for n in pt.nodes
        },
        "node_instruments": {
            str(n): _serialize_instrument(pt.get_instrument(n)) for n in pt.nodes
        },
        "successors": {str(n): list(pt.successors(n)) for n in pt.nodes},
        "descendants": {
            str(n): sorted(pt.descendants(n)) for n in pt.nodes
        },
        "ancestors": {
            str(n): list(pt.ancestors(n)) if n != pt.root else []
            for n in pt.nodes
        },
        "parent": {
            str(n): pt.parent(n) for n in pt.nodes if n != pt.root
        },
        "subtree_leaves": {
            str(n): sorted(pt.subtree_leaves(n)) for n in pt.nodes
        },
        "leaf_nodes": list(pt.leaf_nodes),
        "at_depth": [
            sorted(pt.at_depth(d)) for d in range(pt.depth + 1)
        ],
    }
    return out


def capture_events(uc):
    events = list(uc)
    return [
        {
            "node_id": e.node_id,
            "start": float(e.start),
            "duration": float(e.duration),
            "end": float(e.end),
            "is_rest": e.is_rest,
            "proportion": _jsonable(e.proportion),
            "metric_duration": str(e.metric_duration),
            "pfields": _jsonable(e.pfields),
            "mfields": _jsonable(e.mfields),
        }
        for e in events
    ]


def capture_uc(name, uc):
    _ = uc.events
    return {
        "rt": capture_rt_full(uc._rt),
        "pt": capture_pt_full(uc._pt),
        "events": capture_events(uc),
    }


def _build_chronostasis_before():
    tempus = "10/16"
    beat = "1/16"
    bpm = 140
    n_bars = 2
    S1 = ((3, (1,) * 4), (4, (1,) * 6), (3, (1,) * 4))
    S2 = ((5, (1,) * 5),) * 2

    inst_pat_1 = Pattern(
        [
            ToneInst.HatClosed(),
            [
                ToneInst.HatClosed(),
                [
                    [ToneInst.TomHigh(), ToneInst.TomMid()],
                    [
                        ToneInst.HatOpen(),
                        [ToneInst.Ride(decay=0.2), ToneInst.HatClosed()],
                    ],
                ],
            ],
        ]
    )
    uts1 = UTS()
    uc1 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    uts1.extend([uc1] * n_bars)
    for unit in uts1:
        for leaf in unit.rt.leaf_nodes:
            unit.set_instrument(leaf, next(inst_pat_1))
            unit.set_pfields(leaf, vel=np.random.uniform(0.001, 0.25))

    inst_pat_2 = Pattern(
        [
            [
                [
                    ToneInst.Kick("kick_punchy", punch=16),
                    ToneInst.Kick("kick_pitchy", pitchDecay=0.05, decay=0.9),
                ],
                ToneInst.Snare(),
            ],
            ToneInst.Kick(),
        ]
    )
    uts2 = UTS()
    uc2 = UC(tempus=tempus, prolatio=S2, beat=beat, bpm=bpm)
    uts2.extend([uc2] * n_bars)
    for unit in uts2:
        for leaf in unit.rt.leaf_nodes:
            unit.set_instrument(leaf, next(inst_pat_2))
            unit.set_pfields(leaf, vel=np.random.uniform(0.75, 0.9))

    return BT([uts1, uts2])


def _build_entertain_me_melody_before():
    tempus = "36/16"
    beat = "1/8"
    bpm = 184
    S1 = ((20, ((5, (1,) * 5),) * 4), (15, ((3, (1,) * 3),) * 5))
    scale = Scale.phrygian().root("B3")

    uc_mel = UC(
        tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=ToneInst.Kalimba()
    )
    limbs = uc_mel.rt.at_depth(1)
    uc_mel.set_mfields(limbs[0], idx=0, drct=1, offset=0)
    uc_mel.set_mfields(limbs[1], idx=len(scale), drct=-1, offset=0)
    successors = list(uc_mel.rt.successors(limbs[-1]))
    for k, node in enumerate(successors):
        uc_mel.set_mfields(node, offset=len(successors) - k)

    for b, branch in enumerate(uc_mel.rt.at_depth(2)):
        for k, leaf in enumerate(uc_mel.rt.descendants(branch)):
            offset = uc_mel.get_parameter(leaf, "offset")
            idx = uc_mel.get_parameter(leaf, "idx")
            drct = uc_mel.get_parameter(leaf, "drct")
            scl_idx = offset + idx + drct * k
            uc_mel.set_pfields(leaf, freq=scale[scl_idx].freq)

    return uc_mel


def _build_entertain_me_drums_before():
    tempus = "36/16"
    beat = "1/8"
    bpm = 184
    S1 = ((20, ((5, (1,) * 5),) * 4), (15, ((3, (1,) * 3),) * 5))

    uc_ds = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    limbs = uc_ds.rt.at_depth(1)
    ds_pat = Pattern([[ToneInst.Kick(), ToneInst.Snare()], ToneInst.HatClosed()])

    for k, node in enumerate(uc_ds.rt.subtree_leaves(limbs[0])):
        uc_ds.set_instrument(node, next(ds_pat))
    for k, node in enumerate(uc_ds.rt.subtree_leaves(limbs[-1])):
        uc_ds.set_instrument(
            node,
            ToneInst.HatOpen(vel=0.1) if k % 2 == 0 else ToneInst.HatClosed(),
        )

    return uc_ds


def _build_polyriddim_bass_before():
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
        (
            1,
            (
                (6, ((2, (1,) * 3), (2, (1,) * 3), (2, (1,) * 3))),
                (8, (5, (6, (1,) * 11))),
            ),
        ),
    )
    tempus = "28/16"
    beat = "1/16"
    bpm = 122.5
    n_bars = 2
    scale = Scale.locrian().root("Eb2")
    scl_pat = Pattern([[0, -1, [0, -3]], [1, [3, 4]]])

    uts3 = UTS()
    uc3 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=ToneInst.Bassy())
    uts3.extend([uc3] * n_bars)
    for unit in uts3:
        for k, node in enumerate(unit.rt.leaf_nodes):
            if np.random.uniform() < 0.67:
                unit.make_rest(node)
                continue
            unit.set_pfields(
                node,
                freq=scale[next(scl_pat)].freq,
                vel=np.random.uniform(0.1, 0.5),
            )
    return uts3


def main():
    out = {"uc": {}}

    np.random.seed(42)
    block = _build_chronostasis_before()
    rows = list(block)
    for vi, row in enumerate(rows):
        for ui, unit in enumerate(row):
            out["uc"][f"chronostasis_v{vi}_u{ui}"] = capture_uc(
                f"chronostasis_v{vi}_u{ui}", unit
            )

    uc_mel = _build_entertain_me_melody_before()
    out["uc"]["entertain_me_melody"] = capture_uc("entertain_me_melody", uc_mel)

    uc_ds = _build_entertain_me_drums_before()
    out["uc"]["entertain_me_drums"] = capture_uc("entertain_me_drums", uc_ds)

    np.random.seed(42)
    uts3 = _build_polyriddim_bass_before()
    for ui, unit in enumerate(uts3):
        out["uc"][f"polyriddim_u{ui}"] = capture_uc(f"polyriddim_u{ui}", unit)

    uc = UC(tempus="4/4", prolatio=(1, 1, 1, 1), beat="1/4", bpm=120, inst=ToneInst.Kalimba())
    uc.set_pfields(0, freq=440)
    out["uc"]["set_pfields_root"] = capture_uc("set_pfields_root", uc)

    uc = UC(tempus="4/4", prolatio=(1, 1, 1, 1), beat="1/4", bpm=120, inst=ToneInst.Kalimba())
    freqs = [262, 330, 392, 523]
    for i, leaf in enumerate(uc.rt.leaf_nodes):
        uc.set_pfields(leaf, freq=freqs[i])
    out["uc"]["set_pfields_per_leaf"] = capture_uc("set_pfields_per_leaf", uc)

    uc = UC(
        tempus="4/4",
        prolatio=((3, (1,) * 3), (2, (1,) * 2)),
        beat="1/4",
        bpm=120,
        inst=ToneInst.Kalimba(),
    )
    limbs = uc.rt.at_depth(1)
    uc.set_mfields(limbs[0], idx=0, drct=1)
    uc.set_mfields(limbs[1], idx=5, drct=-1)
    out["uc"]["set_mfields_inheritance"] = capture_uc(
        "set_mfields_inheritance", uc
    )

    json.dump(out, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
