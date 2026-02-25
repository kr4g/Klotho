import math
from html import escape as html_escape

from ._svg_utils import SvgFigureData, svg_wrap


class SvgMasterSetData(SvgFigureData):
    """Container for 2D MasterSet SVG rendering data."""

    __slots__ = ('svg_str', 'width_px', 'height_px')


def _svg_master_set_2d(ms, figsize=(12, 12), node_size=30, text_size=12,
                       show_labels=True, title=None):
    """
    Build a 2D SVG representation of a MasterSet.

    Parameters
    ----------
    ms : MasterSet
        The master set to render.
    figsize : tuple of float, optional
        Width and height in inches.
    node_size : int, optional
        Diameter of each node circle.
    text_size : int, optional
        Font size for node labels.
    show_labels : bool, optional
        Whether to display alias labels inside nodes.
    title : str or None, optional
        Title rendered above the diagram.

    Returns
    -------
    SvgMasterSetData
        SVG string and dimension metadata.
    """
    positions = ms.positions
    edge_pairs = ms.edges
    nd = ms.node_data()

    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    sorted_labels = sorted(positions)
    xs = [positions[l][0] for l in sorted_labels]
    ys = [positions[l][1] for l in sorted_labels]
    if not xs:
        xs, ys = [0], [0]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_span = (x_max - x_min) or 1.0
    y_span = (y_max - y_min) or 1.0
    pad_frac = 0.15

    data_l = x_min - x_span * pad_frac
    data_r = x_max + x_span * pad_frac
    data_b = y_min - y_span * pad_frac
    data_t = y_max + y_span * pad_frac
    dw = data_r - data_l
    dh = data_t - data_b

    aspect_data = dw / dh
    aspect_px = width_px / height_px
    if aspect_data > aspect_px:
        scale = width_px / dw
    else:
        scale = height_px / dh
    cx_data = (data_l + data_r) / 2
    cy_data = (data_b + data_t) / 2

    def tx(v):
        return width_px / 2 + (v - cx_data) * scale

    def ty(v):
        return height_px / 2 - (v - cy_data) * scale

    elements = []

    for fr, to in edge_pairs:
        if fr in positions and to in positions:
            x1, y1 = positions[fr][0], positions[fr][1]
            x2, y2 = positions[to][0], positions[to][1]
            elements.append(
                f'<line x1="{tx(x1):.2f}" y1="{ty(y1):.2f}" '
                f'x2="{tx(x2):.2f}" y2="{ty(y2):.2f}" '
                f'stroke="#808080" stroke-width="1.5"/>'
            )

    r_px = node_size * 0.5
    for label in sorted_labels:
        x, y = positions[label][0], positions[label][1]
        cx, cy = tx(x), ty(y)
        info = nd.get(label, {})
        tooltip_parts = [f"Alias: {label}"]
        if 'factor' in info:
            tooltip_parts.append(f"Factor: {info['factor']}")
            tooltip_parts.append(f"Ratio: {info['ratio']}")
        tooltip = html_escape('\n'.join(tooltip_parts))

        elements.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r_px}" '
            f'fill="white" stroke="white" stroke-width="2">'
            f'<title>{tooltip}</title></circle>'
        )
        if show_labels:
            elements.append(
                f'<text x="{cx:.2f}" y="{cy + 1:.2f}" text-anchor="middle" '
                f'dominant-baseline="central" font-family="Arial Black" '
                f'font-size="{text_size}" font-weight="bold" fill="black" '
                f'pointer-events="none">{html_escape(str(label))}</text>'
            )

    if title is None:
        title = f"MasterSet: {ms.name or 'unnamed'}"
    elements.insert(0,
        f'<text x="{width_px / 2:.1f}" y="18" text-anchor="middle" '
        f'font-family="Arial" font-size="14" fill="white">'
        f'{html_escape(title)}</text>'
    )

    svg_str = svg_wrap('\n'.join(elements), width_px, height_px)
    return SvgMasterSetData(svg_str=svg_str, width_px=width_px, height_px=height_px)
