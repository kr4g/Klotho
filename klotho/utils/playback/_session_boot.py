_booted = False


def boot_supersonic():
    global _booted
    if _booted:
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

    boot_js = f"""<script type="module">
{ss_init_js()}
{draw_scheduler_js()}
{scheduler_core_js()}
</script>"""
    display(HTML(boot_js))
