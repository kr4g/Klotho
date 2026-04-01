"""
Timeline Lane Assignment Experiment
====================================
Generates compositions, resolves Strategy A layout, renders scores
with silhouette place mats + matched inline delimiters.

Output goes to projects/experiments/output/.
"""
import random
import os

from generators import (
    random_ut, random_axis, make_flat_uts, make_flat_bt,
    make_bt_bare_ut_rows, make_nested_bt, make_uts_with_embedded_bt,
    make_bt_mixed_rows, make_random_composition,
)
from generators import UTS, BT
from layout import resolve_layout_A, validate_no_overlap, compute_silhouettes_A
from render import render_score, save_fig

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run(name, comp):
    blocks, groups, total_lanes = resolve_layout_A(comp)
    sils, _ = compute_silhouettes_A(comp)
    ok, fail = validate_no_overlap(blocks)
    status = 'OK' if ok else 'FAIL'
    print(f"  {name:<45} {total_lanes:>3} lanes  {len(blocks):>3} blk  {status}")

    if not ok:
        a, b = fail
        print(f"    !! OVERLAP lane {a.lane}")

    fig = render_score(blocks, groups, sils,
                       title=f'{name}   ({total_lanes} lanes, {len(blocks)} blocks)')
    save_fig(fig, os.path.join(OUTPUT_DIR, f'{name}.png'))


def main():
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith('.png'):
            os.remove(os.path.join(OUTPUT_DIR, f))

    print("=" * 65)
    print("CANONICAL")
    print("=" * 65)

    random.seed(10)
    run('01_flat_uts', make_flat_uts(6))

    random.seed(20)
    run('02_bt_bare_rows', make_bt_bare_ut_rows(3, axis=-1))

    random.seed(25)
    run('03_bt_bare_rows_axis', make_bt_bare_ut_rows(4, axis=0.3))

    random.seed(30)
    run('04_bt_3x4', make_flat_bt(3, 4, axis=-1))

    random.seed(35)
    run('05_bt_3x4_axis', make_flat_bt(3, 4, axis=0.5))

    random.seed(40)
    run('06_bt_uneven_rows', BT([
        UTS([random_ut() for _ in range(3)]),
        UTS([random_ut() for _ in range(6)]),
        UTS([random_ut() for _ in range(2)]),
    ], sort_rows=False, axis=-1))

    random.seed(50)
    run('07_uts_embedded_bt',
        make_uts_with_embedded_bt(n_before=2, n_after=2, bt_rows=3, bt_units=3))

    random.seed(60)
    run('08_bt_mixed_rows', make_bt_mixed_rows(axis=-1))

    random.seed(70)
    run('09_nested_bt_d2', make_nested_bt(depth=2, branching=(2, 3),
                                            units_per_leaf=(2, 4), axis=-1))

    random.seed(80)
    run('10_nested_bt_d3', make_nested_bt(depth=3, branching=(2, 3),
                                            units_per_leaf=(2, 3), axis=-1))

    random.seed(700)
    run('11_uts_of_bts', UTS([
        make_flat_bt(3, 2, axis=-1),
        random_ut(),
        make_flat_bt(4, 2, axis=0.0),
        random_ut(),
        random_ut(),
        make_flat_bt(2, 3, axis=-1),
    ]))

    print()
    print("=" * 65)
    print("RANDOM")
    print("=" * 65)

    for i, seed in enumerate([111, 222, 333, 444, 555, 666], start=12):
        random.seed(seed)
        depth = random.randint(2, 4)
        run(f'{i}_random_s{seed}_d{depth}',
            make_random_composition(max_depth=depth, branching=(2, 4), units_per_leaf=(2, 4)))

    print()
    print("=" * 65)
    print("STRESS")
    print("=" * 65)

    random.seed(7777)
    run('18_stress_d4', make_nested_bt(depth=4, branching=(2, 3), units_per_leaf=(2, 3)))

    random.seed(8888)
    run('19_stress_wide_8rows', make_flat_bt(8, 4))

    random.seed(9999)
    run('20_stress_random_d4', make_random_composition(
        max_depth=4, branching=(2, 3), units_per_leaf=(2, 3)))

    print(f"\nAll PNGs in {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
