import math
from fractions import Fraction
from html import escape as html_escape

from ._svg_utils import SvgFigureData, svg_wrap_viewbox, svg_text


_HALO_NOTE_COLOR = (100, 160, 255)


def _rt_node_tooltip(rt, node_id, audio_source=None):
    node_data = rt[node_id]
    proportion = node_data.get('proportion', None)
    parts = [f"Node: {node_id}"]
    if proportion is not None:
        parts.append(f"Proportion: {proportion}")
    if 'metric_onset' in node_data:
        parts.append(f"Metric Onset: {node_data['metric_onset']}")
    if 'metric_duration' in node_data:
        parts.append(f"Metric Duration: {node_data['metric_duration']}")

    if audio_source is not None:
        from klotho.thetos.composition.compositional import CompositionalUnit as _UC
        chronon_map = getattr(audio_source, '_chronon_map', None)
        if chronon_map is None:
            chronon_map = {}
            for c in audio_source:
                chronon_map[c.node_id] = c
            audio_source._chronon_map = chronon_map
        chronon = chronon_map.get(node_id)
        if chronon is not None:
            parts.append(f"Real Onset: {chronon.start:.4f}s")
            parts.append(f"Real Duration: {abs(chronon.duration):.4f}s")
            if isinstance(audio_source, _UC):
                try:
                    inst = audio_source.get_active_instrument(node_id)
                    if inst is not None and hasattr(inst, 'name'):
                        parts.append(f"Instrument: {inst.name}")
                except Exception:
                    pass
                if hasattr(chronon, 'parameters'):
                    skip = {'synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id'}
                    for k, v in chronon.parameters.items():
                        if k not in skip:
                            parts.append(f"{k}: {v}")

    return "\n".join(parts)


def _svg_halo_ellipses(prefix, cx, cy, rx, ry):
    base = _HALO_NOTE_COLOR
    grad_id = f"{prefix}_rg"
    eid = f"{prefix}_h"
    elements = [
        f'<defs><radialGradient id="{grad_id}">'
        f'<stop offset="0%" stop-color="rgb({base[0]},{base[1]},{base[2]})" stop-opacity="0.5"/>'
        f'<stop offset="60%" stop-color="rgb({base[0]},{base[1]},{base[2]})" stop-opacity="0.15"/>'
        f'<stop offset="100%" stop-color="rgb({base[0]},{base[1]},{base[2]})" stop-opacity="0"/>'
        f'</radialGradient></defs>',
        f'<ellipse id="{eid}" cx="{cx:.4f}" cy="{cy:.4f}" '
        f'rx="{rx * 1.5:.4f}" ry="{ry * 1.5:.4f}" '
        f'fill="url(#{grad_id})" '
        f'style="display:none" pointer-events="none"/>',
    ]
    return [eid], elements


def _wrap_svg(inner_svg, width_px, height_px, y_min, y_max):
    return svg_wrap_viewbox(inner_svg, width_px, height_px, y_min, y_max)


def _svg_text(x, y, text, font_size=12, fill='white', font_family='Arial',
              anchor='middle', weight='normal'):
    return svg_text(x, y, text, font_size=font_size, fill=fill,
                    font_family=font_family, anchor=anchor, weight=weight,
                    invert_y=True)


class SvgRTData(SvgFigureData):
    __slots__ = ('svg_str', 'width_px', 'height_px', 'node_to_ids',
                 'leaf_path_ids', 'leaf_bright_colors', 'leaf_base_colors',
                 'leaf_halo_ids', 'leaf_x_positions', 'all_animated_ids',
                 'leaf_ancestors')


