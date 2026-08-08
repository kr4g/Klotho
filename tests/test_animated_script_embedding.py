"""Script-safe JSON embedding in animated widgets (_animation/animated.py).

Every JSON payload interpolated into an inline ``<script>`` block goes
through ``_script_json`` (``</`` becomes ``<\\/``), so no data string —
e.g. an audio-payload arg or scene label containing ``</script>`` — can
terminate the script element early and kill the widget. Same exposure as
tooltip texts in ``svg_shared.render_tooltip_system``.
"""
from types import SimpleNamespace

from klotho.semeios.visualization._animation.animated import (
    AnimatedLattice3dFigure, AnimatedTimelineSvgFigure, _payload_json_memo)


BOOM = '</scr' + 'ipt><b>boom'
ESCAPED = '<\\/scr' + 'ipt><b>boom'


def _payload_with_marker():
    return {"events": [{"type": "new", "defName": "kl_tri",
                        "args": {"label": BOOM}}]}


def test_payload_memo_escapes_close_tag():
    # _payload_json_memo feeds audioPayload in every animated class.
    fig = SimpleNamespace(audio_payload=_payload_with_marker())
    out = _payload_json_memo(fig)
    assert BOOM not in out
    assert ESCAPED in out


def test_payload_memo_cache_returns_escaped_form():
    fig = SimpleNamespace(audio_payload=_payload_with_marker())
    _payload_json_memo(fig)
    assert BOOM not in _payload_json_memo(fig)


def test_3d_figure_script_close_tag_cannot_break_out():
    sd = SimpleNamespace(
        scene_data={"nodes": [], "label": BOOM},
        path_steps=[[0, BOOM]],
        halo_data={"note": BOOM},
        width_px=100, height_px=100, title="t")
    fig = AnimatedLattice3dFigure(sd, audio_payload=_payload_with_marker())
    html = fig.to_html()
    assert BOOM not in html
    assert ESCAPED in html


def test_timeline_figure_script_close_tag_cannot_break_out():
    sd = SimpleNamespace(
        svg_str="<svg></svg>",
        step_element_ids=[["seg0", BOOM]],
        step_halo_ids=[[]],
        step_durations=[0.5],
        step_bright_colors={"seg0": "#ffffff"},
        step_base_colors={"seg0": "#888888"})
    fig = AnimatedTimelineSvgFigure(sd, audio_payload=_payload_with_marker())
    html = fig.to_html()
    assert BOOM not in html
    assert ESCAPED in html
