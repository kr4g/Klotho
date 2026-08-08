"""
SVG score renderer.

Renders a :class:`~klotho.thetos.composition.score.Score` as a
track-lane timeline on a real-time (seconds) x-axis. Rows are the
score's tracks (registration order, with a fallback band for track-less
items); each item draws its unit's leaf strips exactly like the
UTS/BT timeline (nested containers resolve lanes recursively), and loose
:class:`~klotho.thetos.composition.events.Event` items draw as single
blocks — a held event (``dur=None``) extends to the score's end at
reduced opacity.

Step enumeration contract (mirrored by
:func:`~klotho.utils.playback.supersonic.converters.convert_score_to_sc_animation_events`):
items in insertion order; within an item, units in the recursive lane
DFS order with leaves in rhythm-tree order (rests included); a loose
Event is one step.
"""
import uuid as _uuid

from klotho.thetos.composition.events import Event

from .._shared.svg_utils import SvgFigureData, svg_wrap_viewbox
from .._shared.svg_shared import render_tooltip_system
from .svg_rt import (_rt_node_tooltip, _svg_halo_class_style,
                     _svg_halo_ellipses, _svg_halo_gradient_def)
from .svg_timeline import _resolve_lanes, _unit_tooltip_header

_TRACK_LABEL_COLOR = 'rgba(200,200,200,0.75)'
_TRACK_RULE_COLOR = 'rgba(120,120,120,0.35)'
_ITEM_OUTLINE_COLOR = 'rgba(210,170,110,0.55)'
_EVENT_COLOR = '#8ecae6'
_EVENT_BRIGHT = '#cdeefe'
_HELD_OPACITY = 0.35


class SvgScoreData(SvgFigureData):
    """Container for score SVG rendering data and animation metadata.

    Per-step arrays follow the same contract as
    :class:`~klotho.semeios.visualization._renderers.svg_timeline.SvgTimelineData`,
    indexed by the global step enumeration described in the module
    docstring.
    """

    __slots__ = ('svg_str', 'width_px', 'height_px',
                 'step_element_ids', 'step_bright_colors', 'step_base_colors',
                 'step_halo_ids', 'step_durations', 'track_names')


def _band_key(item):
    return item.track if item.track is not None else 'default'


def _score_bands(score):
    """Ordered ``(band_name, items)`` pairs: registered tracks first (in
    registration order), then any other band keys in first-appearance
    order."""
    items = list(score.items())
    by_band = {}
    appearance = []
    for item in items:
        key = _band_key(item)
        if key not in by_band:
            by_band[key] = []
            appearance.append(key)
        by_band[key].append(item)
    ordered = [name for name in score._tracks if name in by_band]
    ordered += [name for name in appearance if name not in ordered]
    return [(name, by_band[name]) for name in ordered]


def _resolve_lanes_memo(unit, memo):
    """One _resolve_lanes full-DFS per unit per render pass (it was run
    3x per item: band-height sizing, strip drawing, outline sizing)."""
    key = id(unit)
    hit = memo.get(key)
    if hit is None:
        hit = memo[key] = _resolve_lanes(unit)
    return hit


def _item_lane_height(item, memo):
    if isinstance(item.unit, Event):
        return 1
    _, _, height = _resolve_lanes_memo(item.unit, memo)
    return height


