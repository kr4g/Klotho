import math
from html import escape as html_escape


class SvgFigureData:
    __slots__ = ()

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_html(self, **kwargs):
        return self.svg_str


def viewbox_attr(min_x, min_y, width, height):
    """The one place a ``viewBox`` value is formatted.

    ``svg_wrap`` used to write ``viewBox="0 0 400 200"`` while
    ``svg_wrap_viewbox`` wrote ``viewBox="0 -190.0000 800 200.0000"`` for
    the same kind of box, so the two wrappers described identical geometry
    in two different texts and could drift further apart (AF1-1). Fixed
    four-decimal formatting is the convention, because these numbers are
    floats in every caller that has a non-integral extent, and ``repr`` of
    such a float is both long and unstable across platforms.
    """
    return f'{min_x:.4f} {min_y:.4f} {width:.4f} {height:.4f}'


def svg_wrap(inner_svg, width_px, height_px, background="black"):
    return (
        f'<div style="overflow-x:auto;overflow-y:hidden;max-width:100%;">'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_px}" height="{height_px}" '
        f'viewBox="{viewbox_attr(0, 0, width_px, height_px)}" '
        f'style="display:block;background:{background};">'
        f"{inner_svg}</svg></div>"
    )


def svg_wrap_viewbox(inner_svg, width_px, height_px, y_min, y_max,
                     background="black", flip=True):
    """Wrap raw SVG content in a sized ``<svg>`` with a y-range viewBox.

    Parameters
    ----------
    flip : bool, optional
        ``True`` (the default) wraps the content in a ``scale(1,-1)`` group
        and anchors the viewBox at ``-y_max``, giving a **math frame**: the
        caller authors y-UP coordinates and larger y draws higher. Text
        drawn in that frame is mirrored unless it counter-transforms (see
        :func:`svg_text` with ``invert_y=True``).

        ``False`` emits the plain **screen frame** ``viewBox="0 y_min w h"``
        with no transform group: the caller authors y-DOWN coordinates,
        y=0 is the top edge, and text renders the right way up.

        Which one a caller needs is decided by the coordinates it already
        authors, and picking the wrong one is silent -- the picture is
        simply upside down, with no exception and no failing assertion.
        ``svg_score`` and ``svg_timeline`` place lane 0 at y=0 and write
        labels *below* a band's top edge, so they are screen-frame
        (``flip=False``); ``svg_rt`` builds a y-up tree layout and is
        math-frame.
    """
    vb_y = -y_max if flip else y_min
    vb_h = y_max - y_min
    open_group = '<g transform="scale(1,-1)">' if flip else ""
    close_group = "</g>" if flip else ""
    return (
        f'<div style="overflow-x:auto;overflow-y:hidden;max-width:100%;">'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_px}" height="{height_px}" '
        f'viewBox="{viewbox_attr(0, vb_y, width_px, vb_h)}" '
        f'preserveAspectRatio="none" '
        f'style="display:block;background:{background};">'
        f"{open_group}"
        f"{inner_svg}"
        f"{close_group}"
        f"</svg></div>"
    )


def svg_radial_halo(
    gradient_id,
    halo_id,
    cx,
    cy,
    radius,
    color_hex,
    stop_opacities=(0.6, 0.2, 0.0),
    stop_offsets=("0%", "70%", "100%"),
):
    defs = f'<defs><radialGradient id="{gradient_id}">'
    for offset, opacity in zip(stop_offsets, stop_opacities):
        defs += f'<stop offset="{offset}" stop-color="{color_hex}" stop-opacity="{opacity}"/>'
    defs += "</radialGradient></defs>"
    circle = (
        f'<circle id="{halo_id}" cx="{cx:.2f}" cy="{cy:.2f}" r="{radius}" '
        f'fill="url(#{gradient_id})" pointer-events="none"/>'
    )
    return defs, circle


def svg_arrow_polygon(arrow_id, cx, cy, angle_deg, color_hex, size=6):
    svg_angle = angle_deg + 90
    return (
        f'<polygon id="{arrow_id}" '
        f'points="{-size},{size} {size},{size} 0,{-size}" '
        f'fill="{color_hex}" stroke="white" stroke-width="1" '
        f'transform="translate({cx:.2f},{cy:.2f}) rotate({svg_angle:.2f})" '
        f'pointer-events="none"/>'
    )


def svg_path_edge(edge_id, svg_d, color_hex, width=4, opacity=0.9):
    return (
        f'<path id="{edge_id}" d="{svg_d}" fill="none" '
        f'stroke="{color_hex}" stroke-width="{width}" opacity="{opacity}" '
        f'pointer-events="none"/>'
    )


def svg_glow_edge(glow_id, svg_d, width=6, opacity=0.3):
    return (
        f'<path id="{glow_id}" d="{svg_d}" fill="none" '
        f'stroke="white" stroke-width="{width}" opacity="{opacity}" '
        f'pointer-events="none"/>'
    )


def svg_text(
    x,
    y,
    text,
    font_size=12,
    fill="white",
    font_family="Arial",
    anchor="middle",
    weight="normal",
    invert_y=False,
):
    escaped = html_escape(str(text))
    if invert_y:
        return (
            f'<g transform="translate({x:.2f},{y:.2f}) scale(1,-1)">'
            f'<text x="0" y="0" text-anchor="{anchor}" dominant-baseline="central" '
            f'font-family="{font_family}" font-size="{font_size:.1f}" '
            f'font-weight="{weight}" fill="{fill}" pointer-events="none">'
            f"{escaped}</text></g>"
        )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'dominant-baseline="central" '
        f'font-family="{font_family}" font-size="{font_size}" '
        f'font-weight="{weight}" fill="{fill}" pointer-events="none">'
        f"{escaped}</text>"
    )


def compute_quadratic_bezier_midpoint(px1, py1, cpx, cpy, px2, py2, t=0.5):
    mid_x = (1 - t) ** 2 * px1 + 2 * (1 - t) * t * cpx + t ** 2 * px2
    mid_y = (1 - t) ** 2 * py1 + 2 * (1 - t) * t * cpy + t ** 2 * py2
    dt = 0.01
    t1, t2 = t - dt, t + dt
    tan_x = ((1 - t2) ** 2 * px1 + 2 * (1 - t2) * t2 * cpx + t2 ** 2 * px2) - (
        (1 - t1) ** 2 * px1 + 2 * (1 - t1) * t1 * cpx + t1 ** 2 * px2
    )
    tan_y = ((1 - t2) ** 2 * py1 + 2 * (1 - t2) * t2 * cpy + t2 ** 2 * py2) - (
        (1 - t1) ** 2 * py1 + 2 * (1 - t1) * t1 * cpy + t1 ** 2 * py2
    )
    angle = math.degrees(math.atan2(tan_y, tan_x))
    return float(mid_x), float(mid_y), angle
