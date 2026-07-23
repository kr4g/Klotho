# Topos — Foundation Layer

> *"The name topos has been chosen to communicate a double message…
> to unite philosophical insight with mathematical explicitness."*
> — after Guerino Mazzola, *The Topos of Music*

`klotho.topos` provides the abstract mathematical and structural
primitives on which every other subpackage is built.  Nothing in this
layer has musical semantics—it is pure graph theory, set theory, and
formal grammars.

---

## Module Map

```
topos/
├── __init__.py
├── types.py               # abstract structural types
├── collections/
│   ├── _pattern.py        # Pattern runtime internals (NodeSpec, delegates)
│   ├── patterns.py        # permutations, autoref, chaining
│   ├── sequences.py       # Nørgård infinity series, Pattern iterator
│   └── sets.py            # Operations, Sieve, GenCol, CombinationSet, PartitionSet
├── formal_grammars/
│   ├── alphabet.py        # Alphabet — symbol inventory
│   ├── rules.py           # RuleSet — production rules
│   ├── rewriting.py       # RewriteSystem, History + legacy helpers
│   ├── derivation.py      # DerivationTree, derive()
│   ├── interpreter.py     # Interpreter, State (turtle-style word interpretation)
│   └── markov.py          # markov_walk()
├── shapes/
│   └── polyominoes.py     # Shape + polyomino generation/placement
└── graphs/
    ├── core.py            # GraphCore — read-only base (RustworkX) + views
    ├── graphs.py          # Graph — mutable general-purpose graph
    ├── generators.py      # module-level topology generators
    ├── trees/
    │   ├── trees.py       # Tree (rooted DAG, layer-aware)
    │   ├── layers.py      # TreeLayer protocol
    │   └── group.py       # Group — immutable (D, S) tuple
    └── lattices/
        ├── lattices.py    # Lattice (n-dimensional grid)
        └── algorithms.py  # lattice-specific algorithms
```

---

## 1. GraphCore and Graph

**Files:** `topos/graphs/core.py` (`GraphCore`), `topos/graphs/graphs.py` (`Graph`)  
**Backend:** `rustworkx.PyGraph` (undirected) or `rustworkx.PyDiGraph` (directed)

`GraphCore` is the **read-only root** of every graph-shaped structure in
Klotho.  It wraps a RustworkX graph (stored as `self._rx`) and exposes
views, traversal, and query operations only — no public mutators.
`Graph(GraphCore)` adds free-form topology and node-data mutation for
general-purpose use.  Everything else (`Tree`, `Lattice`,
`CombinationSet`, …) inherits `GraphCore` directly and exposes either a
disciplined subset of mutators or none at all.

**Immutability is the absence of mutators**, not a runtime flag: an
immutable class like `Lattice` simply never defines `add_node`, so
calling it raises a plain `AttributeError`.

### Class Diagram

```mermaid
classDiagram
    class GraphCore {
        -_rx : rx.PyGraph | rx.PyDiGraph
        -_meta : dict
        -_structure_version : int
        +nodes : GraphNodeView
        +edges : GraphEdgeView
        +neighbors(node) list
        +predecessors(node) tuple
        +successors(node) tuple
        +descendants(node) tuple
        +ancestors(node) tuple
        +topological_sort()
        +subgraph(node) GraphCore
        +root_nodes : tuple
        +has_edge(u, v) bool
        +copy()
        +to_networkx()
        +to_directed() Graph
        #_add_node_raw(**attr) int
        #_add_edge_raw(u, v, **attr)
        #_write_node_data(node, attrs, replace)
        #_invalidate_caches()
    }

    class Graph {
        +add_node(**attr) int
        +add_edge(u, v, **attr)
        +remove_node(node)
        +remove_edge(u, v)
        +set_node_data(node, **attr)
        +update_node_data(node, attrs)
        +replace_node_data(node, attrs)
        +update(edges, nodes)
        +clear()
    }

    class GraphNodeView {
        +__getitem__(node) MappingProxyType
        +__iter__()
        +__contains__(node)
        +__len__()
        +__call__(data=False)
    }

    class GraphEdgeView {
        +__iter__()
        +__len__()
        +__call__(data=False)
        +__getitem__(edge) dict
    }

    GraphCore <|-- Graph
    GraphCore *-- GraphNodeView
    GraphCore *-- GraphEdgeView
```

### Raw Write Primitives

Subclasses and internal code perform sanctioned writes through the
protected `_*_raw` primitives on `GraphCore` (`_add_node_raw`,
`_add_edge_raw`, `_remove_node_raw`, `_remove_edge_raw`,
`_write_node_data`).  These write directly to `self._rx` and invalidate
caches, but apply **no validation or recomputation policy** — policy
lives in the public mutators of each subclass (`Graph` passes writes
straight through; `Tree` routes them through attached layers, see §2).

