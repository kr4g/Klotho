# Lifecycle and Mutation State Diagrams

This document describes the lifecycle states of the major Klotho
objects — when they are mutable, what triggers recomputation, and
what the valid operation sequences are.

---

## 1. Graph Lifecycle

`Graph` is the simplest lifecycle.  It starts mutable and stays
mutable unless a subclass explicitly locks it.

```mermaid
stateDiagram-v2
    [*] --> Empty : __init__()
    Empty --> Populated : add_node / add_edge
    Populated --> Populated : add_node / add_edge / remove_node / remove_edge
    Populated --> DataMutated : set_node_data / update_node_data
    DataMutated --> Populated : (automatic — caches invalidated)

    note right of Populated
        _topology_mutable = True
        _node_attr_mutable = True
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
        [*] --> Building : _building_tree = True
        Building --> Building : add_node / add_edge\n(raw graph ops OK)
        Building --> [*] : _building_tree = False
    }
    Constructing --> Built : construction complete

    state Built {
        [*] --> Ready
        Ready --> GroupUpdated : add_child / add_subtree /\nprune / graft_subtree
        GroupUpdated --> CachesInvalidated : _invalidate_caches()
        CachesInvalidated --> PostMutation : _post_mutation()
        PostMutation --> GroupRebuilt : _update_group_structure()
        GroupRebuilt --> Ready

        Ready --> DataMutated : set_node_data(proportion=…)
        DataMutated --> CachesInvalidated2 : _invalidate_caches()
        CachesInvalidated2 --> PostMutation2 : _post_mutation()
        PostMutation2 --> Ready
    }

    note right of Built
        add_node() → NotImplementedError
        add_edge() → NotImplementedError
        Structural changes only via
        add_child, add_subtree, prune, etc.
    end note
```

### Key Points

- During `_building_tree = True`, raw `add_node`/`add_edge` are
  allowed.
- After construction, raw graph mutation raises `NotImplementedError`.
- Every structural or data mutation triggers `_post_mutation()`, which
  calls `_update_group_structure()` and then `_after_post_mutation()`
  (the subclass hook).

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
        ProportionChanged --> Validated : _validate_node_attrs()\n[only proportion, tied allowed]
        Validated --> ScopeResolved : _resolve_data_update_scope()\n→ parent or root
        ScopeResolved --> PostMutation : _post_mutation(scope)
        PostMutation --> ReEvaluated : _evaluate(scope_node)\n→ recompute from scope down
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

When a single proportion changes, `_resolve_data_update_scope()`
returns the **parent** of the changed node (not the root).
`_evaluate(parent)` then only recomputes the subtree from that parent
down, avoiding a full-tree re-evaluation.

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
        FactorChanged --> Validated : _validate_node_attrs()\n[only factor allowed]
        Validated --> ReEvaluated : _evaluate()\n→ recompute all harmonics
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
        [*] --> GridBuild : Graph.grid_graph(dims)
        GridBuild --> CoordMap : _build_coordinate_mapping()
        CoordMap --> Locked : _set_mutability_policy(\ntopology=False,\nnode_attr=False)
        Locked --> [*]
    }

    Constructing --> Immutable : fully frozen

    state Immutable {
        [*] --> ReadOnly
        ReadOnly --> ReadOnly : __getitem__(coord)\nneighbors(coord)\nget_coordinates(node)
    }

    note right of Immutable
        add_node → PermissionError
        set_node_data → PermissionError
        All operations are read-only
    end note
```

### ToneLattice

Same as `Lattice` but with additional ratio computation at each
coordinate.  Also fully immutable.

### ParameterField

Extends `Lattice` but **relaxes node-attribute mutability**:
```python
_set_mutability_policy(topology_mutable=False, node_attr_mutable=True)
```
Topology is frozen, but field values at coordinates can be written.

---

## 6. ParameterTree Lifecycle

`ParameterTree` has the most complex lifecycle because it manages
both the tree structure and an effective-value cache with inheritance.

```mermaid
stateDiagram-v2
    [*] --> Created : from_tree_structure(source_tree)

    state Created {
        [*] --> CloneTopology : copy graph, empty node data
        CloneTopology --> InitMeta : pfields=∅, mfields=∅,\n_node_instruments={},\n_effective_cache=None
        InitMeta --> [*]
    }

    Created --> Operational : empty PT, same shape as RT

    state Operational {
        [*] --> Ready

        Ready --> PFieldSet : set_pfields('freq', values)
        PFieldSet --> DistributeValues : write overrides to leaf nodes
        DistributeValues --> CacheInvalidated : _effective_cache = None
        CacheInvalidated --> Ready

        Ready --> InstrumentSet : set_instrument(node, inst)
        InstrumentSet --> StoredInMap : _node_instruments[node] = inst
        StoredInMap --> Ready

        Ready --> PFieldRead : get_pfield(node, 'freq')
        PFieldRead --> CacheCheck : _effective_cache exists?
        CacheCheck --> CacheMiss : No → _build_effective()
        CacheCheck --> CacheHit : Yes → read from cache
        CacheMiss --> CacheHit : cache now built
        CacheHit --> Ready : return value

        Ready --> Cleared : clear()
        Cleared --> Ready : all pfields/mfields/instruments removed
    }

    note right of Operational
        Override storage: per-node dict
        Effective values: root→leaf cache
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

The central composition object, combining `TemporalUnit` (RT + tempo)
with `ParameterTree`.

