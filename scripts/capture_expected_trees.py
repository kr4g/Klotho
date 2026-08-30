"""
Capture expected tree structure from REMOTE klotho.

Run from a worktree checked out to origin/main:
  git worktree add .worktree-remote origin/main
  cd .worktree-remote
  PYTHONPATH=. python /path/to/scripts/capture_expected_trees.py > tests/expected_trees.json

Do NOT run in main workspace - must use remote code only.

REGENERATING COSTS THE ORACLE. The file this writes is what every test that
reads it compares against. Capture it from remote code only: a baseline taken
from the working tree pins the code to itself, and the tests then pass for any
behaviour, including the behaviour they were written to catch.

So, when you rerun this: review the resulting diff line by line with the
intended change in hand -- every altered line must be one you can explain --
and commit the regenerated baseline ALONE, never in the same commit as the
source change it pins, so the diff stays readable in isolation.
"""

import json
import sys

sys.path.insert(0, ".")
from klotho import RhythmTree as RT
from klotho.chronos import TemporalUnit as UT
from klotho.thetos import CompositionalUnit as UC
from klotho.topos.graphs import Group




def _group_to_json(g):
    if isinstance(g, Group):
        return {"D": g.D, "S": [_group_to_json(x) for x in g.S]}
    return g


def _node_tuple(g, node):
    d = g[node]
    return (d.get("proportion"), str(d["metric_duration"]), str(d["metric_onset"]))


def capture_rt_structure(rt):
    def rec(node):
        d = rt[node]
        p = d.get("proportion")
        md = str(d["metric_duration"])
        mo = str(d["metric_onset"])
        children = list(rt.successors(node))
        return [p, md, mo, [rec(c) for c in children]]

    return {
        "num_nodes": len(list(rt.nodes)),
        "depth": rt.depth,
        "span": rt.span,
        "meas": str(rt.meas),
        "leaf_nodes": list(rt.leaf_nodes),
        "durations": [str(d) for d in rt.durations],
        "onsets": [str(o) for o in rt.onsets],
        "at_depth": [
            sorted([list(_node_tuple(rt, n)) for n in rt.at_depth(d)])
            for d in range(rt.depth + 1)
        ],
        "structure": rec(rt.root),
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
        "subtree_leaves": {
            str(n): sorted([list(_node_tuple(rt, l)) for l in rt.subtree_leaves(n)])
            for n in rt.nodes
        },
        "group": _group_to_json(rt.group),
    }


_COMPLEX_SUBDIV = ((3, (1, (2, (-1, 1, 1)))), (5, (1, -2, (1, (1, 1)), 1)), (3, (-1, 1, 1)), (5, (2, 1)))
_PULSE_ACCEL = ((1, (10, 9, 8, 7, 6, 5, 4, 3, 2, 1)), (1, (10, 9, 8, 7, 6, 5, 4, 3, 2, 1)), (1, (10, 9, 8, 7, 6, 5, 4, 3, 2, 1)))
_PULSE_DECEL = ((1, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)), (1, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)), (1, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)))
_ACCEL_OUTER = ((7, (1, 1, 1, 1, 1)), (6, (1, 1, 1, 1, 1)), (5, (1, 1, 1, 1, 1)), (4, (1, 1, 1, 1, 1)), (3, (1, 1, 1, 1, 1)), (2, (1, 1, 1, 1, 1)), (1, (1, 1, 1, 1, 1)))
_DECEL_OUTER = ((1, (1, 1, 1, 1, 1)), (2, (1, 1, 1, 1, 1)), (3, (1, 1, 1, 1, 1)), (4, (1, 1, 1, 1, 1)), (5, (1, 1, 1, 1, 1)), (6, (1, 1, 1, 1, 1)), (7, (1, 1, 1, 1, 1)))
_DESC_ASC = ((7, (1, 2, 3, 4, 5, 6, 7)), (6, (1, 2, 3, 4, 5, 6, 7)), (5, (1, 2, 3, 4, 5, 6, 7)), (4, (1, 2, 3, 4, 5, 6, 7)), (3, (1, 2, 3, 4, 5, 6, 7)), (2, (1, 2, 3, 4, 5, 6, 7)), (1, (1, 2, 3, 4, 5, 6, 7)))
_ASC_DESC = ((1, (7, 6, 5, 4, 3, 2, 1)), (2, (7, 6, 5, 4, 3, 2, 1)), (3, (7, 6, 5, 4, 3, 2, 1)), (4, (7, 6, 5, 4, 3, 2, 1)), (5, (7, 6, 5, 4, 3, 2, 1)), (6, (7, 6, 5, 4, 3, 2, 1)), (7, (7, 6, 5, 4, 3, 2, 1)))
_DESC_CYCLE = ((6, (1, 2, 3, 1, 2, 3)), (5, (1, 2, 3, 1, 2, 3)), (4, (1, 2, 3, 1, 2, 3)), (3, (1, 2, 3, 1, 2, 3)), (2, (1, 2, 3, 1, 2, 3)), (1, (1, 2, 3, 1, 2, 3)))
_ASC_CYCLE = ((1, (1, 2, 3, 1, 2, 3)), (2, (1, 2, 3, 1, 2, 3)), (3, (1, 2, 3, 1, 2, 3)), (4, (1, 2, 3, 1, 2, 3)), (5, (1, 2, 3, 1, 2, 3)), (6, (1, 2, 3, 1, 2, 3)), (7, (1, 2, 3, 1, 2, 3)), (8, (1, 2, 3, 1, 2, 3)))
_SPAN_5_4 = ((1, (1, 1, 1)), 1, 1, (1, (1, 1)), 1)

