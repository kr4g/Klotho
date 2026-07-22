# Playback — Audio Rendering Pipeline

`klotho.utils.playback` converts Klotho musical objects into audible
output within Jupyter notebooks.  It supports two browser-based
synthesis engines (Tone.js and SuperSonic) plus MIDI file export.

---

## Module Map

```
utils/playback/
├── __init__.py
├── player.py                  # play() — top-level dispatcher
├── _config.py                 # set_audio_engine / get_audio_engine
├── _converter_base.py         # shared conversion logic
├── _amplitude.py              # voice amplitude computation
├── _sc_assembly.py            # CompositionalUnit → SC event assembly
├── _sc_validate.py            # SC event-list validation
├── _helpers.py                # shared helpers
├── _session_boot.py           # boot_supersonic()
├── animation_events.py        # events/payloads for animated KlothoPlot playback
├── midi_player.py             # play_midi(), create_midi()
├── tonejs/
│   ├── __init__.py
│   ├── engine.py              # ToneEngine — HTML widget
│   ├── converters.py          # convert_to_events()
│   └── cdn.py                 # CDN URLs for Tone.js, Plotly, Three.js
└── supersonic/
    ├── __init__.py
    ├── engine.py              # SuperSonicEngine — HTML widget
    ├── converters.py          # convert_to_sc_events(), convert_score_to_sc_events()
    ├── registry.py            # register_synthdef(), runtime synthdef registry
    ├── cdn.py                 # SuperSonic CDN URLs
    ├── _js_fragments.py       # JS snippets shared by widgets
    ├── _engine_widget.js      # widget shell
    ├── scheduler_core.js      # core JS scheduler
    ├── scheduler_score.js     # score-aware JS scheduler
    ├── draw.js                # widget drawing
    ├── _vendor/
    │   └── synthdef_parser/   # vendored .scsyndef parser (MIT)
    ├── scripts/
    │   └── regenerate_manifest.py  # rebuilds flat manifest.json from .scsyndef
    └── assets/
        ├── manifest.json      # flat {name: {control: default}} dict
        ├── *.scd              # SC source for the bundled synthdefs
        └── synthdefs/         # ~100 compiled .scsyndef files
```

---

## 1. Top-Level Entry Point

**File:** `utils/playback/player.py`

```python
from klotho import play

play(obj)                     # uses default engine
play(obj, engine='tone')      # force Tone.js
play(obj, engine='supersonic')  # force SuperSonic
```

### Dispatch Flow

```mermaid
flowchart TD
    P["play(obj, engine, **kwargs)"] --> SCORE{"isinstance<br/>Score?"}
    SCORE -->|Yes| S_CONV["convert_score_to_sc_events(score)"]
    S_CONV --> S_ENG["SuperSonicEngine(events,<br/>meta, control_data, ring_time)"]
    S_ENG --> DISP["engine.display()<br/>→ HTML widget"]

    SCORE -->|No| KP{"isinstance<br/>KlothoPlot?"}
    KP -->|Yes| KPLAY["obj.play(**kwargs)<br/>(animated)"]
    KP -->|No| BOOT["boot_supersonic()"]
    BOOT --> ENG{"engine?"}

    ENG -->|supersonic| SC_CONV["convert_to_sc_events(obj)"]
    SC_CONV --> SC_ENG["SuperSonicEngine(events, ring_time)"]
    SC_ENG --> DISP

    ENG -->|tone| T_CONV["convert_to_events(obj)"]
    T_CONV --> T_ENG["ToneEngine(events)"]
    T_ENG --> DISP
```

`Score` playback is always SuperSonic: the converter returns a payload
with `events`, track/FX `meta`, and control-envelope `control_data`,
and the widget accepts a `ring_time` tail (default 5 s).

### Engine Configuration

```python
from klotho import set_audio_engine, get_audio_engine

set_audio_engine('supersonic')  # default
set_audio_engine('tone')        # switch to Tone.js
```

The default engine is `'supersonic'` (browser-based scsynth).

---

## 2. Event Conversion Pipeline

Both engines share a common conversion pipeline that transforms Klotho
objects into flat event lists.

### Supported Input Types

| Type | Category |
|---|---|
| `Pitch` | Single pitch |
| `Scale` | Pitch collection |
| `Chord`, `Voicing` | Pitch collection |
| `ChordSequence` | Sequence of chords |
| `Spectrum` | HarmonicTree spectrum |
| `HarmonicTree` | Tonal system |
| `RhythmTree` | Temporal (default pitch) |
| `TemporalUnit` | Temporal (default pitch) |
| `TemporalUnitSequence` | Temporal sequence |
| `TemporalBlock` | Parallel temporal |
| `CompositionalUnit` | Full composition |
| `Score` | Multi-unit timeline (SuperSonic only) |

### Conversion Architecture

