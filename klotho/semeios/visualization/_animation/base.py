from pathlib import Path

from klotho.utils.playback.tonejs.cdn import cdn_scripts
from klotho.utils.playback._helpers import get_animation_bridge_js

_PLAYBACK_JS_PATH = Path(__file__).parent / '_playback.js'
_SHAPE_PLAYBACK_JS_PATH = Path(__file__).parent / '_shape_playback.js'
_PLAYBACK_JS_TEMPLATE = None
_SHAPE_PLAYBACK_JS_TEMPLATE = None


def normalize_loop_policy(loop):
    if isinstance(loop, bool):
        return ("infinite", 0, loop)
    if isinstance(loop, int) and loop > 1:
        return ("finite", int(loop), True)
    return ("infinite", 0, False)


def build_session_preamble(include_plotly=False, include_tone=False, include_threejs=False,
                           engine="tone"):
    cdn_html = cdn_scripts(
        include_plotly=include_plotly,
        include_tone=(include_tone and engine != "supersonic"),
        include_threejs=include_threejs,
    )

    if engine == "supersonic":
        return cdn_html, "", ""

    from klotho.utils.playback.tonejs.cdn import INSTRUMENTS_JS_PATH, PLAYER_JS_PATH
    instruments_js = INSTRUMENTS_JS_PATH.read_text() if INSTRUMENTS_JS_PATH.exists() else ""
    player_js = PLAYER_JS_PATH.read_text() if PLAYER_JS_PATH.exists() else ""

    return cdn_html, instruments_js, player_js


def build_control_bar_html(wid):
    from klotho.utils.playback.supersonic._js_fragments import control_bar_html
    return control_bar_html(wid)


def build_nav_controls_html(wid, total_groups, display="inline-flex"):
    return f'''    <div id="{wid}_nav" style="display:{display};align-items:center;gap:4px;margin-left:4px;">
        <button id="{wid}_prev" style="
            width:24px;height:24px;border:none;border-radius:4px;
            background:#16213e;cursor:pointer;display:flex;
            align-items:center;justify-content:center;padding:0;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                 stroke="#a0a0a0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
        </button>
        <span id="{wid}_counter" style="color:#a0a0a0;font-size:11px;min-width:36px;text-align:center;">1 / {total_groups}</span>
        <button id="{wid}_next" style="
            width:24px;height:24px;border:none;border-radius:4px;
            background:#16213e;cursor:pointer;display:flex;
            align-items:center;justify-content:center;padding:0;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                 stroke="#a0a0a0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
        </button>
        <label style="display:inline-flex;align-items:center;gap:3px;margin-left:6px;cursor:pointer;">
            <input id="{wid}_solo" type="checkbox" style="
                width:13px;height:13px;accent-color:#4ade80;cursor:pointer;margin:0;">
            <span style="color:#a0a0a0;font-size:11px;">solo</span>
        </label>
    </div>'''


def build_scripts_html(instruments_js, player_js, engine="tone", needed_synthdefs=None):
    if engine == "supersonic":
        import json
        from klotho.utils.playback.supersonic._js_fragments import (
            ss_init_js, draw_scheduler_js, scheduler_core_js,
            synthdef_registry_merge_js, synthdef_loader_js,
        )
        from klotho.utils.playback.supersonic.engine import (
            _load_all_synthdef_assets, _filter_synthdef_assets, _INFRA_SYNTHDEFS,
        )

        if needed_synthdefs is None:
            needed_synthdefs = {'kl_tri', 'kl_kicktone', 'kl_sine', 'kl_saw', 'kl_sqr', 'kl_noisebpf'}
        needed_synthdefs = needed_synthdefs | _INFRA_SYNTHDEFS | {'__klEnvCtrl'}

        all_assets = _load_all_synthdef_assets()
        assets = _filter_synthdef_assets(all_assets, needed_synthdefs)
        assets_json = json.dumps(assets)
        needed_json = json.dumps(list(needed_synthdefs))

        bridge_js = get_animation_bridge_js()
        return f'''<script type="module">
{ss_init_js()}
{draw_scheduler_js()}
{scheduler_core_js()}
{synthdef_registry_merge_js(assets_json)}
{synthdef_loader_js(needed_json)}
{bridge_js}
</script>'''

    bridge_js = get_animation_bridge_js()
    return f'''<script type="module">{instruments_js}</script>
<script type="module">{player_js}</script>
<script type="module">{bridge_js}</script>'''


def build_playback_js(wid, dur_ms, use_gt_for_boundary=True, engine="tone", ring_time=5, loop=False):
    global _PLAYBACK_JS_TEMPLATE
    if _PLAYBACK_JS_TEMPLATE is None:
        _PLAYBACK_JS_TEMPLATE = _PLAYBACK_JS_PATH.read_text()
    boundary_op = ">" if use_gt_for_boundary else ">="
    loop_mode, loop_count, loop_enabled = normalize_loop_policy(loop)
    return (_PLAYBACK_JS_TEMPLATE
            .replace('__WID__', wid)
            .replace('__DUR_MS__', str(dur_ms))
            .replace('__BOUNDARY_OP__', boundary_op)
            .replace('__ENGINE_TYPE__', engine)
            .replace('__RING_TIME__', str(ring_time))
            .replace('__LOOP_MODE__', loop_mode)
            .replace('__LOOP_COUNT__', str(loop_count))
            .replace('__LOOP_ENABLED__', 'true' if loop_enabled else 'false'))


def build_shape_playback_js(wid, dur_ms, total_groups, engine="tone", ring_time=5, loop=False):
    global _SHAPE_PLAYBACK_JS_TEMPLATE
    if _SHAPE_PLAYBACK_JS_TEMPLATE is None:
        _SHAPE_PLAYBACK_JS_TEMPLATE = _SHAPE_PLAYBACK_JS_PATH.read_text()
    loop_mode, loop_count, loop_enabled = normalize_loop_policy(loop)
    return (_SHAPE_PLAYBACK_JS_TEMPLATE
            .replace('__WID__', wid)
            .replace('__DUR_MS__', str(dur_ms))
            .replace('__TOTAL_GROUPS__', str(total_groups))
            .replace('__ENGINE_TYPE__', engine)
            .replace('__RING_TIME__', str(ring_time))
            .replace('__LOOP_MODE__', loop_mode)
            .replace('__LOOP_COUNT__', str(loop_count))
            .replace('__LOOP_ENABLED__', 'true' if loop_enabled else 'false'))
