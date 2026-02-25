Klotho: Graph-Oriented Computer-Assisted Composition
====================================================

**Klotho** is an open source computer-assisted composition toolkit implemented in Python.
It is designed to work in tandem with external synthesis applications and as a resource
for the methods, models, works, and frameworks associated with music composition and
metacomposition.

From the Ancient Greek "Κλωθώ" (Klotho), one of the three Fates who spins the thread of life.

Overview
--------

Klotho extends from a lineage of computer-assisted composition (CAC) theories, practices,
and software environments. While it provides support for conventional musical materials,
its strengths are best utilized when working with complex, abstract, or otherwise
unconventional musical structures not easily accessible with traditional notation software
or digital audio workstations.

Core Modules
------------

Klotho is organized into six primary modules plus utilities:

* **topos** — The foundation of musical topology in its most abstract form. Operates
  independently of specific musical parameters, modeling pure structural relationships,
  patterns, and processes.

* **chronos** — Encompasses all temporal materials from microscopic rhythmic gestures
  to macroscopic formal architectures. Handles nested tuplets, irrational time signatures,
  metric modulation, poly-meter, and poly-tempi.

* **tonos** — Handles all aspects of pitch and harmonic material including tones, pitch
  collections, scales, chords, harmonic systems and spaces, interval relationships, and
  frequency-based transformations. Supports arbitrary n-TET/n-EDO systems, extended Just
  Intonation frameworks, and n-dimensional microtonal lattices.

* **dynatos** — Dedicated to dynamics, articulations, and expressive envelopes. Handles
  conversion of symbolic dynamics (p, mf, ff, etc.) into precise dB/amplitude values,
  mapping of articulations to parametric envelopes, and custom expressive curves.

* **thetos** — The compositional complement to Topos. Handles the concrete assembly and
  combination of musical materials across all dimensions — temporal, tonal, dynamic,
  instrumental, and parametric.

* **semeios** — Manages all forms of musical representation including visualization,
  notation, plotting, animation, and multimedia output. Converts computational processes
  into human-readable and performable representations.

* **utils** — General utilities and helper functions including algorithms for cost matrices,
  graph traversal, ratio analysis, and playback via Tone.js and MIDI.

Installation
------------

.. code-block:: bash

   pip install klotho-cac

Or install from source:

.. code-block:: bash

   git clone https://github.com/kr4g/Klotho.git
   cd Klotho/
   pip install -e .

For contributors (includes testing and documentation tools):

.. code-block:: bash

   pip install -e .[dev]

Tutorials
---------

Browse the interactive tutorial series directly in your browser — no installation required:

`Interactive Tutorials <https://kr4g.github.io/Klotho/>`_

API Documentation
-----------------

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   api/topos
   api/chronos
   api/tonos
   api/thetos
   api/dynatos
   api/semeios
   api/utils

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources:

   examples
   contributing
   changelog

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
