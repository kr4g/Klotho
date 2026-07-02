# Tonos — Pitch and Harmony

> *τόνος* (tonos) — "tension," "tone," "pitch."  The origin of the
> word "tone," describing both the phenomenon of pitch and the
> perception of timbre.

`klotho.tonos` models the tonal domain: individual pitches, scales,
chords, voicings, contour, and three graph-based tonal systems—
harmonic trees, tone lattices, and combination product sets.

---

## Module Map

```
tonos/
├── __init__.py
├── pitch/
│   ├── __init__.py
│   ├── pitch.py               # Pitch
│   ├── pitch_collections.py   # PitchCollection hierarchy + PitchCollection factory
│   └── contour.py             # Contour (scale-degree index sequence)
├── scales/
│   ├── __init__.py
│   └── scale.py               # Scale, InstancedScale
├── chords/
│   ├── __init__.py
│   └── chord.py               # Chord, Voicing, ChordSequence
├── systems/
│   ├── __init__.py
│   ├── harmonic_trees/
│   │   ├── __init__.py
│   │   ├── harmonic_tree.py   # HarmonicTree(Tree)
│   │   ├── spectrum.py        # Spectrum (DataFrame view)
│   │   └── algorithms.py      # harmonic evaluation helpers
│   ├── tone_lattices/
│   │   ├── __init__.py
│   │   ├── tone_lattices.py   # ToneLattice(Lattice)
│   │   └── basis.py           # basis matrix, generator coordinates
│   └── combination_product_sets/
│       ├── __init__.py
│       ├── combination_product_sets.py  # CombinationProductSet(CombinationSet)
│       ├── master_set.py               # MasterSet layout templates + MASTER_SETS registry
│       └── algorithms.py               # match_pattern, sub_cps, classify, faces
└── utils/
    ├── __init__.py
    ├── frequency_conversion.py   # freq ↔ midicent ↔ pitch class
    ├── harmonics.py              # partial_to_fundamental, first_equave
    ├── intervals.py              # ratio_to_cents, interval_cost, n_tet
    └── interval_normalization.py # equave_reduce, fold_interval, reduce_freq
```

---

## 1. Pitch Collection Hierarchy

The core abstraction is a hierarchy of pitch-collection classes, from
abstract to concrete:

```mermaid
classDiagram
    class PitchCollectionBase {
        <<abstract>>
        +pitches
        +intervals
        +__len__()
        +is_relative : bool
        +is_instanced : bool
        +reference_pitch : Pitch | None
    }

    class RelativePitchCollection {
        +degrees : list[Fraction]
        +intervals : list[Fraction]
        +is_instanced : bool
        +root(pitch) collection
        +relative() RelativePitchCollection
    }

    class AbsolutePitchCollection {
        +pitches : list[Pitch]
        +intervals : derived
    }

    class RootedPitchCollection {
        +reference_pitch : Pitch
        +pitches : root × degrees
    }

    PitchCollectionBase <|-- RelativePitchCollection
    PitchCollectionBase <|-- AbsolutePitchCollection
    RelativePitchCollection <|-- RootedPitchCollection
    RelativePitchCollection <|-- Scale
    RelativePitchCollection <|-- Chord
    RelativePitchCollection <|-- Voicing

    class Scale {
        +degrees : tuple
        +mode(mode_number) Scale
        +root(pitch) Scale
    }

    class Chord {
        +__invert__() Chord
        +__neg__() Chord
        +root(pitch) Chord
    }

    class Voicing {
        +root(pitch) Voicing
    }

    class ChordSequence {
        +chords : list
        +__getitem__(i) Chord
        +__len__()
    }

    class Contour {
        +values : tuple[int]
        +__getitem__(i)
    }
```

`Chord` inversion is spelled with operators (`~chord` / `-chord`),
not an `inversion(n)` method.  `ChordSequence` is a thin ordered
wrapper around a list of chords.  `Contour` holds a sequence of
**scale-degree indices** used to index into pitch collections (see the
pitch-collections doc).

### Key Distinctions

All of `Scale`, `Chord`, and `Voicing` extend `RelativePitchCollection`
directly.  They are **not** subclasses of each other — they are
specialized variants that enforce different constraints on the same
interval-based foundation.  Any `RelativePitchCollection` can be
given a root via `.root(pitch)` to produce concrete pitches.

