import json
import uuid

from klotho.utils.playback.tonejs.cdn import (
    cdn_scripts, reset_cdn_flags,
    INSTRUMENTS_JS_PATH, PLAYER_JS_PATH,
    THREEJS_CDN, THREEJS_ORBIT_CDN,
)


class AnimatedLattice3dFigure:
    def __init__(self, scene_data, audio_payload=None, dur=0.5):
        self.scene_data = scene_data
        self.audio_payload = audio_payload
        self.dur = dur
        self.widget_id = f"klotho_3d_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        sd = self.scene_data
        wid = self.widget_id

        cdn_html = cdn_scripts(
            include_plotly=False,
            include_tone=bool(self.audio_payload),
            include_threejs=True,
        )

        kernel_session = uuid.uuid4().hex
        session_script = f'<script>globalThis._KLOTHO_SESSION = "{kernel_session}";</script>'

        instruments_js = INSTRUMENTS_JS_PATH.read_text() if INSTRUMENTS_JS_PATH.exists() else ""
        player_js = PLAYER_JS_PATH.read_text() if PLAYER_JS_PATH.exists() else ""

        scene_json = json.dumps(sd.scene_data)
        steps_json = json.dumps(sd.path_steps)
        halo_json = json.dumps(sd.halo_data)
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"

        w = sd.width_px
        h = sd.height_px
        title_escaped = sd.title.replace("'", "\\'").replace('"', '\\"')

        threejs_cdn = THREEJS_CDN
        orbit_cdn = THREEJS_ORBIT_CDN

        html = f'''
{cdn_html}
<div id="{wid}_wrap" style="position:relative;width:{w}px;background:black;">
    <div id="{wid}_title" style="
        color:white;font-family:Arial,sans-serif;font-size:14px;
        text-align:center;padding:8px 0 4px 0;pointer-events:none;
        display:{'block' if title_escaped else 'none'};
    ">{title_escaped}</div>
    <canvas id="{wid}_canvas" style="display:block;width:{w}px;height:{h}px;"></canvas>
    <div id="{wid}_tooltip" style="
        display:none;position:absolute;pointer-events:none;top:0;left:0;
        background:rgba(30,30,30,0.92);color:white;font-family:monospace;
        font-size:11px;padding:6px 10px;border-radius:4px;
        white-space:pre;max-width:300px;z-index:10;
    "></div>
</div>
<div id="{wid}_controls" style="
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 10px; background: #1a1a2e; border-radius: 6px;
    user-select: none; margin-top: 4px;">
    <button id="{wid}_toggle" style="
        width: 32px; height: 32px; border: none; border-radius: 4px;
        background: #16213e; cursor: pointer; display: flex;
        align-items: center; justify-content: center; padding: 0;">
        <span id="{wid}_icon" style="
            width: 0; height: 0;
            border-top: 7px solid transparent; border-bottom: 7px solid transparent;
            border-left: 12px solid #4ade80; margin-left: 3px;"></span>
    </button>
    <button id="{wid}_loop" style="
        width: 28px; height: 28px; border: none; border-radius: 4px;
        background: #16213e; cursor: pointer; display: flex;
        align-items: center; justify-content: center; padding: 0; opacity: 0.5;">
        <svg id="{wid}_loop_svg" width="16" height="16" viewBox="0 0 24 24"
             fill="none" stroke="#a0a0a0" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 2l4 4-4 4"></path><path d="M3 11v-1a4 4 0 0 1 4-4h14"></path>
            <path d="M7 22l-4-4 4-4"></path><path d="M21 13v1a4 4 0 0 1-4 4H3"></path>
        </svg>
    </button>
</div>
{session_script}
<script>{instruments_js}</script>
<script>{player_js}</script>
<script>
(function _klotho3dInit() {{
    if (typeof THREE === "undefined") {{
        if (!document.querySelector('script[data-klotho-three]')) {{
            var s = document.createElement("script");
            s.src = "{threejs_cdn}";
            s.setAttribute("data-klotho-three", "1");
            (document.head || document.documentElement).appendChild(s);
        }}
        setTimeout(_klotho3dInit, 100);
        return;
    }}

    if (!THREE.OrbitControls) {{
        if (!document.querySelector('script[data-klotho-orbit]')) {{
            var s = document.createElement("script");
            s.src = "{orbit_cdn}";
            s.setAttribute("data-klotho-orbit", "1");
            (document.head || document.documentElement).appendChild(s);
        }}
        setTimeout(_klotho3dInit, 100);
        return;
    }}

    var canvas = document.getElementById("{wid}_canvas");
    if (!canvas) {{ setTimeout(_klotho3dInit, 50); return; }}

    var container = document.getElementById("{wid}_wrap");
    var tooltip   = document.getElementById("{wid}_tooltip");
    var toggleBtn = document.getElementById("{wid}_toggle");
    var iconEl    = document.getElementById("{wid}_icon");
    var loopBtn   = document.getElementById("{wid}_loop");
    var loopSvg   = document.getElementById("{wid}_loop_svg");

    var sceneData = {scene_json};
    var pathSteps = {steps_json};
    var haloData  = {halo_json};
    var audioPayload = {payload_json};
    var titleText = "{title_escaped}";

    var W = {w}, H = {h};

    var scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);

    var camera = new THREE.PerspectiveCamera(50, W / H, 0.01, 1000);

    var axCfg = sceneData.axisConfig;
    var cx = (axCfg.xRange[0] + axCfg.xRange[1]) / 2;
    var cy = (axCfg.yRange[0] + axCfg.yRange[1]) / 2;
    var cz = (axCfg.zRange[0] + axCfg.zRange[1]) / 2;

    var span = Math.max(
        axCfg.xRange[1] - axCfg.xRange[0],
        axCfg.yRange[1] - axCfg.yRange[0],
        axCfg.zRange[1] - axCfg.zRange[0]
    );
    camera.position.set(cx + span * 1.2, cy + span * 1.2, cz + span * 1.2);
    camera.lookAt(cx, cy, cz);

    if (canvas._klothoRenderer) {{
        try {{ canvas._klothoRenderer.dispose(); }} catch(_) {{}}
    }}
    var renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true }});
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    canvas._klothoRenderer = renderer;

    var controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.target.set(cx, cy, cz);
    controls.enableDamping = true;
    controls.dampingFactor = 0.12;
    controls.update();

    if (sceneData.gridEdges.length > 0) {{
        var gVerts = new Float32Array(sceneData.gridEdges.length * 6);
        for (var i = 0; i < sceneData.gridEdges.length; i++) {{
            var e = sceneData.gridEdges[i];
            gVerts[i*6]   = e[0]; gVerts[i*6+1] = e[1]; gVerts[i*6+2] = e[2];
            gVerts[i*6+3] = e[3]; gVerts[i*6+4] = e[4]; gVerts[i*6+5] = e[5];
        }}
        var gGeom = new THREE.BufferGeometry();
        gGeom.setAttribute("position", new THREE.BufferAttribute(gVerts, 3));
        var gMat = new THREE.LineBasicMaterial({{ color: sceneData.gridEdgeColor }});
        scene.add(new THREE.LineSegments(gGeom, gMat));
    }}

    if (sceneData.highlightEdges.length > 0) {{
        var hVerts = new Float32Array(sceneData.highlightEdges.length * 6);
        for (var i = 0; i < sceneData.highlightEdges.length; i++) {{
            var e = sceneData.highlightEdges[i];
            hVerts[i*6]   = e[0]; hVerts[i*6+1] = e[1]; hVerts[i*6+2] = e[2];
            hVerts[i*6+3] = e[3]; hVerts[i*6+4] = e[4]; hVerts[i*6+5] = e[5];
        }}
        var hGeom = new THREE.BufferGeometry();
        hGeom.setAttribute("position", new THREE.BufferAttribute(hVerts, 3));
        var hMat = new THREE.LineBasicMaterial({{ color: 0xffffff, linewidth: 2 }});
        scene.add(new THREE.LineSegments(hGeom, hMat));
    }}

    var nodeCount = sceneData.nodes.length;
    var sphereR = sceneData.nodeSize * 0.015;
    var sphereGeo = new THREE.SphereGeometry(sphereR, 16, 12);
    var nodeMeshes = [];
    var nodeGroup = new THREE.Group();
    var dimColor = new THREE.Color(sceneData.dimmedNodeColor);
    var brightColor = new THREE.Color("#ffffff");
    var pathNodeIndices = sceneData.pathNodeIndices || [];

    for (var i = 0; i < nodeCount; i++) {{
        var n = sceneData.nodes[i];
        var mat = new THREE.MeshBasicMaterial({{ color: sceneData.nodeColors[i] }});
        var mesh = new THREE.Mesh(sphereGeo, mat);
        mesh.position.set(n[0], n[1], n[2]);
        mesh.userData.nodeIdx = i;
        nodeGroup.add(mesh);
        nodeMeshes.push(mesh);
    }}
    scene.add(nodeGroup);

    function dimAllNodes() {{
        for (var i = 0; i < nodeMeshes.length; i++) nodeMeshes[i].material.color.copy(dimColor);
    }}
    function highlightAllPathNodes() {{
        for (var i = 0; i < pathNodeIndices.length; i++) {{
            var idx = pathNodeIndices[i];
            if (idx >= 0 && idx < nodeMeshes.length) nodeMeshes[idx].material.color.copy(brightColor);
        }}
    }}
    function highlightNodeAt(stepIdx) {{
        if (stepIdx >= 0 && stepIdx < pathNodeIndices.length) {{
            var idx = pathNodeIndices[stepIdx];
            if (idx >= 0 && idx < nodeMeshes.length) nodeMeshes[idx].material.color.copy(brightColor);
        }}
    }}

    function makeTextSprite(text, color) {{
        var c2 = document.createElement("canvas");
        var ctx = c2.getContext("2d");
        c2.width = 128; c2.height = 48;
        ctx.fillStyle = color || "#ffffff";
        ctx.font = "24px monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(text, 64, 24);
        var tex = new THREE.CanvasTexture(c2);
        var mat = new THREE.SpriteMaterial({{ map: tex, transparent: true }});
        var sprite = new THREE.Sprite(mat);
        sprite.scale.set(0.5, 0.2, 1);
        return sprite;
    }}

    var labels = axCfg.labels;
    var tickOff = 0.3;
    if (labels[0]) {{
        axCfg.xTicks.forEach(function(t) {{
            var s = makeTextSprite(String(t));
            s.position.set(t, axCfg.yRange[0] - tickOff, axCfg.zRange[0] - tickOff);
            scene.add(s);
        }});
        var xl = makeTextSprite(labels[0], "#aaaaaa");
        xl.position.set(cx, axCfg.yRange[0] - tickOff * 2.5, axCfg.zRange[0] - tickOff * 2.5);
        xl.scale.set(0.7, 0.25, 1);
        scene.add(xl);
    }}
    if (labels[1]) {{
        axCfg.yTicks.forEach(function(t) {{
            var s = makeTextSprite(String(t));
            s.position.set(axCfg.xRange[0] - tickOff, t, axCfg.zRange[0] - tickOff);
            scene.add(s);
        }});
        var yl = makeTextSprite(labels[1], "#aaaaaa");
        yl.position.set(axCfg.xRange[0] - tickOff * 2.5, cy, axCfg.zRange[0] - tickOff * 2.5);
        yl.scale.set(0.7, 0.25, 1);
        scene.add(yl);
    }}
    if (labels[2]) {{
        axCfg.zTicks.forEach(function(t) {{
            var s = makeTextSprite(String(t));
            s.position.set(axCfg.xRange[0] - tickOff, axCfg.yRange[0] - tickOff, t);
            scene.add(s);
        }});
        var zl = makeTextSprite(labels[2], "#aaaaaa");
        zl.position.set(axCfg.xRange[0] - tickOff * 2.5, axCfg.yRange[0] - tickOff * 2.5, cz);
        zl.scale.set(0.7, 0.25, 1);
        scene.add(zl);
    }}

    function makeTube(pts, radius, color, opacity) {{
        var vecs = pts.map(function(p) {{ return new THREE.Vector3(p[0], p[1], p[2]); }});
        var curve = (vecs.length === 2)
            ? new THREE.LineCurve3(vecs[0], vecs[1])
            : new THREE.CatmullRomCurve3(vecs, false, "catmullrom", 0);
        var segs = Math.max(vecs.length * 4, 8);
        var geo = new THREE.TubeGeometry(curve, segs, radius, 6, false);
        var mat = new THREE.MeshBasicMaterial({{ color: color, transparent: opacity < 1, opacity: opacity }});
        return new THREE.Mesh(geo, mat);
    }}

    var stepGroups = [];
    for (var si = 0; si < pathSteps.length; si++) {{
        var step = pathSteps[si];
        if (!step) {{ stepGroups.push(null); continue; }}
        var pts = step.polyline;
        var group = [];

        var glowTube = makeTube(pts, 0.018, 0xffffff, 0.25);
        glowTube.visible = true;
        scene.add(glowTube);
        group.push(glowTube);

        var colTube = makeTube(pts, 0.012, step.color, 1.0);
        colTube.visible = true;
        scene.add(colTube);
        group.push(colTube);

        var coneH = 0.12, coneR = 0.04;
        var coneGeo = new THREE.ConeGeometry(coneR, coneH, 8);
        coneGeo.translate(0, coneH / 2, 0);
        coneGeo.rotateX(Math.PI / 2);
        var cone = new THREE.Mesh(coneGeo, new THREE.MeshBasicMaterial({{ color: step.color }}));
        cone.position.set(step.arrow_pos[0], step.arrow_pos[1], step.arrow_pos[2]);
        var dir = new THREE.Vector3(step.arrow_dir[0], step.arrow_dir[1], step.arrow_dir[2]).normalize();
        var quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
        cone.setRotationFromQuaternion(quat);
        cone.visible = true;
        scene.add(cone);
        group.push(cone);

        stepGroups.push(group);
    }}

    var startHalo = null, endHalo = null;
    if (haloData) {{
        var haloGeo = new THREE.SphereGeometry(0.18, 16, 12);
        startHalo = new THREE.Mesh(haloGeo,
            new THREE.MeshBasicMaterial({{ color: haloData.start.color, transparent: true, opacity: 0.4 }}));
        startHalo.position.set(haloData.start.pos[0], haloData.start.pos[1], haloData.start.pos[2]);
        startHalo.visible = true;
        scene.add(startHalo);

        endHalo = new THREE.Mesh(haloGeo.clone(),
            new THREE.MeshBasicMaterial({{ color: haloData.end.color, transparent: true, opacity: 0.4 }}));
        endHalo.position.set(haloData.end.pos[0], haloData.end.pos[1], haloData.end.pos[2]);
        endHalo.visible = true;
        scene.add(endHalo);
    }}

    if (pathNodeIndices.length > 0) highlightAllPathNodes();

    var raycaster = new THREE.Raycaster();
    var mouse = new THREE.Vector2();
    var hoveredIdx = -1;

    container.addEventListener("mousemove", function(ev) {{
        var rect = canvas.getBoundingClientRect();
        mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
        var hits = raycaster.intersectObjects(nodeMeshes, false);
        if (hits.length > 0) {{
            var idx = hits[0].object.userData.nodeIdx;
            if (idx !== hoveredIdx) {{
                hoveredIdx = idx;
                tooltip.textContent = sceneData.hoverData[idx];
                tooltip.style.display = "block";
            }}
            tooltip.style.left = (ev.clientX - rect.left + 12) + "px";
            tooltip.style.top  = (ev.clientY - rect.top  + 12) + "px";
        }} else {{
            hoveredIdx = -1;
            tooltip.style.display = "none";
        }}
    }});
    container.addEventListener("mouseleave", function() {{
        hoveredIdx = -1;
        tooltip.style.display = "none";
    }});

    function renderLoop() {{
        requestAnimationFrame(renderLoop);
        controls.update();
        renderer.render(scene, camera);
    }}
    renderLoop();

    var looping = false, playing = false;
    var totalSteps = pathSteps.length;

    function hideAllPath() {{
        for (var i = 0; i < stepGroups.length; i++) {{
            var g = stepGroups[i];
            if (g) {{ for (var j = 0; j < g.length; j++) g[j].visible = false; }}
        }}
        if (startHalo) startHalo.visible = false;
        if (endHalo) endHalo.visible = false;
        dimAllNodes();
    }}

    function showAllPath() {{
        for (var i = 0; i < stepGroups.length; i++) {{
            var g = stepGroups[i];
            if (g) {{ for (var j = 0; j < g.length; j++) g[j].visible = true; }}
        }}
        if (startHalo) startHalo.visible = true;
        if (endHalo) endHalo.visible = true;
        highlightAllPathNodes();
    }}

    function revealStep(stepIdx) {{
        if (stepIdx === 0) {{
            hideAllPath();
            if (startHalo) startHalo.visible = true;
            highlightNodeAt(0);
            return;
        }}
        var edgeIdx = stepIdx - 1;
        if (edgeIdx >= 0 && edgeIdx < stepGroups.length) {{
            var g = stepGroups[edgeIdx];
            if (g) {{ for (var j = 0; j < g.length; j++) g[j].visible = true; }}
        }}
        highlightNodeAt(stepIdx);
        if (stepIdx === (audioPayload ? audioPayload.events.length - 1 : totalSteps) && endHalo) {{
            endHalo.visible = true;
        }}
    }}

    function finishPlayback() {{
        playing = false;
        showAllPath();
        setPlayIcon();
    }}

    function setPlayIcon() {{
        iconEl.style.cssText = "width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent;border-left:12px solid #4ade80;border-right:none;margin-left:3px;background:none";
    }}
    function setStopIcon() {{
        iconEl.style.cssText = "width:12px;height:12px;border:none;border-radius:2px;margin-left:0;background:#ef4444";
    }}

    loopBtn.onclick = function() {{
        looping = !looping;
        loopBtn.style.opacity = looping ? "1" : "0.5";
        loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0");
    }};

    if (audioPayload && typeof Tone !== "undefined") {{
        var events = audioPayload.events || [];
        var instruments = globalThis.KLOTHO_BUILD_INSTRUMENTS(audioPayload.instruments || {{}});
        var player = KlothoPlayer.create();
        toggleBtn.onclick = async function() {{
            if (player.isPlaying()) {{ player.stop(); }}
            else {{
                playing = true; setStopIcon(); hideAllPath();
                await player.play(events, instruments, {{
                    loop: looping,
                    onEvent: function(stepIdx) {{ revealStep(stepIdx); }},
                    onStop: function() {{ finishPlayback(); }},
                    onFinish: function() {{ finishPlayback(); }}
                }});
            }}
        }};
    }} else {{
        var durMs = {self.dur * 1000};
        var timerId = null;
        function runAnimation(stepIdx) {{
            if (!playing) return;
            if (stepIdx > totalSteps) {{
                if (looping) {{ hideAllPath(); timerId = setTimeout(function() {{ runAnimation(0); }}, durMs); }}
                else {{ finishPlayback(); }}
                return;
            }}
            revealStep(stepIdx);
            timerId = setTimeout(function() {{ runAnimation(stepIdx + 1); }}, durMs);
        }}
        toggleBtn.onclick = function() {{
            if (playing) {{ playing = false; if (timerId) {{ clearTimeout(timerId); timerId = null; }} finishPlayback(); }}
            else {{ playing = true; setStopIcon(); hideAllPath(); runAnimation(0); }}
        }};
    }}
}})();
</script>
'''
        return html


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


