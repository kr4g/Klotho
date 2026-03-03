from klotho.utils.playback.tonejs.cdn import cdn_scripts

_booted = False


def boot_supersonic():
    global _booted
    if _booted:
        return

    from ._config import get_audio_engine
    if get_audio_engine() != "supersonic":
        return

    try:
        get_ipython()
    except NameError:
        return

    _booted = True

    from IPython.display import display, HTML
    from .supersonic._js_fragments import (
        ss_init_js, draw_scheduler_js, scheduler_core_js,
    )

    boot_js = f"""<script>
{ss_init_js()}
{draw_scheduler_js()}
{scheduler_core_js()}
</script>"""
    display(HTML(boot_js))


def build_supersonic_session_preamble(include_plotly=False, include_threejs=False):
    cdn_html = cdn_scripts(
        include_plotly=include_plotly,
        include_tone=False,
        include_threejs=include_threejs,
    )
    return cdn_html, "", ""
