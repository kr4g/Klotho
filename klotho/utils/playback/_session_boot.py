import json
from pathlib import Path

from klotho.utils.playback.tonejs.cdn import cdn_scripts

_booted = False


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

    from IPython.display import display, HTML
    from .supersonic.cdn import (
        SUPERSONIC_CDN,
        SUPERSONIC_CORE_CDN,
        SUPERSONIC_SYNTHDEFS_CDN,
        SUPERSONIC_SAMPLES_CDN,
        DRAW_JS_PATH,
    )

    _SCHED_CORE_PATH = Path(__file__).resolve().parent / "supersonic" / "scheduler_core.js"

    config = json.dumps({
        "baseURL": f"{SUPERSONIC_CDN}/dist/",
        "coreBaseURL": SUPERSONIC_CORE_CDN,
        "synthdefBaseURL": SUPERSONIC_SYNTHDEFS_CDN,
        "sampleBaseURL": SUPERSONIC_SAMPLES_CDN,
    })

    draw_js = DRAW_JS_PATH.read_text() if DRAW_JS_PATH.exists() else ""
    sched_core_js = _SCHED_CORE_PATH.read_text() if _SCHED_CORE_PATH.exists() else ""

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
}}
{draw_js}
{sched_core_js}
</script>"""
    display(HTML(boot_js))


def build_supersonic_session_preamble(include_plotly=False, include_threejs=False):
    cdn_html = cdn_scripts(
        include_plotly=include_plotly,
        include_tone=False,
        include_threejs=include_threejs,
    )
    return cdn_html, "", ""