RT_CASES = [
    ("single_note", {"subdivisions": (1,)}),
    ("uniform_4", {"subdivisions": (1, 1, 1, 1)}),
    ("uniform_4_scaled", {"subdivisions": (5, 5, 5, 5)}),
    ("uniform_3", {"subdivisions": (1, 1, 1)}),
    ("uniform_5", {"subdivisions": (1, 1, 1, 1, 1)}),
    ("uniform_7", {"subdivisions": (1, 1, 1, 1, 1, 1, 1)}),
    ("uniform_13", {"subdivisions": (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)}),
    ("weighted_4_2_1_1", {"subdivisions": (4, 2, 1, 1)}),
    ("weighted_8_4_2_2", {"subdivisions": (8, 4, 2, 2)}),
    ("weighted_7_2_1_1", {"subdivisions": (7, 2, 1, 1)}),
    ("nested_one_level", {"subdivisions": ((4, (1, 1, 1)), 2, 1, 1)}),
    ("nested_two_levels", {"subdivisions": ((4, (1, 1, (1, (1, 1)))), 2, 1, 1)}),
    ("nested_two_levels_meas1", {"meas": 1, "subdivisions": ((4, (1, 1, (1, (1, 1)))), 2, 1, 1)}),
    ("rests_basic", {"subdivisions": (1, (1, (1, 1)), (1, (1, 1, -1, 1)), (1, (1, 3)))}),
    ("rests_nested", {"subdivisions": (1, (1, (1, (1, (-1, 1)))), (1, (1, 1, -1, 1)), (1, (-1, 2, 1)))}),
    ("rest_group", {"subdivisions": (1, (1, (1, 1)), (-1, (1, 1, 1, 1)), (1, (1, 3)))}),
    ("rest_leaf", {"subdivisions": (1, (1, (1, 1)), -1, (1, (1, 3)))}),
    ("complex_meas1", {"meas": 1, "subdivisions": _COMPLEX_SUBDIV}),
    ("complex_meas_3_4", {"meas": "3/4", "subdivisions": _COMPLEX_SUBDIV}),
    ("complex_meas_6_5", {"meas": "6/5", "subdivisions": _COMPLEX_SUBDIV}),
    ("complex_meas_2_3", {"meas": "2/3", "subdivisions": _COMPLEX_SUBDIV}),
    ("complex_meas_7_2", {"meas": "7/2", "subdivisions": _COMPLEX_SUBDIV}),
    ("span_1_meas_5_4", {"span": 1, "meas": "5/4", "subdivisions": _SPAN_5_4}),
    ("span_2_meas_5_4", {"span": 2, "meas": "5/4", "subdivisions": _SPAN_5_4}),
    ("span_3_meas_5_4", {"span": 3, "meas": "5/4", "subdivisions": _SPAN_5_4}),
    ("accelerating", {"subdivisions": (16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)}),
    ("decelerating", {"subdivisions": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)}),
    ("pulse_accel", {"subdivisions": _PULSE_ACCEL}),
    ("pulse_decel", {"subdivisions": _PULSE_DECEL}),
    ("accel_outer_pulse_inner", {"subdivisions": _ACCEL_OUTER}),
    ("decel_outer_pulse_inner", {"subdivisions": _DECEL_OUTER}),
    ("desc_weights_asc_inner", {"subdivisions": _DESC_ASC}),
    ("asc_weights_desc_inner", {"subdivisions": _ASC_DESC}),
    ("desc_weights_cycle_inner", {"subdivisions": _DESC_CYCLE}),
    ("asc_weights_cycle_inner", {"subdivisions": _ASC_CYCLE}),
]