### Constructors on `Graph`

| Classmethod | Description |
|---|---|
| `from_rustworkx(rx_graph)` | Wrap an existing RustworkX graph |
| `from_networkx(nx_graph)` | Convert from NetworkX |
| `from_nodes_edges(nodes, edges)` | Build from explicit lists |
| `from_edges(edges)` | Infer nodes from edge list |
| `empty_graph(n)` | *n* isolated nodes |
| `directed()` / `digraph()` | Empty directed graph |

### Topology Generators (module-level)

Topology builders are **module-level functions** in
`topos/graphs/generators.py`, re-exported from `klotho.topos.graphs`.
They were moved out of `Graph` so they are not inherited (and broken)
by subclasses such as `Tree` or `RhythmTree`.  Each returns a mutable
`Graph`:

| Function | Description |
|---|---|
| `path_graph(n_nodes)` | Linear chain |
| `cycle_graph(n_nodes)` | Ring |
| `star_graph(n_nodes, center=0)` | Hub-and-spoke |
| `random_graph(n_nodes, p=0.3)` | Erdős–Rényi random |
| `complete_graph(n_nodes)` | Fully connected |
| `grid_graph(dims, periodic=False)` | *n*-dimensional grid |
| `from_cost_matrix(matrix, items)` | Complete weighted graph |

```python
from klotho.topos.graphs import complete_graph
g = complete_graph(5)          # a mutable Graph
```

### Node-Data Access Is Read-Only

`graph.nodes[n]` and `graph[n]` return a `MappingProxyType` — direct
writes like `graph.nodes[n]['key'] = value` raise `TypeError`.  All
node-data mutation goes through the sanctioned methods
(`set_node_data`, `update_node_data`, `replace_node_data`).

### Cache Invalidation

- `_structure_version` is an integer counter bumped on every structural
  change.
- `@lru_cache` decorates `descendants`, `ancestors`, `successors`,
  `predecessors`; the cached methods read `_structure_version` so stale
  entries are never returned.
- `_invalidate_caches()` clears these caches and is called
  automatically by every raw write primitive.

---

## 2. Tree

**File:** `topos/graphs/trees/trees.py`  
**Inherits:** `GraphCore` (always directed)

A rooted directed acyclic tree built from nested `(D, S)` tuple
notation, where `D` is a value and `S` is a tuple of children.

`Tree` does **not** inherit `Graph`, so it never exposes free-form
`add_node`/`add_edge`.  Structural changes go exclusively through its
sanctioned mutators (`add_child`, `add_subtree`, `prune`,
`graft_subtree`, `move_subtree`, …), and node-data writes are routed
through attached **layers** (see below).

### Class Diagram

```mermaid
classDiagram
    GraphCore <|-- Tree

    class Tree {
        +_node_value_attr : str = "label"
        -_layers : list~TreeLayer~
        +root : int
        +group : Group
        +layers : tuple
        +depth : int
        +k : int
        +leaf_nodes : tuple
        +subtree_leaves(node) tuple
        +depth_of(node) int
        +parent(node) int
        +ancestors(node) tuple
        +descendants(node) tuple
        +branch(node) tuple
        +siblings(node) tuple
        +lowest_common_ancestor(a, b) int
        +subtree(node, renumber=True) Tree
        +at_depth(n, operator='==') list
        +path_signature(root, target) tuple
        +node_from_signature(root, signature) int
        +map_parallel_nodes(other_tree) dict
        +attach_layer(layer)
        +set_node_data(node, **attr)
        +update_node_data(node, attrs)
        +replace_node_data(node, attrs)
        +add_child(parent, index, **attr) int
        +add_subtree(parent, subtree, index)
        +prune(node)
        +remove_subtree(node)
        +replace_node(old_node, **attr)
        +graft_subtree(target, subtree, mode)
        +move_subtree(node, new_parent, index)
        +prune_to_depth(max_depth)
        +prune_leaves(n)
    }

    class TreeLayer {
        +owned_keys : frozenset
        +derived_keys : frozenset
        +on_attach(tree)
        +normalize_attrs(tree, node, attrs, op)
        +validate_attrs(tree, node, attrs, op)
        +data_scope(tree, node, changed_keys, op)
        +on_structure_changed(tree, scope, op)
        +invalidate(tree)
        +on_nodes_remapped(tree, mapping)
        +on_clone(tree)
        +clone_state(source_layer, new_tree, memo)
    }

    class Group {
        +D : value
        +S : tuple
    }

    Tree o-- TreeLayer : notifies
    Tree *-- Group
```