| Class | Inherits from | Defined by | Key behavior |
|---|---|---|---|
| `RelativePitchCollection` | `PitchCollectionBase` | Interval ratios/cents | `.root(pitch)` → `RootedPitchCollection`; `.is_instanced` flag |
| `RootedPitchCollection` | `RelativePitchCollection` | Root + intervals | Has `reference_pitch`; produces `Pitch` objects |
| `Scale` | `RelativePitchCollection` | Intervals | Enforces unison, sorts, equave-reduces, adds `.mode(n)` |
| `Chord` | `RelativePitchCollection` | Intervals | Sorts, equave-reduces, no unison required; inversion via `~chord` / `-chord` |
| `Voicing` | `RelativePitchCollection` | Intervals | **No** equave reduction — preserves multi-octave spacing |
| `AbsolutePitchCollection` | `PitchCollectionBase` | Absolute `Pitch` objects | Stores concrete pitches directly |

### `Pitch`

A single pitch, wrapping a frequency ratio (`Fraction`).  Supports
conversion to/from MIDI, midicents, Hz, and pitch-class names.

### Instanced Collections

`InstancedScale`, `InstancedChord`, `InstancedVoicing` are type
aliases (not separate classes) — they are simply `Scale`, `Chord`,
and `Voicing` respectively, constructed with a `reference_pitch`.
Any relative collection becomes "instanced" when `.root(pitch)` is
called, producing concrete `Pitch` objects with Hz values.

---

## 2. HarmonicTree

**File:** `tonos/systems/harmonic_trees/harmonic_tree.py`  
**Inherits:** `Tree` (from `topos.graphs`)

A tree that models **multiplicative harmonic relationships**.  Each
node carries a `factor`; a leaf's *harmonic* is the product of all
factors along the path from the root.  Domain behavior lives in the
attached **`HarmonicLayer`** (owns `factor`, derives
`multiple`/`harmonic`/`ratio`).

### Class Diagram

```mermaid
classDiagram
    Tree <|-- HarmonicTree

    class HarmonicTree {
        +_node_value_attr = "factor"
        +equave : Fraction | None
        +span : int
        +harmonics : tuple
        +ratios : tuple
    }

    class HarmonicLayer {
        owns factor
        derives multiple, harmonic, ratio
    }

    class Spectrum {
        +fundamental : Pitch
        +partials : list
        +data : DataFrame
        +ht : HarmonicTree
        +from_target(target, partials)$
        +pivot(source_partial, target_partial) Spectrum
        +retarget(partial, target) Spectrum
        +modulate(target, source_partial, target_partial) Spectrum
    }

    HarmonicTree o-- HarmonicLayer : attached in _init_layers
    Spectrum --> HarmonicTree : .ht view
```

### Construction

```python
ht = HarmonicTree(
    root=1,
    children=(3, 5, (7, (11, 13))),
    equave=Fraction(2, 1),
    span=1
)
```

### Node Data Model

| Key | Mutable? | Description |
|---|---|---|
| `factor` | **Yes** | The node's multiplicative factor |
| `harmonic` | No (derived) | Product of factors root → node |
| `multiple` | No (derived) | Absolute harmonic number |
| `ratio` | No (derived) | Equave-reduced ratio (if equave set) |

Only `factor` is writable; writes go through the layer-validated
setters (`set_node_data(node, factor=…)`) since node views are
read-only `MappingProxyType` objects.  All other fields are recomputed
by `_evaluate()`, triggered by `HarmonicLayer.on_structure_changed`
with the changed node as scope.

### `_evaluate()` Algorithm

1. Walk the tree root → leaves.
2. Each node's `harmonic = parent.harmonic × node.factor`.
3. `multiple = harmonic` (absolute partial number).
4. If `equave` is set, `ratio = reduce_interval(harmonic, equave, span)`.

Leaf-level results are exposed as the `harmonics` and `ratios`
properties.

### Spectrum

`Spectrum` (`spectrum.py`) is a **separate class**, constructed from a
fundamental (Hz or `Pitch`) plus a list of partials — there is no
`HarmonicTree.spectrum()` method.  It exposes `fundamental`,
`partials`, `data` (a pandas DataFrame), and an `ht` view
(`HarmonicTree` of the partials), plus retuning operations
(`from_target`, `pivot`, `retarget`, `modulate`).