class AnimatedRTSvgFigure:
    def __init__(self, svg_data, audio_payload=None, dur=0.5, glow=False):
        self.svg_data = svg_data
        self.audio_payload = audio_payload
        self.dur = dur
        self.glow = glow
        self.widget_id = f"klotho_svg_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        sd = self.svg_data
        wid = self.widget_id

        cdn_html = cdn_scripts(include_plotly=False, include_tone=bool(self.audio_payload))

        kernel_session = uuid.uuid4().hex
        session_script = f'<script>globalThis._KLOTHO_SESSION = "{kernel_session}";</script>'

        instruments_js = INSTRUMENTS_JS_PATH.read_text() if INSTRUMENTS_JS_PATH.exists() else ""
        player_js = PLAYER_JS_PATH.read_text() if PLAYER_JS_PATH.exists() else ""

        leaf_path_ids_json = json.dumps(sd.leaf_path_ids)
        all_anim_ids_json = json.dumps(sd.all_animated_ids)
        leaf_halo_ids_json = json.dumps(sd.leaf_halo_ids)
        leaf_x_json = json.dumps(sd.leaf_x_positions)
        bright_json = json.dumps(sd.leaf_bright_colors)
        base_json = json.dumps(sd.leaf_base_colors)

        node_to_ids_json = json.dumps({str(k): v for k, v in sd.node_to_ids.items()})
        leaf_ancestors_json = json.dumps([[str(n) for n in path] for path in sd.leaf_ancestors])

        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"

        html = f'''
{cdn_html}
{sd.svg_str}
<div id="{wid}_controls" style="
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 10px; background: #1a1a2e; border-radius: 6px;
    user-select: none; margin-top: 4px;">
    <button id="{wid}_toggle" style="
        width: 32px; height: 32px; border: none; border-radius: 4px;
        background: #16213e; cursor: pointer; display: flex;
        align-items: center; justify-content: center; padding: 0;">
        <span id="{wid}_icon" style="
            width: 0; height: 0;
            border-top: 7px solid transparent; border-bottom: 7px solid transparent;
            border-left: 12px solid #4ade80; margin-left: 3px;"></span>
    </button>
    <button id="{wid}_loop" style="
        width: 28px; height: 28px; border: none; border-radius: 4px;
        background: #16213e; cursor: pointer; display: flex;
        align-items: center; justify-content: center; padding: 0; opacity: 0.5;">
        <svg id="{wid}_loop_svg" width="16" height="16" viewBox="0 0 24 24"
             fill="none" stroke="#a0a0a0" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 2l4 4-4 4"></path><path d="M3 11v-1a4 4 0 0 1 4-4h14"></path>
            <path d="M7 22l-4-4 4-4"></path><path d="M21 13v1a4 4 0 0 1-4 4H3"></path>
        </svg>
    </button>
</div>
{session_script}
<script>{instruments_js}</script>
<script>{player_js}</script>
<script>
(function() {{
    var elCache = {{}};
    function getEl(id) {{ if (!elCache[id]) elCache[id] = document.getElementById(id); return elCache[id]; }}

    var leafPathIds = {leaf_path_ids_json};
    var allAnimIds = {all_anim_ids_json};
    var leafHaloIds = {leaf_halo_ids_json};
    var leafXPositions = {leaf_x_json};
    var brightColors = {bright_json};
    var baseColors = {base_json};
    var nodeToIds = {node_to_ids_json};
    var leafAncestors = {leaf_ancestors_json};
    var audioPayload = {payload_json};
    var glowEnabled = {'true' if self.glow else 'false'};
    var totalSteps = leafAncestors.length;

    var toggleBtn = document.getElementById("{wid}_toggle");
    var iconEl = document.getElementById("{wid}_icon");
    var loopBtn = document.getElementById("{wid}_loop");
    var loopSvg = document.getElementById("{wid}_loop_svg");

    var looping = false, playing = false;
    var prevPathSet = null, prevBrightened = [], prevHaloIds = [];

    function resetAll() {{
        for (var i = 0; i < prevBrightened.length; i++) {{ var el = getEl(prevBrightened[i].id); if (el) el.setAttribute("fill", prevBrightened[i].base); }}
        prevBrightened = [];
        for (var i = 0; i < prevHaloIds.length; i++) {{ var el = getEl(prevHaloIds[i]); if (el) el.style.display = "none"; }}
        prevHaloIds = [];
        for (var i = 0; i < allAnimIds.length; i++) {{ var el = getEl(allAnimIds[i]); if (el) el.style.opacity = ""; }}
        prevPathSet = null;
    }}

    function highlightLeaf(leafIdx) {{
        if (leafIdx < 0 || leafIdx >= totalSteps) return;
        var currIds = leafPathIds[leafIdx];
        var currSet = new Set(currIds);
        var leafNodeId = leafAncestors[leafIdx][leafAncestors[leafIdx].length - 1];
        var leafElIds = nodeToIds[leafNodeId] || [];

        if (prevPathSet === null) {{
            for (var i = 0; i < allAnimIds.length; i++) {{
                var el = getEl(allAnimIds[i]);
                if (el) el.style.opacity = currSet.has(allAnimIds[i]) ? "1" : "0.15";
            }}
        }} else {{
            prevPathSet.forEach(function(eid) {{ if (!currSet.has(eid)) {{ var el = getEl(eid); if (el) el.style.opacity = "0.15"; }} }});
            currSet.forEach(function(eid) {{ if (!prevPathSet.has(eid)) {{ var el = getEl(eid); if (el) el.style.opacity = "1"; }} }});
        }}

        for (var i = 0; i < prevBrightened.length; i++) {{ var el = getEl(prevBrightened[i].id); if (el) el.setAttribute("fill", prevBrightened[i].base); }}
        var newBrightened = [];
        for (var i = 0; i < leafElIds.length; i++) {{
            var eid = leafElIds[i], bright = brightColors[eid];
            if (bright) {{ var el = getEl(eid); if (el) {{ el.setAttribute("fill", bright); newBrightened.push({{id: eid, base: baseColors[eid]}}); }} }}
        }}

        for (var i = 0; i < prevHaloIds.length; i++) {{ var el = getEl(prevHaloIds[i]); if (el) el.style.display = "none"; }}
        var newHaloIds = [];
        if (leafIdx < leafHaloIds.length) {{
            var group = leafHaloIds[leafIdx];
            if (group && group.length > 0) {{
                var toShow = glowEnabled ? group : [group[group.length - 1]];
                for (var i = 0; i < toShow.length; i++) {{ var el = getEl(toShow[i]); if (el) el.style.display = ""; newHaloIds.push(toShow[i]); }}
            }}
        }}
        prevPathSet = currSet; prevBrightened = newBrightened; prevHaloIds = newHaloIds;
    }}

    function finishPlayback() {{ playing = false; resetAll(); setPlayIcon(); }}
    function setPlayIcon() {{ iconEl.style.cssText = "width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent;border-left:12px solid #4ade80;border-right:none;margin-left:3px;background:none"; }}
    function setStopIcon() {{ iconEl.style.cssText = "width:12px;height:12px;border:none;border-radius:2px;margin-left:0;background:#ef4444"; }}

    loopBtn.onclick = function() {{ looping = !looping; loopBtn.style.opacity = looping ? "1" : "0.5"; loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0"); }};

    if (audioPayload && typeof Tone !== "undefined") {{
        var events = audioPayload.events || [];
        var instruments = globalThis.KLOTHO_BUILD_INSTRUMENTS(audioPayload.instruments || {{}});
        var player = KlothoPlayer.create();
        toggleBtn.onclick = async function() {{
            if (player.isPlaying()) {{ player.stop(); }}
            else {{
                playing = true; setStopIcon();
                await player.play(events, instruments, {{
                    loop: looping,
                    onEvent: function(stepIdx) {{ highlightLeaf(stepIdx); }},
                    onStop: function() {{ finishPlayback(); }},
                    onFinish: function() {{ finishPlayback(); }}
                }});
            }}
        }};
    }} else {{
        var durMs = {self.dur * 1000};
        var timerId = null;
        function runAnimation(stepIdx) {{
            if (!playing) return;
            if (stepIdx >= totalSteps) {{ if (looping) {{ timerId = setTimeout(function() {{ runAnimation(0); }}, durMs); }} else {{ finishPlayback(); }} return; }}
            highlightLeaf(stepIdx);
            timerId = setTimeout(function() {{ runAnimation(stepIdx + 1); }}, durMs);
        }}
        toggleBtn.onclick = function() {{
            if (playing) {{ playing = false; if (timerId) {{ clearTimeout(timerId); timerId = null; }} finishPlayback(); }}
            else {{ playing = true; setStopIcon(); runAnimation(0); }}
        }};
    }}
}})();
</script>
'''
        return html


