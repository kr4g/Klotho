from .tonejs import ToneEngine, convert_to_events


def play(obj, custom_js_path=None, custom_js=None, **kwargs):
    events = convert_to_events(obj, **kwargs)
    engine = ToneEngine(events, custom_js_path=custom_js_path, custom_js=custom_js)
    return engine.display()