```mermaid
flowchart TD
    OBJ["Klotho Object"] --> TD{"type dispatch"}

    TD -->|"CompositionalUnit"| UCIR["lower_compositional_ir_to_sc_assembly()"]
    TD -->|"TemporalUnit/Sequence/Block"| UTIR["build events from RT timing"]
    TD -->|"Pitch/Scale/Chord"| PCIR["build events from pitches"]
    TD -->|"HarmonicTree/Spectrum"| HTIR["build events from spectrum"]

    UCIR --> VOICE["lower_poly_pfields_to_voices()"]
    UTIR --> VOICE
    PCIR --> VOICE
    HTIR --> VOICE

    VOICE --> FLAT["flat event list"]

    FLAT --> FMT{"target engine?"}
    FMT -->|Tone.js| TJ["Tone.js event format"]
    FMT -->|SuperSonic| SC["SC event format<br/>(new / set / release)"]
```

### Shared Converter Base (`_converter_base.py`)

| Function | Purpose |
|---|---|
| `_get_addressed_collection(obj)` | Extract pitch data from any collection type |
| `scale_pitch_sequence(obj, equaves=1)` | Pitch sequence spanning *n* equaves of a collection |
| `extract_convert_kwargs(kwargs)` | Parse `dur`, `arp`, `strum`, `mode` kwargs |
| `lower_poly_pfields_to_voices(pfields)` | Expand polyphonic pfields (lists of freqs) into separate voice pfield dicts |
| `lower_event_ir_to_voice_events(event)` | Flatten one intermediate event to a list of voice events |
| `iter_group_sequence(groups, dur, arp=False, strum=0, direction='u', pause=0.0)` | Iterate grouped pitch material into timed events |

### SC Assembly (`_sc_assembly.py`)

Specialized conversion for `CompositionalUnit` → SuperSonic events.
Handles:

- **Gated vs free instruments** — gated instruments use `new` + `set`
  + `release` triplets; free instruments use a single `new`.
- **Slur rendering** — slurred notes sustain across boundaries, with
  `set` messages updating pitch/amp mid-note.
- **Polyphonic voice expansion** — pfields containing lists (e.g.
  chords) are expanded into concurrent voice events.

### Amplitude Computation (`_amplitude.py`)

| Function | Purpose |
|---|---|
| `single_voice_amplitude(freq, n_voices)` | Compute amplitude for one voice in a chord |
| `compute_voice_amplitudes(freqs)` | Frequency-dependent gain balancing |

Uses `freq_amp_scale()` from dynatos for equal-loudness compensation.

---

## 3. Tone.js Engine

**File:** `utils/playback/tonejs/engine.py`

### ToneEngine

Generates an HTML/JS widget that:

1. Loads Tone.js from CDN.
2. Creates synthesizer instances for each instrument.
3. Schedules events on the Tone.js Transport.
4. Renders play/stop/loop controls.

```mermaid
flowchart LR
    subgraph "Python (server)"
        events["event list (JSON)"]
    end

    subgraph "Browser (client)"
        HTML["HTML widget"]
        TONEJS["Tone.js Transport"]
        SYNTH["Tone.Synth instances"]
        AUDIO["Web Audio API"]
    end

    events -->|"embedded in HTML"| HTML
    HTML --> TONEJS
    TONEJS --> SYNTH
    SYNTH --> AUDIO
```

### Event Format (Tone.js)

Musical parameters are nested under `pfields`, not flattened:

```json
{
  "start": 0.0,
  "duration": 0.5,
  "instrument": "Harmonics",
  "pfields": {"freq": 440.0, "amp": 0.8, "vel": 0.8}
}
```

The converter returns a payload of `{"events": [...], "instruments":
{...}}` so the widget can instantiate the right Tone.js classes.

---

## 4. SuperSonic Engine

**File:** `utils/playback/supersonic/engine.py`

### SuperSonicEngine

Generates an HTML widget that:

1. Loads SuperSonic (browser-based scsynth) from CDN.
2. Loads compiled `.scsyndef` synth definitions.
3. Schedules `new` / `set` / `release` messages on a timeline.
4. Renders play/stop controls.

```mermaid
flowchart LR
    subgraph "Python (server)"
        sc_events["SC event list (JSON)"]
        scsyndef[".scsyndef files"]
    end

    subgraph "Browser (client)"
        HTML["HTML widget"]
        SS["SuperSonic runtime"]
        SCSYNTH["scsynth (WASM)"]
        AUDIO["Web Audio API"]
    end

    sc_events -->|"embedded in HTML"| HTML
    scsyndef -->|"embedded base64 (CDN fallback)"| SS
    HTML --> SS
    SS --> SCSYNTH
    SCSYNTH --> AUDIO
```

### Event Format (SuperSonic)