def _svg_rt_ratios(rt, figsize=(11, 0.5), audio_source=None):
    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    ratios = rt.durations
    leaf_nodes = rt.leaf_nodes

    total_ratio = sum(abs(r) for r in ratios)
    segment_widths = [float(abs(r) / total_ratio) for r in ratios]

    positions = [0.0]
    for w in segment_widths[:-1]:
        positions.append(positions[-1] + w)

    bar_h_frac = 0.2
    border_h_frac = 0.6
    bar_y0 = (1 - bar_h_frac) / 2
    bar_y1 = bar_y0 + bar_h_frac
    border_y0 = (1 - border_h_frac) / 2
    border_y1 = border_y0 + border_h_frac

    by0 = bar_y0 * height_px
    by1 = bar_y1 * height_px
    bdy0 = border_y0 * height_px
    bdy1 = border_y1 * height_px

    import uuid as _uuid
    uid = f"svgrt_{_uuid.uuid4().hex[:8]}"
    els = []
    node_to_ids = {}
    leaf_bright = {}
    leaf_base = {}
    all_anim_ids = []

    els.append(f'<rect x="0" y="0" width="{width_px}" height="{height_px}" fill="black"/>')

    for i, (pos, sw, ratio) in enumerate(zip(positions, segment_widths, ratios)):
        is_rest = ratio < 0
        color = 'rgba(128,128,128,0.4)' if is_rest else '#e6e6e6'
        bright = '#ffffff' if not is_rest else 'rgba(160,160,160,0.6)'

        x0 = pos * width_px
        w = sw * width_px

        eid = f"{uid}_r{i}"
        node_id = leaf_nodes[i]
        node_to_ids.setdefault(node_id, []).append(eid)
        all_anim_ids.append(eid)
        leaf_bright[eid] = bright
        leaf_base[eid] = color

        tooltip = html_escape(_rt_node_tooltip(rt, node_id, audio_source))
        els.append(
            f'<rect id="{eid}" x="{x0:.2f}" y="{by0:.2f}" '
            f'width="{w:.2f}" height="{by1 - by0:.2f}" '
            f'fill="{color}" stroke="none">'
            f'<title>{tooltip}</title></rect>'
        )

    for pos in positions + [1.0]:
        px = pos * width_px
        els.append(
            f'<line x1="{px:.2f}" y1="{bdy0:.2f}" x2="{px:.2f}" y2="{bdy1:.2f}" '
            f'stroke="#aaaaaa" stroke-width="2"/>'
        )

    halo_els = []
    leaf_halo_ids = []
    leaf_x_positions = []
    for i, (pos, sw, ratio) in enumerate(zip(positions, segment_widths, ratios)):
        cx = (pos + sw / 2) * width_px
        cy = (by0 + by1) / 2
        hw = (sw / 2 * 1.1) * width_px
        hh = (by1 - by0) / 2 * 2.0
        leaf_x_positions.append(cx)
        if ratio < 0:
            leaf_halo_ids.append([])
        else:
            hids, h_els = _svg_halo_ellipses(f"{uid}_r{i}", cx, cy, hw, hh)
            leaf_halo_ids.append(hids)
            halo_els.extend(h_els)

    leaf_ancestors = []
    for leaf in leaf_nodes:
        ancestors = list(rt.ancestors(leaf))
        leaf_ancestors.append(ancestors + [leaf])

    leaf_path_ids = []
    for path in leaf_ancestors:
        ids = set()
        for node in path:
            ids.update(node_to_ids.get(node, []))
        leaf_path_ids.append(sorted(ids))

    inner = '\n'.join(els + halo_els)
    svg_str = _wrap_svg(inner, width_px, height_px, 0, height_px)

    return SvgRTData(
        svg_str=svg_str, width_px=width_px, height_px=height_px,
        node_to_ids=node_to_ids, leaf_path_ids=leaf_path_ids,
        leaf_bright_colors=leaf_bright, leaf_base_colors=leaf_base,
        leaf_halo_ids=leaf_halo_ids, leaf_x_positions=leaf_x_positions,
        all_animated_ids=all_anim_ids, leaf_ancestors=leaf_ancestors,
    )


