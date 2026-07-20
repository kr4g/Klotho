"""
SVG timeline renderer for temporal containers (UTS / BT).

Renders a :class:`~klotho.chronos.temporal_units.temporal.TemporalUnitSequence`
or :class:`~klotho.chronos.temporal_units.temporal.TemporalBlock` as a
multi-lane timeline on a real-time (seconds) x-axis.  Each contained
:class:`TemporalUnit` / :class:`CompositionalUnit` is drawn as a
"ratios"-style strip (proportional leaf rectangles) spanning its absolute
``[start, end]`` interval, placed on a lane computed by a deterministic
recursive lane-assignment (containers may nest arbitrarily: a UTS may
contain UTSs or BTs, a BT may contain UTSs or other BTs, etc.).
"""
import uuid as _uuid

from klotho.chronos.temporal_units.temporal import (
    TemporalUnit, TemporalUnitSequence, TemporalBlock,
)

from .._shared.svg_utils import SvgFigureData, svg_wrap_viewbox
from .._shared.svg_shared import render_tooltip_system
from .svg_rt import _rt_node_tooltip, _svg_halo_ellipses


_BT_OUTLINE_COLOR = 'rgba(150,120,220,0.55)'
_UTS_OUTLINE_COLOR = 'rgba(210,170,110,0.55)'
_UT_OUTLINE_COLOR = 'rgba(150,150,150,0.45)'


class SvgTimelineData(SvgFigureData):
    """Container for timeline SVG rendering data and animation metadata.

    Per-step arrays are indexed by the global step index: a DFS traversal
    of the container (units in structural order, leaves in order within
    each unit).  Animation event converters enumerate identically.
    """

    __slots__ = ('svg_str', 'width_px', 'height_px',
                 'step_element_ids', 'step_bright_colors', 'step_base_colors',
                 'step_halo_ids', 'step_durations')


class _UnitPlacement:
    __slots__ = ('unit', 'lane', 'depth')

    def __init__(self, unit, lane, depth):
        self.unit = unit
        self.lane = lane
        self.depth = depth


class _ContainerExtent:
    __slots__ = ('kind', 'lane_start', 'lane_count', 'time_start', 'time_end', 'depth')

    def __init__(self, kind, lane_start, lane_count, time_start, time_end, depth):
        self.kind = kind
        self.lane_start = lane_start
        self.lane_count = lane_count
        self.time_start = time_start
        self.time_end = time_end
        self.depth = depth


def _resolve_lanes(container, lane_start=0, depth=0):
    """Recursive lane assignment (max-height strategy).

    - UT/UC: one strip, height 1 lane.
    - UTS: members share ``lane_start``; height = max member height.
    - BT: rows stacked vertically; height = sum of row heights.

    Returns
    -------
    tuple of (list of _UnitPlacement, list of _ContainerExtent, int)
        Unit placements in DFS order, container extents, total lane height.
    """
    placements = []
    extents = []

    if isinstance(container, TemporalUnit):
        placements.append(_UnitPlacement(container, lane_start, depth))
        return placements, extents, 1

    if isinstance(container, TemporalUnitSequence):
        max_height = 0
        for element in container:
            p, e, h = _resolve_lanes(element, lane_start, depth + 1)
            placements.extend(p)
            extents.extend(e)
            if isinstance(element, TemporalUnit):
                # bare UT/UC elements produce no extent of their own, but the
                # members of a sequence should each read as one bordered box
                extents.append(_ContainerExtent('UT', lane_start, h,
                                                element.start, element.end,
                                                depth + 1))
            max_height = max(max_height, h)
        height = max(max_height, 1)
        extents.append(_ContainerExtent('UTS', lane_start, height,
                                        container.start, container.end, depth))
        return placements, extents, height

    if isinstance(container, TemporalBlock):
        current_lane = lane_start
        total_height = 0
        for row in container:
            p, e, h = _resolve_lanes(row, current_lane, depth + 1)
            placements.extend(p)
            extents.extend(e)
            current_lane += h
            total_height += h
        height = max(total_height, 1)
        extents.append(_ContainerExtent('BT', lane_start, height,
                                        container.start, container.end, depth))
        return placements, extents, height

    raise TypeError(
        f"Unsupported member type in temporal container: {type(container).__name__}"
    )


def _unit_tooltip_header(unit, unit_index):
    tempo = f"{unit.beat} = {round(unit.bpm, 3)}"
    return f"Unit: {unit_index} ({unit.tempus}, {tempo})"


