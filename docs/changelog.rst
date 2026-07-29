Changelog
=========

Version 10.16.0 (Current)
-------------------------

* **Recording**: ``play(..., record=True)`` and ``plot(score).play(record=True)``
  add a record button to the playback widget — playback is captured in the
  browser and downloaded as 24-bit WAV when the piece (plus ring time)
  finishes. ``Score`` widgets gain a **stems** checkbox rendering every
  track as a separate, sample-aligned stereo stem plus the full mix in one
  ZIP (single realtime pass via per-track output-channel taps)
* **Custom samples**: runtime sample registry
  (``klotho.register_sample``); ``SynthDefInstrument.sampler`` accepts
  ``.wav`` paths; ``SynthDefKit.from_folder`` builds a kit from a folder
  (subfolders = families, ``NN_`` prefixes order members); stdlib WAV
  header parser with friendly format errors
* **Round-robin kits**: a family name is now a valid ``voice=`` selector,
  rotating deterministically through the family's members per hit —
  variant pools for humanized drums; direct member access, integer
  indices, and ``pick``/``cycle`` unchanged
* ``klotho.fetch_samples(url)`` / ``klotho.upload_samples()`` for getting
  hosted or local sample files onto the notebook runtime (Colab-friendly)
* Demo notebook ``examples/mat111mc_notebooks/MAT_111MC___Custom_Sample_Kits.ipynb``
  with a bundled ``mat_kit/`` sample folder
* Engine boots with 32 output channels (stem-tap pairs; audible output
  unchanged) and a pinned SuperSonic version (0.71.0)
* Fixes: the idle scheduler-queue flush now actually runs
  (``/clearSched`` is blocked in SuperSonic — replaced with ``purge()``);
  sample load failures and unresolvable ``buf`` names warn instead of
  playing silence; ``ens.family('drums')`` call form works as documented
* **Control-envelope playback was silent** — ``apply_envelope(...,
  control=True)`` uploaded its envelope buffer with ``/b_setn`` fills
  sent immediately after ``/b_alloc``, but ``/b_alloc`` is an async
  scsynth command, so the fills were dropped and every ``__klEnvCtrl``
  streamed zeros (mapped pfields pinned to 0). The fills now wait behind
  a ``/sync`` round-trip, ``setupControlEnvelopes`` awaits the upload,
  and the score-extension install guard is versioned
  (``__klothoScoreExtV2``) so stale saved outputs get the fix
* **Stop didn't silence playback** — a side effect of the ``purge()``
  fix above: stop's ``/g_freeAll`` rides the OSC out-ring while
  ``purge()``'s clearSched signal rides the worklet port, an unordered
  channel that could wipe the ring before the frees drained — stopped
  notes kept sounding with their scheduled gate-offs flushed, and
  restarts orphaned them permanently. ``stop()`` and ``play()``'s
  restart path now drain the frees through a ``/sync`` round-trip
  before flushing the queue
* **Late queue-flush acks corrupted the next play** — ``purge()`` is
  async, and an ack landing after a subsequent ``play()`` had already
  scheduled its batch wiped a random slice of it: eaten ``/n_map``/
  ``__klEnvCtrl`` bundles froze control envelopes (pieces played as a
  static cluster), eaten gate-offs and frees made stop intermittently
  hang on sounding notes. ``_unregisterPlayer`` now records the
  in-flight purge on the shared scheduler state, ``play()`` awaits it
  before scheduling, and all sync/purge awaits are time-bounded so a
  lost ack can never hang stop or play
* **Scheduler install guard bumped to** ``__klothoSchedCoreV3`` — pages
  carrying saved 10.16-dev outputs already claim the V2 marker, so the
  fixed core deferred to the raced build and none of the three fixes
  above took effect there. V3 keys on its own name (still claiming V2 so
  a stale core rendering later cannot downgrade the class), and the
  stale-page probe gains a ``stale_1016dev`` state covering it
* **Frequency control envelopes never moved the synth** — ``kl_*``/
  ``fd_*`` instruments glide ``freq`` through ``VarLag(warp: \\exp)``
  (or the FoxDot idiom it matches), which compiles to a ``Changed()``-
  retriggered EnvGen chase. Against a control bus that moves every
  block — exactly what ``__klEnvCtrl`` wrote — the trigger never
  re-arms, so mapped freqs froze at their onset value: freq envelopes
  played as a static cluster while chase-free params (``amp``) followed
  theirs. The bus itself was verifiably correct the whole time, which
  hid the bug from every payload/OSC/bus-level check; only spectrum
  analysis of recorded audio exposed it. ``__klEnvCtrl`` now
  sample-and-holds its writes in ~30 ms steps (floor-quantized BufRd
  phase), pulsing ``Changed()`` once per step so the chase retriggers
  and the synth's own portamento smooths the glide
* **Page-stale synthdef bytes** — the synthdef asset registry merged
  first-wins, so saved outputs from older sessions (whose scripts run
  at page load) pinned their compiled defs for the page's lifetime and
  freshly rendered widgets kept ``/d_recv``-ing the old builds. The
  merge is now last-wins on changed bytes and invalidates the
  loaded-defs registry so the replacement is re-sent to the engine
* Demo notebook ``examples/mat111mc_notebooks/MAT_111MC___The_Deep_Note.ipynb``
  — the THX Deep Note as 30 single-note voices driven entirely by
  ``control=True`` frequency/amplitude envelopes (``warp='exp'``)

Version 10.15.x
---------------

* ``plot(score)`` with animated SuperSonic playback (10.15.0); fix for
  silent playback on pages with stale pre-10.15 widget outputs (10.15.1);
  QC follow-ups (10.15.2)

Version 10.14.x
---------------

* Plot/convert dispatch ladders replaced by an MRO-walking
  ``TypeRegistry`` (10.14.0); playback widgets unified on the shared
  bridge, buttons greyed until engine-ready (10.14.1)

Version 10.13.x
---------------

* Real assignment-based voice leading with anchors and smart doubling
  (10.13.0); uniform slur voice expansion (10.13.1)

Version 10.12.0
---------------

* MIDI and Tone.js playback engines removed — playback is
  SuperSonic-only; dead visualization/playback code culled

Version 10.11.2
---------------

* NumPy-style docstring pass across chronos, thetos, tonos, topos, dynatos,
  and playback modules
* Sphinx ``docs/api/topos.rst`` formal-grammar reference split into submodule
  pages; walkthrough note on pfield value types corrected

Version 10.11.1
---------------

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