Three message types, keyed by a string `id` (uid) with `start` times
and nested `pfields`:

```json
{"type": "new",     "id": "a1…", "start": 0.0,  "defName": "kl_tri", "pfields": {"freq": 440, "amp": 0.8}, "dur": 0.5, "releaseAfter": true}
{"type": "set",     "id": "a1…", "start": 0.25, "pfields": {"freq": 550}}
{"type": "release", "id": "a1…", "start": 0.5}
```

- **`new`** — allocate a synth node with initial parameters.
- **`set`** — update parameters on a running node (used for slurs,
  parameter changes, insert-FX automation).
- **`release`** — free the node explicitly (normally superseded by the
  `dur`/`releaseAfter` auto-release contract below).

### Bundled SynthDefs

**183 compiled synthdefs** ship with the package — the
`kl_*` Klotho family (`kl_tri`, `kl_sine`, `kl_kicktone`, …), a large
`fd_*` FoxDot-derived set, the MAT 111MC `edm_*`/`lofi_*`/`chip_*`
kits, the `tr808_*` drum machine voices (adapted from Yoshinosuke
Horiuchi's SC-808; all non-gated one-shots, `releaseTime` args in real
seconds, exposed via `SynthDefKit.tr808()` and `Ensemble.tr808()`),
and internal control/routing defs
(`__klEnvCtrl`, `__busRouter`, `__chainLimiter`, …).

#### Path-style names

Anywhere a SynthDef name string is accepted (`play(inst=...)`,
`SynthDefInstrument.from_manifest`, `SynthDefFX`, kit member dicts),
a path-style spelling is sugar for the underscore name: `'edm/kick'` →
`edm_kick`, `'lofi/tape'` → `lofi_tape`, `'kl/saw'` → `kl_saw`,
`'fd/blip'` → `fd_blip`.  The transform
(`klotho.thetos.instruments._shared.canonical_def_name`) is purely
syntactic — `/` cannot appear in a real def name because the def name
is the `.scsyndef` filename — so there is no alias table to maintain,
and underscore names keep working unchanged.

#### Kit selector resolution

A `Kit` event's member is chosen by its selector pfield (default
`voice`) at lowering time.  Valid selector values are **concrete**:
a member key, an integer (wrapping mod the member count), a tuple of
either (one synth voice per element), or absent (default member).
An unknown *string* raises a `KeyError` listing the kit's members —
including a hint when the string names a kit *family* (families are a
composition-time concept: draw a key with `kit.family['tas'].pick()`
or hand `kit.tas.pick` to `set_pfields(voice=...)` for per-leaf
draws; the engine itself never sees family names, so lowering stays
deterministic).

Definitions are compiled `.scsyndef` files in
`supersonic/assets/synthdefs/` (with `.scd` sources in
`supersonic/assets/`).  The `manifest.json` lists registered synthdefs
as a flat dict `{synth_name: {control_name: default_value}}`.  It is
auto-regenerated from the compiled `.scsyndef` blobs by

```bash
python -m klotho.utils.playback.supersonic.scripts.regenerate_manifest
```

(use `--dry-run` to preview). The script uses a vendored copy of
`synthdef_parser` at `supersonic/_vendor/synthdef_parser/` (no external
install).

### Runtime SynthDef Registration (`registry.py`)

New in 10.1.0: synthdefs can be registered at runtime without touching
the bundled assets, exposed at the top level as
`klotho.register_synthdef`:

```python
import klotho

klotho.register_synthdef(my_supriya_synthdef)          # from a supriya SynthDef
inst = SynthDefInstrument.from_manifest('my_synth')    # then usable like any other
```

The registry (`supersonic/registry.py`) stores compiled bytes plus
parsed controls in a session-scoped runtime store that the engine
merges with the bundled manifest:

| Function | Purpose |
|---|---|
| `register_synthdef(supriya_synthdef, name=None, pfields=None)` | Compile-and-register from a supriya `SynthDef` |
| `register_compiled(def_name, compiled_bytes, controls)` | Register pre-compiled bytes |
| `runtime_assets()` / `runtime_controls()` | Session-registered blobs / control dicts |
| `is_registered(def_name)` | Check the runtime registry |
| `clear_runtime()` | Drop all runtime registrations |

### Event-list contract: `dur` + `releaseAfter` (auto-release)

Every `new`/`set` event produced by the lowering layer carries two
top-level fields beyond the legacy `type, id, defName, start, pfields`:

- `dur: number` — the leaf's duration in seconds.
- `releaseAfter: bool` — `true` on the terminal event of each uid's
  chain (the last `set` of a slur, or any single-leaf `new`).