### Construction from Nested Tuples

Trees are built from a recursive `(D, S)` notation:

```python
Tree(root=4, children=(1, (2, (1, 1)), 1))
```

This produces:

```
       4
      /|\
     1  2  1
       / \
      1   1
```

During `__init__`, `_build_tree` recursively walks the tuple, using the
protected raw primitives (`_add_node_raw` / `_add_edge_raw`) inherited
from `GraphCore`.  There is no public `add_node`/`add_edge` on `Tree`
at any point — post-construction structural changes must go through
`add_child`, `add_subtree`, `prune`, etc., which always end in
`_post_mutation`.

### Tree Layers

Domain behavior (rhythm, harmony, parameters) lives in `TreeLayer`
objects (`topos/graphs/trees/layers.py`) attached to a tree, not in
subclass method overrides.  A layer owns a set of writable node-data
keys (`owned_keys`), declares the keys it computes (`derived_keys`),
and implements recompute rules.  Subclasses attach their layers in the
`_init_layers` hook:

- **`RhythmLayer`** (chronos) — owns `proportion`/`tied`, derives
  `metric_duration`/`metric_onset`.
- **`HarmonicLayer`** (tonos) — owns `factor`, derives
  `multiple`/`harmonic`/`ratio`.
- **`ParameterLayer`** (thetos) — owns pfield/mfield overrides,
  instruments, and the effective-value cache.

Multiple layers can be attached to a single tree:
`CompositionalTree` carries **both** a rhythm layer and a parameter
layer on one topology, which is how a `CompositionalUnit` avoids
mirroring two trees.

### Node-Data Write Pipeline

Every node-data write (`set_node_data`, `update_node_data`,
`replace_node_data`) is routed through the attached layers:

```mermaid
flowchart LR
    A["set_node_data(node, **attr)"] --> B["layer.normalize_attrs (each layer)"]
    B --> C["layer.validate_attrs (each layer)"]
    C --> D["layer.data_scope → scope node"]
    D --> E["_write_node_data (raw)"]
    E --> F["_post_mutation(scope)"]
    F --> G["_invalidate_caches"]
    F --> H["layer.on_structure_changed (each layer)"]
```

Structural mutators (`add_child`, `prune`, …) skip the data hooks but
also end in `_post_mutation`, so layers always get a chance to
recompute derived fields (e.g. `RhythmLayer` re-runs the rhythm-tree
evaluation for the affected scope).

### `_node_value_attr`

Subclasses override this class attribute to use a domain-specific name:

| Subclass | `_node_value_attr` |
|---|---|
| `Tree` | `'label'` |
| `RhythmTree` | `'proportion'` |
| `HarmonicTree` | `'factor'` |
| `ParameterTree` | `'label'` (popped from node data after init) |

### `from_tree_structure`

A key factory: creates a new tree instance with the **same topology**
as a source tree but **empty node data**, then re-runs `_init_layers`.
Used to derive parameter-tree snapshots from a rhythm-bearing tree's
shape.

---

## 3. Group

**File:** `topos/graphs/trees/group.py`  
**Inherits:** `tuple` (immutable)

An immutable `(D, S)` pair representing a duration and its
subdivisions.  Provides `.D` and `.S` properties plus helper functions:

| Function | Purpose |
|---|---|
| `factor_children` | Multiply all children by a factor |
| `refactor_children` | Normalize children to a new sum |
| `get_signs` | Extract the sign of each child |
| `get_abs` | Absolute value of each child |
| `rotate_children` | Cyclic rotation of subdivision list |
| `format_subdivisions` | Pretty-print a subdivision tuple |

---

## 4. Lattice

**File:** `topos/graphs/lattices/lattices.py`  
**Inherits:** `GraphCore` (undirected)

An *n*-dimensional grid graph with coordinate-based access.  The grid
itself is produced by the `grid_graph` generator during construction.

### Class Diagram

```mermaid
classDiagram
    GraphCore <|-- Lattice

    class Lattice {
        -_coord_to_node : dict
        -_node_to_coord : dict
        -_dimensionality : int
        -_resolution : list[int]
        -_bipolar : bool
        -_periodic : bool
        +dimensionality : int
        +resolution : list[int]
        +bipolar : bool
        +coords : list[tuple]
        +get_node(coord) int
        +get_coordinates(node_id) tuple
        +neighbors(coord) list[tuple]
        +symmetries(reflections=False) list
        +number_of_nodes() int
        +number_of_edges() int
        +__getitem__(coord) MappingProxyType
        +__contains__(coord) bool
    }

    class LatticeEdgeView {
        +__iter__() yields (coord_a, coord_b, data)
    }

    Lattice *-- LatticeEdgeView
```