def _svg_timeline_ratios(container, figsize=None, outlines=True):
    """
    Render a temporal container as a multi-lane ratios timeline.

    Parameters
    ----------
    container : TemporalUnitSequence or TemporalBlock
        Temporal container to render.
    figsize : tuple of float or None, optional
        Width and height in inches.  Defaults to ``(11, 0.55 * lanes)``.
    outlines : bool, optional
        Draw subtle outlines around nested container extents.

    Returns
    -------
    SvgTimelineData
        SVG string and animation metadata.
    """
    placements, extents, lanes = _resolve_lanes(container)
    if not placements:
        raise ValueError(f"Cannot plot an empty {type(container).__name__}")

    t_min = container.start
    t_max = container.end
    total_time = t_max - t_min
    if total_time <= 0:
        raise ValueError(f"Cannot plot a zero-duration {type(container).__name__}")

    if figsize is None:
        figsize = (11, 0.55 * lanes)
    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)
    lane_h = height_px / lanes

    x_pad_frac = 0.015
    inner_span = 1.0 - 2 * x_pad_frac

    def tx_px(t):
        return (x_pad_frac + (t - t_min) / total_time * inner_span) * width_px

    uid = f"svgtl_{_uuid.uuid4().hex[:8]}"
    els = []
    halo_els = []
    hover_texts = []
    step_element_ids = []
    step_bright_colors = {}
    step_base_colors = {}
    step_halo_ids = []
    step_durations = []

    els.append(f'<rect x="0" y="0" width="{width_px}" height="{height_px}" fill="black"/>')

    if outlines:
        for ext in sorted(extents, key=lambda e: e.depth):
            if ext.kind == 'BT':
                color = _BT_OUTLINE_COLOR
            elif ext.kind == 'UTS':
                color = _UTS_OUTLINE_COLOR
            else:
                color = _UT_OUTLINE_COLOR
            inset = 1.5 + 2.5 * ext.depth
            inset_y = min(inset, lane_h * 0.18)
            x0 = tx_px(ext.time_start) - 3.0 + inset
            x1 = tx_px(ext.time_end) + 3.0 - inset
            y0 = ext.lane_start * lane_h + inset_y
            y1 = (ext.lane_start + ext.lane_count) * lane_h - inset_y
            if x1 <= x0 or y1 <= y0:
                continue
            els.append(
                f'<rect x="{x0:.2f}" y="{y0:.2f}" '
                f'width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" '
                f'rx="6" fill="none" stroke="{color}" stroke-width="1.5"/>'
            )

    bar_h_frac = 0.2
    border_h_frac = 0.6

    step = 0
    for unit_index, placement in enumerate(placements):
        unit = placement.unit
        rt = unit._rt
        ratios = rt.durations
        leaf_nodes = rt.leaf_nodes
        real_durations = unit.durations

        ux0 = tx_px(unit.start)
        ux1 = tx_px(unit.end)
        uw = ux1 - ux0
        total_ratio = sum(abs(r) for r in ratios)

        y_base = placement.lane * lane_h
        by0 = y_base + (1 - bar_h_frac) / 2 * lane_h
        by1 = by0 + bar_h_frac * lane_h
        bdy0 = y_base + (1 - border_h_frac) / 2 * lane_h
        bdy1 = bdy0 + border_h_frac * lane_h

        header = _unit_tooltip_header(unit, unit_index)
        edge_positions = [ux0]

        pos = 0.0
        for i, ratio in enumerate(ratios):
            frac = float(abs(ratio) / total_ratio)
            is_rest = ratio < 0
            color = 'rgba(128,128,128,0.4)' if is_rest else '#e6e6e6'
            bright = '#ffffff' if not is_rest else 'rgba(160,160,160,0.6)'

            x0 = ux0 + pos * uw
            w = frac * uw

            eid = f"{uid}_s{step}"
            step_element_ids.append([eid])
            step_bright_colors[eid] = bright
            step_base_colors[eid] = color
            step_durations.append(float(abs(real_durations[i])))

            hover_texts.append(
                header + "\n" + _rt_node_tooltip(rt, leaf_nodes[i], unit)
            )
            els.append(
                f'<rect id="{eid}" x="{x0:.2f}" y="{by0:.2f}" '
                f'width="{w:.2f}" height="{by1 - by0:.2f}" '
                f'fill="{color}" stroke="none" '
                f'data-idx="{step}" data-tip-uid="{uid}"/>'
            )

            cx = x0 + w / 2
            cy = (by0 + by1) / 2
            hw = w / 2 * 1.1
            hh = (by1 - by0) / 2 * 2.0
            if is_rest:
                step_halo_ids.append([])
            else:
                hids, h_els = _svg_halo_ellipses(f"{uid}_s{step}", cx, cy, hw, hh)
                step_halo_ids.append(hids)
                halo_els.extend(h_els)

            pos += frac
            edge_positions.append(ux0 + pos * uw)
            step += 1

        for px in edge_positions:
            els.append(
                f'<line x1="{px:.2f}" y1="{bdy0:.2f}" x2="{px:.2f}" y2="{bdy1:.2f}" '
                f'stroke="#aaaaaa" stroke-width="2"/>'
            )

    inner = '\n'.join(els + halo_els)
    tooltip_html = render_tooltip_system(uid, hover_texts)
    svg_str = svg_wrap_viewbox(inner, width_px, height_px, 0, height_px) + tooltip_html

    return SvgTimelineData(
        svg_str=svg_str, width_px=width_px, height_px=height_px,
        step_element_ids=step_element_ids,
        step_bright_colors=step_bright_colors,
        step_base_colors=step_base_colors,
        step_halo_ids=step_halo_ids,
        step_durations=step_durations,
    )