```mermaid
stateDiagram-v2
    [*] --> Created : from_rt(rt, beat, bpm)

    state Created {
        [*] --> UTInit : TemporalUnit.__init__()\n→ creates internal RT
        UTInit --> PTSync : _create_synchronized_parameter_tree()\n→ clones RT topology
        PTSync --> [*]
    }

    Created --> Configuring : UC with empty PT

    state Configuring {
        [*] --> Ready

        Ready --> SetInstrument : set_instrument(node, inst)
        SetInstrument --> Ready

        Ready --> SetPFields : set_pfields(node, freq=values)
        SetPFields --> Ready

        Ready --> SetMFields : set_mfields(node, group=values)
        SetMFields --> Ready

        Ready --> ApplyEnvelope : apply_envelope(env, 'amp', node)
        ApplyEnvelope --> Ready

        Ready --> ApplySlur : apply_slur(node)
        ApplySlur --> Ready

        Ready --> Subdivide : subdivide(node, S)\n→ modifies RT and PT
        Subdivide --> PTResync : PT topology updated\nto match new RT
        PTResync --> Ready

        Ready --> MakeRest : make_rest(node)
        MakeRest --> Ready
    }

    Configuring --> Reading : read events

    state Reading {
        [*] --> EnsureCache : _ensure_timing_cache()
        EnsureCache --> ComputeCache : _compute_timing_cache()\n(if dirty)
        ComputeCache --> MaterializeEvents : _materialize_events()\n→ Parametron per leaf
        MaterializeEvents --> ResolvePFields : each Parametron resolves:\n1. instrument defaults\n2. PT inherited values\n3. PT node overrides
        ResolvePFields --> [*]
    }

    Reading --> Configuring : can continue editing

    note left of Reading
        Lazy: timing cache computed
        only on first access.
        Parametrons are created
        on-the-fly, not stored.
    end note
```

### PT ↔ RT Synchronization

When `subdivide()` or structural mutations occur on the UC:

1. The RT is modified (new nodes added).
2. The PT is rebuilt via `_create_synchronized_parameter_tree()` or
   updated to match the new RT topology.
3. Previously set pfields/mfields on surviving nodes are preserved.

---

## 8. TemporalUnit Timing Cache Lifecycle

The timing cache within `TemporalUnit` (and `CompositionalUnit`) has
its own mini-lifecycle:

```mermaid
stateDiagram-v2
    [*] --> Dirty : __init__() → _timing_dirty = True

    Dirty --> Computing : _ensure_timing_cache() called\n(on .onsets, .durations, .events, etc.)
    Computing --> Clean : _compute_timing_cache()\n→ real_onset, real_duration for all nodes

    Clean --> Dirty : _invalidate_timing_cache()\n(triggered by bpm change,\noffset change, subdivide,\nmake_rest, set_duration)

    Clean --> Clean : read operations\n(.onsets, .durations, .events)
```

### What Triggers Invalidation

| Operation | Invalidates timing? |
|---|---|
| `set_duration(dur)` | Yes (changes bpm) |
| `make_rest(node)` | Yes |
| `subdivide(node, S)` | Yes |
| `offset = new_val` | Yes |
| `set_pfields(…)` | No |
| `set_instrument(…)` | No |
| `apply_envelope(…)` | No (reads timing, doesn't change it) |

---

## 9. CombinationProductSet / MasterSet Lifecycle

Like `Lattice`, CPS objects are fully immutable after construction:

```mermaid
stateDiagram-v2
    [*] --> Constructing

    state Constructing {
        [*] --> ComputeProducts : generate all r-combinations
        ComputeProducts --> BuildGraph : create nodes (products),\nedges (shared factors)
        BuildGraph --> ComputeRatios : equave_reduce each product
        ComputeRatios --> Lock : _set_mutability_policy(\ntopology=False,\nnode_attr=False)
        Lock --> [*]
    }

    Constructing --> Immutable

    state Immutable {
        [*] --> ReadOnly
        ReadOnly --> ReadOnly : .products, .ratios,\n.complement(), .factors
    }
```

---

## 10. Summary Table

| Object | Construction | Post-construction topology | Post-construction node data | Derived field recomputation |
|---|---|---|---|---|
| `Graph` | `__init__` or factory | Mutable | Mutable | Manual |
| `Tree` | Tuple notation | Via structural API only | Mutable (`_node_value_attr`) | `_post_mutation` → `_after_post_mutation` |
| `RhythmTree` | span + meas + subdivs | Via structural API only | `proportion`, `tied` only | `_evaluate(scope_node)` |
| `HarmonicTree` | root + children + equave | Via structural API only | `factor` only | `_evaluate()` |
| `ParameterTree` | `from_tree_structure` | Via structural API only | Any pfield/mfield | `_build_effective()` (lazy) |
| `Lattice` | dims + resolution | **Frozen** | **Frozen** | N/A |
| `ToneLattice` | generators + resolution | **Frozen** | **Frozen** | N/A |
| `ParameterField` | lattice + function | **Frozen** | Mutable (field values) | On write |
| `CPS` / `MasterSet` | factors + r | **Frozen** | **Frozen** | N/A |
| `TemporalUnit` | tempus + prolatio + bpm | Delegates to RT | Delegates to RT | `_compute_timing_cache()` (lazy) |
| `CompositionalUnit` | from_rt / from_ut | Delegates to RT + PT | via set_pfields, set_instrument | Timing: lazy cache; Params: effective cache |