### Key Properties

- **`dimensionality`** — number of axes (default 2).
- **`resolution`** — points per axis (int or list; default 10).
- **`bipolar`** — if `True` (default), coordinates range `[-res, +res]`;
  otherwise `[0, res]`.
- **`periodic`** — wraps edges at boundaries (torus topology).

Large or high-dimensional lattices are built **lazily**: when the
estimated size crosses a threshold (`_should_use_lazy`), coordinates
are materialized on demand (`_materialize_coord`) instead of eagerly
building the full grid.  `symmetries(reflections=False)` enumerates
the lattice's orientation symmetries (used for shape placement,
10.9.0).

### Coordinate ↔ Node Mapping

Externally, lattice nodes are addressed by coordinate tuples
`(x, y, ...)`.  Internally, each coordinate maps to an integer node ID
in the RustworkX graph.  The `Lattice` acts as an adapter between these
two addressing schemes.

### Immutability

`Lattice` builds its graph during construction and then exposes **no
mutators** — since it inherits only `GraphCore`, there is no
`add_node`/`set_node_data` to call, and attempting one raises a plain
`AttributeError`.  Subclasses that need writable node data
(`ParameterField`) add their own sanctioned write methods (e.g.
`set_field_value`) on top.

---

## 5. Collections

### 5.1 `Operations` (static set operations)

Pure static methods for mathematical set operations:

`union`, `intersect`, `diff`, `symm_diff`, `is_subset`, `is_superset`,
`invert`, `transpose`, `complement`, `congruent`, `intervals`,
`interval_vector`.

### 5.2 `Sieve`

Implements Xenakis-style sieves — modular-arithmetic pitch/rhythm
filters composed with logical operations (`&`, `|`, `^`, `~`).

### 5.3 `GenCol`

Generated collection: multiplicative construction from a generator
ratio iterated within a period
(`GenCol(generator='3/2', period=2, iterations=7)`).  Exposes
`collection`, `normalized_collection` (period-reduced), and `steps`.

### 5.4 `CombinationSet`

**Inherits:** `GraphCore`

Generates all *r*-combinations from a set of factors and **is itself a
graph**: a complete graph with combinations as nodes, built during
construction into the backing rustworkx handle.  There is no separate
`.graph` property — query the object directly (`cs.nodes`,
`cs.edges`, …).  Key properties: `factors`, `rank`, `combos`,
`factor_to_alias`, `alias_to_factor`.  As with all `GraphCore`-only
classes, it exposes no mutators.  `CombinationProductSet` (tonos)
extends it.

### 5.5 `PartitionSet`

A plain (non-graph) class.  Generates all partitions of an integer *n*
into exactly *k* parts and computes structural features.  Key
properties: `data` (pandas DataFrame with `partition`, `unique_count`,
`span`, `variance` columns), `partitions`, `mean`.

### 5.6 `Pattern`

Cyclical iterator over nested structure
(`Pattern(iterable, end=False)`).  A nested list is a **sub-pattern**
that advances by one element each time the enclosing pattern reaches
it (it does *not* flatten):

```python
p = Pattern([1, [2, 3], 4])
[next(p) for _ in range(6)]  # [1, 2, 4, 1, 3, 4]
```

The full cycle length is exposed as `length`; `materialize_period()`
returns one full period without disturbing iteration state;
`position` and `reset()` manage the cursor.  The compiled structure
is available as `spec` (a `NodeSpec` from `_pattern.py`).

### 5.7 `Norg` (Nørgård infinity series)

Per Nørgård's self-similar integer sequence, used as a pitch or
rhythm generator.  Static methods: `inf(start=0, size=128, step=1)`,
`inf_num(n)`, `n_partite(seed, inv_pat, size=128)`, `lake()`.

### Collection Relationships Diagram

```mermaid
classDiagram
    class Operations {
        +union()$
        +intersect()$
        +diff()$
        +transpose()$
        +invert()$
        +complement()$
    }

    class Sieve {
        +modulus : int
        +residue : int
        +N : int
        +period
        +r
        +congr
        +compl
        +__and__()
        +__or__()
        +__sub__()
        +__xor__()
        +__invert__()
    }

    class GenCol {
        +generator : Fraction
        +period : Fraction
        +iterations : int
        +collection : list
        +normalized_collection : list
        +steps : set
    }

    class CombinationSet {
        +factors : tuple
        +rank : int
        +combos : set
        +factor_to_alias : dict
        +alias_to_factor : dict
    }

    class PartitionSet {
        +data : DataFrame
        +partitions : tuple
        +mean : float
    }

    class Pattern {
        +length : int
        +position : int
        +__next__()
        +reset()
        +materialize_period() tuple
    }

    class Norg {
        +inf(start, size, step)$
        +inf_num(n)$
        +n_partite(seed, inv_pat, size)$
        +lake()$
    }

    GraphCore <|-- CombinationSet
```

