import json
import uuid
from pathlib import Path

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.0.0.min.js"
_TONEJS_CDN = "https://unpkg.com/tone@14.7.77/build/Tone.js"
_INSTRUMENTS_JS_PATH = Path(__file__).resolve().parent.parent.parent / "utils" / "playback" / "tonejs" / "instruments.js"
_PLAYER_JS_PATH = Path(__file__).resolve().parent.parent.parent / "utils" / "playback" / "tonejs" / "player.js"

_plotly_included = False
_tone_included = False


class AnimatedFigure:
    def __init__(self, fig, step_trace_groups, halo_indices, all_path_indices,
                 audio_payload=None, dur=0.5, is_3d=False):
        self.fig = fig
        self.step_trace_groups = step_trace_groups
        self.halo_indices = halo_indices
        self.all_path_indices = all_path_indices
        self.audio_payload = audio_payload
        self.dur = dur
        self.is_3d = is_3d
        self.widget_id = f"klotho_anim_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        global _plotly_included, _tone_included

        plot_div_id = f"{self.widget_id}_plot"
        fig_html = self.fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            div_id=plot_div_id,
        )

        cdn_scripts = ''
        if not _plotly_included:
            cdn_scripts += f'<script src="{_PLOTLY_CDN}"></script>\n'
            _plotly_included = True
        if not _tone_included and self.audio_payload:
            cdn_scripts += f'<script src="{_TONEJS_CDN}"></script>\n'
            _tone_included = True

        kernel_session = uuid.uuid4().hex
        session_script = f'<script>globalThis._KLOTHO_SESSION = "{kernel_session}";</script>'

        instruments_js = _INSTRUMENTS_JS_PATH.read_text() if _INSTRUMENTS_JS_PATH.exists() else ""
        player_js = _PLAYER_JS_PATH.read_text() if _PLAYER_JS_PATH.exists() else ""

        steps_json = json.dumps(self.step_trace_groups)
        halos_json = json.dumps(self.halo_indices)
        all_path_json = json.dumps(self.all_path_indices)
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"
        wid = self.widget_id

        html = f'''
{cdn_scripts}
{fig_html}
<div id="{wid}_controls" style="
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: #1a1a2e;
    border-radius: 6px;
    user-select: none;
    margin-top: 4px;
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
</div>
{session_script}
<script>
{instruments_js}
</script>
<script>
{player_js}
</script>
<script>
(() => {{
    const plotDiv = document.getElementById("{plot_div_id}");
    const toggleBtn = document.getElementById("{wid}_toggle");
    const iconEl = document.getElementById("{wid}_icon");
    const loopBtn = document.getElementById("{wid}_loop");
    const loopSvg = document.getElementById("{wid}_loop_svg");

    const steps = {steps_json};
    const haloIndices = {halos_json};
    const allPathIndices = {all_path_json};
    const audioPayload = {payload_json};
    const totalSteps = steps.length;

    let looping = false;
    let playing = false;

    function hideAllPath() {{
        if (allPathIndices.length > 0) {{
            Plotly.restyle(plotDiv, {{ visible: false }}, allPathIndices);
        }}
    }}

    function showAllPath() {{
        if (allPathIndices.length > 0) {{
            Plotly.restyle(plotDiv, {{ visible: true }}, allPathIndices);
        }}
    }}

    function revealStep(stepIdx) {{
        if (stepIdx === 0) {{
            hideAllPath();
            if (haloIndices.length > 0) {{
                Plotly.restyle(plotDiv, {{ visible: true }}, [haloIndices[0]]);
            }}
            return;
        }}
        var edgeIdx = stepIdx - 1;
        if (edgeIdx >= 0 && edgeIdx < steps.length) {{
            var group = steps[edgeIdx];
            if (group && group.length > 0) {{
                Plotly.restyle(plotDiv, {{ visible: true }}, group);
            }}
        }}
        if (stepIdx === (audioPayload ? audioPayload.events.length - 1 : totalSteps) && haloIndices.length > 1) {{
            Plotly.restyle(plotDiv, {{ visible: true }}, [haloIndices[1]]);
        }}
    }}

    function finishPlayback() {{
        playing = false;
        showAllPath();
        setPlayIcon();
    }}

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

    if (audioPayload && typeof Tone !== "undefined") {{
        var events = audioPayload.events || [];
        var instruments = globalThis.KLOTHO_BUILD_INSTRUMENTS(audioPayload.instruments || {{}});
        var player = KlothoPlayer.create();

        toggleBtn.onclick = async () => {{
            if (player.isPlaying()) {{
                player.stop();
            }} else {{
                playing = true;
                setStopIcon();
                hideAllPath();
                await player.play(events, instruments, {{
                    loop: looping,
                    onEvent: function(stepIdx) {{
                        revealStep(stepIdx);
                    }},
                    onStop: function() {{
                        finishPlayback();
                    }},
                    onFinish: function() {{
                        finishPlayback();
                    }}
                }});
            }}
        }};
    }} else {{
        var durMs = {self.dur * 1000};
        var timerId = null;

        function runAnimation(stepIdx) {{
            if (!playing) return;
            if (stepIdx > totalSteps) {{
                if (looping) {{
                    hideAllPath();
                    timerId = setTimeout(function() {{ runAnimation(0); }}, durMs);
                }} else {{
                    finishPlayback();
                }}
                return;
            }}
            revealStep(stepIdx);
            timerId = setTimeout(function() {{
                runAnimation(stepIdx + 1);
            }}, durMs);
        }}

        toggleBtn.onclick = () => {{
            if (playing) {{
                playing = false;
                if (timerId) {{ clearTimeout(timerId); timerId = null; }}
                finishPlayback();
            }} else {{
                playing = true;
                setStopIcon();
                hideAllPath();
                runAnimation(0);
            }}
        }};
    }}
}})();
</script>
'''
        return html


