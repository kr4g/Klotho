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
            try {{ await sonic.loadSynthDef("sonic-pi-beep"); }} catch(e) {{}}
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