The lowering layer **never emits** explicit `{type:"release", id, start}`
events for normal lifecycle gate-off any more. Instead, the SuperSonic
JS scheduler introspects the manifest at fire time: when it sees
`releaseAfter:true` on a `new`/`set` and `'gate' in manifest[defName]`,
it NTP-schedules a `/n_set <node> gate 0` at `start + dur` alongside
the primary OSC bundle. For non-gated synths (no `gate` control) the
scheduler no-ops, so the lowering layer can emit the same metadata
uniformly without per-instrument branching.

`type:"release"` events are still accepted by the validator and the
schedulers as an explicit override path; only the lowering layer was
updated to stop producing them automatically.

The native SC scheduler (`EventScheduler.sc`) will gain the same
fire-time inspection path in a follow-up using
`SynthDescLib.global.at(name).controlDict.includesKey(\gate)`. Until
that lands, SC scheduling falls back to consuming any explicit
`type:"release"` events as before.

### Session Boot

`boot_supersonic()` runs at import of `player.py` and again on each
`play()` invocation (it is idempotent).  It checks whether SuperSonic
is available and pre-loads the CDN resources.  In Jupyter/Colab
environments, it injects the required `<script>` tags.

---

## 5. MIDI Export

**File:** `utils/playback/midi_player.py`

### `play_midi(obj, …)`

Converts a Klotho object to MIDI events, renders to audio (if
FluidSynth is available), and returns an `IPython.display.Audio`
widget.

### `create_midi(obj, …)`

Returns a `mido.MidiFile` for saving to disk.

### MIDI Conversion Flow

```mermaid
flowchart TD
    OBJ["Klotho Object"] --> TD{"type dispatch"}
    TD --> MIDI_CREATE["type-specific MIDI creator"]
    MIDI_CREATE --> MIDO["mido.MidiFile"]

    MIDO --> SAVE["save to .mid"]
    MIDO --> FS{"FluidSynth<br/>available?"}
    FS -->|Yes| AUDIO["render to audio<br/>→ IPython.display.Audio"]
    FS -->|No| LINK["IPython.display.FileLink<br/>(download .mid)"]
```

### MIDI Features

- **Multi-port MIDI** — up to 256 channels (16 channels × 16 ports)
  for large orchestrations.
- **Microtonal pitch bend** — sub-semitone pitches are rendered using
  per-note pitch-bend messages.
- **Drum routing** — `MidiInstrument.is_Drum` routes events to MIDI
  channel 10.
- **Program changes** — instruments with `prgm` numbers insert program
  change events.

### Supported Types for MIDI

| Type | MIDI Output |
|---|---|
| `CompositionalUnit` | Full parametric events with instruments |
| `TemporalUnit` / `TemporalUnitSequence` / `TemporalBlock` | Rhythm with default pitch |
| `RhythmTree` | Rhythm with default pitch |
| `ChordSequence` | Chords with timing |
| `Scale` | Ascending scale |
| `Chord` / `Voicing` | Simultaneous pitches |
| Pitch collection types | Arpeggiated or simultaneous |

---

## 6. Animation Events

**File:** `utils/playback/animation_events.py`

Bridges the playback system with the animation system in semeios:

| Function | Purpose |
|---|---|
| `build_path_audio_events(freqs, dur, amp=None)` | Audio events for lattice path animation |
| `build_shape_audio_events(freq_groups, dur, arp=False, strum=0, direction='u', amp=None)` | Audio events for CPS shape animation |
| `build_path_engine_payload(freqs, dur, engine, …)` | Engine-specific payload for a path animation |
| `build_shape_engine_payload(freq_groups, dur, engine, …)` | Engine-specific payload for a shape animation |
| `normalize_animation_payload_for_engine(audio_payload, engine)` | Convert animation events to engine-specific format |

These functions are called by `KlothoPlot.play()` to synchronize
audio with visual animation.

---

## 7. End-to-End Pipeline Summary

```mermaid
flowchart TD
    subgraph "Composition"
        SCR["Score"]
        UC["CompositionalUnit"]
        UT["TemporalUnit"]
        PC["Pitch Collection"]
    end

    subgraph "Conversion"
        CONV["convert_to_events()<br/>convert_to_sc_events()<br/>convert_score_to_sc_events()<br/>create_midi()"]
    end

    subgraph "Rendering"
        TONE["ToneEngine<br/>(Tone.js)"]
        SS["SuperSonicEngine<br/>(scsynth WASM)"]
        MIDI["mido.MidiFile"]
    end

    subgraph "Output"
        WIDGET["Jupyter HTML Widget<br/>(play/stop/loop)"]
        FILE[".mid file"]
        AUDIO["IPython.display.Audio"]
    end

    SCR --> CONV
    UC --> CONV
    UT --> CONV
    PC --> CONV

    CONV --> TONE
    CONV --> SS
    CONV --> MIDI

    TONE --> WIDGET
    SS --> WIDGET
    MIDI --> FILE
    MIDI --> AUDIO
```