class AnimatedRTFigure:
    def __init__(self, fig, node_to_traces, leaf_ancestors, all_animated_traces,
                 leaf_x_positions=None, leaf_halo_groups=None,
                 trace_bright_colors=None, trace_base_colors=None,
                 audio_payload=None, dur=0.5, glow=False):
        self.fig = fig
        self.node_to_traces = node_to_traces
        self.leaf_ancestors = leaf_ancestors
        self.all_animated_traces = all_animated_traces
        self.leaf_x_positions = leaf_x_positions or []
        self.leaf_halo_groups = leaf_halo_groups or []
        self.trace_bright_colors = trace_bright_colors or {}
        self.trace_base_colors = trace_base_colors or {}
        self.audio_payload = audio_payload
        self.dur = dur
        self.glow = glow
        self.widget_id = f"klotho_rt_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        global _plotly_included, _tone_included

        plot_div_id = f"{self.widget_id}_plot"
        fig_html = self.fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            div_id=plot_div_id,
        )

        cdn_scripts = ''
        if not _plotly_included:
            cdn_scripts += f'<script src="{_PLOTLY_CDN}"></script>\n'
            _plotly_included = True
        if not _tone_included and self.audio_payload:
            cdn_scripts += f'<script src="{_TONEJS_CDN}"></script>\n'
            _tone_included = True

        kernel_session = uuid.uuid4().hex
        session_script = f'<script>globalThis._KLOTHO_SESSION = "{kernel_session}";</script>'

        instruments_js = _INSTRUMENTS_JS_PATH.read_text() if _INSTRUMENTS_JS_PATH.exists() else ""
        player_js = _PLAYER_JS_PATH.read_text() if _PLAYER_JS_PATH.exists() else ""

        node_to_traces_json = json.dumps({str(k): v for k, v in self.node_to_traces.items()})
        leaf_ancestors_json = json.dumps([[str(n) for n in path] for path in self.leaf_ancestors])
        all_anim_json = json.dumps(self.all_animated_traces)
        leaf_x_json = json.dumps(self.leaf_x_positions)
        halo_groups_json = json.dumps(self.leaf_halo_groups)
        bright_colors_json = json.dumps({str(k): v for k, v in self.trace_bright_colors.items()})
        base_colors_json = json.dumps({str(k): v for k, v in self.trace_base_colors.items()})
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"
        wid = self.widget_id

        html = f'''
{cdn_scripts}
{fig_html}
<div id="{wid}_controls" style="
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: #1a1a2e;
    border-radius: 6px;
    user-select: none;
    margin-top: 4px;
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
</div>
{session_script}
<script>
{instruments_js}
</script>
<script>
{player_js}
</script>
<script>
(() => {{
    const plotDiv = document.getElementById("{plot_div_id}");
    const toggleBtn = document.getElementById("{wid}_toggle");
    const iconEl = document.getElementById("{wid}_icon");
    const loopBtn = document.getElementById("{wid}_loop");
    const loopSvg = document.getElementById("{wid}_loop_svg");

    const nodeToTraces = {node_to_traces_json};
    const leafAncestors = {leaf_ancestors_json};
    const allAnimatedTraces = {all_anim_json};
    const leafXPositions = {leaf_x_json};
    const leafHaloGroups = {halo_groups_json};
    const glowEnabled = {'true' if self.glow else 'false'};
    const traceBrightColors = {bright_colors_json};
    const traceBaseColors = {base_colors_json};
    const audioPayload = {payload_json};
    const totalSteps = leafAncestors.length;

    let looping = false;
    let playing = false;
    var brightenedTraces = [];
    var activeHaloGroup = [];

    function restoreBrightened() {{
        for (var i = 0; i < brightenedTraces.length; i++) {{
            var ti = brightenedTraces[i];
            var base = traceBaseColors[String(ti)];
            if (base) {{
                Plotly.restyle(plotDiv, {{ 'fillcolor': base }}, [ti]);
            }}
        }}
        brightenedTraces = [];
    }}

    function hideHalo() {{
        if (activeHaloGroup.length > 0) {{
            Plotly.restyle(plotDiv, {{ visible: false }}, activeHaloGroup);
            activeHaloGroup = [];
        }}
    }}

    function showHalo(leafIdx) {{
        if (leafIdx < leafHaloGroups.length) {{
            var group = leafHaloGroups[leafIdx];
            if (group && group.length > 0) {{
                var toShow = glowEnabled ? group : [group[group.length - 1]];
                Plotly.restyle(plotDiv, {{ visible: true }}, toShow);
                activeHaloGroup = toShow.slice();
            }}
        }}
    }}

    function dimAll() {{
        restoreBrightened();
        hideHalo();
        if (allAnimatedTraces.length > 0) {{
            Plotly.restyle(plotDiv, {{ opacity: 0.15 }}, allAnimatedTraces);
        }}
    }}

    function resetAll() {{
        restoreBrightened();
        hideHalo();
        if (allAnimatedTraces.length > 0) {{
            Plotly.restyle(plotDiv, {{ opacity: 1.0 }}, allAnimatedTraces);
        }}
    }}

    function highlightLeaf(leafIdx) {{
        if (leafIdx < 0 || leafIdx >= leafAncestors.length) return;
        dimAll();
        var ancestorPath = leafAncestors[leafIdx];
        var pathTraces = [];
        var leafNodeId = ancestorPath[ancestorPath.length - 1];
        var leafTraces = nodeToTraces[leafNodeId] || [];
        for (var i = 0; i < ancestorPath.length; i++) {{
            var traces = nodeToTraces[ancestorPath[i]];
            if (traces) {{
                for (var j = 0; j < traces.length; j++) {{
                    if (pathTraces.indexOf(traces[j]) === -1) {{
                        pathTraces.push(traces[j]);
                    }}
                }}
            }}
        }}
        if (pathTraces.length > 0) {{
            Plotly.restyle(plotDiv, {{ opacity: 1.0 }}, pathTraces);
        }}
        for (var k = 0; k < leafTraces.length; k++) {{
            var ti = leafTraces[k];
            var bright = traceBrightColors[String(ti)];
            if (bright) {{
                Plotly.restyle(plotDiv, {{ 'fillcolor': bright }}, [ti]);
                brightenedTraces.push(ti);
            }}
        }}
        showHalo(leafIdx);
        if (leafIdx < leafXPositions.length) {{
            try {{
                var xax = plotDiv._fullLayout.xaxis;
                var plotWidth = plotDiv._fullLayout.width - plotDiv._fullLayout.margin.l - plotDiv._fullLayout.margin.r;
                var xFrac = (leafXPositions[leafIdx] - xax.range[0]) / (xax.range[1] - xax.range[0]);
                var pxX = plotDiv._fullLayout.margin.l + xFrac * plotWidth;
                var scroller = plotDiv.closest('.jp-OutputArea-output') || plotDiv.closest('.output_subarea') || plotDiv.parentElement;
                if (scroller && scroller.scrollWidth > scroller.clientWidth) {{
                    var targetLeft = pxX - scroller.clientWidth * 0.2;
                    if (pxX < scroller.scrollLeft || pxX > scroller.scrollLeft + scroller.clientWidth) {{
                        scroller.scrollLeft = Math.max(0, targetLeft);
                    }}
                }}
            }} catch(_) {{}}
        }}
    }}

    function finishPlayback() {{
        playing = false;
        resetAll();
        setPlayIcon();
    }}

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

    if (audioPayload && typeof Tone !== "undefined") {{
        var events = audioPayload.events || [];
        var instruments = globalThis.KLOTHO_BUILD_INSTRUMENTS(audioPayload.instruments || {{}});
        var player = KlothoPlayer.create();

        toggleBtn.onclick = async () => {{
            if (player.isPlaying()) {{
                player.stop();
            }} else {{
                playing = true;
                setStopIcon();
                await player.play(events, instruments, {{
                    loop: looping,
                    onEvent: function(stepIdx) {{
                        highlightLeaf(stepIdx);
                    }},
                    onStop: function() {{
                        finishPlayback();
                    }},
                    onFinish: function() {{
                        finishPlayback();
                    }}
                }});
            }}
        }};
    }} else {{
        var durMs = {self.dur * 1000};
        var timerId = null;

        function runAnimation(stepIdx) {{
            if (!playing) return;
            if (stepIdx >= totalSteps) {{
                if (looping) {{
                    timerId = setTimeout(function() {{ runAnimation(0); }}, durMs);
                }} else {{
                    finishPlayback();
                }}
                return;
            }}
            highlightLeaf(stepIdx);
            timerId = setTimeout(function() {{
                runAnimation(stepIdx + 1);
            }}, durMs);
        }}

        toggleBtn.onclick = () => {{
            if (playing) {{
                playing = false;
                if (timerId) {{ clearTimeout(timerId); timerId = null; }}
                finishPlayback();
            }} else {{
                playing = true;
                setStopIcon();
                runAnimation(0);
            }}
        }};
    }}
}})();
</script>
'''
        return html
