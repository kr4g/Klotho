import json
import uuid

from klotho.utils.playback.tonejs.cdn import (
    cdn_scripts, reset_cdn_flags,
    INSTRUMENTS_JS_PATH, PLAYER_JS_PATH,
    THREEJS_CDN, THREEJS_ORBIT_CDN,
)

from ._animation_base import (
    build_session_preamble, build_control_bar_html,
    build_nav_controls_html, build_scripts_html, build_playback_js,
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

        cdn_html, session_script, instruments_js, player_js = build_session_preamble(
            include_tone=bool(self.audio_payload), include_threejs=True)
        controls_html = build_control_bar_html(wid)
        scripts_html = build_scripts_html(session_script, instruments_js, player_js)

        scene_json = json.dumps(sd.scene_data)
        steps_json = json.dumps(sd.path_steps)
        halo_json = json.dumps(sd.halo_data)
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"

        w = sd.width_px
        h = sd.height_px
        title_escaped = sd.title.replace("'", "\\'").replace('"', '\\"')

        threejs_cdn = THREEJS_CDN
        orbit_cdn = THREEJS_ORBIT_CDN

        playback_js = build_playback_js(wid, self.dur * 1000)

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
{controls_html}
{scripts_html}
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
    var pathNodeIndices = sceneData.pathNodeIndices || [];
    var pathNodeColors = sceneData.pathNodeColors || [];

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
            var col = pathNodeColors[i] || "#ffffff";
            if (idx >= 0 && idx < nodeMeshes.length) nodeMeshes[idx].material.color.set(col);
        }}
    }}
    function highlightNodeAt(stepIdx) {{
        if (stepIdx >= 0 && stepIdx < pathNodeIndices.length) {{
            var idx = pathNodeIndices[stepIdx];
            var col = pathNodeColors[stepIdx] || "#ffffff";
            if (idx >= 0 && idx < nodeMeshes.length) nodeMeshes[idx].material.color.set(col);
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

    function makeHaloSprite(hex, size) {{
        var c2 = document.createElement("canvas");
        c2.width = 64; c2.height = 64;
        var ctx = c2.getContext("2d");
        var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
        var grad = ctx.createRadialGradient(32,32,0, 32,32,32);
        grad.addColorStop(0, "rgba("+r+","+g+","+b+",0.6)");
        grad.addColorStop(0.7, "rgba("+r+","+g+","+b+",0.15)");
        grad.addColorStop(1, "rgba("+r+","+g+","+b+",0)");
        ctx.fillStyle = grad;
        ctx.fillRect(0,0,64,64);
        var tex = new THREE.CanvasTexture(c2);
        var mat = new THREE.SpriteMaterial({{ map: tex, transparent: true }});
        var sprite = new THREE.Sprite(mat);
        sprite.scale.set(size, size, 1);
        return sprite;
    }}

    var startHalo = null, endHalo = null;
    if (haloData) {{
        startHalo = makeHaloSprite(haloData.start.color, 0.55);
        startHalo.position.set(haloData.start.pos[0], haloData.start.pos[1], haloData.start.pos[2]);
        startHalo.visible = true;
        scene.add(startHalo);

        endHalo = makeHaloSprite(haloData.end.color, 0.55);
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

    function onReset() {{ showAllPath(); }}
    function onBeforePlay() {{ hideAllPath(); }}
    function onStep(stepIdx) {{ revealStep(stepIdx); }}

    {playback_js}
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

        cdn_html, session_script, instruments_js, player_js = build_session_preamble(
            include_plotly=True, include_tone=bool(self.audio_payload))
        controls_html = build_control_bar_html(self.widget_id)
        scripts_html = build_scripts_html(session_script, instruments_js, player_js)

        steps_json = json.dumps(self.step_trace_groups)
        halos_json = json.dumps(self.halo_indices)
        all_path_json = json.dumps(self.all_path_indices)
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"
        wid = self.widget_id

        playback_js = build_playback_js(wid, self.dur * 1000)

        html = f'''
{cdn_html}
<div id="{plot_div_id}" class="plotly-graph-div" style="height:{fig_h}px; width:{fig_w}px;"></div>
{controls_html}
{scripts_html}
<script>
(function _klothoInit() {{
    if (typeof Plotly === "undefined") {{ setTimeout(_klothoInit, 50); return; }}

    var _fig = {fig_json};
    var plotDiv = document.getElementById("{plot_div_id}");
    Plotly.newPlot(plotDiv, _fig.data, _fig.layout, {{responsive: true}});

    var steps = {steps_json};
    var haloIndices = {halos_json};
    var allPathIndices = {all_path_json};
    var audioPayload = {payload_json};
    var totalSteps = steps.length;

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

    function onReset() {{ showAllPath(); }}
    function onBeforePlay() {{ hideAllPath(); }}
    function onStep(stepIdx) {{ revealStep(stepIdx); }}

    {playback_js}
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

        cdn_html, session_script, instruments_js, player_js = build_session_preamble(
            include_plotly=True, include_tone=bool(self.audio_payload))
        controls_html = build_control_bar_html(self.widget_id)
        scripts_html = build_scripts_html(session_script, instruments_js, player_js)

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

        playback_js = build_playback_js(wid, self.dur * 1000, use_gt_for_boundary=False)

        html = f'''
{cdn_html}
<div id="{plot_div_id}" class="plotly-graph-div" style="height:{fig_h}px; width:{fig_w}px;"></div>
{controls_html}
{scripts_html}
<script>
(function _klothoInit() {{
    if (typeof Plotly === "undefined") {{ setTimeout(_klothoInit, 50); return; }}

    var _fig = {fig_json};
    var plotDiv = document.getElementById("{plot_div_id}");
    Plotly.newPlot(plotDiv, _fig.data, _fig.layout, {{responsive: true}});

    var nodeToTraces = {node_to_traces_json};
    var leafAncestors = {leaf_ancestors_json};
    var allAnimatedTraces = {all_anim_json};
    var leafXPositions = {leaf_x_json};
    var leafHaloGroups = {halo_groups_json};
    var glowEnabled = {'true' if self.glow else 'false'};
    var traceBrightColors = {bright_colors_json};
    var traceBaseColors = {base_colors_json};
    var audioPayload = {payload_json};
    var leafPathTraces = {leaf_path_traces_json};
    var totalSteps = leafAncestors.length;

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

    function onReset() {{ resetAll(); }}
    function onBeforePlay() {{}}
    function onStep(stepIdx) {{ highlightLeaf(stepIdx); }}

    {playback_js}
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

        cdn_html, session_script, instruments_js, player_js = build_session_preamble(
            include_tone=bool(self.audio_payload))
        controls_html = build_control_bar_html(wid)
        scripts_html = build_scripts_html(session_script, instruments_js, player_js)

        leaf_path_ids_json = json.dumps(sd.leaf_path_ids)
        all_anim_ids_json = json.dumps(sd.all_animated_ids)
        leaf_halo_ids_json = json.dumps(sd.leaf_halo_ids)
        leaf_x_json = json.dumps(sd.leaf_x_positions)
        bright_json = json.dumps(sd.leaf_bright_colors)
        base_json = json.dumps(sd.leaf_base_colors)

        node_to_ids_json = json.dumps({str(k): v for k, v in sd.node_to_ids.items()})
        leaf_ancestors_json = json.dumps([[str(n) for n in path] for path in sd.leaf_ancestors])

        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"

        playback_js = build_playback_js(wid, self.dur * 1000, use_gt_for_boundary=False)

        html = f'''
{cdn_html}
{sd.svg_str}
{controls_html}
{scripts_html}
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

    function onReset() {{ resetAll(); }}
    function onBeforePlay() {{}}
    function onStep(stepIdx) {{ highlightLeaf(stepIdx); }}

    {playback_js}
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

        cdn_html, session_script, instruments_js, player_js = build_session_preamble(
            include_tone=bool(self.audio_payload))
        controls_html = build_control_bar_html(wid)
        scripts_html = build_scripts_html(session_script, instruments_js, player_js)

        steps_json = json.dumps(sd.step_group_ids)
        halos_json = json.dumps(sd.halo_ids)
        all_path_json = json.dumps(sd.all_path_ids)
        node_ids_json = json.dumps(getattr(sd, 'all_node_ids', []))
        path_node_indices_json = json.dumps(getattr(sd, 'path_node_indices', []))
        path_node_colors_json = json.dumps(getattr(sd, 'path_node_colors', []))
        dimmed_color = getattr(sd, 'dimmed_node_color', '#111111')
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"

        playback_js = build_playback_js(wid, self.dur * 1000)

        html = f'''
{cdn_html}
{sd.svg_str}
{controls_html}
{scripts_html}
<script>
(function() {{
    var steps = {steps_json};
    var haloIds = {halos_json};
    var allPathIds = {all_path_json};
    var audioPayload = {payload_json};
    var allNodeIds = {node_ids_json};
    var pathNodeIndices = {path_node_indices_json};
    var pathNodeColors = {path_node_colors_json};
    var dimmedColor = "{dimmed_color}";
    var totalSteps = steps.length;

    function dimAllNodes() {{
        for (var i = 0; i < allNodeIds.length; i++) {{
            var el = document.getElementById(allNodeIds[i]);
            if (el) el.setAttribute("fill", dimmedColor);
        }}
    }}
    function highlightAllPathNodes() {{
        for (var i = 0; i < pathNodeIndices.length; i++) {{
            var idx = pathNodeIndices[i];
            var col = pathNodeColors[i] || "white";
            if (idx >= 0 && idx < allNodeIds.length) {{
                var el = document.getElementById(allNodeIds[idx]);
                if (el) el.setAttribute("fill", col);
            }}
        }}
    }}
    function highlightNodeAt(stepIdx) {{
        if (stepIdx >= 0 && stepIdx < pathNodeIndices.length) {{
            var idx = pathNodeIndices[stepIdx];
            var col = pathNodeColors[stepIdx] || "white";
            if (idx >= 0 && idx < allNodeIds.length) {{
                var el = document.getElementById(allNodeIds[idx]);
                if (el) el.setAttribute("fill", col);
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

    function onReset() {{ showAllPath(); }}
    function onBeforePlay() {{ hideAllPath(); }}
    function onStep(stepIdx) {{ revealStep(stepIdx); }}

    {playback_js}
}})();
</script>
'''
        return html


AnimatedCPSSvgFigure = AnimatedLatticeSvgFigure


class _AnimatedShapeFigureBase:
    def __init__(self, svg_data, audio_payload=None, dur=0.5):
        self.svg_data = svg_data
        self.audio_payload = audio_payload
        self.dur = dur
        self.widget_id = f"klotho_shp_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        sd = self.svg_data
        wid = self.widget_id

        cdn_html, session_script, instruments_js, player_js = build_session_preamble(
            include_tone=bool(self.audio_payload))
        controls_html = build_control_bar_html(wid)
        scripts_html = build_scripts_html(session_script, instruments_js, player_js)

        group_node_indices_json = json.dumps(sd.shape_group_node_indices)
        group_edge_ids_json = json.dumps(sd.shape_group_edge_ids)
        shape_colors_json = json.dumps(sd.shape_colors)
        all_shape_edge_ids_json = json.dumps(sd.all_shape_edge_ids)
        node_ids_json = json.dumps(sd.all_node_ids)
        dimmed_color = sd.dimmed_node_color
        payload_json = json.dumps(self.audio_payload) if self.audio_payload else "null"
        total_groups = len(sd.shape_group_node_indices)
        is_multi = total_groups > 1

        nav_display = "inline-flex" if is_multi else "none"

        html = f'''
{cdn_html}
{sd.svg_str}
{controls_html}
    <div id="{wid}_nav" style="display:{nav_display};align-items:center;gap:4px;margin-left:4px;">
        <button id="{wid}_prev" style="
            width:24px;height:24px;border:none;border-radius:4px;
            background:#16213e;cursor:pointer;display:flex;
            align-items:center;justify-content:center;padding:0;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                 stroke="#a0a0a0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
        </button>
        <span id="{wid}_counter" style="color:#a0a0a0;font-size:11px;min-width:36px;text-align:center;">1 / {total_groups}</span>
        <button id="{wid}_next" style="
            width:24px;height:24px;border:none;border-radius:4px;
            background:#16213e;cursor:pointer;display:flex;
            align-items:center;justify-content:center;padding:0;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                 stroke="#a0a0a0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
        </button>
        <label style="display:inline-flex;align-items:center;gap:3px;margin-left:6px;cursor:pointer;">
            <input id="{wid}_solo" type="checkbox" style="
                width:13px;height:13px;accent-color:#4ade80;cursor:pointer;margin:0;">
            <span style="color:#a0a0a0;font-size:11px;">solo</span>
        </label>
    </div>
{scripts_html}
<script>
(function() {{
    var groupNodeIndices = {group_node_indices_json};
    var groupEdgeIds = {group_edge_ids_json};
    var shapeColors = {shape_colors_json};
    var allShapeEdgeIds = {all_shape_edge_ids_json};
    var allNodeIds = {node_ids_json};
    var dimmedColor = "{dimmed_color}";
    var audioPayload = {payload_json};
    var totalGroups = {total_groups};

    var toggleBtn = document.getElementById("{wid}_toggle");
    var iconEl = document.getElementById("{wid}_icon");
    var loopBtn = document.getElementById("{wid}_loop");
    var loopSvg = document.getElementById("{wid}_loop_svg");
    var prevBtn = document.getElementById("{wid}_prev");
    var nextBtn = document.getElementById("{wid}_next");
    var counterEl = document.getElementById("{wid}_counter");
    var soloBox = document.getElementById("{wid}_solo");
    var looping = false, playing = false;
    var currentView = 0;
    var playbackOrigin = 0;

    function updateCounter() {{
        if (counterEl) counterEl.textContent = (currentView + 1) + " / " + totalGroups;
    }}

    function dimAllNodes() {{
        for (var i = 0; i < allNodeIds.length; i++) {{
            var el = document.getElementById(allNodeIds[i]);
            if (el) el.setAttribute("fill", dimmedColor);
        }}
    }}
    function hideAllShapeEdges() {{
        for (var i = 0; i < allShapeEdgeIds.length; i++) {{
            var el = document.getElementById(allShapeEdgeIds[i]);
            if (el) el.style.display = "none";
        }}
    }}
    function revealGroup(gi) {{
        dimAllNodes();
        hideAllShapeEdges();
        if (gi < 0 || gi >= totalGroups) return;
        var col = shapeColors[gi] || "white";
        var nodeIdxs = groupNodeIndices[gi] || [];
        for (var i = 0; i < nodeIdxs.length; i++) {{
            var idx = nodeIdxs[i];
            if (idx >= 0 && idx < allNodeIds.length) {{
                var el = document.getElementById(allNodeIds[idx]);
                if (el) el.setAttribute("fill", col);
            }}
        }}
        var edgeIds = groupEdgeIds[gi] || [];
        for (var i = 0; i < edgeIds.length; i++) {{
            var el = document.getElementById(edgeIds[i]);
            if (el) el.style.display = "";
        }}
    }}
    function revealAndTrack(gi) {{
        currentView = gi;
        revealGroup(gi);
        updateCounter();
    }}
    function restoreView() {{ revealGroup(currentView); updateCounter(); }}
    function finishPlayback() {{ playing = false; currentView = playbackOrigin; restoreView(); setPlayIcon(); }}
    function setPlayIcon() {{ iconEl.style.cssText = "width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent;border-left:12px solid #4ade80;border-right:none;margin-left:3px;background:none"; }}
    function setStopIcon() {{ iconEl.style.cssText = "width:12px;height:12px;border:none;border-radius:2px;margin-left:0;background:#ef4444"; }}

    function filterEventsForGroup(allEvents, gi) {{
        var filtered = [];
        var minStart = Infinity;
        for (var i = 0; i < allEvents.length; i++) {{
            if (allEvents[i]._stepIndex === gi) {{
                if (allEvents[i].start < minStart) minStart = allEvents[i].start;
                filtered.push(allEvents[i]);
            }}
        }}
        if (minStart === Infinity) minStart = 0;
        var result = [];
        for (var i = 0; i < filtered.length; i++) {{
            var e = {{}};
            for (var k in filtered[i]) e[k] = filtered[i][k];
            e.start = filtered[i].start - minStart;
            e._stepIndex = 0;
            result.push(e);
        }}
        return result;
    }}

    function reorderEventsFrom(allEvents, startGi, total) {{
        var buckets = [];
        for (var g = 0; g < total; g++) buckets.push([]);
        for (var i = 0; i < allEvents.length; i++) {{
            var si = allEvents[i]._stepIndex;
            if (si >= 0 && si < total) buckets[si].push(allEvents[i]);
        }}
        var groupStarts = [];
        for (var g = 0; g < total; g++) {{
            var mn = Infinity;
            for (var i = 0; i < buckets[g].length; i++) {{
                if (buckets[g][i].start < mn) mn = buckets[g][i].start;
            }}
            groupStarts.push(mn === Infinity ? 0 : mn);
        }}
        var groupDurs = [];
        for (var g = 0; g < total; g++) {{
            var mx = 0;
            for (var i = 0; i < buckets[g].length; i++) {{
                var end = buckets[g][i].start + buckets[g][i].duration;
                if (end > mx) mx = end;
            }}
            groupDurs.push(mx - groupStarts[g]);
        }}
        var result = [];
        var cursor = 0;
        var seqMap = [];
        for (var step = 0; step < total; step++) {{
            var gi = (startGi + step) % total;
            seqMap.push(gi);
            var base = groupStarts[gi];
            for (var i = 0; i < buckets[gi].length; i++) {{
                var e = {{}};
                for (var k in buckets[gi][i]) e[k] = buckets[gi][i][k];
                e.start = cursor + (buckets[gi][i].start - base);
                e._stepIndex = step;
                result.push(e);
            }}
            cursor += groupDurs[gi];
        }}
        return {{ events: result, seqMap: seqMap }};
    }}

    if (totalGroups > 0) {{
        revealGroup(0);
        updateCounter();
    }}

    if (prevBtn) {{
        prevBtn.onclick = function() {{
            if (playing) return;
            currentView = (currentView - 1 + totalGroups) % totalGroups;
            revealGroup(currentView);
            updateCounter();
        }};
    }}
    if (nextBtn) {{
        nextBtn.onclick = function() {{
            if (playing) return;
            currentView = (currentView + 1) % totalGroups;
            revealGroup(currentView);
            updateCounter();
        }};
    }}

    loopBtn.onclick = function() {{ looping = !looping; loopBtn.style.opacity = looping ? "1" : "0.5"; loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0"); }};

    if (audioPayload && typeof Tone !== "undefined") {{
        var allEvents = audioPayload.events || [];
        var instruments = globalThis.KLOTHO_BUILD_INSTRUMENTS(audioPayload.instruments || {{}});
        var player = KlothoPlayer.create();
        toggleBtn.onclick = async function() {{
            if (player.isPlaying()) {{ player.stop(); }}
            else {{
                var solo = soloBox && soloBox.checked;
                playbackOrigin = currentView;
                playing = true; setStopIcon();
                if (solo) {{
                    var soloEvents = filterEventsForGroup(allEvents, currentView);
                    revealAndTrack(currentView);
                    await player.play(soloEvents, instruments, {{
                        loop: looping,
                        onEvent: function() {{}},
                        onStop: function() {{ finishPlayback(); }},
                        onFinish: function() {{ finishPlayback(); }}
                    }});
                }} else {{
                    var reordered = reorderEventsFrom(allEvents, currentView, totalGroups);
                    dimAllNodes(); hideAllShapeEdges();
                    await player.play(reordered.events, instruments, {{
                        loop: looping,
                        onEvent: function(stepIdx) {{ revealAndTrack(reordered.seqMap[stepIdx]); }},
                        onStop: function() {{ finishPlayback(); }},
                        onFinish: function() {{ finishPlayback(); }}
                    }});
                }}
            }}
        }};
    }} else {{
        var durMs = {self.dur * 1000};
        var timerId = null;
        function runAnimation(step) {{
            if (!playing) return;
            if (step >= totalGroups) {{ if (looping) {{ dimAllNodes(); hideAllShapeEdges(); timerId = setTimeout(function() {{ runAnimation(0); }}, durMs); }} else {{ finishPlayback(); }} return; }}
            var gi = (currentView + step) % totalGroups;
            revealAndTrack(gi);
            timerId = setTimeout(function() {{ runAnimation(step + 1); }}, durMs);
        }}
        toggleBtn.onclick = function() {{
            if (playing) {{ playing = false; if (timerId) {{ clearTimeout(timerId); timerId = null; }} finishPlayback(); }}
            else {{
                playbackOrigin = currentView;
                playing = true; setStopIcon(); dimAllNodes(); hideAllShapeEdges();
                runAnimation(0);
            }}
        }};
    }}
}})();
</script>
'''
        return html


AnimatedCPSShapeFigure = _AnimatedShapeFigureBase
AnimatedLatticeShapeFigure = _AnimatedShapeFigureBase
