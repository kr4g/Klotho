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
)

SYNTHDEFS_DIR = Path(__file__).parent / "assets" / "synthdefs"
_WIDGET_JS_PATH = Path(__file__).parent / "_engine_widget.js"
_SCHED_SCORE_PATH = Path(__file__).parent / "scheduler_score.js"
_WIDGET_JS_TEMPLATE = None
_SCHED_SCORE_JS = None
_ALL_SYNTHDEF_ASSETS = None

_INFRA_SYNTHDEFS = frozenset({'__busRouter', '__busRouterMonitor', '__chainLimiter'})


def _load_all_synthdef_assets():
    global _ALL_SYNTHDEF_ASSETS
    if _ALL_SYNTHDEF_ASSETS is None:
        assets = {}
        if SYNTHDEFS_DIR.exists():
            for path in SYNTHDEFS_DIR.glob("*.scsyndef"):
                assets[path.stem] = base64.b64encode(path.read_bytes()).decode("ascii")
        if "default" not in assets and "kl_tri" in assets:
            assets["default"] = assets["kl_tri"]
        _ALL_SYNTHDEF_ASSETS = assets
    return _ALL_SYNTHDEF_ASSETS


def _filter_synthdef_assets(all_assets, needed):
    filtered = {}
    for name in needed | _INFRA_SYNTHDEFS:
        if name in all_assets:
            filtered[name] = all_assets[name]
    if "default" not in filtered and "kl_tri" in all_assets:
        filtered["default"] = all_assets["kl_tri"]
    return filtered


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


def _load_widget_template():
    global _WIDGET_JS_TEMPLATE
    if _WIDGET_JS_TEMPLATE is None:
        _WIDGET_JS_TEMPLATE = _WIDGET_JS_PATH.read_text()
    return _WIDGET_JS_TEMPLATE


def _load_scheduler_score():
    global _SCHED_SCORE_JS
    if _SCHED_SCORE_JS is None:
        _SCHED_SCORE_JS = _SCHED_SCORE_PATH.read_text() if _SCHED_SCORE_PATH.exists() else ""
    return _SCHED_SCORE_JS


class SuperSonicEngine:
    def __init__(self, events, meta=None, control_data=None, ring_time=5):
        self.events = _convert_numpy_types(events)
        self.meta = meta or {}
        self.control_data = control_data or {"buffer": None, "blockSize": 512, "descriptors": []}
        self.ring_time = ring_time
        self.widget_id = f"klotho_ss_{uuid.uuid4().hex[:8]}"
        from klotho.utils.playback._sc_validate import validate_sc_events, validate_sc_meta
        validate_sc_events(self.events)
        if self.meta:
            validate_sc_meta(self.meta)
        self._needed = self._needed_synthdefs() | _INFRA_SYNTHDEFS
        self.synthdef_assets = _filter_synthdef_assets(_load_all_synthdef_assets(), self._needed)
        self._is_score = bool(self.meta.get("groups") or self.meta.get("inserts"))

    def _needed_synthdefs(self):
        names = set()
        for ev in self.events:
            if ev.get("type") == "new" and ev.get("defName"):
                name = ev["defName"]
                if name != "__rest__":
                    names.add(name)
        for track_inserts in self.meta.get("inserts", {}).values():
            for ins in track_inserts:
                dn = ins.get("defName")
                if dn:
                    names.add(dn)
        if self.control_data.get("descriptors"):
            names.add("__klEnvCtrl")
        return names

    def _serialize_control_data(self):
        cd = self.control_data
        result = {"blockSize": cd.get("blockSize", 512), "descriptors": cd.get("descriptors", []), "bufferB64": None, "numFrames": 0}
        buf = cd.get("buffer")
        if buf is not None:
            result["bufferB64"] = base64.b64encode(buf.tobytes()).decode("ascii")
            result["numFrames"] = len(buf)
        return result

    def _generate_html(self):
        events_json = json.dumps(self.events)
        synthdef_assets_json = json.dumps(self.synthdef_assets)
        needed_json = json.dumps(list(self._needed))

        config_json = json.dumps({
            "baseURL": f"{SUPERSONIC_CDN}/dist/",
            "coreBaseURL": SUPERSONIC_CORE_CDN,
            "synthdefBaseURL": SUPERSONIC_SYNTHDEFS_CDN,
            "sampleBaseURL": SUPERSONIC_SAMPLES_CDN,
        })

        wid = self.widget_id

        meta_json = json.dumps(self.meta)
        control_data_json = json.dumps(self._serialize_control_data())

        widget_js = (_load_widget_template()
                     .replace('__WID__', wid)
                     .replace('__EVENTS_JSON__', events_json)
                     .replace('__SYNTHDEF_ASSETS_JSON__', synthdef_assets_json)
                     .replace('__NEEDED_JSON__', needed_json)
                     .replace('__SS_CONFIG_JSON__', config_json)
                     .replace('__META_JSON__', meta_json)
                     .replace('__CONTROL_DATA_JSON__', control_data_json)
                     .replace('__RING_TIME__', str(self.ring_time)))

        score_js = _load_scheduler_score() if self._is_score else ""

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
{score_js}
{widget_js}
</script>
'''
        return html

    def display(self):
        html = self._generate_html()
        return display(HTML(html))

    def _repr_html_(self):
        return self._generate_html()
