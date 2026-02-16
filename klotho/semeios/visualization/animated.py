import json
import uuid

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.0.0.min.js"
_plotly_included = False


class AnimatedFigure:
    def __init__(self, fig, step_trace_groups, halo_indices, all_path_indices,
                 dur=0.5, is_3d=False):
        self.fig = fig
        self.step_trace_groups = step_trace_groups
        self.halo_indices = halo_indices
        self.all_path_indices = all_path_indices
        self.dur = dur
        self.is_3d = is_3d
        self.widget_id = f"klotho_anim_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        global _plotly_included

        plot_div_id = f"{self.widget_id}_plot"
        fig_html = self.fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            div_id=plot_div_id,
        )

        if not _plotly_included:
            plotly_script = f'<script src="{_PLOTLY_CDN}"></script>'
            _plotly_included = True
        else:
            plotly_script = ''

        steps_json = json.dumps(self.step_trace_groups)
        halos_json = json.dumps(self.halo_indices)
        all_path_json = json.dumps(self.all_path_indices)
        wid = self.widget_id
        dur_ms = self.dur * 1000

        html = f'''
{plotly_script}
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
    const durMs = {dur_ms};
    const totalSteps = steps.length;

    let looping = false;
    let playing = false;
    let timerId = null;

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
        var group = steps[stepIdx];
        if (group && group.length > 0) {{
            Plotly.restyle(plotDiv, {{ visible: true }}, group);
        }}
        if (stepIdx === 0 && haloIndices.length > 0) {{
            Plotly.restyle(plotDiv, {{ visible: true }}, [haloIndices[0]]);
        }}
        if (stepIdx === totalSteps - 1 && haloIndices.length > 1) {{
            Plotly.restyle(plotDiv, {{ visible: true }}, [haloIndices[1]]);
        }}
    }}

    function finishPlayback() {{
        playing = false;
        if (timerId) {{ clearTimeout(timerId); timerId = null; }}
        showAllPath();
        setPlayIcon();
    }}

    function runAnimation(stepIdx) {{
        if (!playing) return;
        if (stepIdx >= totalSteps) {{
            if (looping) {{
                hideAllPath();
                timerId = setTimeout(function() {{
                    requestAnimationFrame(function() {{ runAnimation(0); }});
                }}, durMs);
            }} else {{
                finishPlayback();
            }}
            return;
        }}
        requestAnimationFrame(function() {{
            revealStep(stepIdx);
            timerId = setTimeout(function() {{
                runAnimation(stepIdx + 1);
            }}, durMs);
        }});
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

    toggleBtn.onclick = () => {{
        if (playing) {{
            finishPlayback();
        }} else {{
            playing = true;
            setStopIcon();
            hideAllPath();
            requestAnimationFrame(function() {{
                runAnimation(0);
            }});
        }}
    }};
}})();
</script>
'''
        return html