---

## 3. ToneLattice

**File:** `tonos/systems/tone_lattices/tone_lattices.py`  
**Inherits:** `Lattice` (from `topos.graphs`)

An *n*-dimensional lattice where each coordinate axis corresponds to
a prime (or user-defined generator) and each node represents a
frequency ratio.

### Class Diagram

```mermaid
classDiagram
    Lattice <|-- ToneLattice

    class ToneLattice {
        +generators : tuple[Fraction]
        +equave : Fraction
        +bipolar : bool
        +get_ratio(coord) Fraction
        +get_coordinates_for_ratio(ratio, lookup, warn) tuple | list | None
        +from_generators(generators, resolution, ...)$ ToneLattice
    }
```

### Construction

```python
tl = ToneLattice(dimensionality=2, resolution=3)      # default prime basis

tl = ToneLattice.from_generators(
    generators=(Fraction(3, 2), Fraction(5, 4)),      # custom basis
    resolution=3,
)
```

Each coordinate `(a, b)` maps to the ratio
`generator[0]^a × generator[1]^b`, optionally equave-reduced
(`equave_reduce=True` by default).  The reduction window depends on
`bipolar`: `(1/equave, equave)` when bipolar, `[1, equave)` otherwise.

### Coordinate Semantics

The **default** basis uses raw prime generators, one per axis
(skipping the equave prime when reduction is on):
- Axis 0 → powers of 3
- Axis 1 → powers of 5
- Axis 2 → powers of 7, etc.

Stacked-interval bases like `(3/2, 5/4)` are opt-in via
`from_generators`.  Ratio → coordinate lookup supports `"first"`,
`"unique"`, and `"all"` modes and emits a `ToneLatticeLookupWarning`
for ambiguous matches.

The lattice is **immutable** after construction (inherited from
`Lattice` — no mutators exist).

---

## 4. Combination Product Sets (CPS)

**File:** `tonos/systems/combination_product_sets/combination_product_sets.py`  
**Inherits:** `CombinationSet` (from `topos.collections.sets`, itself a `GraphCore`)

Erv Wilson's **Combination Product Sets**: given a set of *n*
harmonic factors and a combination size *r*, the CPS is the set of
all products of *r*-element subsets.  The object **is** the graph —
there is no separate `.graph` property.

### Class Diagram

```mermaid
classDiagram
    GraphCore <|-- CombinationSet
    CombinationSet <|-- CombinationProductSet

    class CombinationSet {
        +factors : tuple
        +rank : int
        +combos : set
        +factor_to_alias : dict
        +alias_to_factor : dict
    }

    class CombinationProductSet {
        +products : tuple[int]
        +ratios : tuple[Fraction]
        +positions : dict
        +master_set : str
        +master_set_instance : MasterSet
        +aliases : dict
        +hexany(factors)$
        +dekany(factors, r)$
        +pentadekany(factors, r)$
        +eikosany(factors)$
        +hebdomekontany(factors)$
    }

    class MasterSet {
        <<layout template>>
        +name : str
        +n_factors : int
        +positions
        +edges
        +relationship_dict
        +with_factors(factors)
    }

    CombinationProductSet --> MasterSet : resolves via MASTER_SETS
```

### Construction and Named CPS Types

CPS construction **requires a `master_set`** — a geometric layout
template resolved by name from the `MASTER_SETS` registry (or passed
as a `MasterSet` instance):

```python
cps = CombinationProductSet((1, 3, 5, 7), r=2, master_set='tetrad')
```

The familiar named types are **classmethod factories** (module-level
names like `Hexany` are aliases to these bound classmethods, not
subclasses):

| Factory | Factors (*n*) | Combination (*r*) | Products | Default master set |
|---|---|---|---|---|
| `CombinationProductSet.hexany` | 4 | 2 | 6 | `'tetrad'` |
| `CombinationProductSet.dekany` | 5 | 2 | 10 | `'arrow'` |
| `CombinationProductSet.pentadekany` | 6 | 2 | 15 | `'asterisk'` |
| `CombinationProductSet.eikosany` | 6 | 3 | 20 | `'asterisk'` |
| `CombinationProductSet.hebdomekontany` | 8 | 4 | 70 | `'ogdoad'` |

### MasterSet

