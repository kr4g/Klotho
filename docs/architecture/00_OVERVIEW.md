# Klotho Architecture Overview

> **Klotho** (from Ancient Greek *κλωθώ*, "to spin") is an open-source
> computer-assisted composition toolkit in Python. It models musical
> structures as graph-theoretic objects—trees, lattices, and
> collections—then layers temporal, tonal, dynamic, and parametric
> semantics on top to produce playable, visualizable compositions.

## Package at a Glance

| Field | Value |
|---|---|
| **PyPI name** | `klotho-cac` |
| **Python** | ≥ 3.11 |
| **License** | CC-BY-SA-4.0 |
| **Graph backend** | RustworkX (`rx`) |
| **Version** | see `klotho/__init__.py` |

---

## Layered Architecture

Klotho is organized into four conceptual layers.  Each layer depends
only on the layers beneath it.

```mermaid
graph TD
    subgraph "Layer 4 — Output"
        semeios["<b>semeios</b><br/>Visualization · Notation"]
        playback["<b>utils.playback</b><br/>Tone.js · SuperSonic · MIDI"]
    end

    subgraph "Layer 3 — Composition"
        thetos["<b>thetos</b><br/>ParameterTree · Instruments<br/>CompositionalUnit · Types"]
    end

    subgraph "Layer 2 — Domain"
        chronos["<b>chronos</b><br/>RhythmTree · TemporalUnit<br/>Sequences · Blocks"]
        tonos["<b>tonos</b><br/>Pitch · Scale · Chord<br/>HarmonicTree · ToneLattice · CPS"]
        dynatos["<b>dynatos</b><br/>Envelope · DynamicRange"]
    end

    subgraph "Layer 1 — Foundation"
        topos["<b>topos</b><br/>Graph · Tree · Lattice<br/>Collections · Grammars"]
        utils["<b>utils</b><br/>Algorithms · Data Structures"]
    end

    topos --> chronos
    topos --> tonos
    topos --> thetos
    utils --> topos

    chronos --> thetos
    tonos --> thetos
    dynatos --> thetos

    thetos --> semeios
    thetos --> playback
    chronos --> semeios
    chronos --> playback
    tonos --> semeios
    tonos --> playback
    dynatos --> semeios
```

### Layer 1 — Foundation (`topos`, `utils`)

Abstract mathematical and structural primitives with no musical
semantics.  `GraphCore` is the read-only base of every graph-shaped
structure; `Graph` adds free-form mutation, `Tree` adds structural
mutators plus attachable `TreeLayer` objects for domain behavior, and
`Lattice` is an immutable *n*-dimensional grid.  Topology generators
(`path_graph`, `complete_graph`, …) are module-level functions in
`topos.graphs.generators`.  Also: `Group`, collection types
(`Pattern`, `CombinationSet`, `PartitionSet`, `Sieve`), formal
grammars, and pure-math algorithms (prime factorization, cost
matrices, graph traversals).

### Layer 2 — Domain (`chronos`, `tonos`, `dynatos`)

Musical domains built on topos structures:

- **chronos** — time and rhythm.  `RhythmTree` extends `Tree` and
  attaches a `RhythmLayer`.
- **tonos** — pitch and harmony.  `HarmonicTree` extends `Tree`
  (with a `HarmonicLayer`); `ToneLattice` extends `Lattice`;
  `CombinationProductSet` extends `CombinationSet` (a `GraphCore`).
- **dynatos** — dynamics and envelopes (standalone; no graph
  inheritance).

### Layer 3 — Composition (`thetos`)

Bridges every domain layer into a unified composition object.
`CompositionalUnit` (extends `TemporalUnit`) carries a single fused
`CompositionalTree` — one topology with both a rhythm layer and a
parameter layer — yielding `Parametron` events that carry temporal
and parametric data together.  (`ParameterTree` remains available as
a standalone parameter tree and as the type of derived snapshots.)
`Score` / `ScoreItem` arrange multiple units on a shared timeline.
Instrument definitions (`SynthDefInstrument`, `MidiInstrument`,
`ToneInstrument`, `Kit`, `Ensemble`) live here.  Typed unit wrappers
(`frequency`, `midi`, `amplitude`, etc.) ensure dimensional
correctness.

### Layer 4 — Output (`semeios`, `utils.playback`)

Rendering and display.  `semeios` dispatches to SVG/Plotly/Three.js
renderers for visualization and provides `KlothoPlot` with integrated
animation and audio.  `utils.playback` converts Klotho objects to event
payloads for two browser-based audio engines (Tone.js, SuperSonic) and
supports MIDI file export.

---

## Subpackage Summary

