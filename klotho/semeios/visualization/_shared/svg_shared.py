"""Shared SVG rendering helpers for path edges, shape groups, layout, and tooltips."""

import math
import json
from pathlib import Path
from collections import defaultdict

from .colors import SHAPE_COLORS, _path_color_array, _rgba_to_hex
from .svg_utils import (
    svg_radial_halo,
    svg_arrow_polygon,
    svg_glow_edge,
    svg_path_edge,
    compute_quadratic_bezier_midpoint,
)

BASE_ARC_OFFSET = 0.15
_ANIMATION_BRIDGE_JS_PATH = Path(__file__).parents[3] / "utils" / "playback" / "_animation_bridge.js"
_ANIMATION_BRIDGE_JS_CACHE = None


def _get_animation_bridge_js():
    global _ANIMATION_BRIDGE_JS_CACHE
    if _ANIMATION_BRIDGE_JS_CACHE is None:
        _ANIMATION_BRIDGE_JS_CACHE = _ANIMATION_BRIDGE_JS_PATH.read_text() if _ANIMATION_BRIDGE_JS_PATH.exists() else ""
    return _ANIMATION_BRIDGE_JS_CACHE


def render_path_edges(path, positions_fn, next_eid, path_cmap="viridis"):
    path_els = []
    step_group_ids = []
    halo_ids = []
    all_path_el_ids = []

    if not path or len(path) < 2:
        return path_els, step_group_ids, halo_ids, all_path_el_ids, None

    colors = _path_color_array(path_cmap, len(path) - 1)
    edge_counts = defaultdict(int)

    for i in range(len(path) - 1):
        key1, key2 = path[i], path[i + 1]
        info1 = positions_fn(key1)
        info2 = positions_fn(key2)
        if info1 is None or info2 is None:
            step_group_ids.append([])
            continue

        x1, y1, px1, py1 = info1
        x2, y2, px2, py2 = info2
        path_color_hex = _rgba_to_hex(colors[i])

        edge_key = tuple(sorted([key1, key2]))
        traversal_idx = edge_counts[edge_key]
        edge_counts[edge_key] += 1
        is_forward = key1 <= key2

        if traversal_idx == 0:
            svg_d = f"M{px1:.2f},{py1:.2f} L{px2:.2f},{py2:.2f}"
            mid_px = (px1 + px2) / 2
            mid_py = (py1 + py2) / 2
            arrow_angle = math.degrees(math.atan2(py2 - py1, px2 - px1))
        else:
            dx, dy = x2 - x1, y2 - y1
            length = math.sqrt(dx * dx + dy * dy)
            if length < 1e-9:
                step_group_ids.append([])
                continue
            perp_x, perp_y = -dy / length, dx / length

            side = 1 if is_forward else -1
            offset_mag = BASE_ARC_OFFSET * max(1, (traversal_idx + 1) // 2)
            if traversal_idx % 2 == 0:
                side = -side

            ctrl_x = (x1 + x2) / 2 + side * perp_x * offset_mag
            ctrl_y = (y1 + y2) / 2 + side * perp_y * offset_mag

            cpx = positions_fn._tx(ctrl_x) if hasattr(positions_fn, "_tx") else ctrl_x
            cpy = positions_fn._ty(ctrl_y) if hasattr(positions_fn, "_ty") else ctrl_y

            svg_d = f"M{px1:.2f},{py1:.2f} Q{cpx:.2f},{cpy:.2f} {px2:.2f},{py2:.2f}"
            mid_px, mid_py, arrow_angle = compute_quadratic_bezier_midpoint(px1, py1, cpx, cpy, px2, py2)

        glow_id = next_eid("pg")
        edge_id = next_eid("pe")
        arrow_id = next_eid("pa")

        path_els.append(svg_glow_edge(glow_id, svg_d))
        path_els.append(svg_path_edge(edge_id, svg_d, path_color_hex))
        path_els.append(svg_arrow_polygon(arrow_id, mid_px, mid_py, arrow_angle, path_color_hex))

        group = [glow_id, edge_id, arrow_id]
        step_group_ids.append(group)
        all_path_el_ids.extend(group)

    start_info = positions_fn(path[0])
    end_info = positions_fn(path[-1])
    if start_info and end_info:
        _, _, sx, sy = start_info
        _, _, ex, ey = end_info

        start_hex = _rgba_to_hex(colors[0])
        end_hex = _rgba_to_hex(colors[-1])

        sg_id = next_eid("rg")
        eg_id = next_eid("rg")
        start_halo_id = next_eid("hs")
        end_halo_id = next_eid("he")

        s_defs, s_circle = svg_radial_halo(sg_id, start_halo_id, sx, sy, 20, start_hex)
        e_defs, e_circle = svg_radial_halo(eg_id, end_halo_id, ex, ey, 20, end_hex)
        path_els.append(s_defs)
        path_els.append(s_circle)
        path_els.append(e_defs)
        path_els.append(e_circle)
        halo_ids = [start_halo_id, end_halo_id]
        all_path_el_ids.extend(halo_ids)

    return path_els, step_group_ids, halo_ids, all_path_el_ids, colors


def render_shape_groups(shape_groups, edge_set_fn, positions_fn, next_eid):
    shape_els = []
    group_edge_ids_list = []
    all_shape_el_ids = []
    node_colors_map = {}
    used_colors = []

    for gi, group in enumerate(shape_groups):
        color = SHAPE_COLORS[gi % len(SHAPE_COLORS)]
        used_colors.append(color)
        gids = []
        for n in group:
            node_colors_map[n] = color

        for i, n1 in enumerate(group):
            for n2 in group[i + 1 :]:
                if not edge_set_fn(n1, n2):
                    continue
                pos1 = positions_fn(n1)
                pos2 = positions_fn(n2)
                if pos1 is None or pos2 is None:
                    continue
                px1, py1 = pos1
                px2, py2 = pos2
                eid = next_eid("se")
                shape_els.append(
                    f'<line id="{eid}" x1="{px1:.2f}" y1="{py1:.2f}" '
                    f'x2="{px2:.2f}" y2="{py2:.2f}" '
                    f'stroke="{color}" stroke-width="3" opacity="0.8" '
                    f'pointer-events="none"/>'
                )
                gids.append(eid)
                all_shape_el_ids.append(eid)
        group_edge_ids_list.append(gids)

    return shape_els, group_edge_ids_list, all_shape_el_ids, used_colors, node_colors_map


def compute_svg_layout(
    positions_dict_or_list,
    figsize,
    margin_left=20,
    margin_right=20,
    margin_top=50,
    margin_bottom=20,
    pad_fraction=0.15,
):
    if isinstance(positions_dict_or_list, dict):
        xs = [pos[0] for pos in positions_dict_or_list.values()]
        ys = [pos[1] for pos in positions_dict_or_list.values()]
    else:
        xs = [p[0] for p in positions_dict_or_list]
        ys = [p[1] for p in positions_dict_or_list]

    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    x_range = x_max - x_min if x_max > x_min else 1.0
    y_range = y_max - y_min if y_max > y_min else 1.0
    x_pad = x_range * pad_fraction
    y_pad = y_range * pad_fraction
    data_x_min = x_min - x_pad
    data_x_max = x_max + x_pad
    data_y_min = y_min - y_pad
    data_y_max = y_max + y_pad
    data_w = data_x_max - data_x_min
    data_h = data_y_max - data_y_min

    plot_w = width_px - margin_left - margin_right
    plot_h = height_px - margin_top - margin_bottom

    aspect = data_w / data_h if data_h > 0 else 1
    plot_aspect = plot_w / plot_h if plot_h > 0 else 1
    if aspect > plot_aspect:
        actual_w = plot_w
        actual_h = plot_w / aspect
    else:
        actual_h = plot_h
        actual_w = plot_h * aspect
    ox = margin_left + (plot_w - actual_w) / 2
    oy = margin_top

    def tx(val):
        return ox + (val - data_x_min) / data_w * actual_w

    def ty(val):
        return oy + actual_h - (val - data_y_min) / data_h * actual_h

    return {
        "width_px": width_px,
        "height_px": height_px,
        "tx": tx,
        "ty": ty,
        "ox": ox,
        "oy": oy,
        "actual_w": actual_w,
        "actual_h": actual_h,
    }


def render_tooltip_system(svg_uid, hover_texts, is_active=None, node_freqs=None, preview_config=None):
    data_json = json.dumps(hover_texts)
    active_json = json.dumps(is_active) if is_active is not None else "null"
    freqs_json = json.dumps(node_freqs) if node_freqs is not None else "null"
    preview_json = json.dumps(preview_config or {})

    return f"""<script>{_get_animation_bridge_js()}</script>
<div id="{svg_uid}_tip" style="
    display:none;position:absolute;pointer-events:none;
    background:rgba(30,30,30,0.92);color:#eee;font-family:monospace;
    font-size:11px;padding:6px 10px;border-radius:4px;
    white-space:pre;max-width:320px;z-index:10;
    line-height:1.4;
"></div>
<script>
(function _klothoTip_{svg_uid}(){{
    var data={data_json};
    var active={active_json};
    var freqs={freqs_json};
    var previewCfg={preview_json};
    var tip=document.getElementById("{svg_uid}_tip");
    if(!tip){{ setTimeout(_klothoTip_{svg_uid},50); return; }}
    var wrap=tip.parentElement;
    if(wrap) wrap.style.position="relative";
    var circles=document.querySelectorAll("[data-tip-uid='{svg_uid}']");
    if(!circles.length){{ setTimeout(_klothoTip_{svg_uid},50); return; }}

    async function _playFreq(freq){{
        if(!freq||freq<=0) return;
        var previewDur = Number(previewCfg.dur);
        if(!Number.isFinite(previewDur) || previewDur <= 0) previewDur = 1.0;
        var previewAmp = Number(previewCfg.amp);
        if(!Number.isFinite(previewAmp) || previewAmp <= 0) previewAmp = 0.3;
        var previewSynth = previewCfg.defName || "kl_tri";
        var previewEngine = previewCfg.engine || "supersonic";
        try{{
            if(typeof globalThis.KlothoPlaybackBridge !== "function"){{
                return;
            }}
            var bridge = globalThis.KlothoPlaybackBridge({{
                engine: previewEngine,
                audioPayload: null,
                ringTime: 5
            }});
            await bridge.ensureReady();
            await bridge.resumeAudio();
            await bridge.preview({{
                freq: freq,
                dur: previewDur,
                amp: previewAmp,
                defName: previewSynth
            }});
        }}catch(e){{}}
    }}

    circles.forEach(function(c){{
        c.addEventListener("mouseenter",function(ev){{
            var idx=parseInt(c.getAttribute("data-idx"),10);
            if(isNaN(idx)||idx<0||idx>=data.length) return;
            tip.textContent=data[idx];
            if(active){{
                if(active[idx]){{
                    tip.style.background="rgba(245,245,245,0.95)";
                    tip.style.color="#222";
                }}else{{
                    tip.style.background="rgba(30,30,30,0.92)";
                    tip.style.color="#eee";
                }}
            }}
            tip.style.display="block";
        }});
        c.addEventListener("mouseleave",function(){{
            tip.style.display="none";
        }});
        c.addEventListener("mousemove",function(ev){{
            var r=wrap.getBoundingClientRect();
            tip.style.left=(ev.clientX-r.left+12)+"px";
            tip.style.top=(ev.clientY-r.top+12)+"px";
        }});
        if(freqs){{
            c.style.cursor="pointer";
            c.addEventListener("click",function(){{
                var idx=parseInt(c.getAttribute("data-idx"),10);
                if(isNaN(idx)||idx<0||idx>=freqs.length) return;
                _playFreq(freqs[idx]);
            }});
        }}
    }});
}})();
</script>"""
