import math
from html import escape as html_escape


class SvgFigureData:
    __slots__ = ()

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_html(self, **kwargs):
        return self.svg_str


def svg_wrap(inner_svg, width_px, height_px, background='black'):
    return (
        f'<div style="overflow-x:auto;overflow-y:hidden;background:{background}">'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_px}" height="{height_px}" '
        f'style="display:block;background:{background}">'
        f'{inner_svg}</svg></div>'
    )


def svg_wrap_viewbox(inner_svg, width_px, height_px, y_min, y_max, background='black'):
    vb_y = -y_max
    vb_h = y_max - y_min
    return (
        f'<div style="overflow-x:auto;overflow-y:hidden;background:{background}">'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_px}" height="{height_px}" '
        f'viewBox="0 {vb_y:.4f} {width_px} {vb_h:.4f}" '
        f'style="display:block;background:{background}" '
        f'preserveAspectRatio="none">'
        f'<g transform="scale(1,-1)">'
        f'{inner_svg}'
        f'</g>'
        f'</svg></div>'
    )


def svg_radial_halo(gradient_id, halo_id, cx, cy, radius, color_hex,
                    stop_opacities=(0.6, 0.2, 0.0), stop_offsets=('0%', '70%', '100%')):
    defs = (
        f'<defs>'
        f'<radialGradient id="{gradient_id}">'
    )
    for offset, opacity in zip(stop_offsets, stop_opacities):
        defs += f'<stop offset="{offset}" stop-color="{color_hex}" stop-opacity="{opacity}"/>'
    defs += f'</radialGradient></defs>'
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


def svg_text(x, y, text, font_size=12, fill='white', font_family='Arial',
             anchor='middle', weight='normal', invert_y=False):
    escaped = html_escape(str(text))
    if invert_y:
        return (
            f'<g transform="translate({x:.2f},{y:.2f}) scale(1,-1)">'
            f'<text x="0" y="0" text-anchor="{anchor}" dominant-baseline="central" '
            f'font-family="{font_family}" font-size="{font_size:.1f}" '
            f'font-weight="{weight}" fill="{fill}" pointer-events="none">'
            f'{escaped}</text></g>'
        )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'dominant-baseline="central" '
        f'font-family="{font_family}" font-size="{font_size}" '
        f'font-weight="{weight}" fill="{fill}" pointer-events="none">'
        f'{escaped}</text>'
    )


def compute_quadratic_bezier_midpoint(px1, py1, cpx, cpy, px2, py2, t=0.5):
    mid_x = (1 - t)**2 * px1 + 2 * (1 - t) * t * cpx + t**2 * px2
    mid_y = (1 - t)**2 * py1 + 2 * (1 - t) * t * cpy + t**2 * py2
    dt = 0.01
    t1, t2 = t - dt, t + dt
    tan_x = ((1-t2)**2*px1 + 2*(1-t2)*t2*cpx + t2**2*px2) - \
             ((1-t1)**2*px1 + 2*(1-t1)*t1*cpx + t1**2*px2)
    tan_y = ((1-t2)**2*py1 + 2*(1-t2)*t2*cpy + t2**2*py2) - \
             ((1-t1)**2*py1 + 2*(1-t1)*t1*cpy + t1**2*py2)
    angle = math.degrees(math.atan2(tan_y, tan_x))
    return float(mid_x), float(mid_y), angle
