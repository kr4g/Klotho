"""
Composition generators for timeline layout experiments.
"""
import random
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from klotho.chronos.temporal_units.temporal import (
    TemporalUnit as UT,
    TemporalUnitSequence as UTS,
    TemporalBlock as BT,
)

TEMPUS_POOL = [f"{n}/4" for n in range(1, 11)]


def random_ut():
    tempus = random.choice(TEMPUS_POOL)
    return UT(span=1, tempus=tempus, prolatio='d', beat='1/4', bpm=60)


def random_axis():
    return random.uniform(-1.0, 1.0)


# ---------------------------------------------------------------------------
# Canonical (structured) generators
# ---------------------------------------------------------------------------

def make_flat_uts(n_units=5):
    return UTS([random_ut() for _ in range(n_units)])


def make_flat_bt(n_rows=3, units_per_row=4, axis=None):
    rows = [UTS([random_ut() for _ in range(units_per_row)]) for _ in range(n_rows)]
    return BT(rows, sort_rows=False, axis=axis if axis is not None else random_axis())


def make_bt_bare_ut_rows(n_rows=3, axis=None):
    rows = [random_ut() for _ in range(n_rows)]
    return BT(rows, sort_rows=False, axis=axis if axis is not None else random_axis())


def make_nested_bt(depth=2, branching=(2, 4), units_per_leaf=(2, 5), axis=None):
    if depth <= 0:
        n = random.randint(*units_per_leaf)
        return UTS([random_ut() for _ in range(n)])
    n_rows = random.randint(*branching)
    rows = [make_nested_bt(depth - 1, branching, units_per_leaf) for _ in range(n_rows)]
    return BT(rows, sort_rows=False, axis=axis if axis is not None else random_axis())


def make_uts_with_embedded_bt(n_before=2, n_after=1, bt_rows=3, bt_units=3):
    elements = [random_ut() for _ in range(n_before)]
    elements.append(make_flat_bt(n_rows=bt_rows, units_per_row=bt_units))
    elements.extend(random_ut() for _ in range(n_after))
    return UTS(elements)


def make_bt_mixed_rows(axis=None):
    rows = [
        random_ut(),
        UTS([random_ut() for _ in range(random.randint(3, 5))]),
        make_flat_bt(random.randint(2, 3), random.randint(2, 3)),
    ]
    return BT(rows, sort_rows=False, axis=axis if axis is not None else random_axis())


# ---------------------------------------------------------------------------
# Fully random recursive generator
# ---------------------------------------------------------------------------

def _random_element(depth, max_depth, branching, units_per_leaf):
    if depth >= max_depth:
        return random_ut()
    kind = random.choices(['UT', 'UTS', 'BT'], weights=[3, 2, 2])[0]
    if kind == 'UT':
        return random_ut()
    elif kind == 'UTS':
        n = random.randint(*units_per_leaf)
        elems = [_random_element(depth + 1, max_depth, branching, units_per_leaf)
                 for _ in range(n)]
        return UTS(elems)
    else:
        n_rows = random.randint(*branching)
        rows = [_random_element(depth + 1, max_depth, branching, units_per_leaf)
                for _ in range(n_rows)]
        return BT(rows, sort_rows=False, axis=random_axis())


def make_random_composition(max_depth=3, branching=(2, 4), units_per_leaf=(2, 5)):
    root_type = random.choice(['BT', 'UTS'])
    n = random.randint(*branching)
    children = [_random_element(1, max_depth, branching, units_per_leaf) for _ in range(n)]
    if root_type == 'BT':
        return BT(children, sort_rows=False, axis=random_axis())
    else:
        return UTS(children)