class AnimatedLatticeSvgFigure:
    def __init__(self, svg_data, audio_payload=None, dur=0.5):
        self.svg_data = svg_data
        self.audio_payload = audio_payload
        self.dur = dur
        self.widget_id = f"klotho_slat_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        sd = self.svg_data
        wid = self.widget_id

        cdn_html = cdn_scripts(include_plotly=False, include_tone=bool(self.audio_payload))

        kernel_session = uuid.uuid4().hex
        session_script = f'<script>globalThis._KLOTHO_SESSION = "{kernel_session}";</script>'

        instruments_js = INSTRUMENTS_JS_PATH.read_text() if INSTRUMENTS_JS_PATH.exists() else ""
        player_js = PLAYER_JS_PATH.read_text() if PLAYER_JS_PATH.exists() else ""

        steps_json = json.dumps(sd.step_group_ids)
        halos_json = json.dumps(sd.halo_ids)
        all_path_json = json.dumps(sd.all_path_ids)
        node_ids_json = json.dumps(getattr(sd, 'all_node_ids', []))
        path_node_indices_json = json.dumps(getattr(sd, 'path_node_indices', []))
        dimmed_color = getattr(sd, 'dimmed_node_color', '#111111')
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"

        html = f'''
{cdn_html}
{sd.svg_str}
<div id="{wid}_controls" style="
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 10px; background: #1a1a2e; border-radius: 6px;
    user-select: none; margin-top: 4px;">
    <button id="{wid}_toggle" style="
        width: 32px; height: 32px; border: none; border-radius: 4px;
        background: #16213e; cursor: pointer; display: flex;
        align-items: center; justify-content: center; padding: 0;">
        <span id="{wid}_icon" style="
            width: 0; height: 0;
            border-top: 7px solid transparent; border-bottom: 7px solid transparent;
            border-left: 12px solid #4ade80; margin-left: 3px;"></span>
    </button>
    <button id="{wid}_loop" style="
        width: 28px; height: 28px; border: none; border-radius: 4px;
        background: #16213e; cursor: pointer; display: flex;
        align-items: center; justify-content: center; padding: 0; opacity: 0.5;">
        <svg id="{wid}_loop_svg" width="16" height="16" viewBox="0 0 24 24"
             fill="none" stroke="#a0a0a0" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 2l4 4-4 4"></path><path d="M3 11v-1a4 4 0 0 1 4-4h14"></path>
            <path d="M7 22l-4-4 4-4"></path><path d="M21 13v1a4 4 0 0 1-4 4H3"></path>
        </svg>
    </button>
</div>
{session_script}
<script>{instruments_js}</script>
<script>{player_js}</script>
<script>
(function() {{
    var steps = {steps_json};
    var haloIds = {halos_json};
    var allPathIds = {all_path_json};
    var audioPayload = {payload_json};
    var allNodeIds = {node_ids_json};
    var pathNodeIndices = {path_node_indices_json};
    var dimmedColor = "{dimmed_color}";
    var totalSteps = steps.length;

    var toggleBtn = document.getElementById("{wid}_toggle");
    var iconEl = document.getElementById("{wid}_icon");
    var loopBtn = document.getElementById("{wid}_loop");
    var loopSvg = document.getElementById("{wid}_loop_svg");

    var looping = false, playing = false;

    function dimAllNodes() {{
        for (var i = 0; i < allNodeIds.length; i++) {{
            var el = document.getElementById(allNodeIds[i]);
            if (el) el.setAttribute("fill", dimmedColor);
        }}
    }}
    function highlightAllPathNodes() {{
        for (var i = 0; i < pathNodeIndices.length; i++) {{
            var idx = pathNodeIndices[i];
            if (idx >= 0 && idx < allNodeIds.length) {{
                var el = document.getElementById(allNodeIds[idx]);
                if (el) el.setAttribute("fill", "white");
            }}
        }}
    }}
    function highlightNodeAt(stepIdx) {{
        if (stepIdx >= 0 && stepIdx < pathNodeIndices.length) {{
            var idx = pathNodeIndices[stepIdx];
            if (idx >= 0 && idx < allNodeIds.length) {{
                var el = document.getElementById(allNodeIds[idx]);
                if (el) el.setAttribute("fill", "white");
            }}
        }}
    }}

    function hideAllPath() {{
        for (var i = 0; i < allPathIds.length; i++) {{
            var el = document.getElementById(allPathIds[i]);
            if (el) el.style.display = "none";
        }}
        dimAllNodes();
    }}

    function showAllPath() {{
        for (var i = 0; i < allPathIds.length; i++) {{
            var el = document.getElementById(allPathIds[i]);
            if (el) el.style.display = "";
        }}
        highlightAllPathNodes();
    }}

    function revealStep(stepIdx) {{
        if (stepIdx === 0) {{
            hideAllPath();
            if (haloIds.length > 0) {{
                var el = document.getElementById(haloIds[0]);
                if (el) el.style.display = "";
            }}
            highlightNodeAt(0);
            return;
        }}
        var edgeIdx = stepIdx - 1;
        if (edgeIdx >= 0 && edgeIdx < steps.length) {{
            var group = steps[edgeIdx];
            if (group) {{
                for (var i = 0; i < group.length; i++) {{
                    var el = document.getElementById(group[i]);
                    if (el) el.style.display = "";
                }}
            }}
        }}
        highlightNodeAt(stepIdx);
        if (stepIdx === (audioPayload ? audioPayload.events.length - 1 : totalSteps) && haloIds.length > 1) {{
            var el = document.getElementById(haloIds[1]);
            if (el) el.style.display = "";
        }}
    }}

    function finishPlayback() {{ playing = false; showAllPath(); setPlayIcon(); }}
    function setPlayIcon() {{ iconEl.style.cssText = "width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent;border-left:12px solid #4ade80;border-right:none;margin-left:3px;background:none"; }}
    function setStopIcon() {{ iconEl.style.cssText = "width:12px;height:12px;border:none;border-radius:2px;margin-left:0;background:#ef4444"; }}

    loopBtn.onclick = function() {{ looping = !looping; loopBtn.style.opacity = looping ? "1" : "0.5"; loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0"); }};

    if (audioPayload && typeof Tone !== "undefined") {{
        var events = audioPayload.events || [];
        var instruments = globalThis.KLOTHO_BUILD_INSTRUMENTS(audioPayload.instruments || {{}});
        var player = KlothoPlayer.create();
        toggleBtn.onclick = async function() {{
            if (player.isPlaying()) {{ player.stop(); }}
            else {{
                playing = true; setStopIcon(); hideAllPath();
                await player.play(events, instruments, {{
                    loop: looping,
                    onEvent: function(stepIdx) {{ revealStep(stepIdx); }},
                    onStop: function() {{ finishPlayback(); }},
                    onFinish: function() {{ finishPlayback(); }}
                }});
            }}
        }};
    }} else {{
        var durMs = {self.dur * 1000};
        var timerId = null;
        function runAnimation(stepIdx) {{
            if (!playing) return;
            if (stepIdx > totalSteps) {{ if (looping) {{ hideAllPath(); timerId = setTimeout(function() {{ runAnimation(0); }}, durMs); }} else {{ finishPlayback(); }} return; }}
            revealStep(stepIdx);
            timerId = setTimeout(function() {{ runAnimation(stepIdx + 1); }}, durMs);
        }}
        toggleBtn.onclick = function() {{
            if (playing) {{ playing = false; if (timerId) {{ clearTimeout(timerId); timerId = null; }} finishPlayback(); }}
            else {{ playing = true; setStopIcon(); hideAllPath(); runAnimation(0); }}
        }};
    }}
}})();
</script>
'''
        return html
