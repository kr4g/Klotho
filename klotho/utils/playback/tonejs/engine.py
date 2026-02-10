import json
import uuid
from pathlib import Path
from IPython.display import HTML, display

_TONEJS_CDN = "https://unpkg.com/tone@14.7.77/build/Tone.js"
_INSTRUMENTS_JS_PATH = Path(__file__).parent / "instruments.js"


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


class ToneEngine:
    def __init__(self, events, custom_js_path=None, custom_js=None):
        self.events = _convert_numpy_types(events)
        self.custom_js_path = Path(custom_js_path) if custom_js_path else None
        self.custom_js = custom_js
        self.widget_id = f"klotho_{uuid.uuid4().hex[:8]}"
    
    def _load_instruments_js(self):
        return _INSTRUMENTS_JS_PATH.read_text()

    def _load_user_custom_js(self):
        if self.custom_js_path and self.custom_js_path.exists():
            return self.custom_js_path.read_text()
        if self.custom_js:
            return self.custom_js
        return ""
    
    def _generate_html(self):
        payload_json = json.dumps(self.events)
        user_custom_js = self._load_user_custom_js()
        instruments_js = self._load_instruments_js()
        scripts = "\n".join([s for s in (user_custom_js, instruments_js) if s])
        
        html = f'''
<div id="{self.widget_id}" style="
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: #1a1a2e;
    border-radius: 6px;
    user-select: none;
">
    <button id="{self.widget_id}_toggle" style="
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
        <span id="{self.widget_id}_icon" style="
            width: 0;
            height: 0;
            border-top: 7px solid transparent;
            border-bottom: 7px solid transparent;
            border-left: 12px solid #4ade80;
            margin-left: 3px;
        "></span>
    </button>
    <button id="{self.widget_id}_loop" style="
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
        <svg id="{self.widget_id}_loop_svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a0a0a0" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 2l4 4-4 4"></path>
            <path d="M3 11v-1a4 4 0 0 1 4-4h14"></path>
            <path d="M7 22l-4-4 4-4"></path>
            <path d="M21 13v1a4 4 0 0 1-4 4H3"></path>
        </svg>
    </button>
</div>

<script src="{_TONEJS_CDN}"></script>
<script>
{scripts}
</script>
<script>
(() => {{
    const toggleBtn = document.getElementById("{self.widget_id}_toggle");
    const iconEl = document.getElementById("{self.widget_id}_icon");
    const loopBtn = document.getElementById("{self.widget_id}_loop");
    const loopSvg = document.getElementById("{self.widget_id}_loop_svg");
    const payload = {payload_json};
    const events = Array.isArray(payload) ? payload : (payload.events || []);
    const instrumentMap = Array.isArray(payload) ? null : (payload.instruments || null);
    const KLOTHO_INSTRUMENTS = globalThis.KLOTHO_BUILD_INSTRUMENTS(instrumentMap);
    
    let session = 0;
    let currentGain = null;
    let stopTimer = null;
    let playing = false;
    let looping = false;
    
    const orphaned = [];

    function setPlayIcon() {{
        iconEl.style.width = "0";
        iconEl.style.height = "0";
        iconEl.style.borderTop = "7px solid transparent";
        iconEl.style.borderBottom = "7px solid transparent";
        iconEl.style.borderLeft = "12px solid #4ade80";
        iconEl.style.borderRight = "none";
        iconEl.style.marginLeft = "3px";
        iconEl.style.background = "none";
    }}

    function setStopIcon() {{
        iconEl.style.width = "12px";
        iconEl.style.height = "12px";
        iconEl.style.border = "none";
        iconEl.style.borderRadius = "2px";
        iconEl.style.marginLeft = "0";
        iconEl.style.background = "#ef4444";
    }}
    
    function cleanupOld() {{
        const now = Date.now();
        while (orphaned.length > 0 && now - orphaned[0].time > 1000) {{
            const old = orphaned.shift();
            try {{ old.part.stop(); }} catch(_) {{}}
            try {{ old.part.dispose(); }} catch(_) {{}}
            for (const k in old.insts) {{ try {{ old.insts[k].dispose(); }} catch(_) {{}} }}
            try {{ old.gain.dispose(); }} catch(_) {{}}
        }}
    }}

    function deepClone(obj) {{
        return obj && typeof obj === "object" ? JSON.parse(JSON.stringify(obj)) : obj;
    }}

    function stripNoteFields(pf) {{
        const out = {{}};
        for (const k in pf) {{
            if (k === "freq" || k === "vel" || k === "amp") continue;
            out[k] = pf[k];
        }}
        return out;
    }}

    function diffParams(next, current) {{
        const diff = {{}};
        for (const k in next) {{
            const nv = next[k];
            const cv = current ? current[k] : undefined;
            if (nv && typeof nv === "object" && !Array.isArray(nv)) {{
                if (!cv || typeof cv !== "object" || Array.isArray(cv)) {{
                    diff[k] = deepClone(nv);
                }} else {{
                    const child = diffParams(nv, cv);
                    if (Object.keys(child).length) diff[k] = child;
                }}
            }} else if (Array.isArray(nv)) {{
                if (!Array.isArray(cv) || JSON.stringify(nv) !== JSON.stringify(cv)) {{
                    diff[k] = deepClone(nv);
                }}
            }} else {{
                if (nv !== cv) diff[k] = nv;
            }}
        }}
        return diff;
    }}

    function stop() {{
        session++;
        playing = false;
        if (stopTimer) {{ clearTimeout(stopTimer); stopTimer = null; }}
        if (currentGain) {{ try {{ currentGain.gain.rampTo(0, 0.01); }} catch(_) {{}} }}
        setPlayIcon();
    }}

    async function play() {{
        cleanupOld();
        
        session++;
        const mySession = session;
        playing = true;
        setStopIcon();
        
        try {{
            await Tone.start();
            if (Tone.context.state !== "running") await Tone.context.resume();
        }} catch(e) {{
            playing = false;
            setPlayIcon();
            return;
        }}
        
        if (session !== mySession) return;
        
        if (Tone.Transport.state !== "started") Tone.Transport.start();

        const myGain = new Tone.Gain(0.85).toDestination();
        currentGain = myGain;
        const myInsts = {{}};
        const currentParams = {{}};
        for (const name of Object.keys(KLOTHO_INSTRUMENTS)) {{
            const spec = KLOTHO_INSTRUMENTS[name];
            myInsts[name] = spec.create();
            myInsts[name].connect(myGain);
            currentParams[name] = deepClone(spec.preset || {{}});
        }}

        const end = events.length ? Math.max(...events.map(e => e.start + e.duration)) : 0;

        const myPart = new Tone.Part((time, ev) => {{
            if (session !== mySession) return;
            const spec = KLOTHO_INSTRUMENTS[ev.instrument];
            const inst = myInsts[ev.instrument];
            if (!spec || !inst) return;
            const pf = ev.pfields || {{}};
            const vel = pf.vel ?? pf.amp ?? (spec.defaults && spec.defaults.vel !== undefined ? spec.defaults.vel : 0.6);
            const freq = pf.freq ?? (spec.defaults && spec.defaults.freq !== undefined ? spec.defaults.freq : 440);
            if (spec.custom) {{
                try {{ spec.trigger(inst, freq, Math.max(0.01, ev.duration), time, Math.max(0, Math.min(1, vel)), pf); }} catch(_) {{}}
                return;
            }}
            const desired = stripNoteFields(pf);
            const current = currentParams[ev.instrument] || {{}};
            const delta = diffParams(desired, current);
            if (Object.keys(delta).length) {{
                try {{ inst.set(delta); }} catch(_) {{}}
                currentParams[ev.instrument] = deepClone(desired);
            }}
            try {{ spec.trigger(inst, freq, Math.max(0.01, ev.duration), time, Math.max(0, Math.min(1, vel))); }} catch(_) {{}}
        }}, events.map(ev => [ev.start, ev]));

        orphaned.push({{ part: myPart, insts: myInsts, gain: myGain, time: Date.now() }});

        if (looping) {{
            myPart.loop = true;
            myPart.loopStart = 0;
            myPart.loopEnd = end;
        }} else {{
            myPart.loop = false;
            stopTimer = setTimeout(() => {{ if (session === mySession) stop(); }}, (end + 0.5) * 1000);
        }}

        myPart.start("+0.05");
    }}

    loopBtn.onclick = () => {{
        looping = !looping;
        loopBtn.style.opacity = looping ? "1" : "0.5";
        loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0");
    }};

    toggleBtn.onclick = async () => {{
        if (playing) {{
            stop();
        }} else {{
            await play();
        }}
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
