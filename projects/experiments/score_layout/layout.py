"""
Lane assignment algorithms for timeline layout.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from klotho.chronos.temporal_units.temporal import (
    TemporalUnit as UT,
    TemporalUnitSequence as UTS,
    TemporalBlock as BT,
)


class LaneBlock:
    __slots__ = ('offset', 'duration', 'lane', 'label', 'depth',
                 'ratios', 'rest_mask')

    def __init__(self, offset, duration, lane, label='',
                 depth=0, ratios=None, rest_mask=None):
        self.offset = offset
        self.duration = duration
        self.lane = lane
        self.label = label
        self.depth = depth
        self.ratios = ratios or []
        self.rest_mask = rest_mask or []


class LaneGroup:
    __slots__ = ('lane_start', 'lane_count', 'time_start', 'time_end',
                 'container_type', 'depth')

    def __init__(self, lane_start, lane_count, time_start, time_end,
                 container_type, depth):
        self.lane_start = lane_start
        self.lane_count = lane_count
        self.time_start = time_start
        self.time_end = time_end
        self.container_type = container_type
        self.depth = depth


def _ut_ratios(ut):
    ratios = list(ut._rt.durations)
    rest_mask = [r < 0 for r in ratios]
    return ratios, rest_mask


# ---------------------------------------------------------------------------
# Strategy A: max-height (uniform UTS allocation)
# ---------------------------------------------------------------------------

def resolve_layout_A(container, lane_start=0, depth=0):
    blocks = []
    groups = []

    if isinstance(container, UT):
        ratios, rest_mask = _ut_ratios(container)
        blocks.append(LaneBlock(
            offset=container.offset,
            duration=container.duration,
            lane=lane_start,
            label=f"{container.tempus}",
            depth=depth,
            ratios=ratios,
            rest_mask=rest_mask,
        ))
        return blocks, groups, 1

    if isinstance(container, UTS):
        max_height = 0
        for element in container:
            b, g, h = resolve_layout_A(element, lane_start, depth + 1)
            blocks.extend(b)
            groups.extend(g)
            max_height = max(max_height, h)
        height = max(max_height, 1)
        groups.append(LaneGroup(
            lane_start=lane_start,
            lane_count=height,
            time_start=container.offset,
            time_end=container.offset + container.duration,
            container_type='UTS',
            depth=depth,
        ))
        return blocks, groups, height

    if isinstance(container, BT):
        current_lane = lane_start
        total_height = 0
        for row in container:
            b, g, h = resolve_layout_A(row, current_lane, depth + 1)
            blocks.extend(b)
            groups.extend(g)
            current_lane += h
            total_height += h
        groups.append(LaneGroup(
            lane_start=lane_start,
            lane_count=total_height,
            time_start=container.offset,
            time_end=container.offset + container.duration,
            container_type='BT',
            depth=depth,
        ))
        return blocks, groups, total_height

    return blocks, groups, 1


# ---------------------------------------------------------------------------
# Strategy B: occupancy skyline
# ---------------------------------------------------------------------------

def _skyline_base(placed_blocks, parent_base, t0, t1):
    base = parent_base(t0, t1)
    for blk in placed_blocks:
        blk_end = blk.offset + blk.duration
        if blk.offset < t1 and blk_end > t0:
            base = max(base, blk.lane + 1)
    return base


def resolve_layout_B(container, lane_start=0, depth=0):
    base_fn = lambda t0, t1: lane_start
    blocks, groups, lo, hi = _assign_B(container, base_fn, depth)
    total_lanes = (hi - lo + 1) if blocks else 1
    return blocks, groups, total_lanes


def _assign_B(container, get_base, depth):
    blocks = []
    groups = []

    if isinstance(container, UT):
        t0 = container.offset
        t1 = t0 + container.duration
        lane = get_base(t0, t1)
        ratios, rest_mask = _ut_ratios(container)
        blocks.append(LaneBlock(
            offset=t0, duration=container.duration, lane=lane,
            label=f"{container.tempus}", depth=depth,
            ratios=ratios, rest_mask=rest_mask,
        ))
        return blocks, groups, lane, lane

    if isinstance(container, UTS):
        min_l = float('inf')
        max_l = float('-inf')
        for element in container:
            b, g, lo, hi = _assign_B(element, get_base, depth + 1)
            blocks.extend(b)
            groups.extend(g)
            min_l = min(min_l, lo)
            max_l = max(max_l, hi)
        if min_l == float('inf'):
            base = get_base(container.offset, container.offset + container.duration)
            min_l = max_l = base
        groups.append(LaneGroup(
            lane_start=min_l,
            lane_count=max_l - min_l + 1,
            time_start=container.offset,
            time_end=container.offset + container.duration,
            container_type='UTS',
            depth=depth,
        ))
        return blocks, groups, min_l, max_l

    if isinstance(container, BT):
        min_l = float('inf')
        max_l = float('-inf')
        preceding_blocks = []

        for row in container:
            def _make_row_base(prev_blks, parent_base):
                snapshot = list(prev_blks)
                def _row_base(t0, t1):
                    return _skyline_base(snapshot, parent_base, t0, t1)
                return _row_base

            row_base = _make_row_base(preceding_blocks, get_base)
            b, g, lo, hi = _assign_B(row, row_base, depth + 1)
            blocks.extend(b)
            groups.extend(g)
            preceding_blocks.extend(b)
            min_l = min(min_l, lo)
            max_l = max(max_l, hi)

        if min_l == float('inf'):
            base = get_base(container.offset, container.offset + container.duration)
            min_l = max_l = base
        groups.append(LaneGroup(
            lane_start=min_l,
            lane_count=max_l - min_l + 1,
            time_start=container.offset,
            time_end=container.offset + container.duration,
            container_type='BT',
            depth=depth,
        ))
        return blocks, groups, min_l, max_l

    return blocks, groups, 0, 0


# ---------------------------------------------------------------------------
# Silhouette computation (for place-mat rendering)
# ---------------------------------------------------------------------------

class Silhouette:
    __slots__ = ('columns', 'depth', 'container_type')

    def __init__(self, columns, depth, container_type):
        self.columns = columns
        self.depth = depth
        self.container_type = container_type


def compute_silhouettes_A(container, lane_start=0, depth=0):
    sils = []

    if isinstance(container, UT):
        return sils, 1

    if isinstance(container, UTS):
        columns = []
        max_height = 0
        for element in container:
            sub, h = compute_silhouettes_A(element, lane_start, depth + 1)
            sils.extend(sub)
            columns.append((element.offset, element.offset + element.duration,
                            lane_start, lane_start + h))
            max_height = max(max_height, h)
        height = max(max_height, 1)
        sils.append(Silhouette(columns, depth, 'UTS'))
        return sils, height

    if isinstance(container, BT):
        columns = []
        current_lane = lane_start
        total_height = 0
        for row in container:
            sub, h = compute_silhouettes_A(row, current_lane, depth + 1)
            sils.extend(sub)
            columns.append((row.offset, row.offset + row.duration,
                            current_lane, current_lane + h))
            current_lane += h
            total_height += h
        sils.append(Silhouette(columns, depth, 'BT'))
        return sils, total_height

    return sils, 1


def compute_silhouettes_B(container, lane_start=0, depth=0):
    base_fn = lambda t0, t1: lane_start
    sils, _, _ = _sil_B(container, base_fn, depth)
    return sils


def _sil_B(container, get_base, depth):
    sils = []

    if isinstance(container, UT):
        t0 = container.offset
        t1 = t0 + container.duration
        lane = get_base(t0, t1)
        return sils, lane, lane

    if isinstance(container, UTS):
        columns = []
        for element in container:
            sub, lo, hi = _sil_B(element, get_base, depth + 1)
            sils.extend(sub)
            columns.append((element.offset, element.offset + element.duration, lo, hi + 1))
        sils.append(Silhouette(columns, depth, 'UTS'))
        all_lo = min(c[2] for c in columns) if columns else 0
        all_hi = max(c[3] - 1 for c in columns) if columns else 0
        return sils, all_lo, all_hi

    if isinstance(container, BT):
        columns = []
        preceding_blocks_proxy = []

        for row in container:
            def _make_base(prev, parent):
                snap = list(prev)
                def _base(t0, t1):
                    b = parent(t0, t1)
                    for (bo, bd, bl) in snap:
                        if bo < t1 and bo + bd > t0:
                            b = max(b, bl + 1)
                    return b
                return _base

            row_base = _make_base(preceding_blocks_proxy, get_base)
            sub, lo, hi = _sil_B(row, row_base, depth + 1)
            sils.extend(sub)
            columns.append((row.offset, row.offset + row.duration, lo, hi + 1))

            for s in sub:
                for (ct0, ct1, cl, ch) in s.columns:
                    for lane in range(cl, ch):
                        preceding_blocks_proxy.append((ct0, ct1 - ct0, lane))

            if not sub:
                t0 = row.offset
                t1 = t0 + row.duration
                lane = row_base(t0, t1)
                preceding_blocks_proxy.append((t0, t1 - t0, lane))

        sils.append(Silhouette(columns, depth, 'BT'))
        all_lo = min(c[2] for c in columns) if columns else 0
        all_hi = max(c[3] - 1 for c in columns) if columns else 0
        return sils, all_lo, all_hi

    return sils, 0, 0


# ---------------------------------------------------------------------------
# Overlap validator
# ---------------------------------------------------------------------------

def validate_no_overlap(blocks):
    for i, a in enumerate(blocks):
        for b in blocks[i + 1:]:
            if a.lane != b.lane:
                continue
            a_end = a.offset + a.duration
            b_end = b.offset + b.duration
            overlap = min(a_end, b_end) - max(a.offset, b.offset)
            if overlap > 1e-9:
                return False, (a, b)
    return True, None