| Subpackage | Greek root | Domain | Key classes |
|---|---|---|---|
| `topos` | τόπος — "place" | Abstract structure | `GraphCore`, `Graph`, `Tree`, `Lattice`, `Group`, `Pattern`, `CombinationSet`, `PartitionSet`, `Sieve`, `GenCol` |
| `chronos` | χρόνος — "time" | Rhythm & time | `RhythmTree`, `Meas`, `RhythmPair`, `TemporalUnit`, `TemporalUnitSequence`, `TemporalBlock`, `Chronon` |
| `tonos` | τόνος — "tone" | Pitch & harmony | `Pitch`, `Scale`, `Chord`, `Voicing`, `ChordSequence`, `Contour`, `HarmonicTree`, `Spectrum`, `ToneLattice`, `CombinationProductSet`, `MasterSet` |
| `dynatos` | δυνατός — "powerful" | Dynamics & expression | `Dynamic`, `DynamicRange`, `Envelope` |
| `thetos` | θέτος — "placed" | Composition & params | `ParameterTree`, `ParameterField`, `CompositionalUnit`, `Parametron`, `Score`, `ScoreItem`, `Instrument`, `SynthDefInstrument`, `MidiInstrument`, `ToneInstrument`, `Kit`, `Ensemble`, `Unit` subclasses |
| `semeios` | σημεῖον — "sign" | Visualization & notation | `plot()`, `KlothoPlot` |
| `utils` | — | Shared utilities | algorithms, data structures, playback engines |

Top-level exports from `klotho` itself: `plot`, `play`, `play_midi`,
`create_midi`, `set_audio_engine`, `get_audio_engine`,
`register_synthdef`, `GraphCore`, `Graph`, `Tree`, `Lattice`, `Group`.

---

## Domain Abbreviations

These short aliases appear frequently in code and discussion:

| Abbreviation | Full name | Subpackage |
|---|---|---|
| **RT** | RhythmTree | chronos |
| **RP** | RhythmPair | chronos |
| **UT** | TemporalUnit | chronos |
| **UTS** | TemporalUnitSequence | chronos |
| **BT** | TemporalBlock | chronos |
| **HT** | HarmonicTree | tonos |
| **TL** | ToneLattice | tonos |
| **CPS** | CombinationProductSet | tonos |
| **MS** | MasterSet | tonos |
| **PT** | ParameterTree | thetos |
| **PF** | ParameterField | thetos |
| **UC** | CompositionalUnit | thetos |
| **PS** | PartitionSet | topos |
| **PC** | PitchCollection | tonos |
| **ST** | ScaleTree | *(planned; not yet implemented)* |

> Some abbreviations (`UT`, `UC`) derive from French terminology—this is
> intentional and consistent with the IRCAM tradition.

---

## Module Count

~160 Python modules across 7 main subpackages, organized in the tree
shown below.

```
klotho/
├── __init__.py
├── chronos/          (15 modules)
├── dynatos/          (11 modules)
├── semeios/          (26 modules)
├── thetos/           (19 modules)
├── tonos/            (27 modules)
├── topos/            (20 modules)
└── utils/            (39 modules)
```

---

## Key External Dependencies

| Dependency | Role |
|---|---|
| **rustworkx** | High-performance graph backend (Rust-based) |
| **numpy** | Numeric arrays, unit wrappers |
| **sympy** | Symbolic math, prime tests |
| **scipy** | Interpolation, distance metrics, dynamics scaling |
| **pandas** | Tabular metadata (spectra, lattice meta) |
| **matplotlib** | Static 2-D plots |
| **plotly** | Interactive 2-D/3-D plots |
| **networkx** | Graph layout algorithms (spring, spectral) |
| **scikit-learn** | MDS / SpectralEmbedding for CPS layouts |
| **mido** | MIDI file I/O |
| **IPython** | Jupyter HTML widgets, `display` |
| **tabulate** | Pretty-printed ASCII tables |

---

## Architecture Documents Index

### Subsystem Reference

| Document | Scope |
|---|---|
| [01_TOPOS.md](01_TOPOS.md) | Foundation: `Graph`, `Tree`, `Lattice`, collections, grammars |
| [02_CHRONOS.md](02_CHRONOS.md) | Time & rhythm: `RhythmTree`, `TemporalUnit`, sequences, blocks |
| [03_TONOS.md](03_TONOS.md) | Pitch & harmony: pitch collections, `HarmonicTree`, `ToneLattice`, CPS |
| [04_DYNATOS.md](04_DYNATOS.md) | Dynamics & expression: `Dynamic`, `Envelope`, amplitude utilities |
| [05_THETOS.md](05_THETOS.md) | Composition: `ParameterTree`, instruments, `CompositionalUnit`, type system |
| [06_SEMEIOS.md](06_SEMEIOS.md) | Visualization: plot dispatch, SVG/Three.js renderers, animation |
| [07_PLAYBACK.md](07_PLAYBACK.md) | Audio: Tone.js engine, SuperSonic engine, MIDI export |
| [09_UTILS.md](09_UTILS.md) | Shared utilities: algorithms, data structures, constants |

### Guides and Cross-Cutting

| Document | Scope |
|---|---|
| [08_DESIGN_PATTERNS.md](08_DESIGN_PATTERNS.md) | Cross-cutting patterns: mutation policy, caching, factories, naming |
| [10_WALKTHROUGH.md](10_WALKTHROUGH.md) | End-to-end walkthrough: tracing a composition through every layer |
| [11_PITCH_COLLECTIONS.md](11_PITCH_COLLECTIONS.md) | Pitch collection decision guide: choosing the right class |
| [12_LIFECYCLE.md](12_LIFECYCLE.md) | Lifecycle and mutation state diagrams for all major objects |
| [13_IMPORT_GRAPH.md](13_IMPORT_GRAPH.md) | Module-level import dependency graph with analysis |
