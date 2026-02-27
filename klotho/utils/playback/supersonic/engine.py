import json
import uuid
import base64
from pathlib import Path

from IPython.display import HTML, display

from klotho.utils.playback.supersonic.cdn import (
    SUPERSONIC_CDN,
    SUPERSONIC_CORE_CDN,
    SUPERSONIC_SYNTHDEFS_CDN,
    SUPERSONIC_SAMPLES_CDN,
    SCHEDULER_JS_PATH,
    DRAW_JS_PATH,
)

MANIFEST_PATH = Path(__file__).parent / "assets" / "manifest.json"
SYNTHDEFS_DIR = Path(__file__).parent / "assets" / "synthdefs"


def _convert_numpy_types(obj):
    try:
        import numpy as np
        if isinstance(obj, dict):
            return {k: _convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_convert_numpy_types(v) for v in obj]
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        else:
            return obj
    except ImportError:
        return obj


def _load_manifest():
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {"synths": {}, "inserts": {}}


def _load_synthdef_assets():
    assets = {}
    if SYNTHDEFS_DIR.exists():
        for path in SYNTHDEFS_DIR.glob("*.scsyndef"):
            name = path.stem
            assets[name] = base64.b64encode(path.read_bytes()).decode("ascii")
    return assets


class SuperSonicEngine:
    def __init__(self, events):
        self.events = _convert_numpy_types(events)
        self.widget_id = f"klotho_ss_{uuid.uuid4().hex[:8]}"
        self.manifest = _load_manifest()
        self.synthdef_assets = _load_synthdef_assets()

    def _load_draw_js(self):
        return DRAW_JS_PATH.read_text()

    def _load_scheduler_js(self):
        return SCHEDULER_JS_PATH.read_text()

    def _needed_synthdefs(self):
        names = set()
        for ev in self.events:
            if ev.get("type") == "new" and ev.get("synthName"):
                name = ev["synthName"]
                if name != "__rest__":
                    names.add(name)
        return names

    def _generate_html(self):
        events_json = json.dumps(self.events)
        manifest_json = json.dumps(self.manifest)
        synthdef_assets_json = json.dumps(self.synthdef_assets)
        needed = self._needed_synthdefs()

        config_json = json.dumps({
            "baseURL": f"{SUPERSONIC_CDN}/dist/",
            "coreBaseURL": SUPERSONIC_CORE_CDN,
            "synthdefBaseURL": SUPERSONIC_SYNTHDEFS_CDN,
            "sampleBaseURL": SUPERSONIC_SAMPLES_CDN,
        })

        draw_js = self._load_draw_js()
        scheduler_js = self._load_scheduler_js()

        needed_json = json.dumps(list(needed))
        wid = self.widget_id

        html = f'''
<div id="{wid}" style="
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
    </button>
    <span id="{wid}_status" style="
        color: #666;
        font-size: 10px;
        min-width: 60px;
    ">ready</span>
</div>

<script>
{draw_js}

{scheduler_js}

(function __klothoSSInit_{wid}() {{
    var wid = "{wid}";
    var toggleBtn = document.getElementById(wid + "_toggle");
    if (!toggleBtn) {{
        setTimeout(__klothoSSInit_{wid}, 50);
        return;
    }}
    var iconEl = document.getElementById(wid + "_icon");
    var loopBtn = document.getElementById(wid + "_loop");
    var loopSvg = document.getElementById(wid + "_loop_svg");
    var statusEl = document.getElementById(wid + "_status");
    var allEvents = {events_json};
    var manifest = {manifest_json};
    var synthdefAssets = {synthdef_assets_json};
    var neededSynthdefs = {needed_json};
    var ssConfig = {config_json};

    var looping = false;
    var scheduler = null;
    var ready = false;
    var _loadPromise = null;

    function setPlayIcon() {{
        iconEl.style.cssText =
            "width:0;height:0;border-top:7px solid transparent;"
            + "border-bottom:7px solid transparent;border-left:12px solid #4ade80;"
            + "border-right:none;margin-left:3px;background:none";
    }}

    function setStopIcon() {{
        iconEl.style.cssText =
            "width:12px;height:12px;border:none;border-radius:2px;"
            + "margin-left:0;background:#ef4444";
    }}

    loopBtn.onclick = function() {{
        looping = !looping;
        loopBtn.style.opacity = looping ? "1" : "0.5";
        loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0");
    }};

    function ensureSharedSonic() {{
        var state = globalThis.__klothoSonic;
        if (state && state.instance) return Promise.resolve(state.instance);
        if (state && state.promise) return state.promise;
        state = {{ instance: null, promise: null, loadedDefs: new Set() }};
        globalThis.__klothoSonic = state;
        state.promise = (async function() {{
            try {{
                var mod = await import("{SUPERSONIC_CDN}");
                globalThis.SuperSonic = mod.SuperSonic;
                var s = new mod.SuperSonic(ssConfig);
                await s.init();
                state.instance = s;
                return s;
            }} catch(e) {{
                return null;
            }}
        }})();
        return state.promise;
    }}

    async function loadDefs(sonic) {{
        var loaded = globalThis.__klothoSonic.loadedDefs;
        for (var name in synthdefAssets) {{
            if (!synthdefAssets.hasOwnProperty(name)) continue;
            if (loaded.has(name)) continue;
            var b64 = synthdefAssets[name];
            var bytes = Uint8Array.from(atob(b64), function(c) {{ return c.charCodeAt(0); }});
            await sonic.loadSynthDef(bytes);
            loaded.add(name);
        }}
        for (var i = 0; i < neededSynthdefs.length; i++) {{
            var sname = neededSynthdefs[i];
            if (loaded.has(sname)) continue;
            if (synthdefAssets[sname]) continue;
            try {{
                await sonic.loadSynthDef(sname);
                loaded.add(sname);
            }} catch(e) {{}}
        }}
    }}

    function ensureReady() {{
        if (ready) return Promise.resolve(true);
        if (_loadPromise) return _loadPromise;
        _loadPromise = (async function() {{
            var sonic = await ensureSharedSonic();
            if (!sonic) {{
                _loadPromise = null;
                statusEl.textContent = "error";
                statusEl.style.color = "#ef4444";
                return false;
            }}
            await loadDefs(sonic);
            scheduler = new BrowserScheduler({{
                sonic: sonic,
                manifest: manifest,
            }});
            ready = true;
            statusEl.textContent = "ready";
            statusEl.style.color = "#4ade80";
            return true;
        }})();
        return _loadPromise;
    }}

    statusEl.textContent = "loading...";
    statusEl.style.color = "#f0ad4e";
    ensureReady();

    function doPlay(skipStop) {{
        var evts = allEvents;
        if (evts.length === 0) return;

        setStopIcon();
        statusEl.textContent = "playing";
        statusEl.style.color = "#4ade80";

        scheduler.play(evts, {{
            _skipStop: !!skipStop,
            onFinish: function() {{
                if (looping) {{
                    doPlay(true);
                }} else {{
                    setPlayIcon();
                    statusEl.textContent = "ready";
                    statusEl.style.color = "#4ade80";
                }}
            }}
        }});
    }}

    toggleBtn.onclick = async function() {{
        if (scheduler && scheduler.isPlaying) {{
            await scheduler.stop();
            setPlayIcon();
            statusEl.textContent = "ready";
            statusEl.style.color = "#4ade80";
            return;
        }}
        var ok = await ensureReady();
        if (!ok) return;
        var sonic = globalThis.__klothoSonic.instance;
        if (sonic.audioContext && sonic.audioContext.state === "suspended") {{
            await sonic.audioContext.resume();
        }}
        doPlay(false);
    }};
}})();
</script>
'''
        return html

    def display(self):
        html = self._generate_html()
        return display(HTML(html))

    def _repr_html_(self):
        return self._generate_html()
