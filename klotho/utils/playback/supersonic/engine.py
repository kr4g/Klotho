import json
import uuid
import base64
from pathlib import Path

from IPython.display import HTML, display

from klotho.utils.playback.supersonic.cdn import supersonic_config
from klotho.utils.playback._helpers import convert_numpy_types
from klotho.utils.playback.supersonic._js_fragments import (
    ss_init_js, draw_scheduler_js, scheduler_core_js, scheduler_score_js,
    synthdef_registry_merge_js, control_bar_html, lifecycle_js,
)
from klotho.thetos.instruments._shared import load_ss_manifest

SYNTHDEFS_DIR = Path(__file__).parent / "assets" / "synthdefs"
_WIDGET_JS_PATH = Path(__file__).parent / "_engine_widget.js"
_WIDGET_JS_TEMPLATE = None
_DISK_SYNTHDEF_ASSETS = None

_INFRA_SYNTHDEFS = frozenset({'__busRouter', '__busRouterMonitor', '__chainLimiter'})


def _load_disk_synthdef_assets():
    global _DISK_SYNTHDEF_ASSETS
    if _DISK_SYNTHDEF_ASSETS is None:
        assets = {}
        if SYNTHDEFS_DIR.exists():
            for path in sorted(SYNTHDEFS_DIR.rglob("*.scsyndef")):
                assets[path.stem] = base64.b64encode(path.read_bytes()).decode("ascii")
        if "default" not in assets and "kl_tri" in assets:
            assets["default"] = assets["kl_tri"]
        _DISK_SYNTHDEF_ASSETS = assets
    return _DISK_SYNTHDEF_ASSETS


def _load_all_synthdef_assets():
    """Disk-baked assets overlaid with any runtime-registered SynthDefs.

    Runtime registrations (see
    :mod:`klotho.utils.playback.supersonic.registry`) take precedence and
    become visible immediately, without reimporting the package.
    """
    from klotho.utils.playback.supersonic.registry import runtime_assets
    return {**_load_disk_synthdef_assets(), **runtime_assets()}


def needed_spatial_synthdefs(meta):
    """The width-family defs a spatial score's scheduler instantiates.

    None of these names is ever an event's ``defName``: the scheduler
    builds the wide routers and the headphone decoder from
    ``meta.spatial``, so a walk over events cannot see them, and a def the
    page was never sent is one scsynth SKIPS -- the ``/s_new`` creates
    nothing and the array plays SILENTLY with no message anywhere.

    The decoder's width is main's width, which is the widest declared
    track: every track sums into main, so main's bus is the one place the
    whole array exists at once.  Whether a fold is actually possible (a
    labels-only array has no geometry) is the scheduler's decision, and
    one small blob is cheaper than duplicating that decision here.
    """
    tracks = ((meta or {}).get("spatial") or {}).get("tracks") or {}
    widths = {
        entry.get("width") for entry in tracks.values()
        if isinstance(entry.get("width"), int) and entry.get("width") > 0
    }
    if not widths:
        return set()
    main_width = max(widths | {2})
    names = {f"__busRouter{w}" for w in widths | {main_width} if w != 2}
    names.add(f"__spatialDecode{main_width}")
    return names


def needed_synthdefs(events, meta=None, control_data=None):
    """Every SynthDef name a payload needs sent to its page.

    ONE source of truth for both playback surfaces.  ``play(score)``
    reaches it through :class:`SuperSonicEngine`; ``plot(score).play()``
    reaches it through
    ``klotho.semeios.visualization._animation.animated._extract_needed_synthdefs``,
    which only unwraps the payload's shape before delegating here.

    They were separate, and the animation copy collected event
    ``defName`` s alone.  Every other source below was therefore missing
    from the animated page, and the drop is SILENT at every layer:
    ``_filter_synthdef_assets`` skips a name it cannot place, and scsynth
    skips an ``/s_new`` naming a def it never received.  An insert FX is
    the only writer of its track's ``fxBus``, which the track's summing
    router reads, so a track with an insert played in TOTAL SILENCE; a
    spatial score, whose wide routers exist only here, did not play at
    all.  Keep the two callers on this function.

    Parameters
    ----------
    events : sequence of dict
        Lowered SC events.  ``__rest__`` carries no sound and is skipped.
    meta : dict, optional
        Score metadata.  ``inserts`` names per-track FX defs; ``spatial``
        names the width family (see :func:`needed_spatial_synthdefs`).
    control_data : dict, optional
        Control-envelope payload.  Any ``descriptors`` mean the page runs
        ``__klEnvCtrl`` synths, which are likewise never an event
        ``defName``.

    Returns
    -------
    set of str
        SynthDef names, without the infrastructure defs every page gets
        (see ``_INFRA_SYNTHDEFS``).
    """
    meta = meta or {}
    names = set()
    for ev in events or ():
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "new" and ev.get("defName"):
            name = ev["defName"]
            if name != "__rest__":
                names.add(name)
    for track_inserts in (meta.get("inserts") or {}).values():
        for ins in track_inserts or ():
            dn = ins.get("defName") if isinstance(ins, dict) else None
            if dn:
                names.add(dn)
    if (control_data or {}).get("descriptors"):
        names.add("__klEnvCtrl")
    names |= needed_spatial_synthdefs(meta)
    return names


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


