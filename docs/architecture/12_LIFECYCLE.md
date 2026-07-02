# Lifecycle and Mutation State Diagrams

This document describes the lifecycle states of the major Klotho
objects — when they are mutable, what triggers recomputation, and
what the valid operation sequences are.

---

## 1. Graph Lifecycle

`Graph` is the simplest lifecycle.  It starts mutable and stays
mutable — mutability is a property of the class, not a runtime flag.
(The read-only base `GraphCore` never enters the mutable states at
all: classes that inherit only `GraphCore` are frozen by construction
because they expose no mutators.)

```mermaid
stateDiagram-v2
    [*] --> Empty : __init__()
    Empty --> Populated : add_node / add_edge
    Populated --> Populated : add_node / add_edge / remove_node / remove_edge
    Populated --> DataMutated : set_node_data / update_node_data
    DataMutated --> Populated : (automatic — caches invalidated)

    note right of Populated
        Free-form mutators defined
        directly on Graph.
        Node views stay read-only
        (MappingProxyType).
    end note
```

---

## 2. Tree Lifecycle

`Tree` has a two-phase lifecycle: **construction** (where the
underlying graph is built from tuple notation) and **operational**
(where only the structural API is allowed).

```mermaid
stateDiagram-v2
    [*] --> Constructing : __init__(root, children)
    state Constructing {
        [*] --> Building : _build_tree()
        Building --> Building : _add_node_raw / _add_edge_raw\n(protected primitives)
        Building --> Layers : _init_layers()\n(attach domain layers)
        Layers --> [*]
    }
    Constructing --> Built : construction complete

    state Built {
        [*] --> Ready
        Ready --> Mutated : add_child / add_subtree /\nprune / graft_subtree / move_subtree
        Mutated --> PostMutation : _post_mutation(scope)
        PostMutation --> CachesInvalidated : _invalidate_caches()\n(group marked dirty)
        CachesInvalidated --> LayersNotified : layer.on_structure_changed(scope)\nfor each attached layer
        LayersNotified --> Ready

        Ready --> DataMutated : set_node_data(…)\n(normalize → validate → scope via layers)
        DataMutated --> PostMutation
    }

    note right of Built
        No add_node / add_edge exist on Tree
        (calling one → AttributeError).
        Structural changes only via
        add_child, add_subtree, prune, etc.
        Group rebuilt lazily on next
        .group access.
    end note
```

### Key Points

- Construction writes through the protected `GraphCore` primitives
  (`_add_node_raw` / `_add_edge_raw`); there is never a public
  `add_node`/`add_edge` on `Tree`.
- Domain layers are attached at the end of construction via the
  `_init_layers` hook.
- Every structural or data mutation ends in `_post_mutation(scope)`,
  which invalidates caches (marking the `Group` representation dirty
  for lazy rebuild) and notifies every attached layer via
  `on_structure_changed`.

---

## 3. RhythmTree Lifecycle

`RhythmTree` extends the `Tree` lifecycle with an `_evaluate()` step
that computes derived metric fields.

```mermaid
stateDiagram-v2
    [*] --> Constructing : __init__(span, meas, subdivisions)

    state Constructing {
        [*] --> CastSubdivs : _cast_subdivs()
        CastSubdivs --> TreeBuild : Tree.__init__()
        TreeBuild --> Evaluate : _evaluate()
        Evaluate --> [*]
    }

    Constructing --> Operational : all nodes have\nmetric_duration, metric_onset

    state Operational {
        [*] --> Ready

        Ready --> ProportionChanged : set_node_data(node, proportion=N)
        ProportionChanged --> Validated : RhythmLayer.validate_attrs()\n[only proportion, tied allowed]
        Validated --> ScopeResolved : RhythmLayer.data_scope()\n→ parent or root
        ScopeResolved --> PostMutation : _post_mutation(scope)
        PostMutation --> ReEvaluated : RhythmLayer.on_structure_changed\n→ _evaluate(scope) from scope down
        ReEvaluated --> Ready

        Ready --> Subdivided : subdivide(node, S)\n[leaf only]
        Subdivided --> PostMutation
        
        Ready --> Rested : make_rest(node)\n→ negate proportion
        Rested --> PostMutation
    }

    note right of Operational
        MUTABLE: proportion, tied
        DERIVED: metric_duration,
                 metric_onset
        REJECTED: label, metric_*
    end note
```