def _svg_rt_containers(rt, figsize=(11, 2), invert=True,
                       vertical_lines=True, barlines=True,
                       barline_color='#666666', subdivision_line_color='#aaaaaa',
                       audio_source=None):
    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    def get_node_scaling(node, rt, min_scale=0.5):
        if rt.out_degree(node) == 0:
            return min_scale
        current_depth = rt.depth_of(node)
        max_descendant_depth = current_depth
        for descendant in rt.descendants(node):
            if rt.out_degree(descendant) == 0:
                d_depth = rt.depth_of(descendant)
                if d_depth > max_descendant_depth:
                    max_descendant_depth = d_depth
        levels_to_leaf = max_descendant_depth - current_depth
        if levels_to_leaf == 0:
            return min_scale
        max_levels_for_scaling = 3
        return 1.0 - ((1.0 - min_scale) * min(1.0, (max_levels_for_scaling - levels_to_leaf) / max_levels_for_scaling))

    max_depth = rt.depth
    margin_frac = 0.01
    ratio_space_frac = 0.15
    usable_height = 1.0 - (2 * margin_frac) - ratio_space_frac
    level_height = usable_height / (max_depth + 1)

    level_positions = []
    for level in range(max_depth + 1):
        if invert:
            y_pos = 1.0 - margin_frac - (level * level_height) - (level_height / 2)
        else:
            y_pos = margin_frac + ratio_space_frac + (level * level_height) + (level_height / 2)
        level_positions.append(y_pos)

    onset_text_y_frac = -0.015
    line_cutoff_frac = onset_text_y_frac + (margin_frac * 3.0)
    y_min_frac = onset_text_y_frac - 0.02
    y_max_frac = 1.005

    def fy(frac):
        return frac * height_px

    import uuid as _uuid
    uid = f"svgrc_{_uuid.uuid4().hex[:8]}"
    els = []
    node_to_ids = {}
    leaf_bright = {}
    leaf_base = {}
    all_anim_ids = []
    leaf_block_geom = {}
    eid_counter = [0]

    def next_eid(prefix="n"):
        eid_counter[0] += 1
        return f"{uid}_{prefix}{eid_counter[0]}"

    els.append(f'<rect x="0" y="{fy(y_min_frac):.2f}" width="{width_px}" '
               f'height="{fy(y_max_frac - y_min_frac):.2f}" fill="black"/>')

    vertical_line_positions = set()

    if rt.span > 1 and barlines:
        top_bar_height = level_height * 0.5 * get_node_scaling(rt.root, rt)
        for i in range(rt.span + 1):
            x_pos = i / rt.span
            y_top = fy(level_positions[0] + top_bar_height / 2)
            y_bot = fy(line_cutoff_frac)
            els.append(
                f'<line x1="{x_pos * width_px:.2f}" y1="{y_bot:.2f}" '
                f'x2="{x_pos * width_px:.2f}" y2="{y_top:.2f}" '
                f'stroke="{barline_color}" stroke-width="1.5" '
                f'stroke-dasharray="4 6" opacity="0.3"/>'
            )

    for level in range(max_depth + 1):
        nodes = rt.at_depth(level)
        y_pos = level_positions[level]

        nodes_by_parent = {}
        for node in nodes:
            p = rt.parent(node)
            if p not in nodes_by_parent:
                nodes_by_parent[p] = []
            nodes_by_parent[p].append(node)

        for p, siblings in nodes_by_parent.items():
            if p is not None:
                parent_successors = list(rt.successors(p))
                siblings.sort(key=lambda x: parent_successors.index(x) if x in parent_successors else 0)

        for node in nodes:
            node_data = rt[node]
            ratio = node_data.get('metric_duration', None)
            proportion = node_data.get('proportion', None)

            if ratio is None:
                continue

            parent = rt.parent(node)

            if parent is None:
                if rt.span > 1:
                    for i in range(rt.span):
                        x_start = i / rt.span
                        w = 1 / rt.span

                        is_leaf = rt.out_degree(node) == 0
                        is_rest = Fraction(str(ratio)) < 0
                        color = '#404040' if is_rest else ('#e6e6e6' if is_leaf else '#c8c8c8')
                        bar_h = level_height * 0.5 * get_node_scaling(node, rt)

                        bx0 = x_start * width_px
                        bw = w * width_px
                        by0_px = fy(y_pos - bar_h / 2)
                        bh_px = fy(bar_h)

                        eid = next_eid()
                        node_to_ids.setdefault(node, []).append(eid)
                        all_anim_ids.append(eid)
                        tooltip = html_escape(_rt_node_tooltip(rt, node, audio_source))
                        els.append(
                            f'<rect id="{eid}" x="{bx0:.2f}" y="{by0_px:.2f}" '
                            f'width="{bw:.2f}" height="{bh_px:.2f}" '
                            f'fill="{color}" stroke="black" stroke-width="1">'
                            f'<title>{tooltip}</title></rect>'
                        )

                        text_color = 'white' if is_rest else 'black'
                        font_size = 12 * get_node_scaling(node, rt, 9 / 12)
                        cx_px = (x_start + w / 2) * width_px
                        els.append(_svg_text(cx_px, fy(y_pos), str(rt.meas),
                                             font_size=font_size, fill=text_color))

                    rt[node]['_x_start'] = 0
                    rt[node]['_width'] = 1
                    continue
                else:
                    x_start = 0
                    w = 1
                    is_first_child = True
                    is_last_child = True
            else:
                siblings = nodes_by_parent[parent]
                parent_data = rt[parent]

                is_first_child = siblings[0] == node
                is_last_child = siblings[-1] == node

                total_proportion = sum(abs(rt[sib].get('proportion', 1)) for sib in siblings)
                preceding_proportion = 0
                for sib in siblings:
                    if sib == node:
                        break
                    preceding_proportion += abs(rt[sib].get('proportion', 1))

                parent_x_start = parent_data.get('_x_start', 0)
                parent_width = parent_data.get('_width', 1)

                x_start = float(parent_x_start + (preceding_proportion / total_proportion) * parent_width)
                w = float((abs(proportion) / total_proportion) * parent_width)

            rt[node]['_x_start'] = x_start
            rt[node]['_width'] = w

            is_leaf = rt.out_degree(node) == 0
            is_rest = Fraction(str(ratio)) < 0
            color = '#404040' if is_rest else ('#e6e6e6' if is_leaf else '#c8c8c8')

            bar_h = level_height * 0.5 * get_node_scaling(node, rt)
            bx0 = x_start * width_px
            bw = w * width_px
            by0_px = fy(y_pos - bar_h / 2)
            bh_px = fy(bar_h)

            eid = next_eid()
            node_to_ids.setdefault(node, []).append(eid)
            all_anim_ids.append(eid)

            tooltip = html_escape(_rt_node_tooltip(rt, node, audio_source))
            els.append(
                f'<rect id="{eid}" x="{bx0:.2f}" y="{by0_px:.2f}" '
                f'width="{bw:.2f}" height="{bh_px:.2f}" '
                f'fill="{color}" stroke="black" stroke-width="1">'
                f'<title>{tooltip}</title></rect>'
            )

            if is_leaf:
                bright = '#ffffff' if not is_rest else '#707070'
                leaf_bright[eid] = bright
                leaf_base[eid] = color
                cx = bx0 + bw / 2
                cy = by0_px + bh_px / 2
                leaf_block_geom[node] = (cx, cy, bw / 2, bh_px / 2, is_rest)

            text_color = 'white' if is_rest else 'black'
            font_size = 12 * get_node_scaling(node, rt, 9 / 12)
            cx_px = (x_start + w / 2) * width_px
            label_text = f"{ratio}" if ratio is not None else ""
            els.append(_svg_text(cx_px, fy(y_pos), label_text,
                                 font_size=font_size, fill=text_color))

            if vertical_lines:
                left_x = x_start
                right_x = x_start + w

                if not is_first_child and left_x not in vertical_line_positions:
                    vertical_line_positions.add(left_x)
                    y_top = fy(y_pos - bar_h / 2)
                    y_bot = fy(line_cutoff_frac)
                    els.append(
                        f'<line x1="{left_x * width_px:.2f}" y1="{y_bot:.2f}" '
                        f'x2="{left_x * width_px:.2f}" y2="{y_top:.2f}" '
                        f'stroke="{subdivision_line_color}" stroke-width="0.8" '
                        f'stroke-dasharray="2 4" opacity="0.9"/>'
                    )

                if not is_last_child and right_x not in vertical_line_positions:
                    vertical_line_positions.add(right_x)
                    y_top = fy(y_pos - bar_h / 2)
                    y_bot = fy(line_cutoff_frac)
                    els.append(
                        f'<line x1="{right_x * width_px:.2f}" y1="{y_bot:.2f}" '
                        f'x2="{right_x * width_px:.2f}" y2="{y_top:.2f}" '
                        f'stroke="{subdivision_line_color}" stroke-width="0.8" '
                        f'stroke-dasharray="2 4" opacity="0.9"/>'
                    )

    if vertical_lines:
        top_y_pos = level_positions[0]
        top_bar_height = level_height * 0.5 * get_node_scaling(rt.root, rt)
        top_bar_top = fy(top_y_pos + (top_bar_height / 2) - 0.001)
        lc = fy(line_cutoff_frac)

        if 0 not in vertical_line_positions:
            els.append(
                f'<line x1="0" y1="{lc:.2f}" x2="0" y2="{top_bar_top:.2f}" '
                f'stroke="{barline_color}" stroke-width="1.5" opacity="0.9"/>'
            )
        if 1 not in vertical_line_positions:
            els.append(
                f'<line x1="{width_px}" y1="{lc:.2f}" '
                f'x2="{width_px}" y2="{top_bar_top:.2f}" '
                f'stroke="{barline_color}" stroke-width="1.5" opacity="0.9"/>'
            )

    durations = rt.durations
    leaf_nodes = rt.leaf_nodes
    total_ratio = sum(abs(r) for r in durations)
    seg_widths = [float(abs(r) / total_ratio) for r in durations]
    positions = [0.0]
    for sw in seg_widths[:-1]:
        positions.append(positions[-1] + sw)

    ratio_bar_h_frac = ratio_space_frac * 0.2
    ratio_y_center_frac = margin_frac + ratio_space_frac * 0.5
    ry0 = fy(ratio_y_center_frac - ratio_bar_h_frac / 2)
    ry1 = fy(ratio_y_center_frac + ratio_bar_h_frac / 2)
    rh = ry1 - ry0

    for i, (pos, sw, ratio) in enumerate(zip(positions, seg_widths, durations)):
        color = '#404040' if ratio < 0 else '#e6e6e6'
        rx0 = pos * width_px
        rw = sw * width_px

        leaf_id = leaf_nodes[i]
        eid = next_eid("rb")
        node_to_ids.setdefault(leaf_id, []).append(eid)
        all_anim_ids.append(eid)

        is_rest = ratio < 0
        leaf_bright[eid] = '#707070' if is_rest else '#ffffff'
        leaf_base[eid] = color

        tooltip = html_escape(_rt_node_tooltip(rt, leaf_id, audio_source))
        els.append(
            f'<rect id="{eid}" x="{rx0:.2f}" y="{ry0:.2f}" '
            f'width="{rw:.2f}" height="{rh:.2f}" '
            f'fill="{color}" stroke="none">'
            f'<title>{tooltip}</title></rect>'
        )

    for pos in positions + [1.0]:
        px = pos * width_px
        els.append(
            f'<line x1="{px:.2f}" y1="{ry0:.2f}" x2="{px:.2f}" y2="{ry1:.2f}" '
            f'stroke="{subdivision_line_color}" stroke-width="2"/>'
        )

    for i, onset in enumerate(rt.onsets):
        if i < len(positions):
            px = positions[i] * width_px
            els.append(_svg_text(px, fy(onset_text_y_frac), str(onset),
                                 font_size=10, fill='white'))

    halo_els = []
    leaf_halo_ids = []
    leaf_x_positions = []
    for i, leaf in enumerate(rt.leaf_nodes):
        geom = leaf_block_geom.get(leaf)
        if i < len(positions) and i < len(seg_widths):
            leaf_x_positions.append((positions[i] + seg_widths[i] / 2) * width_px)
        else:
            leaf_x_positions.append(0.0)
        if geom:
            cx, cy, hw, hh, is_rest_l = geom
            if is_rest_l:
                leaf_halo_ids.append([])
            else:
                hids, h_els = _svg_halo_ellipses(
                    f"{uid}_hl{i}", cx, cy, hw * 1.2, hh * 1.4
                )
                leaf_halo_ids.append(hids)
                halo_els.extend(h_els)
        else:
            leaf_halo_ids.append([])

    leaf_ancestors = []
    for leaf in leaf_nodes:
        ancestors = list(rt.ancestors(leaf))
        leaf_ancestors.append(ancestors + [leaf])

    leaf_path_ids = []
    for path in leaf_ancestors:
        ids = set()
        for node in path:
            ids.update(node_to_ids.get(node, []))
        leaf_path_ids.append(sorted(ids))

    inner = '\n'.join(els + halo_els)
    svg_str = _wrap_svg(inner, width_px, height_px,
                        fy(y_min_frac), fy(y_max_frac))

    return SvgRTData(
        svg_str=svg_str, width_px=width_px, height_px=height_px,
        node_to_ids=node_to_ids, leaf_path_ids=leaf_path_ids,
        leaf_bright_colors=leaf_bright, leaf_base_colors=leaf_base,
        leaf_halo_ids=leaf_halo_ids, leaf_x_positions=leaf_x_positions,
        all_animated_ids=all_anim_ids, leaf_ancestors=leaf_ancestors,
    )


