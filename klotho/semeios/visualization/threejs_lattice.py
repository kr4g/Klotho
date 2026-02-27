import math
import numpy as np
from collections import defaultdict

from ._colors import _path_color_array, _rgba_to_hex
from ._geometry import bezier_3d as _bezier_3d, rodrigues_rotate as _rodrigues_rotate, get_perp as _get_perp, unpack3 as _unpack3
from ._svg_utils import SvgFigureData


class ThreejsLatticeData(SvgFigureData):
    """Container for Three.js 3D lattice scene data and path metadata."""

    __slots__ = ('scene_data', 'path_steps', 'halo_data',
                 'title', 'width_px', 'height_px')

    def to_html(self, **kwargs):
        return _static_threejs_html(self)


def _static_threejs_html(sd):
    """
    Generate a self-contained HTML snippet for a static Three.js lattice.

    Parameters
    ----------
    sd : ThreejsLatticeData
        Scene descriptor containing node positions, edges, and metadata.

    Returns
    -------
    str
        HTML string with embedded JavaScript for Three.js rendering.
    """
    import json
    import uuid

    wid = f"klotho_3d_static_{uuid.uuid4().hex[:8]}"
    scene_json = json.dumps(sd.scene_data)
    steps_json = json.dumps(sd.path_steps)
    halo_json = json.dumps(sd.halo_data)
    w = sd.width_px
    h = sd.height_px
    title_escaped = (sd.title or '').replace("'", "\\'").replace('"', '\\"')

    from klotho.utils.playback.tonejs.cdn import (
        THREEJS_CDN, THREEJS_ORBIT_CDN, THREEJS_TRACKBALL_CDN,
    )
    threejs_cdn = THREEJS_CDN
    orbit_cdn = THREEJS_ORBIT_CDN
    trackball_cdn = THREEJS_TRACKBALL_CDN

    return f'''
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
<script>
(function _klotho3dStaticInit() {{
    if (typeof THREE === "undefined") {{
        if (!document.querySelector('script[data-klotho-three]')) {{
            var s = document.createElement("script");
            s.src = "{threejs_cdn}";
            s.setAttribute("data-klotho-three", "1");
            (document.head || document.documentElement).appendChild(s);
        }}
        setTimeout(_klotho3dStaticInit, 100);
        return;
    }}
    if (!THREE.OrbitControls) {{
        if (!document.querySelector('script[data-klotho-orbit]')) {{
            var s = document.createElement("script");
            s.src = "{orbit_cdn}";
            s.setAttribute("data-klotho-orbit", "1");
            (document.head || document.documentElement).appendChild(s);
        }}
        setTimeout(_klotho3dStaticInit, 100);
        return;
    }}
    if (!THREE.TrackballControls) {{
        if (!document.querySelector('script[data-klotho-trackball]')) {{
            var s = document.createElement("script");
            s.src = "{trackball_cdn}";
            s.setAttribute("data-klotho-trackball", "1");
            (document.head || document.documentElement).appendChild(s);
        }}
        setTimeout(_klotho3dStaticInit, 100);
        return;
    }}

    var canvas = document.getElementById("{wid}_canvas");
    if (!canvas) {{ setTimeout(_klotho3dStaticInit, 50); return; }}
    var container = document.getElementById("{wid}_wrap");
    var tooltip   = document.getElementById("{wid}_tooltip");

    var sceneData = {scene_json};
    var pathSteps = {steps_json};
    var haloData  = {halo_json};

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
            gVerts[i*6]=e[0]; gVerts[i*6+1]=e[1]; gVerts[i*6+2]=e[2];
            gVerts[i*6+3]=e[3]; gVerts[i*6+4]=e[4]; gVerts[i*6+5]=e[5];
        }}
        var gGeom = new THREE.BufferGeometry();
        gGeom.setAttribute("position", new THREE.BufferAttribute(gVerts, 3));
        scene.add(new THREE.LineSegments(gGeom,
            new THREE.LineBasicMaterial({{ color: sceneData.gridEdgeColor }})));
    }}
    if (sceneData.highlightEdges.length > 0) {{
        var hVerts = new Float32Array(sceneData.highlightEdges.length * 6);
        for (var i = 0; i < sceneData.highlightEdges.length; i++) {{
            var e = sceneData.highlightEdges[i];
            hVerts[i*6]=e[0]; hVerts[i*6+1]=e[1]; hVerts[i*6+2]=e[2];
            hVerts[i*6+3]=e[3]; hVerts[i*6+4]=e[4]; hVerts[i*6+5]=e[5];
        }}
        var hGeom = new THREE.BufferGeometry();
        hGeom.setAttribute("position", new THREE.BufferAttribute(hVerts, 3));
        scene.add(new THREE.LineSegments(hGeom,
            new THREE.LineBasicMaterial({{ color: 0xffffff, linewidth: 2 }})));
    }}

    var sphereR = sceneData.nodeSize * 0.015;
    var sphereGeo = new THREE.SphereGeometry(sphereR, 16, 12);
    var nodeMeshes = [];
    var nodeGroup = new THREE.Group();
    var pathNodeIndices = sceneData.pathNodeIndices || [];
    var pathNodeColors = sceneData.pathNodeColors || [];

    for (var i = 0; i < sceneData.nodes.length; i++) {{
        var n = sceneData.nodes[i];
        var mat = new THREE.MeshBasicMaterial({{ color: sceneData.nodeColors[i] }});
        var mesh = new THREE.Mesh(sphereGeo, mat);
        mesh.position.set(n[0], n[1], n[2]);
        mesh.userData.nodeIdx = i;
        nodeGroup.add(mesh);
        nodeMeshes.push(mesh);
    }}
    scene.add(nodeGroup);

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
            s.position.set(t, axCfg.yRange[0]-tickOff, axCfg.zRange[0]-tickOff);
            scene.add(s);
        }});
        var xl = makeTextSprite(labels[0], "#aaaaaa");
        xl.position.set(cx, axCfg.yRange[0]-tickOff*2.5, axCfg.zRange[0]-tickOff*2.5);
        xl.scale.set(0.7, 0.25, 1); scene.add(xl);
    }}
    if (labels[1]) {{
        axCfg.yTicks.forEach(function(t) {{
            var s = makeTextSprite(String(t));
            s.position.set(axCfg.xRange[0]-tickOff, t, axCfg.zRange[0]-tickOff);
            scene.add(s);
        }});
        var yl = makeTextSprite(labels[1], "#aaaaaa");
        yl.position.set(axCfg.xRange[0]-tickOff*2.5, cy, axCfg.zRange[0]-tickOff*2.5);
        yl.scale.set(0.7, 0.25, 1); scene.add(yl);
    }}
    if (labels[2]) {{
        axCfg.zTicks.forEach(function(t) {{
            var s = makeTextSprite(String(t));
            s.position.set(axCfg.xRange[0]-tickOff, axCfg.yRange[0]-tickOff, t);
            scene.add(s);
        }});
        var zl = makeTextSprite(labels[2], "#aaaaaa");
        zl.position.set(axCfg.xRange[0]-tickOff*2.5, axCfg.yRange[0]-tickOff*2.5, cz);
        zl.scale.set(0.7, 0.25, 1); scene.add(zl);
    }}

    function makeTube(pts, radius, color, opacity) {{
        var vecs = pts.map(function(p) {{ return new THREE.Vector3(p[0],p[1],p[2]); }});
        var curve = (vecs.length === 2)
            ? new THREE.LineCurve3(vecs[0], vecs[1])
            : new THREE.CatmullRomCurve3(vecs, false, "catmullrom", 0);
        var segs = Math.max(vecs.length * 4, 8);
        var geo = new THREE.TubeGeometry(curve, segs, radius, 6, false);
        var mat = new THREE.MeshBasicMaterial({{ color:color, transparent:opacity<1, opacity:opacity }});
        return new THREE.Mesh(geo, mat);
    }}

    for (var si = 0; si < pathSteps.length; si++) {{
        var step = pathSteps[si];
        if (!step) continue;
        scene.add(makeTube(step.polyline, 0.018, 0xffffff, 0.25));
        scene.add(makeTube(step.polyline, 0.012, step.color, 1.0));
        var coneH = 0.12, coneR = 0.04;
        var coneGeo = new THREE.ConeGeometry(coneR, coneH, 8);
        coneGeo.translate(0, coneH/2, 0);
        coneGeo.rotateX(Math.PI/2);
        var cone = new THREE.Mesh(coneGeo,
            new THREE.MeshBasicMaterial({{ color: step.color }}));
        cone.position.set(step.arrow_pos[0], step.arrow_pos[1], step.arrow_pos[2]);
        var dir = new THREE.Vector3(step.arrow_dir[0], step.arrow_dir[1], step.arrow_dir[2]).normalize();
        cone.setRotationFromQuaternion(
            new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1), dir));
        scene.add(cone);
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
        ctx.fillStyle = grad; ctx.fillRect(0,0,64,64);
        var tex = new THREE.CanvasTexture(c2);
        var mat = new THREE.SpriteMaterial({{ map:tex, transparent:true }});
        var sprite = new THREE.Sprite(mat);
        sprite.scale.set(size, size, 1);
        return sprite;
    }}
    if (haloData) {{
        var sh = makeHaloSprite(haloData.start.color, 0.55);
        sh.position.set(haloData.start.pos[0], haloData.start.pos[1], haloData.start.pos[2]);
        scene.add(sh);
        var eh = makeHaloSprite(haloData.end.color, 0.55);
        eh.position.set(haloData.end.pos[0], haloData.end.pos[1], haloData.end.pos[2]);
        scene.add(eh);
    }}

    for (var i = 0; i < pathNodeIndices.length; i++) {{
        var idx = pathNodeIndices[i];
        var col = pathNodeColors[i] || "#ffffff";
        if (idx >= 0 && idx < nodeMeshes.length) nodeMeshes[idx].material.color.set(col);
    }}

    var raycaster = new THREE.Raycaster();
    var mouse = new THREE.Vector2();
    container.addEventListener("mousemove", function(ev) {{
        var rect = canvas.getBoundingClientRect();
        mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
        var hits = raycaster.intersectObjects(nodeMeshes, false);
        if (hits.length > 0) {{
            tooltip.textContent = sceneData.hoverData[hits[0].object.userData.nodeIdx];
            tooltip.style.display = "block";
            tooltip.style.left = (ev.clientX - rect.left + 12) + "px";
            tooltip.style.top  = (ev.clientY - rect.top  + 12) + "px";
        }} else {{
            tooltip.style.display = "none";
        }}
    }});
    container.addEventListener("mouseleave", function() {{
        tooltip.style.display = "none";
    }});

    var _clickCtx = null;
    var _nodeFreqs = sceneData.nodeFreqs || null;
    function _playFreq(freq) {{
        if (!freq || freq <= 0) return;
        try {{
            if (!_clickCtx) _clickCtx = new (window.AudioContext || window.webkitAudioContext)();
            if (_clickCtx.state === "suspended") _clickCtx.resume();
            var osc = _clickCtx.createOscillator();
            var gain = _clickCtx.createGain();
            osc.type = "sine";
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(0.3, _clickCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, _clickCtx.currentTime + 0.6);
            osc.connect(gain); gain.connect(_clickCtx.destination);
            osc.start(); osc.stop(_clickCtx.currentTime + 0.65);
        }} catch(e) {{}}
    }}
    if (_nodeFreqs) {{
        var _downX = 0, _downY = 0;
        canvas.addEventListener("pointerdown", function(ev) {{
            _downX = ev.clientX; _downY = ev.clientY;
        }});
        canvas.addEventListener("pointerup", function(ev) {{
            var dx = ev.clientX - _downX, dy = ev.clientY - _downY;
            if (dx * dx + dy * dy > 9) return;
            var rect = canvas.getBoundingClientRect();
            mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
            raycaster.setFromCamera(mouse, camera);
            var hits = raycaster.intersectObjects(nodeMeshes, false);
            if (hits.length > 0) {{
                var idx = hits[0].object.userData.nodeIdx;
                if (idx >= 0 && idx < _nodeFreqs.length) _playFreq(_nodeFreqs[idx]);
            }}
        }});
    }}
}})();
</script>
'''