### Scoped Recomputation

When a single proportion changes, `RhythmLayer.data_scope()` returns
the **parent** of the changed node (not the root).  The layer's
`on_structure_changed` then re-runs `_evaluate(parent)`, recomputing
only the subtree from that parent down and avoiding a full-tree
re-evaluation.

---

## 4. HarmonicTree Lifecycle

Structurally identical to `RhythmTree`, but with `factor` instead
of `proportion` and multiplicative evaluation instead of proportional.

```mermaid
stateDiagram-v2
    [*] --> Constructing : __init__(root, children, equave, span)

    state Constructing {
        [*] --> TreeBuild : Tree.__init__()
        TreeBuild --> Evaluate : _evaluate()\n→ compute harmonic, multiple, ratio
        Evaluate --> [*]
    }

    Constructing --> Operational

    state Operational {
        [*] --> Ready

        Ready --> FactorChanged : set_node_data(node, factor=N)
        FactorChanged --> Validated : HarmonicLayer.validate_attrs()\n[only factor allowed]
        Validated --> ScopeResolved : HarmonicLayer.data_scope()\n→ the changed node
        ScopeResolved --> ReEvaluated : _evaluate(scope)\n→ recompute from that node down
        ReEvaluated --> Ready
    }

    note right of Operational
        MUTABLE: factor
        DERIVED: harmonic, multiple, ratio
        REJECTED: label, harmonic,
                  multiple, ratio
    end note
```

---

## 5. Lattice / ToneLattice Lifecycle

Lattices are **immutable after construction** — both topology and
node data are locked.

```mermaid
stateDiagram-v2
    [*] --> Constructing : __init__(dimensionality, resolution, …)

    state Constructing {
        [*] --> GridBuild : grid_graph(dims)\n(module-level generator)
        GridBuild --> CoordMap : _build_coordinate_mapping()
        CoordMap --> [*]
    }

    Constructing --> Immutable : fully frozen

    state Immutable {
        [*] --> ReadOnly
        ReadOnly --> ReadOnly : __getitem__(coord)\nneighbors(coord)\nget_coordinates(node)
    }

    note right of Immutable
        Lattice inherits only GraphCore,
        so add_node / set_node_data
        simply do not exist
        (calling one → AttributeError).
    end note
```

There is no "lock" step — immutability is structural.  `Lattice`
inherits only the read-only `GraphCore`, so once construction finishes
(via the protected raw primitives) there is no public API left that
could change it.

### ToneLattice

Same as `Lattice` but with additional ratio computation at each
coordinate.  Also fully immutable.

### ParameterField

Extends `Lattice` and adds its **own sanctioned writer** for field
values (`set_field_value` at coordinates).  Topology remains frozen —
`ParameterField` defines no structural mutators — but field data at
coordinates can be written through that method.

---

## 6. ParameterTree Lifecycle

`ParameterTree` has the most complex lifecycle because it manages
both the tree structure and an effective-value cache with inheritance.
All parameter state (registered pfield/mfield key sets, per-node
instrument bindings, effective-value cache) lives on the attached
`ParameterLayer`; the public API is provided by `ParameterApiMixin`.

```mermaid
stateDiagram-v2
    [*] --> Created : __init__ or from_tree_structure(source_tree)

    state Created {
        [*] --> CloneTopology : copy graph, empty node data
        CloneTopology --> InitLayer : _init_layers() attaches ParameterLayer\n(_pfields=∅, _mfields=∅,\n_node_instruments={},\n_effective_cache=None)
        InitLayer --> [*]
    }

    Created --> Operational : empty PT

    state Operational {
        [*] --> Ready

        Ready --> PFieldSet : set_pfields(node, freq=values)
        PFieldSet --> DistributeValues : layer registers keys,\nwrites overrides at node
        DistributeValues --> CacheInvalidated : _effective_cache = None
        CacheInvalidated --> Ready

        Ready --> InstrumentSet : set_instrument(node, inst)
        InstrumentSet --> StoredInMap : layer._node_instruments[node] = inst
        StoredInMap --> Ready

        Ready --> PFieldRead : get_pfield(node, 'freq')
        PFieldRead --> CacheCheck : _effective_cache exists?
        CacheCheck --> CacheMiss : No → _build_effective()\n(lazy, on read)
        CacheCheck --> CacheHit : Yes → read from cache
        CacheMiss --> CacheHit : cache now built
        CacheHit --> Ready : return value

        Ready --> Cleared : clear_fields(node=None)
        Cleared --> Ready : pfields/mfields/instruments removed\n(whole tree or subtree)
    }

    note right of Operational
        Override storage: per-node dict
        Effective values: root→leaf cache,
        built lazily on read
        Instrument lookup: ancestor walk
    end note
```

