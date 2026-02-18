import json
import uuid

from klotho.utils.playback.tonejs.cdn import (
    cdn_scripts, reset_cdn_flags,
    INSTRUMENTS_JS_PATH, PLAYER_JS_PATH,
)


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
        plot_div_id = f"{self.widget_id}_plot"
        fig_json = self.fig.to_json()
        fig_w = self.fig.layout.width or 700
        fig_h = self.fig.layout.height or 450

        cdn_html = cdn_scripts(include_plotly=True, include_tone=bool(self.audio_payload))

        kernel_session = uuid.uuid4().hex
        session_script = f'<script>globalThis._KLOTHO_SESSION = "{kernel_session}";</script>'

        instruments_js = INSTRUMENTS_JS_PATH.read_text() if INSTRUMENTS_JS_PATH.exists() else ""
        player_js = PLAYER_JS_PATH.read_text() if PLAYER_JS_PATH.exists() else ""

        steps_json = json.dumps(self.step_trace_groups)
        halos_json = json.dumps(self.halo_indices)
        all_path_json = json.dumps(self.all_path_indices)
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"
        wid = self.widget_id

        html = f'''
{cdn_html}
<div id="{plot_div_id}" class="plotly-graph-div" style="height:{fig_h}px; width:{fig_w}px;"></div>
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
(function _klothoInit() {{
    if (typeof Plotly === "undefined") {{ setTimeout(_klothoInit, 50); return; }}

    var _fig = {fig_json};
    var plotDiv = document.getElementById("{plot_div_id}");
    Plotly.newPlot(plotDiv, _fig.data, _fig.layout, {{responsive: true}});

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
                 leaf_path_traces=None,
                 leaf_x_positions=None, leaf_halo_groups=None,
                 trace_bright_colors=None, trace_base_colors=None,
                 audio_payload=None, dur=0.5, glow=False):
        self.fig = fig
        self.node_to_traces = node_to_traces
        self.leaf_ancestors = leaf_ancestors
        self.leaf_path_traces = leaf_path_traces or []
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
        plot_div_id = f"{self.widget_id}_plot"
        fig_json = self.fig.to_json()
        fig_w = self.fig.layout.width or 700
        fig_h = self.fig.layout.height or 450

        cdn_html = cdn_scripts(include_plotly=True, include_tone=bool(self.audio_payload))

        kernel_session = uuid.uuid4().hex
        session_script = f'<script>globalThis._KLOTHO_SESSION = "{kernel_session}";</script>'

        instruments_js = INSTRUMENTS_JS_PATH.read_text() if INSTRUMENTS_JS_PATH.exists() else ""
        player_js = PLAYER_JS_PATH.read_text() if PLAYER_JS_PATH.exists() else ""

        node_to_traces_json = json.dumps({str(k): v for k, v in self.node_to_traces.items()})
        leaf_ancestors_json = json.dumps([[str(n) for n in path] for path in self.leaf_ancestors])
        all_anim_json = json.dumps(self.all_animated_traces)
        leaf_x_json = json.dumps(self.leaf_x_positions)
        halo_groups_json = json.dumps(self.leaf_halo_groups)
        bright_colors_json = json.dumps({str(k): v for k, v in self.trace_bright_colors.items()})
        base_colors_json = json.dumps({str(k): v for k, v in self.trace_base_colors.items()})
        leaf_path_traces_json = json.dumps(self.leaf_path_traces)
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"
        wid = self.widget_id

        html = f'''
{cdn_html}
<div id="{plot_div_id}" class="plotly-graph-div" style="height:{fig_h}px; width:{fig_w}px;"></div>
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
(function _klothoInit() {{
    if (typeof Plotly === "undefined") {{ setTimeout(_klothoInit, 50); return; }}

    var _fig = {fig_json};
    var plotDiv = document.getElementById("{plot_div_id}");
    Plotly.newPlot(plotDiv, _fig.data, _fig.layout, {{responsive: true}});

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
    const leafPathTraces = {leaf_path_traces_json};
    const totalSteps = leafAncestors.length;

    let looping = false;
    let playing = false;
    var prevPathSet = null;
    var prevBrightened = [];
    var prevHaloGroup = [];

    function resetAll() {{
        if (prevBrightened.length > 0) {{
            var ci = [], cv = [];
            for (var i = 0; i < prevBrightened.length; i++) {{
                ci.push(prevBrightened[i].idx);
                cv.push(prevBrightened[i].base);
            }}
            Plotly.restyle(plotDiv, {{fillcolor: cv}}, ci);
            prevBrightened = [];
        }}
        if (prevHaloGroup.length > 0) {{
            Plotly.restyle(plotDiv, {{visible: false}}, prevHaloGroup);
            prevHaloGroup = [];
        }}
        if (allAnimatedTraces.length > 0) {{
            Plotly.restyle(plotDiv, {{opacity: 1.0}}, allAnimatedTraces);
        }}
        prevPathSet = null;
    }}

    function highlightLeaf(leafIdx) {{
        if (leafIdx < 0 || leafIdx >= totalSteps) return;

        var currPathTraces = leafPathTraces[leafIdx];
        var currPathSet = new Set(currPathTraces);
        var leafNodeId = leafAncestors[leafIdx][leafAncestors[leafIdx].length - 1];
        var leafTraceIds = nodeToTraces[leafNodeId] || [];

        var opIdx = [], opVal = [];
        if (prevPathSet === null) {{
            for (var i = 0; i < allAnimatedTraces.length; i++) {{
                var ti = allAnimatedTraces[i];
                opIdx.push(ti);
                opVal.push(currPathSet.has(ti) ? 1.0 : 0.15);
            }}
        }} else {{
            prevPathSet.forEach(function(ti) {{
                if (!currPathSet.has(ti)) {{ opIdx.push(ti); opVal.push(0.15); }}
            }});
            currPathSet.forEach(function(ti) {{
                if (!prevPathSet.has(ti)) {{ opIdx.push(ti); opVal.push(1.0); }}
            }});
        }}
        if (opIdx.length > 0) {{
            Plotly.restyle(plotDiv, {{opacity: opVal}}, opIdx);
        }}

        var cIdx = [], cVal = [];
        for (var i = 0; i < prevBrightened.length; i++) {{
            cIdx.push(prevBrightened[i].idx);
            cVal.push(prevBrightened[i].base);
        }}
        var newBrightened = [];
        for (var i = 0; i < leafTraceIds.length; i++) {{
            var ti = leafTraceIds[i];
            var bright = traceBrightColors[String(ti)];
            if (bright) {{
                cIdx.push(ti);
                cVal.push(bright);
                newBrightened.push({{idx: ti, base: traceBaseColors[String(ti)]}});
            }}
        }}
        if (cIdx.length > 0) {{
            Plotly.restyle(plotDiv, {{fillcolor: cVal}}, cIdx);
        }}

        var vIdx = [], vVal = [];
        for (var i = 0; i < prevHaloGroup.length; i++) {{
            vIdx.push(prevHaloGroup[i]); vVal.push(false);
        }}
        var newHaloGroup = [];
        if (leafIdx < leafHaloGroups.length) {{
            var group = leafHaloGroups[leafIdx];
            if (group && group.length > 0) {{
                var toShow = glowEnabled ? group : [group[group.length - 1]];
                for (var i = 0; i < toShow.length; i++) {{
                    vIdx.push(toShow[i]); vVal.push(true);
                }}
                newHaloGroup = toShow.slice();
            }}
        }}
        if (vIdx.length > 0) {{
            Plotly.restyle(plotDiv, {{visible: vVal}}, vIdx);
        }}

        prevPathSet = currPathSet;
        prevBrightened = newBrightened;
        prevHaloGroup = newHaloGroup;

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
