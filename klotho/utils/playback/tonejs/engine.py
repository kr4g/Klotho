import json
import uuid
from pathlib import Path
from IPython.display import HTML, display

_TONEJS_CDN = "https://unpkg.com/tone@14.7.77/build/Tone.js"
_INSTRUMENTS_JS_PATH = Path(__file__).parent / "instruments.js"
_PLAYER_JS_PATH = Path(__file__).parent / "player.js"

_tone_included = False
_KERNEL_SESSION = uuid.uuid4().hex


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

    def _load_player_js(self):
        return _PLAYER_JS_PATH.read_text()

    def _load_user_custom_js(self):
        if self.custom_js_path and self.custom_js_path.exists():
            return self.custom_js_path.read_text()
        if self.custom_js:
            return self.custom_js
        return ""

    def _generate_html(self):
        global _tone_included
        payload_json = json.dumps(self.events)
        user_custom_js = self._load_user_custom_js()
        instruments_js = self._load_instruments_js()
        player_js = self._load_player_js()
        scripts = "\n".join([s for s in (user_custom_js, instruments_js, player_js) if s])

        if not _tone_included:
            tone_script = f'<script src="{_TONEJS_CDN}"></script>'
            _tone_included = True
        else:
            tone_script = ''

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

{tone_script}
<script>globalThis._KLOTHO_SESSION = "{_KERNEL_SESSION}";</script>
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
    const events = payload.events || [];
    const instruments = globalThis.KLOTHO_BUILD_INSTRUMENTS(payload.instruments || {{}});
    const player = KlothoPlayer.create();

    let looping = false;

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

    loopBtn.onclick = () => {{
        looping = !looping;
        loopBtn.style.opacity = looping ? "1" : "0.5";
        loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0");
    }};

    toggleBtn.onclick = async () => {{
        if (player.isPlaying()) {{
            player.stop();
            setPlayIcon();
        }} else {{
            setStopIcon();
            await player.play(events, instruments, {{
                loop: looping,
                onFinish: () => setPlayIcon()
            }});
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
