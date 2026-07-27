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

