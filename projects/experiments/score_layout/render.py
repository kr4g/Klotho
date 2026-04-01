"""
Score renderer for timeline layout experiments.

Notation strategy:
  - Silhouette place mats: each container gets a filled polygon showing its
    own contour (one level of detail). Children add finer detail on top.
  - Matched inline delimiters: ( ) for BT (slight curve), [ ] for UTS (square).
    Each container instance gets a unique color.
  - Strategy A layout (uniform UTS allocation).
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.path import Path
import matplotlib.patheffects as pe
import colorsys
import numpy as np


LANE_HEIGHT = 0.8
LANE_GAP = 0.2
LANE_TOTAL = LANE_HEIGHT + LANE_GAP

NOTE_COLOR = '#d4d4d4'
REST_COLOR = '#505050'
BG_COLOR = '#0c0c0c'
GRID_COLOR = '#181818'


# ---------------------------------------------------------------------------
# Silhouette colors (depth + type based)
# ---------------------------------------------------------------------------

_SIL_BT_BASES  = [
    (0.13, 0.13, 0.25),
    (0.18, 0.15, 0.28),
    (0.22, 0.18, 0.32),
    (0.26, 0.21, 0.35),
    (0.30, 0.24, 0.38),
    (0.34, 0.27, 0.40),
]

_SIL_UTS_BASES = [
    (0.18, 0.15, 0.12),
    (0.22, 0.18, 0.15),
    (0.26, 0.21, 0.18),
    (0.30, 0.24, 0.21),
    (0.34, 0.27, 0.24),
    (0.38, 0.30, 0.27),
]


def _sil_color(depth, container_type):
    if container_type == 'BT':
        palette = _SIL_BT_BASES
    else:
        palette = _SIL_UTS_BASES
    idx = min(depth, len(palette) - 1)
    return palette[idx]


# ---------------------------------------------------------------------------
# Delimiter colors (auto-assigned per container instance)
# ---------------------------------------------------------------------------

_DELIM_PALETTE = [
    '#4ec9b0', '#c586c0', '#ce9178', '#569cd6',
    '#d7ba7d', '#9cdcfe', '#e06c75', '#b5cea8',
    '#dcdcaa', '#6a9955', '#d19a66', '#4fc1ff',
]


def _delim_color(index):
    return _DELIM_PALETTE[index % len(_DELIM_PALETTE)]


# ---------------------------------------------------------------------------
# Silhouette polygon computation
# ---------------------------------------------------------------------------

def _uts_polygon(columns, inset):
    cols = sorted(columns, key=lambda c: c[0])
    if not cols:
        return []

    y_bot = min(c[2] for c in cols) * LANE_TOTAL - LANE_GAP / 2 + inset

    top_verts = []
    for i, (t0, t1, _, lane_top) in enumerate(cols):
        y_top = lane_top * LANE_TOTAL - LANE_GAP / 2 - inset
        x0 = t0 + inset
        x1 = t1 - inset

        if i > 0:
            prev_y = cols[i - 1][3] * LANE_TOTAL - LANE_GAP / 2 - inset
            if abs(y_top - prev_y) > 0.001:
                top_verts.append((x0, prev_y))
                top_verts.append((x0, y_top))

        top_verts.append((x0, y_top))
        top_verts.append((x1, y_top))

    first_x = cols[0][0] + inset
    last_x = cols[-1][1] - inset
    bot_verts = [(last_x, y_bot), (first_x, y_bot)]

    return top_verts + bot_verts


def _bt_polygon(columns, inset):
    rows = sorted(columns, key=lambda c: c[2])
    if not rows:
        return []

    left_verts = []
    for i, (t0, t1, lb, lt) in enumerate(rows):
        y_bot = lb * LANE_TOTAL - LANE_GAP / 2 + inset
        y_top = lt * LANE_TOTAL - LANE_GAP / 2 - inset
        x = t0 + inset

        if i == 0:
            left_verts.append((x, y_bot))
        else:
            prev_x = rows[i - 1][0] + inset
            prev_y_top = rows[i - 1][3] * LANE_TOTAL - LANE_GAP / 2 - inset
            if abs(x - prev_x) > 0.001:
                left_verts.append((prev_x, y_bot))
                left_verts.append((x, y_bot))
        left_verts.append((x, y_top))

    right_verts = []
    for i, (t0, t1, lb, lt) in enumerate(reversed(rows)):
        y_bot = lb * LANE_TOTAL - LANE_GAP / 2 + inset
        y_top = lt * LANE_TOTAL - LANE_GAP / 2 - inset
        x = t1 - inset

        if i == 0:
            right_verts.append((x, y_top))
        else:
            prev_row = rows[len(rows) - i]
            prev_x = prev_row[1] - inset
            prev_y_bot = prev_row[2] * LANE_TOTAL - LANE_GAP / 2 + inset
            if abs(x - prev_x) > 0.001:
                right_verts.append((prev_x, y_bot + (y_top - y_bot)))
                right_verts.append((x, y_bot + (y_top - y_bot)))
        right_verts.append((x, y_bot))

    return left_verts + right_verts


def _sil_polygon(sil, inset):
    if sil.container_type == 'UTS':
        return _uts_polygon(sil.columns, inset)
    else:
        return _bt_polygon(sil.columns, inset)


# ---------------------------------------------------------------------------
# Bracket drawing: ( ) for BT, [ ] for UTS
# ---------------------------------------------------------------------------

_BT_BULGE = 0.06
_UTS_CAP = 0.10


def _draw_bt_open(ax, x, y_bot, y_top, color, lw):
    b = _BT_BULGE
    h = y_top - y_bot
    n = max(8, int(h * 10))
    ts = np.linspace(0, 1, n)
    xs = x - b * np.sin(ts * np.pi)
    ys = y_bot + ts * h
    ax.plot(xs, ys, color=color, linewidth=lw, solid_capstyle='round', zorder=9)


def _draw_bt_close(ax, x, y_bot, y_top, color, lw):
    b = _BT_BULGE
    h = y_top - y_bot
    n = max(8, int(h * 10))
    ts = np.linspace(0, 1, n)
    xs = x + b * np.sin(ts * np.pi)
    ys = y_bot + ts * h
    ax.plot(xs, ys, color=color, linewidth=lw, solid_capstyle='round', zorder=9)


def _draw_uts_open(ax, x, y_bot, y_top, color, lw):
    ax.plot([x + _UTS_CAP, x, x, x + _UTS_CAP], [y_top, y_top, y_bot, y_bot],
            color=color, linewidth=lw, solid_capstyle='butt',
            solid_joinstyle='miter', zorder=9)


def _draw_uts_close(ax, x, y_bot, y_top, color, lw):
    ax.plot([x - _UTS_CAP, x, x, x - _UTS_CAP], [y_top, y_top, y_bot, y_bot],
            color=color, linewidth=lw, solid_capstyle='butt',
            solid_joinstyle='miter', zorder=9)


# ---------------------------------------------------------------------------
# Common drawing helpers
# ---------------------------------------------------------------------------

def _draw_grid(ax, max_lane):
    for i in range(max_lane + 1):
        y = i * LANE_TOTAL - LANE_GAP / 2
        ax.axhline(y=y, color=GRID_COLOR, linewidth=0.4, linestyle='-', zorder=1)


def _draw_blocks(ax, blocks):
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
                    facecolor=color, edgecolor='none', linewidth=0, zorder=6,
                )
                ax.add_patch(rect)
                x_cursor += seg_width
        else:
            rect = mpatches.Rectangle(
                (block.offset, y), block.duration, LANE_HEIGHT,
                facecolor=NOTE_COLOR, edgecolor='none', linewidth=0, zorder=6,
            )
            ax.add_patch(rect)

        font_size = max(5, min(7, block.duration * 3))
        if block.duration >= 0.4:
            ax.text(
                block.offset + block.duration / 2,
                y + LANE_HEIGHT / 2,
                block.label,
                ha='center', va='center',
                fontsize=font_size, color='#555555', fontweight='bold', zorder=8,
            )


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_score(blocks, groups, silhouettes, title='Score', figsize=None):
    if not blocks:
        return None

    max_lane = max(b.lane for b in blocks) + 1
    max_time = max(b.offset + b.duration for b in blocks)

    if figsize is None:
        w = max(14, max_time * 1.2 + 1.5)
        h = max(3, max_lane * LANE_TOTAL + 1.2)
        figsize = (w, h)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    sorted_sils = sorted(silhouettes, key=lambda s: s.depth)
    for sil in sorted_sils:
        if sil.depth == 0:
            continue
        inset = 0.04 * sil.depth
        verts = _sil_polygon(sil, inset)
        if len(verts) < 3:
            continue
        color = _sil_color(sil.depth, sil.container_type)
        poly = plt.Polygon(verts, facecolor=color, edgecolor='none',
                           zorder=0.1 + sil.depth * 0.01, closed=True)
        ax.add_patch(poly)

    _draw_grid(ax, max_lane)
    _draw_blocks(ax, blocks)

    sorted_groups = sorted(groups, key=lambda g: (g.depth, g.time_start))
    color_idx = 0
    for grp in sorted_groups:
        if grp.depth == 0:
            color_idx += 1
            continue

        color = _delim_color(color_idx)
        color_idx += 1

        y_bot = grp.lane_start * LANE_TOTAL - LANE_GAP / 2
        y_top = (grp.lane_start + grp.lane_count) * LANE_TOTAL - LANE_GAP / 2
        lw = max(0.8, 1.8 - grp.depth * 0.15)

        if grp.container_type == 'BT':
            _draw_bt_open(ax, grp.time_start, y_bot, y_top, color, lw)
            _draw_bt_close(ax, grp.time_end, y_bot, y_top, color, lw)
        else:
            _draw_uts_open(ax, grp.time_start, y_bot, y_top, color, lw)
            _draw_uts_close(ax, grp.time_end, y_bot, y_top, color, lw)

    ax.set_xlim(-0.5, max_time + 0.5)
    ax.set_ylim(-LANE_GAP - 0.1, max_lane * LANE_TOTAL + 0.1)

    ax.set_xlabel('Time (seconds)', color='#888888', fontsize=9)
    ax.set_title(title, color='white', fontsize=12, fontweight='bold', pad=10)
    ax.tick_params(axis='x', colors='#666666', labelsize=7)
    ax.tick_params(axis='y', colors='#666666', labelsize=7)
    ax.set_yticks([i * LANE_TOTAL + LANE_HEIGHT / 2 for i in range(max_lane)])
    ax.set_yticklabels([f'{i}' for i in range(max_lane)])
    ax.set_ylabel('Lane', color='#888888', fontsize=9)

    for spine in ax.spines.values():
        spine.set_color('#333333')

    bt_handle = mlines.Line2D([], [], color='#888888', linewidth=1.5, label='BT  ( )')
    uts_handle = mlines.Line2D([], [], color='#888888', linewidth=1.2, label='UTS [ ]',
                                marker='|', markersize=0)
    note_handle = mpatches.Patch(facecolor=NOTE_COLOR, edgecolor='#333333', label='Note')
    rest_handle = mpatches.Patch(facecolor=REST_COLOR, edgecolor='#333333', label='Rest')
    bt_sil = mpatches.Patch(facecolor=_sil_color(2, 'BT'), label='BT silhouette')
    uts_sil = mpatches.Patch(facecolor=_sil_color(2, 'UTS'), label='UTS silhouette')
    ax.legend(handles=[bt_handle, uts_handle, bt_sil, uts_sil, note_handle, rest_handle],
              loc='upper right', fontsize=5.5, facecolor='#141414',
              edgecolor='#333333', labelcolor='#aaaaaa', framealpha=0.9)

    plt.tight_layout()
    return fig


def save_fig(fig, path, dpi=150):
    if fig:
        plt.savefig(path, dpi=dpi, bbox_inches='tight', facecolor=BG_COLOR)
        plt.close(fig)