def _svg_score_timeline(score, figsize=None, outlines=True):
    """
    Render a Score as a track-lane timeline.

    Parameters
    ----------
    score : Score
        The score to render. Must contain at least one item and span a
        positive duration.
    figsize : tuple of float or None, optional
        Width and height in inches. Defaults to ``(12, 0.6 * lanes)``.
    outlines : bool, optional
        Draw outlines around item extents.

    Returns
    -------
    SvgScoreData
        SVG string and animation metadata.
    """
    items = list(score.items())
    if not items:
        raise ValueError("Cannot plot an empty Score")

    lanes_memo = {}  # id(unit) -> _resolve_lanes result, one render pass

    t_min = min(item.start for item in items)
    t_max = max(item.end for item in items)
    total_time = t_max - t_min
    if total_time <= 0:
        raise ValueError("Cannot plot a zero-duration Score")

    bands = _score_bands(score)
    band_layout = []      # (name, lane_start, lane_count, {item name -> item lane offset})
    lane_cursor = 0
    for name, band_items in bands:
        height = max((_item_lane_height(it, lanes_memo) for it in band_items), default=1)
        band_layout.append((name, lane_cursor, height, band_items))
        lane_cursor += height
    lanes = max(lane_cursor, 1)

    if figsize is None:
        figsize = (12, max(0.6 * lanes, 0.6 * len(bands)))
    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)
    lane_h = height_px / lanes

    x_pad_frac = 0.015
    inner_span = 1.0 - 2 * x_pad_frac

    def tx_px(t):
        return (x_pad_frac + (t - t_min) / total_time * inner_span) * width_px

    uid = f"svgsc_{_uuid.uuid4().hex[:8]}"
    els = []
    halo_els = []
    hover_texts = []
    step_element_ids = []
    step_bright_colors = {}
    step_base_colors = {}
    step_halo_ids = []
    step_durations = []

    els.append(f'<rect x="0" y="0" width="{width_px}" height="{height_px}" fill="black"/>')

    # Track bands: separator rules + labels.
    item_band_lane = {}
    for name, lane_start, lane_count, band_items in band_layout:
        y0 = lane_start * lane_h
        if lane_start > 0:
            els.append(
                f'<line x1="0" y1="{y0:.2f}" x2="{width_px}" y2="{y0:.2f}" '
                f'stroke="{_TRACK_RULE_COLOR}" stroke-width="1"/>'
            )
        els.append(
            f'<text x="6" y="{y0 + 13:.2f}" fill="{_TRACK_LABEL_COLOR}" '
            f'font-family="ui-monospace, Menlo, monospace" font-size="11" '
            f'pointer-events="none">{name}</text>'
        )
        for item in band_items:
            item_band_lane[item.name] = lane_start

    bar_h_frac = 0.2
    border_h_frac = 0.6

    def _draw_unit_strip(unit, lane, header_prefix, step):
        """One UT/UC leaf strip on absolute time; returns the next step."""
        rt = unit._rt
        ratios = rt.durations
        leaf_nodes = rt.leaf_nodes
        real_durations = unit.durations

        ux0 = tx_px(unit.start)
        ux1 = tx_px(unit.end)
        uw = ux1 - ux0
        total_ratio = sum(abs(r) for r in ratios)

        y_base = lane * lane_h
        by0 = y_base + (1 - bar_h_frac) / 2 * lane_h
        by1 = by0 + bar_h_frac * lane_h
        bdy0 = y_base + (1 - border_h_frac) / 2 * lane_h
        bdy1 = bdy0 + border_h_frac * lane_h

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
                header_prefix + "\n" + _rt_node_tooltip(rt, leaf_nodes[i], unit)
            )
            els.append(
                f'<rect id="{eid}" x="{x0:.2f}" y="{by0:.2f}" '
                f'width="{w:.2f}" height="{by1 - by0:.2f}" '
                f'fill="{color}" '
                f'data-idx="{step}" data-tip-uid="{uid}"/>'
            )

            cx = x0 + w / 2
            cy = (by0 + by1) / 2
            hw = w / 2 * 1.1
            hh = (by1 - by0) / 2 * 2.0
            if is_rest:
                step_halo_ids.append([])
            else:
                if not halo_els:
                    halo_els.append(_svg_halo_gradient_def(f"{uid}_halo_rg"))
                    halo_els.append(_svg_halo_class_style(f"{uid}_hl",
                                                          f"{uid}_halo_rg"))
                hids, h_els = _svg_halo_ellipses(f"{uid}_s{step}", cx, cy, hw, hh,
                                                 grad_id=f"{uid}_halo_rg",
                                                 css_class=f"{uid}_hl")
                step_halo_ids.append(hids)
                halo_els.extend(h_els)

            pos += frac
            edge_positions.append(ux0 + pos * uw)
            step += 1

        # One path per strip for the leaf-edge ticks (was one <line> per
        # tick — ~70 bytes more each). Same stroke geometry: M x,y0 V y1.
        ticks = ''.join(f'M{px:.2f} {bdy0:.2f}V{bdy1:.2f}'
                        for px in edge_positions)
        els.append(f'<path d="{ticks}" fill="none" '
                   f'stroke="#aaaaaa" stroke-width="2"/>')
        return step

    # Items in insertion order — the global step enumeration.
    step = 0
    for item in items:
        band_lane = item_band_lane[item.name]

        if isinstance(item.unit, Event):
            ev = item.unit
            is_hold = ev._dur is None and ev._release is None
            x0 = tx_px(item.start)
            x1 = tx_px(t_max if is_hold else max(item.end, item.start))
            if x1 - x0 < 2.0:
                x1 = x0 + 2.0
            y_base = band_lane * lane_h
            by0 = y_base + 0.3 * lane_h
            by1 = y_base + 0.7 * lane_h
            opacity = _HELD_OPACITY if is_hold else 1.0

            eid = f"{uid}_s{step}"
            step_element_ids.append([eid])
            step_bright_colors[eid] = _EVENT_BRIGHT
            step_base_colors[eid] = _EVENT_COLOR
            dur_s = (t_max - item.start) if is_hold else max(item.duration, 0.0)
            step_durations.append(float(dur_s))
            hover_texts.append(
                f"Event: {item.name}"
                + (f" [{item.track}]" if item.track else "")
                + ("\nheld (until release)" if is_hold else f"\ndur: {dur_s:.3f}s")
            )
            els.append(
                f'<rect id="{eid}" x="{x0:.2f}" y="{by0:.2f}" '
                f'width="{x1 - x0:.2f}" height="{by1 - by0:.2f}" rx="3" '
                f'fill="{_EVENT_COLOR}" fill-opacity="{opacity}" stroke="none" '
                f'data-idx="{step}" data-tip-uid="{uid}"/>'
            )
            cx = (x0 + x1) / 2
            cy = (by0 + by1) / 2
            if not halo_els:
                halo_els.append(_svg_halo_gradient_def(f"{uid}_halo_rg"))
                halo_els.append(_svg_halo_class_style(f"{uid}_hl",
                                                      f"{uid}_halo_rg"))
            hids, h_els = _svg_halo_ellipses(f"{uid}_s{step}", cx, cy,
                                             (x1 - x0) / 2 * 1.1,
                                             (by1 - by0) / 2 * 2.0,
                                             grad_id=f"{uid}_halo_rg",
                                             css_class=f"{uid}_hl")
            step_halo_ids.append(hids)
            halo_els.extend(h_els)
            step += 1
            continue

        placements, _, _ = _resolve_lanes_memo(item.unit, lanes_memo)
        for unit_index, placement in enumerate(placements):
            header = (f"Item: {item.name}"
                      + (f" [{item.track}]" if item.track else "")
                      + "\n" + _unit_tooltip_header(placement.unit, unit_index))
            step = _draw_unit_strip(placement.unit, band_lane + placement.lane,
                                    header, step)

        if outlines:
            x0 = tx_px(item.start) - 1.5
            x1 = tx_px(item.end) + 1.5
            y0 = band_lane * lane_h + min(3.0, lane_h * 0.1)
            y1 = (band_lane + _item_lane_height(item, lanes_memo)) * lane_h - min(3.0, lane_h * 0.1)
            if x1 > x0 and y1 > y0:
                els.append(
                    f'<rect x="{x0:.2f}" y="{y0:.2f}" '
                    f'width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" '
                    f'rx="6" fill="none" stroke="{_ITEM_OUTLINE_COLOR}" '
                    f'stroke-width="1.5"/>'
                )

    inner = '\n'.join(els + halo_els)
    tooltip_html = render_tooltip_system(uid, hover_texts)
    svg_str = svg_wrap_viewbox(inner, width_px, height_px, 0, height_px) + tooltip_html

    return SvgScoreData(
        svg_str=svg_str, width_px=width_px, height_px=height_px,
        step_element_ids=step_element_ids,
        step_bright_colors=step_bright_colors,
        step_base_colors=step_base_colors,
        step_halo_ids=step_halo_ids,
        step_durations=step_durations,
        track_names=[name for name, *_ in band_layout],
    )