def serialize_control_data(control_data):
    """JSON-safe control-envelope payload: the float32 buffer as base64.

    Shared by the standalone widget and the animated plot(score) path.
    """
    cd = control_data or {}
    result = {"blockSize": cd.get("blockSize", 512),
              "descriptors": cd.get("descriptors", []),
              "bufferB64": None, "numFrames": 0}
    buf = cd.get("buffer")
    if buf is not None:
        result["bufferB64"] = base64.b64encode(buf.tobytes()).decode("ascii")
        result["numFrames"] = len(buf)
    return result


class SuperSonicEngine:
    """Browser playback widget running SuperCollider synthesis via WebAssembly.

    Renders an HTML/JS widget that boots scsynth in the browser, loads the
    required SynthDefs (bundled assets plus any runtime registrations), and
    schedules the given events. This is the default audio engine used by
    :func:`~klotho.utils.playback.player.play`.

    Parameters
    ----------
    events : list of dict
        SuperCollider-style playback events (as produced by the converters
        in :mod:`klotho.utils.playback.supersonic.converters`).
    meta : dict, optional
        Score-level metadata (track groups, insert FX chains, slurs).
    control_data : dict, optional
        Control-envelope buffer and descriptors for continuous automation.
    ring_time : float, optional
        Seconds of reverb/release tail to keep the audio context alive
        after the last event (default is 5).
    loop : bool or int, optional
        Initial loop policy, matching ``plot(...).play(loop=...)``:
        ``False`` (default) leaves the loop button off, ``True`` starts
        with infinite looping, and an int > 1 loops that many cycles.
        The widget's loop button toggles the configured policy.
    record : bool, optional
        When ``True``, the widget gains a record button: pressing it
        plays the events exactly like play while capturing the audio,
        and a 24-bit ``.wav`` download is offered once playback (plus
        ring time) finishes. Score payloads with registered tracks also
        get a "stems" checkbox that renders every track as a separate
        time-aligned stem (plus the full mix) in one ZIP.
    """

    def __init__(self, events, meta=None, control_data=None, ring_time=5, loop=False,
                 record=False):
        self.events = convert_numpy_types(events)
        self.meta = convert_numpy_types(meta or {})
        raw_control = control_data or {"buffer": None, "blockSize": 512, "descriptors": []}
        raw_buffer = raw_control.get("buffer")
        control_without_buffer = {k: v for k, v in raw_control.items() if k != "buffer"}
        self.control_data = convert_numpy_types(control_without_buffer)
        self.control_data["buffer"] = raw_buffer
        self.ring_time = ring_time
        self.loop = loop
        self.record = bool(record)
        self.widget_id = f"klotho_ss_{uuid.uuid4().hex[:8]}"
        from klotho.utils.playback._sc_validate import (
            validate_sc_events, validate_sc_meta, warn_unknown_event_groups,
        )
        validate_sc_events(self.events)
        if self.meta:
            validate_sc_meta(self.meta)
        # The only place holding both halves; a misrouted group is otherwise
        # silent all the way to the speakers.
        warn_unknown_event_groups(self.events, self.meta)
        self._needed = self._needed_synthdefs() | _INFRA_SYNTHDEFS
        self.synthdef_assets = _filter_synthdef_assets(_load_all_synthdef_assets(), self._needed)
        self.sample_assets = self._load_needed_samples()
        # ``spatial`` alone makes this a score: a speaker array declared on
        # "main" produces no ``groups`` and need produce no ``inserts``, and
        # without scheduler_score.js there is no setupTracks at all -- the
        # declaration would be dropped in silence rather than played.
        self._is_score = bool(self.meta.get("groups") or self.meta.get("inserts")
                              or self.meta.get("spatial"))

    def _needed_synthdefs(self):
        return needed_synthdefs(self.events, self.meta, self.control_data)

    def _needed_spatial_synthdefs(self):
        return needed_spatial_synthdefs(self.meta)

    def _needed_samples(self):
        """Sample names referenced symbolically by ``buf*`` pfields."""
        names = set()
        for ev in self.events:
            pfields = ev.get("pfields")
            if not isinstance(pfields, dict):
                continue
            for key, val in pfields.items():
                if isinstance(val, str) and key.startswith('buf'):
                    names.add(val)
        return names

    _SAMPLE_EMBED_WARN_BYTES = 6 * 1024 * 1024

    def _load_needed_samples(self):
        from klotho.utils.playback.supersonic.samples import (
            sample_info, sample_bytes_b64,
        )
        assets = {}
        total_b64 = 0
        for name in sorted(self._needed_samples()):
            info = sample_info(name)
            b64 = sample_bytes_b64(name)
            total_b64 += len(b64)
            assets[name] = {
                "b64": b64,
                "channels": info["channels"],
            }
        # b64 inflates by 4/3; compare the decoded size against the cap.
        total_bytes = (total_b64 * 3) // 4
        if total_bytes > self._SAMPLE_EMBED_WARN_BYTES:
            import warnings
            warnings.warn(
                f"This widget embeds {total_bytes / 1048576:.1f} MB of sample "
                f"audio in its HTML, and every play() re-embeds it (saved "
                f"notebooks store it per cell; Colab cells cannot share it). "
                f"Consider trimming samples or using fewer per piece.",
                stacklevel=3,
            )
        return assets

    def _serialize_control_data(self):
        return serialize_control_data(self.control_data)

    def _generate_html(self):
        events_json = json.dumps(self.events)
        synthdef_assets_json = json.dumps(self.synthdef_assets)
        needed_json = json.dumps(list(self._needed))
        config_json = json.dumps(supersonic_config())
        wid = self.widget_id
        meta_json = json.dumps(self.meta)
        control_data_json = json.dumps(self._serialize_control_data())
        manifest_json = json.dumps(load_ss_manifest())

        samples_json = json.dumps(self.sample_assets)

        from klotho.utils.playback._helpers import (
            get_animation_bridge_js, get_loop_control_js, substitute_loop_tokens,
        )

        widget_js = (_load_widget_template()
                     .replace('__WID__', wid)
                     .replace('__EVENTS_JSON__', events_json)
                     .replace('__NEEDED_JSON__', needed_json)
                     .replace('__SS_CONFIG_JSON__', config_json)
                     .replace('__META_JSON__', meta_json)
                     .replace('__CONTROL_DATA_JSON__', control_data_json)
                     .replace('__SAMPLES_JSON__', samples_json)
                     .replace('__MANIFEST_JSON__', manifest_json)
                     .replace('__RING_TIME__', str(self.ring_time)))
        widget_js = get_loop_control_js() + substitute_loop_tokens(widget_js, self.loop)

        needs_score_js = self._is_score or bool(self.control_data.get("descriptors"))
        score_js = scheduler_score_js() if needs_score_js else ""

        stems = self.record and bool(self.meta.get("groups"))
        bar_html = control_bar_html(wid, record=self.record, stems=stems)
        recorder_js = ""
        if self.record:
            from klotho.utils.playback._helpers import get_recorder_js
            recorder_js = get_recorder_js()

        html = f'''
{bar_html}

<script type="module">
{ss_init_js()}
{draw_scheduler_js()}
{scheduler_core_js()}
{score_js}
globalThis.__klothoManifest = {manifest_json};
{synthdef_registry_merge_js(synthdef_assets_json)}
{lifecycle_js()}
{get_animation_bridge_js()}
{recorder_js}
{widget_js}
</script>
'''
        return html

    def display(self):
        """Render the playback widget in the current notebook output."""
        html = self._generate_html()
        return display(HTML(html))

    def _repr_html_(self):
        return self._generate_html()
