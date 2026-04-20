# Semeios — Visualization and Notation

> *σημεῖον* (semeion) — "sign," "mark."  This module provides tools for
> visualizing and notating musical structures.

`klotho.semeios` is the primary output layer for visual representation.
It provides a universal `plot()` dispatcher that routes Klotho objects
to type-specific renderers (SVG, Plotly, Three.js), wraps the results
in `KlothoPlot` objects with integrated animation and audio playback,
and exports note-list data for SuperCollider.

---

## Module Map

```
semeios/
├── __init__.py
├── notelists/
│   ├── __init__.py
│   └── supercollider.py               # Scheduler — SC event export
└── visualization/
    ├── __init__.py
    ├── plots.py                        # plot() dispatcher
    ├── _dispatch/
    │   ├── __init__.py
    │   ├── _klotho_plot.py             # KlothoPlot wrapper
    │   ├── plot_rt.py                  # RhythmTree plotting
    │   ├── plot_lattice.py             # Lattice / ToneLattice plotting
    │   └── plot_cps.py                 # CPS / MasterSet plotting
    ├── _renderers/
    │   ├── __init__.py
    │   ├── svg_rt.py                   # SVG renderer: rhythm trees
    │   ├── svg_lattice.py              # SVG renderer: lattices
    │   ├── svg_cps.py                  # SVG renderer: CPS
    │   ├── svg_master_set.py           # SVG renderer: master sets
    │   ├── threejs_lattice.py          # Three.js renderer: lattices (3D)
    │   ├── threejs_cps.py              # Three.js renderer: CPS (3D)
    │   └── threejs_master_set.py       # Three.js renderer: master sets (3D)
    ├── _animation/
    │   ├── __init__.py
    │   ├── base.py                     # animation base utilities
    │   ├── animated.py                 # AnimatedLattice3dFigure
    │   ├── _playback.js                # JS for lattice animation audio
    │   └── _shape_playback.js          # JS for CPS/shape animation audio
    └── _shared/
        ├── __init__.py
        ├── colors.py                   # color scales, palettes
        ├── geometry.py                 # geometric layout helpers
        ├── svg_shared.py               # shared SVG building blocks
        └── svg_utils.py                # SVG utility functions
```

---

## 1. The `plot()` Dispatcher

**File:** `semeios/visualization/plots.py`

The single entry point for all visualization:

```python
from klotho import plot

result = plot(obj, **kwargs)
```

### Dispatch Logic

```mermaid
flowchart TD
    P["plot(obj)"] --> T{"type(obj)?"}

    T -->|RhythmTree<br/>TemporalUnit<br/>CompositionalUnit| RT["_plot_rt(obj)"]
    T -->|Lattice<br/>ToneLattice<br/>ParameterField| LAT["_plot_lattice(obj)"]
    T -->|CombinationProductSet<br/>Hexany, Dekany…| CPS["_plot_cps(obj)"]
    T -->|MasterSet| MS["_plot_master_set(obj)"]
    T -->|Scale| SC["scale bar chart"]
    T -->|Chord / Voicing| CH["chord visualization"]
    T -->|DynamicRange| DR["dynamics plot"]
    T -->|Envelope| EN["envelope curve"]
    T -->|CombinationSet / PartitionSet| CS["graph plot"]
    T -->|Tree / Graph| GR["generic graph layout"]

    RT --> KP["KlothoPlot<br/>(animatable)"]
    LAT --> KP
    CPS --> KP
    MS --> KP

    SC --> DISP["IPython.display.display()"]
    CH --> DISP
    DR --> DISP
    EN --> DISP
    CS --> DISP
    GR --> DISP
```

### Return Values

- **Animatable types** (RhythmTree, Lattice, CPS, TemporalUnit,
  CompositionalUnit) → returns a `KlothoPlot`.
- **Non-animatable types** (Scale, Chord, Envelope, etc.) → displayed
  immediately via `IPython.display.display()`, returns `None`.

---

## 2. KlothoPlot

**File:** `semeios/visualization/_dispatch/_klotho_plot.py`

A wrapper that holds a static figure (Plotly or SVG HTML) and knows
how to trigger animated playback with audio.

```mermaid
classDiagram
    class KlothoPlot {
        -_figure_html : str
        -_audio_events : list
        -_animation_type : str
        +_repr_html_() str
        +play(**kwargs) DisplayHandle
    }
```

### Lifecycle

1. `plot(obj)` builds the static figure HTML and extracts audio
   event data.
2. Returns `KlothoPlot` to the notebook cell.
3. Jupyter calls `_repr_html_()` → the static SVG/Plotly figure
   renders inline.
4. User calls `.play()` → the widget replaces itself with an
   animated version that synchronizes visual highlights with audio
   events through the selected playback engine.

---

## 3. Renderers

### 3.1 SVG Renderers (`_renderers/svg_*.py`)

Custom SVG generation for precise musical notation-style visuals:

| Renderer | Input types | Output |
|---|---|---|
| `svg_rt` | `RhythmTree`, `TemporalUnit`, `CompositionalUnit` | Proportional-notation timeline |
| `svg_lattice` | `Lattice`, `ToneLattice` | 2D lattice grid with ratio labels |
| `svg_cps` | `CombinationProductSet` | Polygonal CPS diagram |
| `svg_master_set` | `MasterSet` | Nested CPS subsets |

