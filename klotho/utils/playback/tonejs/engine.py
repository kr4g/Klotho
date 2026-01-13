import json
import uuid
from IPython.display import HTML, display

_TONEJS_CDN = "https://unpkg.com/tone@14.7.77/build/Tone.js"


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
    def __init__(self, events):
        self.events = _convert_numpy_types(events)
        self.widget_id = f"klotho_{uuid.uuid4().hex[:8]}"
    
    def _generate_html(self):
        events_json = json.dumps(self.events)
        
        html = f'''
<div id="{self.widget_id}" style="
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: #1a1a2e;
    border-radius: 6px;
    user-select: none;
">
    <button id="{self.widget_id}_play" style="
        padding: 4px 12px;
        border: none;
        border-radius: 4px;
        background: #16213e;
        color: #e94560;
        cursor: pointer;
        font-size: 12px;
    ">Play</button>
    <button id="{self.widget_id}_stop" style="
        padding: 4px 12px;
        border: none;
        border-radius: 4px;
        background: #16213e;
        color: #e94560;
        cursor: pointer;
        font-size: 12px;
    ">Stop</button>
    <span id="{self.widget_id}_status" style="
        font-size: 11px;
        color: #a0a0a0;
        margin-left: 8px;
    ">ready</span>
</div>

<script src="{_TONEJS_CDN}"></script>
<script>
(() => {{
    const playBtn = document.getElementById("{self.widget_id}_play");
    const stopBtn = document.getElementById("{self.widget_id}_stop");
    const statusEl = document.getElementById("{self.widget_id}_status");
    const events = {events_json};
    
    let scheduledIds = [];
    let instruments = null;

    function clearSchedule() {{
        for (const id of scheduledIds) Tone.Transport.clear(id);
        scheduledIds = [];
        Tone.Transport.cancel(0);
    }}

    function disposeInstruments() {{
        if (!instruments) return;
        for (const k of Object.keys(instruments.instances)) {{
            const inst = instruments.instances[k];
            if (inst && inst.releaseAll) {{ try {{ inst.releaseAll(); }} catch(_) {{}} }}
            if (inst && inst.dispose) {{ try {{ inst.dispose(); }} catch(_) {{}} }}
        }}
        if (instruments.master && instruments.master.dispose) {{ try {{ instruments.master.dispose(); }} catch(_) {{}} }}
        instruments = null;
    }}

    function buildInstruments() {{
        const master = new Tone.Gain(0.9).toDestination();
        const instances = {{}};
        
        instances.synth = new Tone.PolySynth(Tone.Synth, {{
            maxPolyphony: 16,
            options: {{
                oscillator: {{ type: "triangle" }},
                envelope: {{ attack: 0.01, decay: 0.08, sustain: 0.25, release: 0.20 }}
            }}
        }});
        instances.synth.connect(master);
        
        instances.sine = new Tone.PolySynth(Tone.Synth, {{
            maxPolyphony: 32,
            options: {{
                oscillator: {{ type: "sine" }},
                envelope: {{ attack: 0.05, decay: 0.2, sustain: 0.5, release: 0.8 }}
            }}
        }});
        instances.sine.connect(master);
        
        instances.membrane = new Tone.MembraneSynth({{
            pitchDecay: 0.008,
            octaves: 7,
            envelope: {{ attack: 0.001, decay: 0.10, sustain: 0.0, release: 0.02 }}
        }});
        instances.membrane.connect(master);
        
        return {{ master, instances }};
    }}

    function triggerEvent(ev, time) {{
        if (!instruments) return;
        const inst = instruments.instances[ev.instrument];
        if (!inst) return;
        
        const pfields = ev.pfields || {{}};
        const freq = pfields.freq || 440;
        const vel = Math.max(0, Math.min(1, pfields.vel || 0.6));
        
        inst.triggerAttackRelease(freq, ev.duration, time, vel);
    }}

    async function hardStop() {{
        try {{ Tone.Transport.stop(); }} catch (_) {{}}
        try {{ Tone.Transport.position = 0; }} catch (_) {{}}
        try {{ clearSchedule(); }} catch (_) {{}}
        try {{ disposeInstruments(); }} catch (_) {{}}
    }}

    stopBtn.onclick = async () => {{
        await hardStop();
        statusEl.textContent = "stopped";
    }};

    playBtn.onclick = async () => {{
        // Ensure audio context is running - this is the key for local Jupyter
        if (Tone.context.state !== "running") {{
            await Tone.context.resume();
        }}
        await Tone.start();
        
        await hardStop();

        instruments = buildInstruments();

        for (const ev of events) {{
            const id = Tone.Transport.schedule((time) => triggerEvent(ev, time), ev.start);
            scheduledIds.push(id);
        }}

        const end = Math.max(...events.map(e => e.start + e.duration)) + 0.5;
        const stopId = Tone.Transport.schedule(async () => {{
            await hardStop();
            statusEl.textContent = "finished";
        }}, end);
        scheduledIds.push(stopId);

        statusEl.textContent = "playing";
        Tone.Transport.start("+0.05");
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
