Examples
========

For comprehensive examples and tutorials, visit the
`Interactive Tutorials <https://kr4g.github.io/Klotho/>`_ — no installation required.

The tutorial series covers:

* **Rhythm Trees** — Creating and manipulating rhythm trees, rhythmic vocabulary, partitions
* **Temporal Units** — Working with temporal structures and sequences
* **Tone Lattices** — Harmonic spaces, embedded structures, custom lattice generators
* **Combination Product Sets** — CPS construction, higher-dimensional sets, interactive explorer

SuperSonic Playback
-------------------

SuperSonic is Klotho's default audio engine: it runs SuperCollider synthesis
directly in the browser via WebAssembly, so ``play(obj)`` works in any Jupyter
notebook with no external synth application.

Instruments are backed by SuperCollider SynthDefs. Every SynthDef bundled with
Klotho is available by name:

.. code-block:: python

   from klotho import CompositionalUnit
   from klotho.thetos.instruments import SynthDefInstrument
   from klotho.utils.playback.player import play

   uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 2), beat='1/4', bpm=96)
   uc.set_instrument(uc.root, SynthDefInstrument.from_manifest('kl_tri'))
   play(uc)

Custom SynthDefs authored with `Supriya <https://github.com/supriya-project/supriya>`_
can be registered at runtime with ``register_synthdef``, which compiles the
def, makes it loadable by the in-browser engine, and returns a ready-to-use
instrument:

.. code-block:: python

   from supriya.ugens import synthdef
   from klotho.utils.playback.supersonic.registry import register_synthdef

   # my_synthdef built with @synthdef or SynthDefBuilder.build()
   inst = register_synthdef(my_synthdef)
   uc.set_instrument(uc.root, inst)
   play(uc)

To switch engines globally, use ``set_audio_engine('tone')`` /
``set_audio_engine('supersonic')`` from ``klotho.utils.playback._config``.

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
