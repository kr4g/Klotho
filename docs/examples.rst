Examples
========

For comprehensive examples and tutorials, visit the
`Interactive Tutorials <https://kr4g.github.io/Klotho/>`_ — no installation required.

The tutorial series covers:

* **Rhythm Trees** — Creating and manipulating rhythm trees, rhythmic vocabulary, partitions
* **Temporal Units** — Working with temporal structures and sequences
* **Tone Lattices** — Harmonic spaces, embedded structures, custom lattice generators
* **Combination Product Sets** — CPS construction, higher-dimensional sets, interactive explorer

Tone.js Custom Instruments
--------------------------

Klotho's Tone.js playback engine supports custom JS instruments that can be scheduled with per-event pfields. Custom instruments must be registered in JavaScript under ``KLOTHO_CUSTOM_INSTRUMENTS`` and expose the following hooks:

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

On the Python side, you can reference the custom instrument by name with ``ToneInstrument`` and supply default pfields if desired.
