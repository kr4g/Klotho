import json
from pathlib import Path

from .cdn import SUPERSONIC_CDN, supersonic_config

_DIR = Path(__file__).parent
_DRAW_JS_CACHE = None
_SCHED_CORE_CACHE = None
_SCHED_SCORE_CACHE = None
_LIFECYCLE_JS_CACHE = None


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


def lifecycle_js():
    """The shared ``KlothoEngineLifecycle`` module (installed once per page)."""
    return _read_cached(_DIR / "_lifecycle.js", "_LIFECYCLE_JS_CACHE")


def ss_init_js(config_json=None):
    if config_json is None:
        config_json = json.dumps(supersonic_config())
    cdn = SUPERSONIC_CDN
    return f"""if (!globalThis.__klothoSonic) {{
    globalThis.__klothoSonic = {{ instance: null, promise: null, loadedDefs: new Set() }};
    globalThis.__klothoSonic.promise = (async function() {{
        try {{
            var config = {config_json};
            // Stashed so widgets can inspect the engine's boot options
            // (stems need the 10.16 multichannel config). An engine
            // booted by a stale pre-10.16 output has no bootConfig,
            // which is exactly how the recorder detects it.
            globalThis.__klothoSonic.bootConfig = config;
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
    # Last-wins on changed bytes: saved outputs from older sessions run
    # first on page load, and a first-wins merge would pin their stale
    # synthdef builds for the page's lifetime — every later widget then
    # d_recv's the old bytes no matter what the kernel rendered (this hid
    # the stepped __klEnvCtrl fix behind the old interpolating build).
    # When an asset's bytes change, the name is also dropped from the
    # loaded-defs registry so the next loadDefs re-sends /d_recv, which
    # replaces the def server-side.
    return f"""(function() {{
    var _r = globalThis.__klothoSynthdefAssets = globalThis.__klothoSynthdefAssets || {{}};
    var _new = {assets_json};
    var _st = globalThis.__klothoSonic;
    for (var k in _new) {{
        if (!_new.hasOwnProperty(k)) continue;
        if (_r[k] !== _new[k]) {{
            _r[k] = _new[k];
            if (_st && _st.loadedDefs) _st.loadedDefs.delete(k);
        }}
    }}
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


def control_bar_html(wid, record=False, stems=False):
    """Playback control bar. The play button renders disabled and greyed
    out; the widget controller enables it via ``KlothoGateToggle`` when
    the engine-ready warm-up settles.

    ``record=True`` inserts a record button between play and loop (plus a
    hidden download-link container); ``stems=True`` (Score payloads with
    registered tracks) additionally appends a "stems" checkbox. Widget
    controllers key off element presence, so the defaults keep existing
    call sites byte-identical.
    """
    record_html = f'''
    <button id="{wid}_rec" disabled title="Record" style="
        width: 28px;
        height: 28px;
        border: none;
        border-radius: 4px;
        background: #16213e;
        cursor: not-allowed;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        opacity: 0.3;
    ">
        <svg id="{wid}_rec_svg" width="14" height="14" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="8" fill="#ef4444"></circle>
        </svg>
    </button>''' if record else ''
    stems_html = f'''
    <label style="display:inline-flex;align-items:center;gap:3px;margin-left:2px;cursor:pointer;">
        <input id="{wid}_stems" type="checkbox" style="
            width:13px;height:13px;accent-color:#ef4444;cursor:pointer;margin:0;">
        <span style="color:#a0a0a0;font-size:11px;">stems</span>
    </label>''' if record and stems else ''
    download_html = f'''
    <span id="{wid}_dl" style="display:none;align-items:center;"></span>''' if record else ''
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
    <button id="{wid}_toggle" disabled style="
        width: 32px;
        height: 32px;
        border: none;
        border-radius: 4px;
        background: #16213e;
        cursor: not-allowed;
        opacity: 0.3;
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
    </button>{record_html}
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
    </button>{stems_html}{download_html}
</div>'''