### Effective Cache Rebuild

```mermaid
flowchart TD
    A["_build_effective()"] --> B["stack = [root]"]
    B --> C{"stack empty?"}
    C -->|No| D["pop node"]
    D --> E["parent_eff = cache[parent] or {}"]
    E --> F["cache[node] = {**parent_eff, **node_overrides}"]
    F --> G["push children"]
    G --> C
    C -->|Yes| H["done — O(n) total"]
```

---

## 7. CompositionalUnit Lifecycle

The central composition object.  `CompositionalUnit` sets
`_tree_class = CompositionalTree`, so the single tree built by
`TemporalUnit.__init__` (`uc._rt`) carries **both** a rhythm layer and
a parameter layer on one topology.  There is no mirrored
`ParameterTree` — `uc.pt` is a derived snapshot.

```mermaid
stateDiagram-v2
    [*] --> Created : from_rt(rt, beat, bpm)

    state Created {
        [*] --> UTInit : TemporalUnit.__init__()\n→ builds CompositionalTree via _tree_class\n(rhythm + parameter layers on one tree)
        UTInit --> ParamInit : _init_parameter_fields()\n→ registers pfields/mfields on _rt
        ParamInit --> [*]
    }

    Created --> Configuring : UC with fused tree, no overrides

    state Configuring {
        [*] --> Ready

        Ready --> SetInstrument : set_instrument(node, inst)\n→ _rt.set_instrument(...)
        SetInstrument --> Ready

        Ready --> SetPFields : set_pfields(node, freq=values)\n→ _rt.set_pfields(...)
        SetPFields --> Ready

        Ready --> SetMFields : set_mfields(node, group=values)\n→ _rt.set_mfields(...)
        SetMFields --> Ready

        Ready --> ApplyEnvelope : apply_envelope(env, pfields, node)\n(baked, or recorded if control=True)
        ApplyEnvelope --> Ready

        Ready --> ApplySlur : apply_slur(node)\n→ recorded in _slur_specs
        ApplySlur --> Ready

        Ready --> Subdivide : subdivide(node, S)\n→ mutates _rt in place,\ncascades pfields to new children
        Subdivide --> Ready

        Ready --> MakeRest : make_rest(node)
        MakeRest --> Ready
    }

    Configuring --> Reading : read events

    state Reading {
        [*] --> EnsureCache : _ensure_timing_cache()
        EnsureCache --> ComputeCache : _compute_timing_cache()\n(if dirty)
        ComputeCache --> Snapshot : _build_effective_parameter_tree()\n→ effective PT snapshot\n(with slur/control overlays)
        Snapshot --> MaterializeEvents : Parametron per leaf,\nbacked by the snapshot
        MaterializeEvents --> ResolvePFields : each Parametron resolves:\n1. instrument defaults\n2. inherited values\n3. node overrides
        ResolvePFields --> [*]
    }

    Reading --> Configuring : can continue editing

    note left of Reading
        Lazy: timing cache computed
        only on first access.
        Parametrons are created
        on-the-fly, not stored.
        uc.events returns a DataFrame;
        iterate the UC for Parametrons.
    end note
```

### The Fused Tree (no PT ↔ RT sync)

There is nothing to synchronize: rhythm and parameters live on the
same `CompositionalTree` (`uc._rt`).

- `uc.rt` returns a **copy** of the rhythm view; `uc.pt` returns an
  effective `ParameterTree` **snapshot** (node ids preserved, built by
  `_extract_parameter_tree` / `_build_effective_parameter_tree`).
- `subdivide(node, S)` mutates `_rt` in place; the parent's pfields
  cascade to the new children automatically.
- UC-level overlays (`_slur_specs`, control envelopes) are stored on
  the unit and folded into the effective snapshot at read time.
