"""
Focused silhouette test: one hand-crafted composition.
UTS [ UT, UT, BT(4 jagged rows, axis=0.3), UT, UT ]
"""
import random
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from generators import random_ut, UTS, BT
from layout import resolve_layout_A, compute_silhouettes_A, validate_no_overlap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

LANE_HEIGHT = 0.8
LANE_GAP = 0.2
LANE_TOTAL = LANE_HEIGHT + LANE_GAP
NOTE_COLOR = '#d4d4d4'
REST_COLOR = '#505050'
BG_COLOR = '#0c0c0c'
GRID_COLOR = '#181818'

SIL_PALETTE = [
    '#1a2845',
    '#253658',
    '#31456c',
    '#3d5480',
    '#4a6394',
    '#5772a8',
]

SIL_EDGE_PALETTE = [
    '#283a5c',
    '#344870',
    '#405684',
    '#4c6498',
    '#5873ac',
    '#6482c0',
]

SIL_INSET = 0.05


def sil_color(depth):
    idx = min(depth, len(SIL_PALETTE) - 1)
    return SIL_PALETTE[idx]

def sil_edge(depth):
    idx = min(depth, len(SIL_EDGE_PALETTE) - 1)
    return SIL_EDGE_PALETTE[idx]


def uts_polygon(columns, inset):
    cols = sorted(columns, key=lambda c: c[0])
    if not cols:
        return []

    y_bot = min(c[2] for c in cols) * LANE_TOTAL - LANE_GAP / 2 + inset

    top = []
    for i, (t0, t1, _, lt) in enumerate(cols):
        y_top = lt * LANE_TOTAL - LANE_GAP / 2 - inset
        x0 = t0 + inset
        x1 = t1 - inset

        if i > 0:
            prev_y = cols[i - 1][3] * LANE_TOTAL - LANE_GAP / 2 - inset
            if abs(y_top - prev_y) > 0.001:
                top.append((x0, prev_y))
                top.append((x0, y_top))

        top.append((x0, y_top))
        top.append((x1, y_top))

    first_x = cols[0][0] + inset
    last_x = cols[-1][1] - inset
    bot = [(last_x, y_bot), (first_x, y_bot)]
    return top + bot


def bt_polygon(columns, inset):
    rows = sorted(columns, key=lambda c: c[2])
    if not rows:
        return []

    left = []
    for i, (t0, t1, lb, lt) in enumerate(rows):
        y_bot = lb * LANE_TOTAL - LANE_GAP / 2 + inset
        y_top = lt * LANE_TOTAL - LANE_GAP / 2 - inset
        x = t0 + inset

        if i == 0:
            left.append((x, y_bot))
        else:
            prev_x = rows[i - 1][0] + inset
            if abs(x - prev_x) > 0.001:
                left.append((prev_x, y_bot))
                left.append((x, y_bot))
        left.append((x, y_top))

    right = []
    for i, (t0, t1, lb, lt) in enumerate(reversed(rows)):
        y_bot = lb * LANE_TOTAL - LANE_GAP / 2 + inset
        y_top = lt * LANE_TOTAL - LANE_GAP / 2 - inset
        x = t1 - inset

        if i == 0:
            right.append((x, y_top))
        else:
            ri = len(rows) - i
            prev_x = rows[ri][1] - inset
            prev_y_top = rows[ri][3] * LANE_TOTAL - LANE_GAP / 2 - inset
            if abs(x - prev_x) > 0.001:
                right.append((prev_x, y_top))
                right.append((x, y_top))
        right.append((x, y_bot))

    return left + right


def draw_sil(ax, sil, depth_offset=0):
    inset = SIL_INSET * (sil.depth + depth_offset)
    if sil.container_type == 'UTS':
        verts = uts_polygon(sil.columns, inset)
    else:
        verts = bt_polygon(sil.columns, inset)

    if len(verts) < 3:
        return

    fc = sil_color(sil.depth)
    ec = sil_edge(sil.depth)
    poly = plt.Polygon(verts, facecolor=fc, edgecolor=ec, linewidth=0.7,
                       zorder=0.1 + sil.depth * 0.01, closed=True)
    ax.add_patch(poly)


def draw_blocks(ax, blocks):
    for block in blocks:
        y = block.lane * LANE_TOTAL
        total_ratio = sum(abs(r) for r in block.ratios) if block.ratios else 1
        x_cursor = block.offset

        outer = mpatches.Rectangle(
            (block.offset, y), block.duration, LANE_HEIGHT,
            facecolor='none', edgecolor='#444444', linewidth=0.5, zorder=7,
        )
        ax.add_patch(outer)

        if block.ratios:
            for i, ratio in enumerate(block.ratios):
                seg_width = (abs(ratio) / total_ratio) * block.duration
                is_rest = block.rest_mask[i] if i < len(block.rest_mask) else False
                color = REST_COLOR if is_rest else NOTE_COLOR
                rect = mpatches.Rectangle(
                    (x_cursor, y), seg_width, LANE_HEIGHT,
                    facecolor=color, edgecolor='none', zorder=6,
                )
                ax.add_patch(rect)
                x_cursor += seg_width
        else:
            rect = mpatches.Rectangle(
                (block.offset, y), block.duration, LANE_HEIGHT,
                facecolor=NOTE_COLOR, edgecolor='none', zorder=6,
            )
            ax.add_patch(rect)

        if block.duration >= 0.4:
            ax.text(block.offset + block.duration / 2, y + LANE_HEIGHT / 2,
                    block.label, ha='center', va='center',
                    fontsize=max(5, min(7, block.duration * 3)),
                    color='#555555', fontweight='bold', zorder=8)


