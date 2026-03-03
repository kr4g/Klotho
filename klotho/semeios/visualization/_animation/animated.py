import json
import uuid

from klotho.utils.playback.tonejs.cdn import (
    cdn_scripts,
    INSTRUMENTS_JS_PATH, PLAYER_JS_PATH,
    THREEJS_CDN, THREEJS_ORBIT_CDN, THREEJS_TRACKBALL_CDN,
)
from klotho.utils.playback._config import get_audio_engine
from klotho.utils.playback.animation_events import normalize_animation_payload_for_engine

from .base import (
    build_session_preamble, build_control_bar_html,
    build_nav_controls_html, build_scripts_html, build_playback_js,
    build_shape_playback_js,
)


def _maybe_convert_payload(audio_payload, engine):
    return normalize_animation_payload_for_engine(audio_payload, engine)


class AnimatedLattice3dFigure:
    """Animated Three.js 3D lattice figure with step-by-step path reveal.

    Wraps a ``ThreejsLatticeData`` scene with playback controls that
    progressively show path edges and update node colours.  Optional
    audio events are dispatched through the Tone.js player.

    Parameters
    ----------
    scene_data : ThreejsLatticeData
        Pre-built Three.js scene descriptor.
    audio_payload : dict or None, optional
        Tone.js-compatible event payload for audio playback.
    dur : float, optional
        Seconds between animation steps.
    """

    def __init__(self, scene_data, audio_payload=None, dur=0.5, engine=None, ring_time=5, loop=False):
        self.scene_data = scene_data
        self.audio_payload = audio_payload
        self.dur = dur
        self.ring_time = ring_time
        self.loop = loop
        self.engine = engine or get_audio_engine()
        self.widget_id = f"klotho_3d_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        """Return a self-contained HTML string for Jupyter display."""
        sd = self.scene_data
        wid = self.widget_id
        eng = self.engine

        cdn_html, instruments_js, player_js = build_session_preamble(
            include_tone=(bool(self.audio_payload) and eng == "tone"),
            include_threejs=True,
            engine=eng)
        controls_html = build_control_bar_html(wid)
        scripts_html = build_scripts_html(instruments_js, player_js, engine=eng)

        scene_json = json.dumps(sd.scene_data)
        steps_json = json.dumps(sd.path_steps)
        halo_json = json.dumps(sd.halo_data)
        converted = _maybe_convert_payload(self.audio_payload, eng)
        payload_json = json.dumps(converted) if converted else "null"

        w = sd.width_px
        h = sd.height_px
        title_escaped = sd.title.replace("'", "\\'").replace('"', '\\"')

        threejs_cdn = THREEJS_CDN
        orbit_cdn = THREEJS_ORBIT_CDN
        trackball_cdn = THREEJS_TRACKBALL_CDN

        playback_js = build_playback_js(wid, self.dur * 1000, engine=eng, ring_time=self.ring_time, loop=self.loop)

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
    <div id="{wid}_transport" style="
        display:flex;align-items:center;gap:12px;
        background:#1a1a1a;padding:4px 10px;font-family:Arial,sans-serif;
        font-size:11px;color:#aaa;width:{w}px;box-sizing:border-box;
    ">
        <label style="display:flex;align-items:center;gap:4px;white-space:nowrap;">
            Node size
            <input id="{wid}_nodeSize" type="range" min="0.5" max="10" step="0.5" value="2"
                   style="width:80px;accent-color:#666;">
        </label>
        <span style="flex:1;"></span>
        <button id="{wid}_btnReset" style="
            background:#222;color:#aaa;border:1px solid #444;border-radius:3px;
            padding:1px 8px;font-size:11px;cursor:pointer;
        ">Reset</button>
        <button id="{wid}_btnOrbit" style="
            background:#444;color:white;border:1px solid #666;border-radius:3px;
            padding:1px 8px;font-size:11px;cursor:pointer;
        ">Orbit</button>
        <button id="{wid}_btnTrackball" style="
            background:#222;color:#888;border:1px solid #444;border-radius:3px;
            padding:1px 8px;font-size:11px;cursor:pointer;
        ">Trackball</button>
    </div>
</div>
{controls_html}
{scripts_html}
<script>
(typeof requestIdleCallback==='function'?requestIdleCallback:function(f){{setTimeout(f,0)}})(function _klotho3dInit() {{
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
    if (!THREE.TrackballControls) {{
        if (!document.querySelector('script[data-klotho-trackball]')) {{
            var s = document.createElement("script");
            s.src = "{trackball_cdn}";
            s.setAttribute("data-klotho-trackball", "1");
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
    var dist = (span / 2) / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    dist *= 1.3;
    camera.position.set(cx + dist * 0.6, cy + dist * 0.4, cz + dist);
    camera.lookAt(cx, cy, cz);

    var initPos = camera.position.clone();
    var initUp = camera.up.clone();
    var initTarget = new THREE.Vector3(cx, cy, cz);

    if (canvas._klothoRenderer) {{
        try {{ canvas._klothoRenderer.dispose(); }} catch(_) {{}}
    }}
    var renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true }});
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    canvas._klothoRenderer = renderer;

    function makeOrbitControls() {{
        var c = new THREE.OrbitControls(camera, renderer.domElement);
        c.target.set(cx, cy, cz);
        c.enableDamping = true;
        c.dampingFactor = 0.12;
        c.update();
        return c;
    }}
    function makeTrackballControls() {{
        var c = new THREE.TrackballControls(camera, renderer.domElement);
        c.target.set(cx, cy, cz);
        c.rotateSpeed = 2.0;
        c.zoomSpeed = 1.2;
        c.panSpeed = 0.8;
        c.staticMoving = false;
        c.dynamicDampingFactor = 0.12;
        c.update();
        return c;
    }}

    var controls = makeOrbitControls();
    var controlsMode = "orbit";

    function switchControls(mode) {{
        if (mode === controlsMode) return;
        var oldTarget = controls.target.clone();
        controls.dispose();
        if (mode === "trackball") {{
            controls = makeTrackballControls();
        }} else {{
            controls = makeOrbitControls();
        }}
        controls.target.copy(oldTarget);
        controls.update();
        controlsMode = mode;
        btnOrbit.style.background = mode === "orbit" ? "#444" : "#222";
        btnOrbit.style.color = mode === "orbit" ? "white" : "#888";
        btnOrbit.style.borderColor = mode === "orbit" ? "#666" : "#444";
        btnTrackball.style.background = mode === "trackball" ? "#444" : "#222";
        btnTrackball.style.color = mode === "trackball" ? "white" : "#888";
        btnTrackball.style.borderColor = mode === "trackball" ? "#666" : "#444";
    }}

    var btnOrbit = document.getElementById("{wid}_btnOrbit");
    var btnTrackball = document.getElementById("{wid}_btnTrackball");
    var btnReset = document.getElementById("{wid}_btnReset");
    btnOrbit.addEventListener("click", function() {{ switchControls("orbit"); }});
    btnTrackball.addEventListener("click", function() {{ switchControls("trackball"); }});

    var baseNodeSize = sceneData.nodeSize;
    var nodeSizeSlider = document.getElementById("{wid}_nodeSize");
    nodeSizeSlider.value = baseNodeSize;
    nodeSizeSlider.addEventListener("input", function() {{
        var s = parseFloat(this.value) / baseNodeSize;
        for (var i = 0; i < nodeMeshes.length; i++) nodeMeshes[i].scale.setScalar(s);
    }});

    btnReset.addEventListener("click", function() {{
        camera.position.copy(initPos);
        camera.up.copy(initUp);
        camera.lookAt(initTarget);
        controls.dispose();
        if (controlsMode === "trackball") {{
            controls = makeTrackballControls();
        }} else {{
            controls = makeOrbitControls();
        }}
        controls.target.copy(initTarget);
        controls.update();
        nodeSizeSlider.value = baseNodeSize;
        for (var i = 0; i < nodeMeshes.length; i++) nodeMeshes[i].scale.setScalar(1);
    }});

    (function renderLoop() {{
        requestAnimationFrame(renderLoop);
        controls.update();
        renderer.render(scene, camera);
    }})();

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
    var _nodeFreqs3d = sceneData.nodeFreqs || null;
    var _isActive3d = sceneData.isActive || null;

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
                if (_isActive3d) {{
                    if (_isActive3d[idx]) {{
                        tooltip.style.background = "rgba(245,245,245,0.95)";
                        tooltip.style.color = "#222";
                    }} else {{
                        tooltip.style.background = "rgba(30,30,30,0.92)";
                        tooltip.style.color = "#eee";
                    }}
                }}
                tooltip.style.display = "block";
            }}
            tooltip.style.left = (ev.clientX - rect.left + 12) + "px";
            tooltip.style.top  = (ev.clientY - rect.top  + 12) + "px";
            canvas.style.cursor = _nodeFreqs3d ? "pointer" : "default";
        }} else {{
            hoveredIdx = -1;
            tooltip.style.display = "none";
            canvas.style.cursor = "default";
        }}
    }});
    container.addEventListener("mouseleave", function() {{
        hoveredIdx = -1;
        tooltip.style.display = "none";
        canvas.style.cursor = "default";
    }});

    async function _playFreq3d(freq) {{
        if (!freq || freq <= 0) return;
        try {{
            if (typeof globalThis.KlothoPlaybackBridge !== "function") {{
                return;
            }}
            var bridge = globalThis.KlothoPlaybackBridge({{
                engine: "{eng}",
                audioPayload: null,
                ringTime: 5
            }});
            await bridge.ensureReady();
            await bridge.resumeAudio();
            await bridge.preview({{
                freq: freq,
                dur: 1.0,
                amp: 0.3,
                defName: "kl_tri"
            }});
        }} catch(e) {{}}
    }}
    if (_nodeFreqs3d) {{
        var _dX3d = 0, _dY3d = 0;
        canvas.addEventListener("pointerdown", function(ev) {{
            _dX3d = ev.clientX; _dY3d = ev.clientY;
        }});
        canvas.addEventListener("pointerup", function(ev) {{
            var dx = ev.clientX - _dX3d, dy = ev.clientY - _dY3d;
            if (dx * dx + dy * dy > 9) return;
            var rect = canvas.getBoundingClientRect();
            mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
            raycaster.setFromCamera(mouse, camera);
            var hits = raycaster.intersectObjects(nodeMeshes, false);
            if (hits.length > 0) {{
                var idx = hits[0].object.userData.nodeIdx;
                if (idx >= 0 && idx < _nodeFreqs3d.length) _playFreq3d(_nodeFreqs3d[idx]);
            }}
        }});
    }}

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
        if (stepIdx >= totalSteps && endHalo) {{
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



class AnimatedRTSvgFigure:
    """Animated SVG figure for rhythm-tree leaf-by-leaf playback.

    Highlights successive leaf nodes and their ancestor paths inside an
    SVG rhythm-tree diagram, optionally synchronised with audio events.

    Parameters
    ----------
    svg_data : SvgRTData
        Pre-built SVG data for the rhythm tree.
    audio_payload : dict or None, optional
        Tone.js-compatible event payload for audio playback.
    dur : float, optional
        Seconds between animation steps.
    glow : bool, optional
        Enable halo glow on the active leaf node.
    """

    def __init__(self, svg_data, audio_payload=None, dur=0.5, glow=False, engine=None, ring_time=5, loop=False):
        self.svg_data = svg_data
        self.audio_payload = audio_payload
        self.dur = dur
        self.glow = glow
        self.ring_time = ring_time
        self.loop = loop
        self.engine = engine or get_audio_engine()
        self.widget_id = f"klotho_svg_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        """Return a self-contained HTML string for Jupyter display."""
        sd = self.svg_data
        wid = self.widget_id
        eng = self.engine

        cdn_html, instruments_js, player_js = build_session_preamble(
            include_tone=(bool(self.audio_payload) and eng == "tone"),
            engine=eng)
        controls_html = build_control_bar_html(wid)
        scripts_html = build_scripts_html(instruments_js, player_js, engine=eng)

        leaf_path_ids_json = json.dumps(sd.leaf_path_ids)
        all_anim_ids_json = json.dumps(sd.all_animated_ids)
        leaf_halo_ids_json = json.dumps(sd.leaf_halo_ids)
        leaf_x_json = json.dumps(sd.leaf_x_positions)
        bright_json = json.dumps(sd.leaf_bright_colors)
        base_json = json.dumps(sd.leaf_base_colors)

        node_to_ids_json = json.dumps({str(k): v for k, v in sd.node_to_ids.items()})
        leaf_ancestors_json = json.dumps([[str(n) for n in path] for path in sd.leaf_ancestors])

        converted = _maybe_convert_payload(self.audio_payload, eng)
        payload_json = json.dumps(converted) if converted else "null"

        playback_js = build_playback_js(wid, self.dur * 1000, use_gt_for_boundary=False, engine=eng, ring_time=self.ring_time, loop=self.loop)

        html = f'''
{cdn_html}
{sd.svg_str}
{controls_html}
{scripts_html}
<script>
(typeof requestIdleCallback==='function'?requestIdleCallback:function(f){{setTimeout(f,0)}})(function() {{
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
    """Animated SVG figure for step-by-step lattice path traversal.

    Progressively reveals path edges and updates node colours inside a
    2D SVG lattice diagram, optionally synchronised with audio events.

    Parameters
    ----------
    svg_data : SvgLatticeData or SvgCPSData
        Pre-built SVG data for the lattice or CPS.
    audio_payload : dict or None, optional
        Tone.js-compatible event payload for audio playback.
    dur : float, optional
        Seconds between animation steps.
    """

    def __init__(self, svg_data, audio_payload=None, dur=0.5, engine=None, ring_time=5, loop=False):
        self.svg_data = svg_data
        self.audio_payload = audio_payload
        self.dur = dur
        self.ring_time = ring_time
        self.loop = loop
        self.engine = engine or get_audio_engine()
        self.widget_id = f"klotho_slat_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        """Return a self-contained HTML string for Jupyter display."""
        sd = self.svg_data
        wid = self.widget_id
        eng = self.engine

        cdn_html, instruments_js, player_js = build_session_preamble(
            include_tone=(bool(self.audio_payload) and eng == "tone"),
            engine=eng)
        controls_html = build_control_bar_html(wid)
        scripts_html = build_scripts_html(instruments_js, player_js, engine=eng)

        steps_json = json.dumps(sd.step_group_ids)
        halos_json = json.dumps(sd.halo_ids)
        all_path_json = json.dumps(sd.all_path_ids)
        node_ids_json = json.dumps(getattr(sd, 'all_node_ids', []))
        path_node_indices_json = json.dumps(getattr(sd, 'path_node_indices', []))
        path_node_colors_json = json.dumps(getattr(sd, 'path_node_colors', []))
        dimmed_color = getattr(sd, 'dimmed_node_color', '#111111')
        converted = _maybe_convert_payload(self.audio_payload, eng)
        payload_json = json.dumps(converted) if converted else "null"

        playback_js = build_playback_js(wid, self.dur * 1000, engine=eng, ring_time=self.ring_time, loop=self.loop)

        html = f'''
{cdn_html}
{sd.svg_str}
{controls_html}
{scripts_html}
<script>
(typeof requestIdleCallback==='function'?requestIdleCallback:function(f){{setTimeout(f,0)}})(function() {{
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
        if (stepIdx >= totalSteps && haloIds.length > 1) {{
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
"""Alias for ``AnimatedLatticeSvgFigure`` used for CPS path animations."""


class _AnimatedShapeFigureBase:
    """Animated SVG figure for chord / chord-sequence shape playback.

    Cycles through shape groups (chords), highlighting their nodes and
    edges with per-group colouring.  Includes prev/next navigation,
    solo mode, and optional audio synchronisation.

    Parameters
    ----------
    svg_data : SvgLatticeData or SvgCPSData
        Pre-built SVG data containing shape group metadata.
    audio_payload : dict or None, optional
        Tone.js-compatible event payload for audio playback.
    dur : float, optional
        Seconds between animation steps.
    """

    def __init__(self, svg_data, audio_payload=None, dur=0.5, engine=None, ring_time=5, loop=False):
        self.svg_data = svg_data
        self.audio_payload = audio_payload
        self.dur = dur
        self.ring_time = ring_time
        self.loop = loop
        self.engine = engine or get_audio_engine()
        self.widget_id = f"klotho_shp_{uuid.uuid4().hex[:8]}"

    def to_html(self, **kwargs):
        """Return a self-contained HTML string for Jupyter display."""
        sd = self.svg_data
        wid = self.widget_id
        eng = self.engine

        cdn_html, instruments_js, player_js = build_session_preamble(
            include_tone=(bool(self.audio_payload) and eng == "tone"),
            engine=eng)
        controls_html = build_control_bar_html(wid)
        scripts_html = build_scripts_html(instruments_js, player_js, engine=eng)

        group_node_indices_json = json.dumps(sd.shape_group_node_indices)
        group_edge_ids_json = json.dumps(sd.shape_group_edge_ids)
        shape_colors_json = json.dumps(sd.shape_colors)
        all_shape_edge_ids_json = json.dumps(sd.all_shape_edge_ids)
        node_ids_json = json.dumps(sd.all_node_ids)
        dimmed_color = sd.dimmed_node_color
        converted = _maybe_convert_payload(self.audio_payload, eng)
        payload_json = json.dumps(converted) if converted else "null"
        total_groups = len(sd.shape_group_node_indices)
        is_multi = total_groups > 1

        nav_display = "inline-flex" if is_multi else "none"

        shape_js = build_shape_playback_js(
            wid, self.dur * 1000, total_groups,
            engine=eng, ring_time=self.ring_time, loop=self.loop)

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
(typeof requestIdleCallback==='function'?requestIdleCallback:function(f){{setTimeout(f,0)}})(function() {{
    var groupNodeIndices = {group_node_indices_json};
    var groupEdgeIds = {group_edge_ids_json};
    var shapeColors = {shape_colors_json};
    var allShapeEdgeIds = {all_shape_edge_ids_json};
    var allNodeIds = {node_ids_json};
    var dimmedColor = "{dimmed_color}";
    var audioPayload = {payload_json};

    {shape_js}
}})();
</script>
'''
        return html


AnimatedCPSShapeFigure = _AnimatedShapeFigureBase
"""Alias for ``_AnimatedShapeFigureBase`` used for CPS shape animations."""

AnimatedLatticeShapeFigure = _AnimatedShapeFigureBase
"""Alias for ``_AnimatedShapeFigureBase`` used for lattice shape animations."""
