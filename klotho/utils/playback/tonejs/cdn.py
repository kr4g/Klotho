from pathlib import Path

PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.0.0.min.js"
TONEJS_CDN = "https://unpkg.com/tone@14.7.77/build/Tone.js"
THREEJS_CDN = "https://unpkg.com/three@0.147.0/build/three.min.js"
THREEJS_ORBIT_CDN = "https://unpkg.com/three@0.147.0/examples/js/controls/OrbitControls.js"
THREEJS_TRACKBALL_CDN = "https://unpkg.com/three@0.147.0/examples/js/controls/TrackballControls.js"
INSTRUMENTS_JS_PATH = Path(__file__).parent / "instruments.js"
PLAYER_JS_PATH = Path(__file__).parent / "player.js"


def _guarded_cdn(global_check, cdn_url):
    """
    Generate a ``<script>`` tag that loads a CDN resource only once.

    Checks for the existence of a global variable and a matching
    ``<script>`` element before injecting the resource.

    Parameters
    ----------
    global_check : str
        JavaScript global variable name to test (e.g. ``'Tone'``).
    cdn_url : str
        Full URL of the CDN resource.

    Returns
    -------
    str
        An HTML ``<script>`` snippet.
    """
    return (
        f'<script>if(typeof {global_check}==="undefined"&&'
        f'!document.querySelector(\'script[src="{cdn_url}"]\'))'
        f'{{var _s=document.createElement("script");_s.src="{cdn_url}";'
        f'document.head.appendChild(_s);}}</script>\n'
    )


def cdn_scripts(include_plotly=False, include_tone=False, include_threejs=False):
    """
    Build combined CDN ``<script>`` tags for the requested libraries.

    Parameters
    ----------
    include_plotly : bool, optional
        Include the Plotly CDN script (default ``False``).
    include_tone : bool, optional
        Include the Tone.js CDN script (default ``False``).
    include_threejs : bool, optional
        Include the Three.js CDN script (default ``False``).
        Currently unused.

    Returns
    -------
    str
        Concatenated HTML ``<script>`` tags.
    """
    s = ''
    if include_plotly:
        s += _guarded_cdn('Plotly', PLOTLY_CDN)
    if include_tone:
        s += _guarded_cdn('Tone', TONEJS_CDN)
    return s