def _threejs_lattice_3d(lattice, coords, G, path, nodes,
                        highlighted_coords, coord_mapping, original_coords,
                        effective_dimensionality, use_dimmed, mute_background,
                        path_mode, figsize, node_size, title,
                        is_tone_lattice, coord_label, gen_labels,
                        path_cmap='viridis'):
    """
    Build a Three.js 3D scene for a lattice.

    Generates grid edges, highlighted edges, node spheres with hover
    data, optional path tubes with arrow-head cones, and start/end
    halo sprites.

    Parameters
    ----------
    lattice : Lattice
        The lattice object.
    coords : list of tuple
        Coordinates to render.
    G : networkx.Graph
        Edge structure for the rendered region.
    path : list of tuple or None
        Coordinate path to overlay.
    nodes : list of tuple or None
        Coordinates to highlight.
    highlighted_coords : set
        Union of all highlighted coordinates.
    coord_mapping : dict
        Maps original coordinates to reduced ones.
    original_coords : list of tuple
        Pre-reduction coordinate list.
    effective_dimensionality : int
        Always 3 for this renderer.
    use_dimmed : bool
        Dim non-highlighted elements.
    mute_background : bool
        Hide non-selected nodes.
    path_mode : str
        ``'adjacent'`` or ``'origin'``.
    figsize : tuple of float
        Width and height in inches.
    node_size : float
        Base node diameter.
    title : str
        Scene title.
    is_tone_lattice : bool
        Whether the lattice carries ratio information.
    coord_label : str
        Label prefix for hover text.
    gen_labels : list of str
        Axis labels from lattice generators.
    path_cmap : str, optional
        Matplotlib colormap for path colouring.

    Returns
    -------
    ThreejsLatticeData
        Three.js scene description and metadata.
    """
    import networkx as nx

    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    reverse_coord_mapping = {v: k for k, v in coord_mapping.items()} if len(coord_mapping) > 0 else {}

    dimmed_edge_color = '#333333'
    dimmed_node_color = '#080808'
    drawn_nodes = set()

    grid_edges = []
    if not ((nodes or path) and mute_background):
        edge_color = dimmed_edge_color if use_dimmed else '#808080'
        edge_width = 1 if use_dimmed else 3
        for u, v in G.edges():
            x1, y1, z1 = _unpack3(u)
            x2, y2, z2 = _unpack3(v)
            grid_edges.append([x1, y1, z1, x2, y2, z2])
    else:
        edge_color = '#808080'
        edge_width = 3

    highlight_edges = []
    if nodes and len(highlighted_coords) >= 1:
        highlighted_list = list(highlighted_coords)
        if path_mode == 'adjacent' and len(highlighted_coords) > 1:
            for i in range(len(highlighted_list)):
                for j in range(i + 1, len(highlighted_list)):
                    coord1, coord2 = highlighted_list[i], highlighted_list[j]
                    diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                    same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                    if diff_count == 1 and same_count == len(coord1) - 1:
                        if lattice.dimensionality > 3:
                            if coord1 in coord_mapping and coord2 in coord_mapping:
                                pc1, pc2 = coord_mapping[coord1], coord_mapping[coord2]
                            else:
                                continue
                        else:
                            pc1, pc2 = coord1, coord2
                        x1, y1, z1 = _unpack3(pc1)
                        x2, y2, z2 = _unpack3(pc2)
                        drawn_nodes.add((x1, y1, z1))
                        drawn_nodes.add((x2, y2, z2))
                        highlight_edges.append([x1, y1, z1, x2, y2, z2])
        elif path_mode == 'origin':
            origin = tuple(0 for _ in range(lattice.dimensionality))
            origin_plot = coord_mapping.get(origin, origin) if lattice.dimensionality > 3 else origin
            for target_coord in highlighted_list:
                if target_coord != origin:
                    try:
                        target_plot = coord_mapping.get(target_coord, target_coord) if lattice.dimensionality > 3 else target_coord
                        if hasattr(G, 'has_node') and G.has_node(origin_plot) and G.has_node(target_plot):
                            path_coords = nx.shortest_path(G, origin_plot, target_plot)
                            for k in range(len(path_coords) - 1):
                                pc1, pc2 = path_coords[k], path_coords[k + 1]
                                x1, y1, z1 = _unpack3(pc1)
                                x2, y2, z2 = _unpack3(pc2)
                                drawn_nodes.add((x1, y1, z1))
                                drawn_nodes.add((x2, y2, z2))
                                highlight_edges.append([x1, y1, z1, x2, y2, z2])
                    except Exception:
                        continue

    path_steps = []
    halo_data = None
    base_arc_offset = 0.15
    n_bezier_points = 20

    if path and len(path) >= 2:
        colors = _path_color_array(path_cmap, len(path) - 1)
        edge_counts = defaultdict(int)

        for i in range(len(path) - 1):
            coord1, coord2 = path[i], path[i + 1]

            if lattice.dimensionality > 3:
                if coord1 in coord_mapping and coord2 in coord_mapping:
                    plot_coord1, plot_coord2 = coord_mapping[coord1], coord_mapping[coord2]
                else:
                    path_steps.append(None)
                    continue
            else:
                plot_coord1, plot_coord2 = coord1, coord2

            x1, y1, z1 = _unpack3(plot_coord1)
            x2, y2, z2 = _unpack3(plot_coord2)
            drawn_nodes.add((x1, y1, z1))
            drawn_nodes.add((x2, y2, z2))

            edge_key = tuple(sorted([plot_coord1, plot_coord2]))
            traversal_idx = edge_counts[edge_key]
            edge_counts[edge_key] += 1

            path_color_hex = _rgba_to_hex(colors[i])
            dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
            length = math.sqrt(dx*dx + dy*dy + dz*dz)

            if traversal_idx == 0:
                polyline = [[x1, y1, z1], [x2, y2, z2]]
                mid = [(x1+x2)/2, (y1+y2)/2, (z1+z2)/2]
            else:
                if length < 1e-9:
                    path_steps.append(None)
                    continue
                edge_dir = np.array([dx, dy, dz]) / length
                base_perp = _get_perp(edge_dir)
                rotation_angle = (math.pi / 3) * traversal_idx
                perp = _rodrigues_rotate(base_perp, edge_dir, rotation_angle)
                offset_mag = base_arc_offset * math.ceil(traversal_idx / 2)
                if traversal_idx % 2 == 0:
                    perp = -perp
                ctrl = np.array([(x1+x2)/2, (y1+y2)/2, (z1+z2)/2]) + perp * offset_mag
                bx, by, bz = _bezier_3d(
                    (x1, y1, z1), (x2, y2, z2),
                    (ctrl[0], ctrl[1], ctrl[2]), n_bezier_points
                )
                polyline = [[float(bx[k]), float(by[k]), float(bz[k])] for k in range(len(bx))]
                mid_idx = n_bezier_points // 2
                mid = [float(bx[mid_idx]), float(by[mid_idx]), float(bz[mid_idx])]

            norm = length if length > 1e-9 else 1.0
            arrow_dir = [dx / norm, dy / norm, dz / norm]

            path_steps.append({
                'polyline': polyline,
                'color': path_color_hex,
                'arrow_pos': mid,
                'arrow_dir': arrow_dir,
            })

        start_coord = path[0]
        end_coord = path[-1]
        if lattice.dimensionality > 3:
            start_plot = coord_mapping.get(start_coord, start_coord)
            end_plot = coord_mapping.get(end_coord, end_coord)
        else:
            start_plot = start_coord
            end_plot = end_coord

        sx, sy, sz = _unpack3(start_plot)
        ex, ey, ez = _unpack3(end_plot)
        start_hex = _rgba_to_hex(colors[0])
        end_hex = _rgba_to_hex(colors[-1])

        halo_data = {
            'start': {'pos': [sx, sy, sz], 'color': start_hex},
            'end': {'pos': [ex, ey, ez], 'color': end_hex},
        }

    node_positions = []
    node_colors = []
    hover_texts = []
    node_freqs = [] if is_tone_lattice else None
    ref_freq = 261.63
    has_path = path and len(path) >= 2

    coords_iter = coords
    if (nodes or path) and mute_background and len(drawn_nodes) > 0:
        coords_iter = list(drawn_nodes)

    for i, coord in enumerate(coords_iter):
        x, y, z = _unpack3(coord)
        node_positions.append([x, y, z])

        if lattice.dimensionality <= 3 or len(reverse_coord_mapping) == 0:
            orig_coord = coord
        else:
            orig_coord = reverse_coord_mapping.get(coord, None)

        if lattice.dimensionality > 3 and orig_coord is not None:
            orig_str = str(orig_coord).replace(',)', ')')
            reduced_str = f"({x:.2f}, {y:.2f}, {z:.2f})"
            hover_text = f"Original: {orig_str}\nReduced: {reduced_str}"
        else:
            hover_text = f"{coord_label}: ({x}, {y}, {z})"

        if is_tone_lattice:
            try:
                coord_to_use = orig_coord if orig_coord is not None else coord
                ratio = lattice._coord_to_ratio(coord_to_use)
                hover_text += f"\nRatio: {ratio}"
                if node_freqs is not None:
                    node_freqs.append(ref_freq * float(ratio))
            except (KeyError, AttributeError):
                if node_freqs is not None:
                    node_freqs.append(ref_freq)

        hover_texts.append(hover_text)

        if highlighted_coords and orig_coord in highlighted_coords:
            node_colors.append('#ffffff')
        elif use_dimmed:
            node_colors.append(dimmed_node_color)
        else:
            node_colors.append('#ffffff')

    pos_to_node_idx = {}
    for i, p in enumerate(node_positions):
        key = (round(p[0], 6), round(p[1], 6), round(p[2], 6))
        pos_to_node_idx[key] = i

    path_node_indices = []
    path_node_colors = []
    path_node_final = {}
    if has_path:
        colors = _path_color_array(path_cmap, len(path) - 1)
        for k, coord in enumerate(path):
            if lattice.dimensionality > 3:
                plot_coord = coord_mapping.get(coord, coord)
            else:
                plot_coord = coord
            px, py, pz = _unpack3(plot_coord)
            key = (round(px, 6), round(py, 6), round(pz, 6))
            idx = pos_to_node_idx.get(key, -1)
            path_node_indices.append(idx)
            step_color = _rgba_to_hex(colors[0]) if k == 0 else _rgba_to_hex(colors[k - 1])
            path_node_colors.append(step_color)
            if idx >= 0:
                path_node_final[idx] = step_color

        for i in range(len(node_colors)):
            node_colors[i] = path_node_final.get(i, dimmed_node_color)

    x_all = [p[0] for p in node_positions] if node_positions else [c[0] for c in coords]
    y_all = [p[1] for p in node_positions] if node_positions else [c[1] if len(c) > 1 else 0 for c in coords]
    z_all = [p[2] for p in node_positions] if node_positions else [c[2] if len(c) > 2 else 0 for c in coords]

    x_min, x_max = min(x_all), max(x_all)
    y_min, y_max = min(y_all), max(y_all)
    z_min, z_max = min(z_all), max(z_all)
    pad = 0.5

    if lattice.dimensionality > 3:
        x_ticks = [round(t, 1) for t in np.linspace(x_min, x_max, min(10, int(x_max - x_min) + 1))]
        y_ticks = [round(t, 1) for t in np.linspace(y_min, y_max, min(10, int(y_max - y_min) + 1))]
        z_ticks = [round(t, 1) for t in np.linspace(z_min, z_max, min(10, int(z_max - z_min) + 1))]
        axis_labels = ['', '', '']
    else:
        x_ticks = list(range(int(x_min), int(x_max) + 1))
        y_ticks = list(range(int(y_min), int(y_max) + 1))
        z_ticks = list(range(int(z_min), int(z_max) + 1))
        axis_labels = [
            gen_labels[0] if len(gen_labels) > 0 else 'X',
            gen_labels[1] if len(gen_labels) > 1 else 'Y',
            gen_labels[2] if len(gen_labels) > 2 else 'Z',
        ]

    scene_data = {
        'gridEdges': grid_edges,
        'gridEdgeColor': edge_color,
        'gridEdgeWidth': edge_width,
        'highlightEdges': highlight_edges,
        'nodes': node_positions,
        'nodeColors': node_colors,
        'nodeSize': 2,
        'hoverData': hover_texts,
        'nodeFreqs': node_freqs,
        'dimmedNodeColor': dimmed_node_color,
        'pathNodeIndices': path_node_indices,
        'pathNodeColors': path_node_colors,
        'axisConfig': {
            'xRange': [x_min - pad, x_max + pad],
            'yRange': [y_min - pad, y_max + pad],
            'zRange': [z_min - pad, z_max + pad],
            'xTicks': x_ticks,
            'yTicks': y_ticks,
            'zTicks': z_ticks,
            'labels': axis_labels,
        },
        'camera': {'eye': [1.5, 1.5, 1.5]},
    }

    return ThreejsLatticeData(
        scene_data=scene_data,
        path_steps=path_steps,
        halo_data=halo_data,
        title=title or '',
        width_px=width_px,
        height_px=height_px,
    )
