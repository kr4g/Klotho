import base64
import json
from pathlib import Path

from klotho.utils.playback.tonejs.cdn import cdn_scripts

_booted = False
_SS_MANIFEST_PATH = Path(__file__).resolve().parent / "supersonic" / "assets" / "manifest.json"
_SS_SYNTHDEFS_DIR = Path(__file__).resolve().parent / "supersonic" / "assets" / "synthdefs"


def boot_supersonic():
    global _booted
    if _booted:
        return

    from ._config import get_audio_engine
    if get_audio_engine() != "supersonic":
        return

    try:
        get_ipython()
    except NameError:
        return

    _booted = True

    import json
    from IPython.display import display, HTML
    from .supersonic.cdn import (
        SUPERSONIC_CDN,
        SUPERSONIC_CORE_CDN,
        SUPERSONIC_SYNTHDEFS_CDN,
        SUPERSONIC_SAMPLES_CDN,
    )

    config = json.dumps({
        "baseURL": f"{SUPERSONIC_CDN}/dist/",
        "coreBaseURL": SUPERSONIC_CORE_CDN,
        "synthdefBaseURL": SUPERSONIC_SYNTHDEFS_CDN,
        "sampleBaseURL": SUPERSONIC_SAMPLES_CDN,
    })

    boot_js = f"""<script>
if (!globalThis.__klothoSonic) {{
    globalThis.__klothoSonic = {{ instance: null, promise: null, loadedDefs: new Set() }};
    globalThis.__klothoSonic.promise = (async function() {{
        try {{
            var config = {config};
            var mod = await import("{SUPERSONIC_CDN}");
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
</script>"""
    display(HTML(boot_js))


def _load_manifest_json():
    if _SS_MANIFEST_PATH.exists():
        return _SS_MANIFEST_PATH.read_text()
    return '{"synths": {}, "inserts": {}}'


def _load_synthdef_assets_json():
    assets = {}
    if _SS_SYNTHDEFS_DIR.exists():
        for path in _SS_SYNTHDEFS_DIR.glob("*.scsyndef"):
            assets[path.stem] = base64.b64encode(path.read_bytes()).decode("ascii")
    return json.dumps(assets)


def build_supersonic_session_preamble(include_plotly=False, include_threejs=False):
    from .supersonic.cdn import (
        SUPERSONIC_CDN,
        SUPERSONIC_CORE_CDN,
        SUPERSONIC_SYNTHDEFS_CDN,
        SUPERSONIC_SAMPLES_CDN,
        DRAW_JS_PATH,
        SCHEDULER_JS_PATH,
    )

    ss_config = json.dumps({
        "baseURL": f"{SUPERSONIC_CDN}/dist/",
        "coreBaseURL": SUPERSONIC_CORE_CDN,
        "synthdefBaseURL": SUPERSONIC_SYNTHDEFS_CDN,
        "sampleBaseURL": SUPERSONIC_SAMPLES_CDN,
    })

    draw_js = DRAW_JS_PATH.read_text() if DRAW_JS_PATH.exists() else ""
    sched_js = SCHEDULER_JS_PATH.read_text() if SCHEDULER_JS_PATH.exists() else ""

    cdn_html = cdn_scripts(
        include_plotly=include_plotly,
        include_tone=False,
        include_threejs=include_threejs,
    )

    manifest_json = _load_manifest_json()
    synthdef_assets_json = _load_synthdef_assets_json()

    ss_boot_js = f'''
var __ssConfig = {ss_config};
var __klothoManifest = {manifest_json};
var __klothoSynthdefAssets = {synthdef_assets_json};
async function __loadKlothoSynthdefsOnce(sonic, state) {{
    var loaded = state.loadedDefs || new Set();
    for (var name in __klothoSynthdefAssets) {{
        if (!__klothoSynthdefAssets.hasOwnProperty(name)) continue;
        if (loaded.has(name)) continue;
        var b64 = __klothoSynthdefAssets[name];
        var bytes = Uint8Array.from(atob(b64), function(c) {{ return c.charCodeAt(0); }});
        try {{
            await sonic.loadSynthDef(bytes);
            loaded.add(name);
        }} catch(e) {{}}
    }}
    state.loadedDefs = loaded;
}}
if (!globalThis.__ensureSuperSonic) {{
    globalThis.__ensureSuperSonic = function() {{
        var state = globalThis.__klothoSonic;
        if (state && state.instance) {{
            return __loadKlothoSynthdefsOnce(state.instance, state).then(function() {{
                return state.instance;
            }});
        }}
        if (state && state.promise) {{
            return state.promise.then(function(sonic) {{
                if (!sonic) return sonic;
                return __loadKlothoSynthdefsOnce(sonic, state).then(function() {{
                    return sonic;
                }});
            }});
        }}
        if (!state) {{
            state = {{ instance: null, promise: null, loadedDefs: new Set() }};
            globalThis.__klothoSonic = state;
        }}
        state.promise = (async function() {{
            try {{
                var mod = await import("{SUPERSONIC_CDN}");
                globalThis.SuperSonic = mod.SuperSonic;
                var sonic = new mod.SuperSonic(__ssConfig);
                await sonic.init();
                await __loadKlothoSynthdefsOnce(sonic, state);
                state.instance = sonic;
                return sonic;
            }} catch(e) {{
                state.promise = null;
                return null;
            }}
        }})();
        return state.promise;
    }};
}}
var __ensureSuperSonic = globalThis.__ensureSuperSonic;
__ensureSuperSonic();
'''
    return cdn_html, ss_boot_js + "\n" + draw_js + "\n" + sched_js, ""