def render_one(comp, name, title):
    blocks, groups, total = resolve_layout_A(comp)
    sils, _ = compute_silhouettes_A(comp)
    ok, _ = validate_no_overlap(blocks)

    print(f"  {name:<45} {total:>2} lanes  {len(blocks):>3} blk  {len(sils)} sils  {'OK' if ok else 'FAIL'}")

    max_lane = max(b.lane for b in blocks) + 1
    max_time = max(b.offset + b.duration for b in blocks)

    fig, ax = plt.subplots(figsize=(max(14, max_time * 1.2 + 1), max(4, max_lane * LANE_TOTAL + 1.5)))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    for sil in sorted(sils, key=lambda s: s.depth):
        draw_sil(ax, sil)

    for i in range(max_lane + 1):
        y = i * LANE_TOTAL - LANE_GAP / 2
        ax.axhline(y=y, color=GRID_COLOR, linewidth=0.4, zorder=1)

    draw_blocks(ax, blocks)

    ax.set_xlim(-0.5, max_time + 0.5)
    ax.set_ylim(-LANE_GAP - 0.1, max_lane * LANE_TOTAL + 0.1)
    ax.set_xlabel('Time (seconds)', color='#888888', fontsize=9)
    ax.set_ylabel('Lane', color='#888888', fontsize=9)
    ax.set_title(f'{title}   ({total} lanes, {len(blocks)} blocks)',
                 color='white', fontsize=11, fontweight='bold', pad=10)
    ax.tick_params(axis='x', colors='#666666', labelsize=7)
    ax.tick_params(axis='y', colors='#666666', labelsize=7)
    ax.set_yticks([i * LANE_TOTAL + LANE_HEIGHT / 2 for i in range(max_lane)])
    ax.set_yticklabels([f'{i}' for i in range(max_lane)])
    for spine in ax.spines.values():
        spine.set_color('#333333')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, f'sil_{name}.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close(fig)


def main():
    for f in os.listdir(OUTPUT_DIR):
        if f.startswith('sil_') and f.endswith('.png'):
            os.remove(os.path.join(OUTPUT_DIR, f))

    print("Silhouette-only rendering")
    print("=" * 70)

    random.seed(42)
    bt_inner = BT([
        UTS([random_ut() for _ in range(4)]),
        UTS([random_ut() for _ in range(3)]),
        UTS([random_ut() for _ in range(5)]),
        UTS([random_ut() for _ in range(2)]),
    ], sort_rows=False, axis=0.3)
    comp1 = UTS([random_ut(), random_ut(), bt_inner, random_ut(), random_ut()])
    render_one(comp1, '01_uts_with_jagged_bt',
               'UTS [ UT, UT, BT(4 rows, axis=0.3), UT, UT ]')

    random.seed(100)
    comp2 = BT([
        random_ut(),
        UTS([random_ut() for _ in range(4)]),
        BT([
            UTS([random_ut() for _ in range(3)]),
            UTS([random_ut() for _ in range(2)]),
        ], sort_rows=False, axis=0.5),
    ], sort_rows=False, axis=-1)
    render_one(comp2, '02_bt_mixed_rows',
               'BT [ UT, UTS(4), BT(2 rows, axis=0.5) ]')

    random.seed(200)
    comp3 = UTS([
        BT([
            UTS([random_ut() for _ in range(3)]),
            UTS([random_ut() for _ in range(2)]),
            UTS([random_ut() for _ in range(4)]),
        ], sort_rows=False, axis=-1),
        random_ut(),
        random_ut(),
        BT([
            UTS([random_ut() for _ in range(2)]),
            UTS([random_ut() for _ in range(3)]),
        ], sort_rows=False, axis=0.0),
        random_ut(),
    ])
    render_one(comp3, '03_uts_of_two_bts',
               'UTS [ BT(3 rows), UT, UT, BT(2 rows, axis=0), UT ]')

    random.seed(300)
    from generators import make_nested_bt
    comp4 = make_nested_bt(depth=3, branching=(2, 3), units_per_leaf=(2, 3), axis=-1)
    render_one(comp4, '04_nested_d3', 'Nested BT depth=3')

    random.seed(400)
    from generators import make_random_composition
    comp5 = make_random_composition(max_depth=3, branching=(2, 4), units_per_leaf=(2, 4))
    render_one(comp5, '05_random_d3', 'Random depth=3')

    print(f"\nAll sil_*.png saved to {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