`MasterSet` (`master_set.py`) is **not** a CPS subclass — it is a
standalone geometric layout template defining node positions and edge
relationships (angle, distance, elevation, displacement) keyed by
symbolic factor ratios.  Presets live in the `MASTER_SETS` registry.
A CPS resolves its template at construction and uses it to build its
edge structure and normalized node positions (consumed by the
visualization layer).

### Graph Structure

Nodes represent combinations, carrying `combo`, `product`, `ratio`,
and `alias` data.  Edges come from the master set's
`relationship_dict`, keyed by the symbolic ratio between two
combinations' aliases.  The graph is **immutable** after construction
(no mutators — `CombinationSet` inherits only `GraphCore`).

CPS analysis helpers live in `algorithms.py`: `match_pattern`,
`sub_cps`, `classify`, `faces`.

---

## 5. Tonos Utilities

### `frequency_conversion.py`

| Function | Description |
|---|---|
| `freq_to_midicents(freq)` | Hz → midicents (MIDI × 100) |
| `midicents_to_freq(mc)` | Midicents → Hz |
| `freq_to_pitchclass(freq)` | Hz → pitch class name |
| `midicents_to_pitchclass(mc)` | Midicents → pitch class name |
| `pitchclass_to_freq(name)` | Pitch class name → Hz |

Constants: `A4_Hz = 440.0`, `A4_MIDI = 69`, `PITCH_CLASSES` (dict).

### `intervals.py`

| Function | Description |
|---|---|
| `ratio_to_cents(ratio, round_to=4)` | Frequency ratio → cents |
| `cents_to_ratio(cents)` | Cents → frequency ratio |
| `cents_to_setclass(cent_value, n_tet=12)` | Cents → set-class value in an *n*-TET |
| `ratio_to_setclass(ratio, n_tet=12)` | Ratio → set-class value in an *n*-TET |
| `split_partial(interval, n=2)` | Decompose into equave power + remainder |
| `harmonic_mean(a, b)` | Harmonic mean of two ratios |
| `arithmetic_mean(a, b)` | Arithmetic mean of two ratios |
| `harmonic_distance(ratio)` | Tenney harmonic distance of one ratio |
| `logarithmic_distance(a, b)` | Log-distance between two ratios |
| `interval_cost(a, b, diff_coeff=1.0, prime_coeff=1.0, …)` | Weighted cost between two intervals |
| `n_tet(divisions=12, equave=2, nth_division=1)` | One step ratio of an equal temperament |
| `ratios_n_tet(divisions=12, equave=2)` | All step ratios of an equal temperament |

### `harmonics.py`

| Function | Description |
|---|---|
| `partial_to_fundamental(pitchclass, octave=4, partial=1, cent_offset=0.0)` | `(pitchclass, cents)` of the fundamental implied by a partial |
| `first_equave(harmonic, equave=2, max_equave=None)` | Equave **register number** (int) in which a harmonic first appears |

### `interval_normalization.py`

| Function | Description |
|---|---|
| `equave_reduce(interval, equave=2, n_equaves=1)` | Reduce ratio into `[1, equave)` |
| `reduce_interval(interval, equave=2, n_equaves=1)` | Reduce within *n* equaves |
| `reduce_interval_relative(target, source, equave=2)` | Reduce relative to a reference |
| `reduce_sequence_relative(sequence, equave=2)` | Reduce a sequence preserving contour |
| `fold_interval(interval, lower_thresh, upper_thresh)` | Fold into an explicit `[lower, upper]` window |
| `reduce_freq(freq, lower=27.5, upper=4186, equave=2)` | Reduce Hz into a frequency band |

---

## Class Inheritance Summary

```mermaid
classDiagram
    direction LR

    PitchCollectionBase <|-- RelativePitchCollection
    PitchCollectionBase <|-- AbsolutePitchCollection
    RelativePitchCollection <|-- RootedPitchCollection
    RelativePitchCollection <|-- Scale
    RelativePitchCollection <|-- Chord
    RelativePitchCollection <|-- Voicing

    Tree <|-- HarmonicTree
    Lattice <|-- ToneLattice
    GraphCore <|-- CombinationSet
    CombinationSet <|-- CombinationProductSet
```

`MasterSet` and the named CPS types (`Hexany`, `Dekany`, …) do not
appear in the inheritance tree: the former is a standalone layout
template, the latter are aliases to `CombinationProductSet`
classmethods.