def _svg_rt_tree(rt, attributes=None, figsize=(11, 2), invert=True, audio_source=None):
    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    max_depth = rt.depth
    margin_frac = 0.01
    ratio_space_frac = 0.15
    usable_height = 1.0 - (2 * margin_frac) - ratio_space_frac
    level_height = usable_height / (max_depth + 1)

    level_positions = []
    for level in range(max_depth + 1):
        if invert:
            y_pos = 1.0 - margin_frac - (level * level_height) - (level_height / 2)
        else:
            y_pos = margin_frac + ratio_space_frac + (level * level_height) + (level_height / 2)
        level_positions.append(y_pos)

    pos = {}
    for level in range(max_depth + 1):
        nodes = rt.at_depth(level)
        y_pos = level_positions[level]

        nodes_by_parent = {}
        for node in nodes:
            parent = rt.parent(node)
            if parent not in nodes_by_parent:
                nodes_by_parent[parent] = []
            nodes_by_parent[parent].append(node)

        for parent, siblings in nodes_by_parent.items():
            if parent is not None:
                parent_successors = list(rt.successors(parent))
                siblings.sort(key=lambda x: parent_successors.index(x) if x in parent_successors else 0)

        for node in nodes:
            node_data = rt[node]
            ratio = node_data.get('metric_duration', None)
            proportion = node_data.get('proportion', None)

            if ratio is None:
                continue

            parent = rt.parent(node)

            if parent is None:
                x_start = 0
                width = 1
            else:
                siblings = nodes_by_parent[parent]
                parent_data = rt[parent]
                total_proportion = sum(abs(rt[sib].get('proportion', 1)) for sib in siblings)
                preceding_proportion = 0
                for sib in siblings:
                    if sib == node:
                        break
                    preceding_proportion += abs(rt[sib].get('proportion', 1))
                parent_x_start = parent_data.get('_x_start', 0)
                parent_width = parent_data.get('_width', 1)
                x_start = parent_x_start + (preceding_proportion / total_proportion) * parent_width
                width = (abs(proportion) / total_proportion) * parent_width

            rt[node]['_x_start'] = x_start
            rt[node]['_width'] = width
            pos[node] = ((x_start + width / 2) * width_px, y_pos * height_px)

    x_pad = 15
    y_pad = 15

    max_breadth = max(len(rt.at_depth(level)) for level in range(rt.depth + 1))
    density_factor = max(1.0, max_breadth / 8.0)
    node_size = max(8, 25 / density_factor)
    text_size = max(6, 15 / density_factor)

    import uuid as _uuid
    uid = f"svgtt_{_uuid.uuid4().hex[:8]}"
    els = []
    node_to_ids = {}
    all_anim_ids = []
    eid_counter = [0]

    def next_eid(prefix="tn"):
        eid_counter[0] += 1
        return f"{uid}_{prefix}{eid_counter[0]}"

    y_min_px = -y_pad
    y_max_px = height_px + y_pad

    els.append(f'<rect x="-{x_pad}" y="{y_min_px}" '
               f'width="{width_px + 2 * x_pad}" height="{y_max_px - y_min_px}" fill="black"/>')

    for u, v in rt.edges():
        if u in pos and v in pos:
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            v_prop = rt[v].get('proportion', None)
            edge_color = '#505050' if (v_prop is not None and v_prop < 0) else '#808080'
            eid = next_eid("e")
            node_to_ids.setdefault(v, []).append(eid)
            all_anim_ids.append(eid)
            els.append(
                f'<line id="{eid}" x1="{x1:.2f}" y1="{y1:.2f}" '
                f'x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{edge_color}" stroke-width="2"/>'
            )

    for node in rt.nodes():
        if node not in pos:
            continue
        x, y = pos[node]
        node_data = rt[node]

        display_text = ""
        if attributes is None:
            if 'proportion' in node_data:
                display_text = str(node_data['proportion'])
            else:
                display_text = str(node)
        else:
            label_parts = []
            for attr in attributes:
                if attr in {"node_id", "node", "id"}:
                    label_parts.append(str(node))
                elif attr in node_data:
                    label_parts.append(str(node_data[attr]))
            display_text = "\n".join(label_parts)

        proportion = node_data.get('proportion', None)
        is_rest = proportion is not None and proportion < 0
        is_leaf = len(list(rt.neighbors(node))) == 0

        if is_rest:
            node_color = '#404040'
            border_color = '#606060'
            text_color = 'white'
        elif is_leaf:
            node_color = '#e6e6e6'
            border_color = '#e6e6e6'
            text_color = '#404040'
        else:
            node_color = '#c8c8c8'
            border_color = '#c8c8c8'
            text_color = '#404040'

        eid = next_eid()
        node_to_ids.setdefault(node, []).append(eid)
        all_anim_ids.append(eid)

        tooltip = html_escape(_rt_node_tooltip(rt, node, audio_source))
        r = node_size / 2

        if is_leaf:
            els.append(
                f'<rect id="{eid}" x="{x - r:.2f}" y="{y - r:.2f}" '
                f'width="{node_size:.2f}" height="{node_size:.2f}" '
                f'fill="{node_color}" stroke="{border_color}" stroke-width="2">'
                f'<title>{tooltip}</title></rect>'
            )
        else:
            els.append(
                f'<circle id="{eid}" cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" '
                f'fill="{node_color}" stroke="{border_color}" stroke-width="2">'
                f'<title>{tooltip}</title></circle>'
            )

        els.append(_svg_text(x, y, display_text, font_size=text_size,
                             fill=text_color, weight='bold'))

    halo_els = []
    leaf_halo_ids = []
    leaf_x_positions = []
    halo_r_x = node_size * 1.1
    halo_r_y = node_size * 1.1

    for i, leaf in enumerate(rt.leaf_nodes):
        if leaf in pos:
            lx, ly = pos[leaf]
            leaf_x_positions.append(float(lx))
            leaf_prop = rt[leaf].get('proportion', None)
            is_rest_leaf = leaf_prop is not None and leaf_prop < 0
            if is_rest_leaf:
                leaf_halo_ids.append([])
            else:
                hids, h_els = _svg_halo_ellipses(f"{uid}_hl{i}", lx, ly, halo_r_x, halo_r_y)
                leaf_halo_ids.append(hids)
                halo_els.extend(h_els)
        else:
            leaf_x_positions.append(0.0)
            leaf_halo_ids.append([])

    leaf_ancestors = []
    leaf_nodes_list = rt.leaf_nodes
    for leaf in leaf_nodes_list:
        ancestors = list(rt.ancestors(leaf))
        leaf_ancestors.append(ancestors + [leaf])

    leaf_path_ids = []
    for path in leaf_ancestors:
        ids = set()
        for node in path:
            ids.update(node_to_ids.get(node, []))
        leaf_path_ids.append(sorted(ids))

    inner = '\n'.join(els + halo_els)
    svg_str = _wrap_svg(inner, width_px, height_px, y_min_px, y_max_px)

    return SvgRTData(
        svg_str=svg_str, width_px=width_px, height_px=height_px,
        node_to_ids=node_to_ids, leaf_path_ids=leaf_path_ids,
        leaf_bright_colors={}, leaf_base_colors={},
        leaf_halo_ids=leaf_halo_ids, leaf_x_positions=leaf_x_positions,
        all_animated_ids=all_anim_ids, leaf_ancestors=leaf_ancestors,
    )
