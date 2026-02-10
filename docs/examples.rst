Examples
========

This section will contain examples of using Klotho for various musical tasks.

.. note::
   Examples are coming soon! Check back later for comprehensive tutorials and use cases.

Basic Usage
-----------

Coming soon...

Tone.js Custom Instruments
--------------------------

Klotho’s Tone.js playback engine supports custom JS instruments that can be scheduled with per-event pfields. Custom instruments must be registered in JavaScript under ``KLOTHO_CUSTOM_INSTRUMENTS`` and expose the following hooks:

- ``create()``: return a voice instance with any required Tone.js nodes.
- ``connect(inst, out)``: connect the voice instance to the output gain.
- ``apply(inst, pfields)``: apply pfields to the voice instance for each event.
- ``trigger(inst, freq, duration, time, vel, pfields)``: trigger the voice instance.

Optional fields:

- ``maxPolyphony``: maximum simultaneous voices for this instrument.
- ``pfields``: default pfields for the instrument.
- ``defaults``: default ``freq`` and ``vel`` for event scheduling.

To use custom instruments, inject a JS file when invoking the Tone.js player:

``play(obj, custom_js_path="path/to/custom_instruments.js")``

On the Python side, you can reference the custom instrument by name with ``JsInstrument`` and supply default pfields if desired.

Advanced Examples
-----------------

Coming soon... 