UT_CASES = [
    ("default_ut", {"tempus": "4/4"}),
    ("default_ut_120bpm", {"tempus": "4/4", "bpm": 120}),
    ("ut_3_4_pulse", {"tempus": "3/4", "prolatio": "p"}),
    ("ut_6_8_pulse_90bpm", {"tempus": "6/8", "prolatio": "p", "bpm": 90}),
    ("ut_4_2_1_1", {"tempus": "4/4", "prolatio": (4, 2, 1, 1)}),
    ("ut_complex", {"tempus": "3/4", "prolatio": _COMPLEX_SUBDIV}),
    ("ut_span2_5_4", {"span": 2, "tempus": "5/4", "prolatio": _SPAN_5_4}),
    ("ut_7_8_2_3_2", {"tempus": "7/8", "prolatio": (2, 3, 2), "bpm": 120}),
    ("ut_rest", {"tempus": "4/4", "prolatio": "r"}),
    ("ut_duration", {"tempus": "4/4", "prolatio": "d"}),
    ("ut_2_4_pulse", {"tempus": "2/4", "prolatio": "p"}),
    ("ut_3_4_pulse_alt", {"tempus": "3/4", "prolatio": "p"}),
    ("ut_5_8_pulse", {"tempus": "5/8", "prolatio": "p"}),
    ("ut_7_8_pulse", {"tempus": "7/8", "prolatio": "p"}),
    ("ut_6_4_pulse", {"tempus": "6/4", "prolatio": "p"}),
    ("ut_2_4_60", {"tempus": "2/4", "prolatio": "p", "bpm": 60}),
    ("ut_2_4_90", {"tempus": "2/4", "prolatio": "p", "bpm": 90}),
    ("ut_2_4_120", {"tempus": "2/4", "prolatio": "p", "bpm": 120}),
    ("ut_2_4_200", {"tempus": "2/4", "prolatio": "p", "bpm": 200}),
    ("ut_3_8_60", {"tempus": "3/8", "prolatio": "p", "bpm": 60}),
    ("ut_3_8_90", {"tempus": "3/8", "prolatio": "p", "bpm": 90}),
    ("ut_3_8_120", {"tempus": "3/8", "prolatio": "p", "bpm": 120}),
    ("ut_3_8_200", {"tempus": "3/8", "prolatio": "p", "bpm": 200}),
    ("ut_5_4_60", {"tempus": "5/4", "prolatio": "p", "bpm": 60}),
    ("ut_5_4_90", {"tempus": "5/4", "prolatio": "p", "bpm": 90}),
    ("ut_5_4_120", {"tempus": "5/4", "prolatio": "p", "bpm": 120}),
    ("ut_5_4_200", {"tempus": "5/4", "prolatio": "p", "bpm": 200}),
    ("ut_span1", {"span": 1, "tempus": "4/4", "prolatio": "p"}),
    ("ut_span2", {"span": 2, "tempus": "4/4", "prolatio": "p"}),
    ("ut_span3", {"span": 3, "tempus": "4/4", "prolatio": "p"}),
    ("ut_span4", {"span": 4, "tempus": "4/4", "prolatio": "p"}),
    ("ut_nested_120", {"tempus": "4/4", "prolatio": ((4, (1, 1, (1, (1, 1)))), 2, 1, 1), "bpm": 120}),
    ("ut_accel", {"tempus": "4/4", "prolatio": (8, 7, 6, 5, 4, 3, 2, 1), "bpm": 120}),
    ("ut_offset", {"tempus": "4/4", "prolatio": "p", "bpm": 60, "offset": 2.5}),
]

UC_CASES = [
    ("uc_default", {"tempus": "4/4"}),
    ("uc_4_2_1_1", {"tempus": "4/4", "prolatio": (4, 2, 1, 1)}),
    ("uc_pulse", {"tempus": "4/4", "prolatio": "p"}),
    ("uc_nested", {"tempus": "4/4", "prolatio": ((4, (1, 1, 1)), 2, 1, 1)}),
]


def _jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    return obj


def main():
    out = {"rt": {}, "ut": {}, "uc": {}}

    for name, kwargs in RT_CASES:
        rt = RT(**kwargs)
        out["rt"][name] = {"kwargs": _jsonable(kwargs), "expected": capture_rt_structure(rt)}

    for name, kwargs in UT_CASES:
        ut = UT(**kwargs)
        _ = ut.events
        out["ut"][name] = {"kwargs": _jsonable(kwargs), "expected": capture_rt_structure(ut._rt)}

    for name, kwargs in UC_CASES:
        uc = UC(**kwargs)
        _ = uc.events
        out["uc"][name] = {"kwargs": _jsonable(kwargs), "expected": capture_rt_structure(uc._rt)}

    json.dump(out, sys.stdout, indent=2)


if __name__ == "__main__":
    # --- oracle lock ---------------------------------------------------
    # Inside __main__ on purpose: tests/test_uc_pt_regression.py imports
    # this module for its serialisers, and a guard at import scope kills
    # the whole test run. Guard the ACT, not the file.
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / 'tests'))
    from _oracle_lock import require_regen_authorization as _require
    _require('tests/expected_trees.json', must_import_remote=True)
    # -------------------------------------------------------------------
    main()