---

## 6. Formal Grammars

`topos/formal_grammars/` is a full rewriting-system package (expanded
in 10.5.0/10.6.0 from the old single-module engine):

| Symbol | Module | Purpose |
|---|---|---|
| `Alphabet` | `alphabet.py` | Symbol inventory of a rewriting system |
| `RuleSet(rules, alphabet=None)` | `rules.py` | Mapping of production rules (weighted options allowed) |
| `RewriteSystem(rules, axiom, alphabet=None, rng=None)` | `rewriting.py` | L-system-style rewriting; `step(word)`, `generate(generations, word_limit=None, mutation=0.0)` → `History` |
| `History(words, rules)` | `rewriting.py` | Sequence of words, one per generation |
| `DerivationTree` / `derive(axiom, rules, max_depth=4, rng=None)` | `derivation.py` | Recursive (possibly stochastic) derivation as a tree |
| `Interpreter(state=None, actions=None, brackets=None, …)` / `State` | `interpreter.py` | Turtle-style word interpretation; `run(word)` |
| `markov_walk(table, start=None, length=16, rng=None)` | `markov.py` | First-order Markov chain walk |

Word utilities in `rewriting.py`: `balance_brackets(word)`,
`bracket_depth(word)`, `show_generations(history)`,
`word_stats(word, alphabet=None)`.

Legacy helpers (kept, now in `rewriting.py`):

| Function | Purpose |
|---|---|
| `rand_rules(symbols, word_length_min=1, word_length_max=3)` | Generate random production rules |
| `constrain_rules(rules, constraints)` | Mutate rules to satisfy constraints |
| `apply_rules(rules, axiom)` | One step of rule application |
| `gen_str(generations=0, axiom='', rules=None, display=False)` | Dict of strings, one per derivation step |

---

## 7. Shapes (`topos/shapes/`)

Polyomino generation and placement (new in 10.8.0):

| Symbol | Purpose |
|---|---|
| `Shape` | Immutable tuple of cells with canonical form |
| `polyominoes(n, dims=2, kind='one-sided')` | Generate all polyominoes (or polycubes) of *n* cells |
| `normalize(cells)` | Translate cells to canonical origin |
| `translate(cells, offset)` | Shift cells by an offset |
| `rotations(cells, reflections=False, group=None)` | All orientations of a cell set |
| `center(cells)` | Centroid of a cell set |
| `fits(cells, lattice)` / `placements(piece, lattice, orientations=True)` | Test / enumerate placements on a lattice |
| `overlap(a, b)` / `contact(a, b)` | Cell-set intersection / adjacency tests |

Shapes pair with `Lattice.symmetries()` and the
`plot(lattice, layout='cells', shape=…)` board-style visualization
(see the semeios doc).

---

## Inheritance Summary

```mermaid
classDiagram
    GraphCore <|-- Graph
    GraphCore <|-- Tree
    GraphCore <|-- Lattice
    GraphCore <|-- CombinationSet
    Tree <|-- RhythmTree
    Tree <|-- HarmonicTree
    Tree <|-- ParameterTree
    RhythmTree <|-- CompositionalTree
    Lattice <|-- ToneLattice
    Lattice <|-- ParameterField
    CombinationSet <|-- CombinationProductSet

    class GraphCore { topos }
    class Graph { topos }
    class Tree { topos }
    class Lattice { topos }
    class CombinationSet { topos }
    class RhythmTree { chronos }
    class HarmonicTree { tonos }
    class ParameterTree { thetos }
    class CompositionalTree { thetos }
    class ToneLattice { tonos }
    class ParameterField { thetos }
    class CombinationProductSet { tonos }
```

All domain-specific graph structures trace back to **`GraphCore`**
through `Tree`, `Lattice`, or `CombinationSet`, inheriting the views,
traversal/query API, and cache system.  Mutation is opt-in per class:
`Graph` for free-form graphs, `Tree` for structural mutators plus
layer-validated node data, and nothing at all for the immutable
classes.  (`CompositionalTree` additionally mixes in
`ParameterApiMixin` — see the thetos doc.)
