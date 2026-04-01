"""
Compare notation strategies on the same compositions.
N1-N3: existing strategies (use Strategy A layout)
N4: silhouette place mats + matched delimiters (Strategy A and B)
"""
import random
import os

from generators import (
    random_ut, random_axis, make_flat_bt, make_flat_uts,
    make_nested_bt, make_uts_with_embedded_bt, make_bt_mixed_rows,
    make_random_composition,
)
from generators import UTS, BT
from layout import (
    resolve_layout_A, resolve_layout_B, validate_no_overlap,
    compute_silhouettes_A, compute_silhouettes_B,
)
from render import (
    render_N1_margin_brackets,
    render_N2_inline_brackets,
    render_N3_nested_boxes,
    render_N4_silhouette,
    save_fig,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def compare(name, comp):
    ba, ga, ha = resolve_layout_A(comp)
    bb, gb, hb = resolve_layout_B(comp)
    sils_a, _ = compute_silhouettes_A(comp)
    sils_b = compute_silhouettes_B(comp)

    ok_a, _ = validate_no_overlap(ba)
    ok_b, _ = validate_no_overlap(bb)
    print(f"  {name:<40} A={ha:>2}  B={hb:>2}  blk={len(ba):>3}  "
          f"{'OK' if ok_a else 'FAIL'}/{'OK' if ok_b else 'FAIL'}")

    fig = render_N1_margin_brackets(ba, ga,
            title=f'{name}  [N1 margin]  ({ha} lanes)')
    save_fig(fig, os.path.join(OUTPUT_DIR, f'cmp_{name}_N1.png'))

    fig = render_N3_nested_boxes(ba, ga,
            title=f'{name}  [N3 boxes]  ({ha} lanes)')
    save_fig(fig, os.path.join(OUTPUT_DIR, f'cmp_{name}_N3.png'))

    fig = render_N4_silhouette(ba, ga, sils_a,
            title=f'{name}  [N4 sil+delim, Strat A]  ({ha} lanes)')
    save_fig(fig, os.path.join(OUTPUT_DIR, f'cmp_{name}_N4a.png'))

    fig = render_N4_silhouette(bb, gb, sils_b,
            title=f'{name}  [N4 sil+delim, Strat B]  ({hb} lanes)')
    save_fig(fig, os.path.join(OUTPUT_DIR, f'cmp_{name}_N4b.png'))


def main():
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith('.png'):
            os.remove(os.path.join(OUTPUT_DIR, f))

    print("Notation strategy comparison (N1, N3, N4a, N4b)")
    print("=" * 70)

    random.seed(50)
    compare('A_uts_embedded_bt',
            make_uts_with_embedded_bt(n_before=2, n_after=2, bt_rows=3, bt_units=3))

    random.seed(60)
    compare('B_bt_mixed', make_bt_mixed_rows(axis=-1))

    random.seed(80)
    compare('C_nested_d3',
            make_nested_bt(depth=3, branching=(2, 3), units_per_leaf=(2, 3), axis=-1))

    random.seed(700)
    compare('D_uts_of_bts', UTS([
        make_flat_bt(3, 2, axis=-1),
        random_ut(),
        make_flat_bt(4, 2, axis=-1),
        random_ut(),
        random_ut(),
        make_flat_bt(2, 3, axis=-1),
    ]))

    random.seed(900)
    compare('E_random_d4',
            make_random_composition(max_depth=4, branching=(2, 3), units_per_leaf=(2, 3)))

    random.seed(7777)
    compare('F_stress_d4',
            make_nested_bt(depth=4, branching=(2, 3), units_per_leaf=(2, 3)))

    print(f"\nAll PNGs saved to {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
