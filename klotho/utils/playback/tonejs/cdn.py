from pathlib import Path

PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.0.0.min.js"
TONEJS_CDN = "https://unpkg.com/tone@14.7.77/build/Tone.js"
THREEJS_CDN = "https://unpkg.com/three@0.147.0/build/three.min.js"
THREEJS_ORBIT_CDN = "https://unpkg.com/three@0.147.0/examples/js/controls/OrbitControls.js"
THREEJS_TRACKBALL_CDN = "https://unpkg.com/three@0.147.0/examples/js/controls/TrackballControls.js"
INSTRUMENTS_JS_PATH = Path(__file__).parent / "instruments.js"
PLAYER_JS_PATH = Path(__file__).parent / "player.js"


def _idempotent_load(global_check, cdn_url):
    return (
        f'<script>if(typeof {global_check}==="undefined")'
        f'{{var s=document.createElement("script");s.src="{cdn_url}";'
        f'document.head.appendChild(s);}}</script>\n'
    )


def cdn_scripts(include_plotly=False, include_tone=False, include_threejs=False):
    s = ''
    if include_plotly:
        s += _idempotent_load('Plotly', PLOTLY_CDN)
    if include_tone:
        s += _idempotent_load('Tone', TONEJS_CDN)
    return s
