import json
from pathlib import Path

from .cdn import SUPERSONIC_CDN, supersonic_config

_DIR = Path(__file__).parent
_DRAW_JS_CACHE = None
_SCHED_CORE_CACHE = None
_SCHED_SCORE_CACHE = None


def _read_cached(path, attr_name):
    g = globals()
    if g[attr_name] is None:
        g[attr_name] = path.read_text() if path.exists() else ""
    return g[attr_name]


def draw_scheduler_js():
    return _read_cached(_DIR / "draw.js", "_DRAW_JS_CACHE")


def scheduler_core_js():
    return _read_cached(_DIR / "scheduler_core.js", "_SCHED_CORE_CACHE")


def scheduler_score_js():
    return _read_cached(_DIR / "scheduler_score.js", "_SCHED_SCORE_CACHE")


def ss_init_js(config_json=None):
    if config_json is None:
        config_json = json.dumps(supersonic_config())
    cdn = SUPERSONIC_CDN
    return f"""if (!globalThis.__klothoSonic) {{
    globalThis.__klothoSonic = {{ instance: null, promise: null, loadedDefs: new Set() }};
    globalThis.__klothoSonic.promise = (async function() {{
        try {{
            var config = {config_json};
            var mod = await import("{cdn}");
            globalThis.SuperSonic = mod.SuperSonic;
            var sonic = new mod.SuperSonic(config);
            await sonic.init();
            globalThis.__klothoSonic.instance = sonic;
            return sonic;
        }} catch(e) {{
            console.warn("[Klotho] SuperSonic session boot failed:", e);
            globalThis.__klothoSonic.promise = null;
            return null;
        }}
    }})();
}}
globalThis.__klothoSynthdefAssets = globalThis.__klothoSynthdefAssets || {{}};
if (!globalThis.__ensureSuperSonic) {{
    globalThis.__ensureSuperSonic = function() {{
        var state = globalThis.__klothoSonic;
        if (!state) {{
            state = {{ instance: null, promise: null, loadedDefs: new Set() }};
            globalThis.__klothoSonic = state;
        }}
        if (state.instance) return Promise.resolve(state.instance);
        if (state.promise) return state.promise;
        return Promise.resolve(null);
    }};
}}"""


def synthdef_registry_merge_js(assets_json):
    return f"""(function() {{
    var _r = globalThis.__klothoSynthdefAssets = globalThis.__klothoSynthdefAssets || {{}};
    var _new = {assets_json};
    for (var k in _new) {{ if (_new.hasOwnProperty(k) && !_r[k]) _r[k] = _new[k]; }}
}})();"""


def synthdef_loader_js(needed_json):
    return f"""(async function() {{
    var state = globalThis.__klothoSonic;
    if (!state || !state.promise) return;
    var sonic = await state.promise;
    if (!sonic) return;
    var registry = globalThis.__klothoSynthdefAssets || {{}};
    var needed = {needed_json};
    var loaded = state.loadedDefs || new Set();
    for (var i = 0; i < needed.length; i++) {{
        var name = needed[i];
        if (loaded.has(name)) continue;
        var b64 = registry[name];
        if (b64) {{
            var bytes = Uint8Array.from(atob(b64), function(c) {{ return c.charCodeAt(0); }});
            try {{ await sonic.loadSynthDef(bytes); loaded.add(name); }} catch(e) {{}}
        }} else {{
            try {{ await sonic.loadSynthDef(name); loaded.add(name); }} catch(e) {{}}
        }}
    }}
    state.loadedDefs = loaded;
}})();"""


def control_bar_html(wid, show_status=False):
    status_span = ""
    if show_status:
        status_span = f"""
    <span id="{wid}_status" style="
        color: #666;
        font-size: 10px;
        min-width: 60px;
    ">ready</span>"""
    return f'''<div id="{wid}" style="
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: #1a1a2e;
    border-radius: 6px;
    user-select: none;
">
    <button id="{wid}_toggle" style="
        width: 32px;
        height: 32px;
        border: none;
        border-radius: 4px;
        background: #16213e;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
    ">
        <span id="{wid}_icon" style="
            width: 0;
            height: 0;
            border-top: 7px solid transparent;
            border-bottom: 7px solid transparent;
            border-left: 12px solid #4ade80;
            margin-left: 3px;
        "></span>
    </button>
    <button id="{wid}_loop" style="
        width: 28px;
        height: 28px;
        border: none;
        border-radius: 4px;
        background: #16213e;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        opacity: 0.5;
    ">
        <svg id="{wid}_loop_svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a0a0a0" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 2l4 4-4 4"></path>
            <path d="M3 11v-1a4 4 0 0 1 4-4h14"></path>
            <path d="M7 22l-4-4 4-4"></path>
            <path d="M21 13v1a4 4 0 0 1-4 4H3"></path>
        </svg>
    </button>{status_span}
</div>'''
