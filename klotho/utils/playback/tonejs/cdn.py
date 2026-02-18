from pathlib import Path

PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.0.0.min.js"
TONEJS_CDN = "https://unpkg.com/tone@14.7.77/build/Tone.js"
INSTRUMENTS_JS_PATH = Path(__file__).parent / "instruments.js"
PLAYER_JS_PATH = Path(__file__).parent / "player.js"

_plotly_included = False
_tone_included = False


def cdn_scripts(include_plotly=False, include_tone=False):
    global _plotly_included, _tone_included
    s = ''
    if include_plotly and not _plotly_included:
        s += f'<script src="{PLOTLY_CDN}"></script>\n'
        _plotly_included = True
    if include_tone and not _tone_included:
        s += f'<script src="{TONEJS_CDN}"></script>\n'
        _tone_included = True
    return s


def reset_cdn_flags():
    global _plotly_included, _tone_included
    _plotly_included = False
    _tone_included = False