- `clear_parameters(node=None)` clears overrides, instruments, slurs,
  and envelopes for the whole unit or a subtree.

---

## 8. TemporalUnit Timing Cache Lifecycle

The timing cache within `TemporalUnit` (and `CompositionalUnit`) has
its own mini-lifecycle:

```mermaid
stateDiagram-v2
    [*] --> Dirty : __init__() → _timing_dirty = True

    Dirty --> Computing : _ensure_timing_cache() called\n(on .onsets, .durations, .events, etc.)
    Computing --> Clean : _compute_timing_cache()\n→ real_onset, real_duration for all nodes

    Clean --> Dirty : _invalidate_timing_cache()\n(triggered by subdivide,\nmake_rest, container re-alignment,\nor Score placement / ScoreItem.set_duration)

    Clean --> Clean : read operations\n(.onsets, .durations, .events)
```

### What Triggers Invalidation

| Operation | Invalidates timing? |
|---|---|
| `ScoreItem.set_duration(dur)` | Yes (scales owned unit's bpm) |
| `ScoreItem.stretch(factor)` | Yes (scales owned unit's bpm) |
| `make_rest(node)` | Yes |
| `subdivide(node, S)` | Yes |
| Score placement (``add(at=)`` / ``after=`` / ``before=``) | Yes |
| Container re-alignment (``_set_offsets``, ``_align_rows``) | Yes |
| `set_pfields(…)` | No |
| `set_instrument(…)` | No |
| `apply_envelope(…)` | No (reads timing, doesn't change it) |

Outside a :class:`~klotho.thetos.composition.score.Score`, a temporal
unit's time is immutable: there is no public offset setter and no
``set_duration`` method.  All time mutation is mediated by
:class:`~klotho.thetos.composition.score.ScoreItem`.

---

## 9. CombinationProductSet / MasterSet Lifecycle

Like `Lattice`, CPS objects are fully immutable after construction.
`CombinationProductSet` extends `CombinationSet(GraphCore)` — the
object **is** the graph, and immutability comes from exposing no
mutators (`MasterSet` is a separate layout template, not a graph
class).

```mermaid
stateDiagram-v2
    [*] --> Constructing

    state Constructing {
        [*] --> ComputeCombos : generate all r-combinations\n(CombinationSet)
        ComputeCombos --> BuildGraph : build graph into own\nrustworkx handle (_rx)
        BuildGraph --> ComputeRatios : products → equave_reduce\n→ ratios
        ComputeRatios --> Layout : resolve master_set template\n→ positions, edges
        Layout --> [*]
    }

    Constructing --> Immutable

    state Immutable {
        [*] --> ReadOnly
        ReadOnly --> ReadOnly : .factors, .rank, .combos,\n.products, .ratios,\n.positions, .master_set
    }
```

---

## 10. Summary Table

| Object | Construction | Post-construction topology | Post-construction node data | Derived field recomputation |
|---|---|---|---|---|
| `Graph` | `__init__` or factory | Mutable | Mutable | Manual |
| `Tree` | Tuple notation | Via structural API only | Via layer-validated setters | `_post_mutation` → layer `on_structure_changed` |
| `RhythmTree` | span + meas + subdivs | Via structural API only | `proportion`, `tied` only | `RhythmLayer` → `_evaluate(scope)` |
| `HarmonicTree` | root + children + equave | Via structural API only | `factor` only | `HarmonicLayer` → `_evaluate(scope)` |
| `ParameterTree` | `__init__` / `from_tree_structure` | Via structural API only | Any pfield/mfield | `ParameterLayer._build_effective()` (lazy) |
| `Lattice` | dims + resolution | **Frozen** | **Frozen** | N/A |
| `ToneLattice` | generators + resolution | **Frozen** | **Frozen** | N/A |
| `ParameterField` | lattice + function | **Frozen** | Mutable (field values) | On write |
| `CombinationSet` / `CPS` | factors + r | **Frozen** | **Frozen** | N/A |
| `TemporalUnit` | tempus + prolatio + bpm | Delegates to RT | Delegates to RT | `_compute_timing_cache()` (lazy) |
| `CompositionalUnit` | from_rt / from_ut | Delegates to fused `CompositionalTree` (`_rt`) | via set_pfields, set_instrument | Timing: lazy cache; Params: effective snapshot |
