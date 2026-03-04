import json
import uuid
import base64
from pathlib import Path

from IPython.display import HTML, display

from klotho.utils.playback.supersonic.cdn import supersonic_config
from klotho.utils.playback._helpers import convert_numpy_types
from klotho.utils.playback.supersonic._js_fragments import (
    ss_init_js, draw_scheduler_js, scheduler_core_js, scheduler_score_js,
    synthdef_registry_merge_js, control_bar_html,
)

SYNTHDEFS_DIR = Path(__file__).parent / "assets" / "synthdefs"
_WIDGET_JS_PATH = Path(__file__).parent / "_engine_widget.js"
_WIDGET_JS_TEMPLATE = None
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


def _load_widget_template():
    global _WIDGET_JS_TEMPLATE
    if _WIDGET_JS_TEMPLATE is None:
        _WIDGET_JS_TEMPLATE = _WIDGET_JS_PATH.read_text()
    return _WIDGET_JS_TEMPLATE


class SuperSonicEngine:
    def __init__(self, events, meta=None, control_data=None, ring_time=5):
        self.events = convert_numpy_types(events)
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
        config_json = json.dumps(supersonic_config())
        wid = self.widget_id
        meta_json = json.dumps(self.meta)
        control_data_json = json.dumps(self._serialize_control_data())

        widget_js = (_load_widget_template()
                     .replace('__WID__', wid)
                     .replace('__EVENTS_JSON__', events_json)
                     .replace('__NEEDED_JSON__', needed_json)
                     .replace('__SS_CONFIG_JSON__', config_json)
                     .replace('__META_JSON__', meta_json)
                     .replace('__CONTROL_DATA_JSON__', control_data_json)
                     .replace('__RING_TIME__', str(self.ring_time)))

        score_js = scheduler_score_js() if self._is_score else ""

        bar_html = control_bar_html(wid, show_status=True)

        html = f'''
{bar_html}

<script type="module">
{ss_init_js()}
{draw_scheduler_js()}
{scheduler_core_js()}
{score_js}
{synthdef_registry_merge_js(synthdef_assets_json)}
{widget_js}
</script>
'''
        return html

    def display(self):
        html = self._generate_html()
        return display(HTML(html))

    def _repr_html_(self):
        return self._generate_html()
