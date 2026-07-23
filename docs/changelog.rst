Changelog
=========

Version 10.11.1 (Current)
-------------------------

* Architecture documentation refreshed across all ``docs/architecture/``
  guides for the 10.x API: Tonnetz, polyomino shapes, kit families and
  SynthDef path aliases, score events, lattice scale/shape playback,
  playback engine details, and updated module counts
* Sphinx ``index.rst`` overview updated (Tonnetz, kits/ensembles, playback)

Version 10.11.0
---------------

* ``plot(..., nodes=<Scale>)`` highlights lattice coordinates for scale
  degrees with equave-run shape playback

Version 10.10.0
---------------

* New SuperSonic SynthDef libraries: **chip**, **edm**, **lofi**, and
  **tr808** (85 defs) with ``kinds.json`` classification
* ``Kit``/``Ensemble`` **families** with ``pick``/``cycle`` views
* SynthDef **path aliases** (``edm/kick`` → ``edm_kick``)

Version 10.9.0
--------------

* New ``Tonnetz`` tone-lattice system (``klotho.tonos.systems.tonnetz``):
  a two-generator triangular lattice (default 3/2 x 5/4, derived third
  direction 6/5) with exact-JI labeling, D6 point-group ``symmetries()``,
  and general shape operations ``reflect(cells, edge=/axis=, through=)``
  and ``rotate(cells, n, about=)``
* Tonnetz triangle moves: ``flip(cells, move)`` (the neo-Riemannian
  letters ``'P'``/``'R'``/``'L'`` as reflections across a shape's own
  edges, ``'S'`` as the third-holding half-turn, or any axis) and
  ``perform(cells, moves)`` (fold a flip/slide instruction list into a
  shape history)
* ``rotations(cells, reflections=False, group=None)`` generalized: pass any
  matrix group to orbit shapes in non-square coordinate systems;
  ``Lattice.symmetries(reflections=False)`` exposes each lattice's point
  group (signed axis permutations for grids, D6 for a Tonnetz)
* ``plot(..., layout='tonnetz')``: isometric triangular rendering with all
  three edge families, auto-selected for ``Tonnetz`` objects; node
  identity, tooltips, paths, and shape playback stay in axial coordinates
* ``plot(..., shape_color=...)``: group coloring policies for shape
  playback — ``'one-sided'`` (rotations and translations share a color,
  the Tetris convention) and ``'fixed'`` (every distinct orientation gets
  its own color; translations share). Tonnetz plots default to
  ``'fixed'`` so major and minor shapes read apart
* Animated shape playback with ``trail=`` now onion-skins past chords'
  *edges* as well as their nodes (2D SVG and 3D figures)
* New example notebook ``MAT_111MC___Radiohead_Chord_Generator.ipynb``:
  chord generation as flips and slides of shapes on the Tonnetz —
  chord-silhouette gallery, scripted progressions by hand, and two
  probabilistic generators (basic flips; expanded researched move table)

Version 10.2.0
--------------

* ``plot()`` and ``plot(...).play()`` for ``TemporalUnitSequence`` and
  ``TemporalBlock``: multi-lane ratios timeline with playback-synced pulse
  highlighting (nested UTS/BT/UT/UC containers supported)

Version 10.1.x
--------------

* Runtime SynthDef registration for SuperSonic: ``register_synthdef`` compiles
  a Supriya SynthDef, registers it with the in-browser engine, and returns a
  ready-to-use ``SynthDefInstrument`` (10.1.0)
* Fixed ``decompose(depth=1)`` crash on flat-prolatio CompositionalUnits (10.1.1)
* Architecture docs and Sphinx API docs overhauled for the 10.x API

Version 10.0.0
--------------

* Graph hierarchy refactored around ``GraphCore``: a read-only base providing
  views, traversal, and queries; ``Graph`` adds free-form mutators and
  ``Tree`` exposes structural mutators only
* Domain behavior moved into attachable ``TreeLayer`` objects
  (``RhythmLayer``, ``HarmonicLayer``, ``ParameterLayer``); facades such as
  ``RhythmTree``, ``HarmonicTree``, and ``ParameterTree`` are thin ``Tree``
  subclasses that attach their layer
* ``CompositionalUnit`` now uses a single fused ``CompositionalTree`` carrying
  both rhythm and parameter data — the shadow ParameterTree mirror is gone
* Topology generators (``path_graph``, ``complete_graph``, ``grid_graph``, ...)
  are module-level functions in ``klotho.topos.graphs.generators``
* Immutability by construction: ``CombinationSet``/``CombinationProductSet``
  are ``GraphCore`` subclasses with no mutators (and no ``.graph`` property)
* Removed the defunct ``semeios.notelists`` scheduler surface

Version 8.x
-----------

* Node API redesigned around handle-first selection semantics: ``UTNodeHandle``
  and ``UTNodeSelector`` are the canonical node-selection currency (8.0.0)
* Fixed SuperSonic animation auto-release in book widgets (8.0.1)

Version 7.x
-----------

* Temporal + Score API revamp: ``ScoreItem`` wrapper and deferred lowering of
  score items to playback events (7.0.0)
* SuperSonic auto-release refactor, flat SynthDef manifest, FX/loop/scheduler
  fixes (7.1.0)
* ``Pattern`` backend refactor with cycle/tree visualization (7.2.0)

Version 6.x
-----------

* Typed units relocated to per-domain modules (``klotho.chronos.types``,
  ``klotho.tonos.types``, ``klotho.dynatos.types``) with a slimmer top-level
  namespace (6.0.0)
* New N-dimensional master sets and expanded plot dimensionality-reduction
  menu (6.1.0)
* Plot/play fixes, MasterSet play parity, click-to-play gating (6.2.0)
* Envelope fixes, mid-play automation, handles API groundwork (6.3.0)

Version 5.x
-----------

* SuperSonic playback engine: SuperCollider synthesis in the browser via
  WebAssembly, now the default audio engine
* ``Score`` with tracks, insert FX chains, groups, and control envelopes
* Instrument layer expansion: ``Kit``, ``SynthDefKit``, ``Ensemble``,
  ``Effect``/``SynthDefFX``
* Graph mutation policy enforcement and canonical tree keys
* ParameterTree backend refactor with effective-value caching
* Visualization internals refactored behind a strict ``plot`` API with the
  ``KlothoPlot`` handle

Version 4.x
------------

* Major API restructuring across all modules
* Removed ``maquettes``, ``animation``, ``notation``, ``midi``, and ``allolib`` submodules from semeios
* Removed ``fields`` subtree from ``topos.graphs.lattices``
* Added ``tone_lattices`` system to tonos
* Renamed CPS modules (``cps.py`` → ``combination_product_sets.py``, ``nkany.py`` → ``algorithms.py``)
* Added ``Contour`` class to tonos.pitch
* Added ``basis.py`` to utils.algorithms
* Graph backend migrated to RustworkX for performance

Version 3.0.5
--------------

* Documentation infrastructure setup
* Added comprehensive Sphinx documentation
* NumPy-style docstring standards established
* Dependencies added: panel, bokeh, jupyter_bokeh for interactive visualization
* ``klotho.utils.algorithms`` module architecture improvements

Previous Versions
-----------------

See the `GitHub repository <https://github.com/kr4g/Klotho>`_ for full commit history.