SVG renderers use shared utilities from `_shared/svg_shared.py` and
`_shared/svg_utils.py` for consistent styling, node shapes, and edge
drawing.

### 3.2 Three.js Renderers (`_renderers/threejs_*.py`)

Interactive 3D visualizations rendered via Three.js in the browser:

| Renderer | Input types | Output |
|---|---|---|
| `threejs_lattice` | `Lattice`, `ToneLattice` (3D+) | Rotating 3D lattice |
| `threejs_cps` | `CombinationProductSet` | 3D CPS polyhedron |
| `threejs_master_set` | `MasterSet` | 3D nested CPS |

Three.js renderers generate HTML/JS widgets embedded in Jupyter cells.
They use `_shared/geometry.py` for coordinate transformations and
`_shared/colors.py` for consistent coloring.

### 3.3 Renderer Selection

The dispatch layer auto-selects SVG (2D) or Three.js (3D) based on
the object's dimensionality:

```mermaid
flowchart LR
    OBJ["Lattice/CPS object"] --> DIM{"dimensionality?"}
    DIM -->|"≤ 2"| SVG["SVG renderer"]
    DIM -->|"≥ 3"| THREE["Three.js renderer"]
```

---

## 4. Animation System

**File:** `semeios/visualization/_animation/`

### AnimatedLattice3dFigure

Extends Three.js lattice visualizations with time-synchronized
animation:

```mermaid
sequenceDiagram
    participant User
    participant KlothoPlot
    participant Animation
    participant AudioEngine

    User->>KlothoPlot: .play()
    KlothoPlot->>Animation: build animation payload
    Animation->>AudioEngine: load audio events
    Animation->>Animation: start requestAnimationFrame loop
    loop Each frame
        Animation->>Animation: update visual highlights
        AudioEngine->>AudioEngine: trigger scheduled events
    end
```

### JavaScript Playback Modules

- **`_playback.js`** — Audio-visual sync for lattice path animations.
  Highlights nodes as audio events trigger.
- **`_shape_playback.js`** — Audio-visual sync for CPS/shape
  animations.  Highlights facets and vertices.

---

## 5. Layout and Positioning

### CPS Layout (`_dispatch/plot_cps.py`)

CPS nodes are positioned using geometric or dimensional-reduction
techniques:

| Method | When used |
|---|---|
| Polygon vertices | Small CPS (hexany = hexagon, dekany = decagon) |
| MDS (`sklearn.manifold.MDS`) | Larger CPS, distance-based |
| SpectralEmbedding | Alternative for high-dimensional CPS |

`_reduce_positions()` and `_cps_node_positions()` handle the
coordinate computation.

### Lattice Layout

2D lattices use direct coordinate mapping.  3D+ lattices pass
coordinates to Three.js for camera-rotatable rendering.

### RT Layout

Rhythm trees are laid out as proportional timelines — each leaf's
width is proportional to its duration, nested subdivisions are shown
as grouped brackets.

---

## 6. Shared Utilities (`_shared/`)

| Module | Contents |
|---|---|
| `colors.py` | Color scales (ratio-based hue mapping), palettes, opacity functions |
| `geometry.py` | 2D/3D coordinate transforms, polygon generation, edge midpoints |
| `svg_shared.py` | Reusable SVG building blocks (nodes, edges, labels, arrows) |
| `svg_utils.py` | SVG string assembly, viewport calculation, CSS injection |

---

## 7. Notelists

### Scheduler (`semeios/notelists/supercollider.py`)

Exports Klotho composition data as a JSON event list compatible with
SuperCollider's pattern system:

```python
from klotho.semeios.notelists.supercollider import Scheduler

sched = Scheduler(compositional_unit)
sched.to_json('output.json')
```

The `Scheduler` iterates over `Parametron` events and serializes
each event's temporal and parameter data into a dictionary structure
that can be loaded by the Klotho-SC SuperCollider extension.

---

## 8. Supported Plot Types — Full Matrix

| Input type | Renderer | Returns | Animatable |
|---|---|---|---|
| `RhythmTree` | SVG (proportional timeline) | `KlothoPlot` | Yes |
| `TemporalUnit` | SVG (proportional timeline) | `KlothoPlot` | Yes |
| `CompositionalUnit` | SVG (proportional timeline) | `KlothoPlot` | Yes |
| `Lattice` (2D) | SVG grid | `KlothoPlot` | Yes |
| `Lattice` (3D+) | Three.js | `KlothoPlot` | Yes |
| `ToneLattice` | SVG or Three.js | `KlothoPlot` | Yes |
| `ParameterField` | SVG or Three.js | `KlothoPlot` | Yes |
| `CombinationProductSet` | SVG polygon or Three.js | `KlothoPlot` | Yes |
| `MasterSet` | SVG or Three.js | `KlothoPlot` | Yes |
| `Scale` | Plotly bar chart | `None` | No |
| `Chord` / `Voicing` | Plotly | `None` | No |
| `DynamicRange` | Plotly | `None` | No |
| `Envelope` | Plotly curve | `None` | No |
| `CombinationSet` | NetworkX + Matplotlib | `None` | No |
| `PartitionSet` | NetworkX + Matplotlib | `None` | No |
| `Tree` / `Graph` | NetworkX + Matplotlib | `None` | No |
