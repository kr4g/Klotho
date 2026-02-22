import uuid
from pathlib import Path

from klotho.utils.playback.tonejs.cdn import (
    cdn_scripts,
    INSTRUMENTS_JS_PATH, PLAYER_JS_PATH,
)

_PLAYBACK_JS_PATH = Path(__file__).parent / '_playback.js'
_PLAYBACK_JS_TEMPLATE = None


def build_session_preamble(include_plotly=False, include_tone=False, include_threejs=False):
    cdn_html = cdn_scripts(
        include_plotly=include_plotly,
        include_tone=include_tone,
        include_threejs=include_threejs,
    )

    kernel_session = uuid.uuid4().hex
    session_script = f'<script>globalThis._KLOTHO_SESSION = "{kernel_session}";</script>'

    instruments_js = INSTRUMENTS_JS_PATH.read_text() if INSTRUMENTS_JS_PATH.exists() else ""
    player_js = PLAYER_JS_PATH.read_text() if PLAYER_JS_PATH.exists() else ""

    return cdn_html, session_script, instruments_js, player_js


def build_control_bar_html(wid):
    return f'''<div id="{wid}_controls" style="
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 10px; background: #1a1a2e; border-radius: 6px;
    user-select: none; margin-top: 4px;">
    <button id="{wid}_toggle" style="
        width: 32px; height: 32px; border: none; border-radius: 4px;
        background: #16213e; cursor: pointer; display: flex;
        align-items: center; justify-content: center; padding: 0;">
        <span id="{wid}_icon" style="
            width: 0; height: 0;
            border-top: 7px solid transparent; border-bottom: 7px solid transparent;
            border-left: 12px solid #4ade80; margin-left: 3px;"></span>
    </button>
    <button id="{wid}_loop" style="
        width: 28px; height: 28px; border: none; border-radius: 4px;
        background: #16213e; cursor: pointer; display: flex;
        align-items: center; justify-content: center; padding: 0; opacity: 0.5;">
        <svg id="{wid}_loop_svg" width="16" height="16" viewBox="0 0 24 24"
             fill="none" stroke="#a0a0a0" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 2l4 4-4 4"></path><path d="M3 11v-1a4 4 0 0 1 4-4h14"></path>
            <path d="M7 22l-4-4 4-4"></path><path d="M21 13v1a4 4 0 0 1-4 4H3"></path>
        </svg>
    </button>
</div>'''


def build_nav_controls_html(wid, total_groups):
    return f'''
    <span style="display:inline-flex;align-items:center;gap:4px;margin-left:8px;">
        <button id="{wid}_prev" style="
            width: 28px; height: 28px; border: none; border-radius: 4px;
            background: #16213e; cursor: pointer; display: flex;
            align-items: center; justify-content: center; padding: 0;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                 stroke="#a0a0a0" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
        </button>
        <span id="{wid}_counter" style="
            color:#a0a0a0;font-size:12px;min-width:40px;text-align:center;">
            1 / {total_groups}
        </span>
        <button id="{wid}_next" style="
            width: 28px; height: 28px; border: none; border-radius: 4px;
            background: #16213e; cursor: pointer; display: flex;
            align-items: center; justify-content: center; padding: 0;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                 stroke="#a0a0a0" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
        </button>
        <label style="display:inline-flex;align-items:center;gap:4px;margin-left:6px;color:#a0a0a0;font-size:12px;cursor:pointer;">
            <input id="{wid}_solo" type="checkbox" style="cursor:pointer;">Solo
        </label>
    </span>'''


def build_scripts_html(session_script, instruments_js, player_js):
    return f'''{session_script}
<script>{instruments_js}</script>
<script>{player_js}</script>'''


def build_playback_js(wid, dur_ms, use_gt_for_boundary=True):
    global _PLAYBACK_JS_TEMPLATE
    if _PLAYBACK_JS_TEMPLATE is None:
        _PLAYBACK_JS_TEMPLATE = _PLAYBACK_JS_PATH.read_text()
    boundary_op = ">" if use_gt_for_boundary else ">="
    return (_PLAYBACK_JS_TEMPLATE
            .replace('__WID__', wid)
            .replace('__DUR_MS__', str(dur_ms))
            .replace('__BOUNDARY_OP__', boundary_op))
