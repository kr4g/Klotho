[![PyPI version](https://img.shields.io/pypi/v/klotho-cac.svg)](https://pypi.org/project/klotho-cac/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/klotho-cac.svg)](https://pypi.org/project/klotho-cac/)
[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

# Klotho

*Klotho*, from the Ancient Greek *κλώθω* (klṓthō), meaning "to spin." The mythological figure Clotho, one of the three Fates, takes her name from this same word.

**Klotho** is an open source computer-assisted composition toolkit implemented in Python. It is designed to work in tandem with external synthesis applications and as a resource for the methods, models, works, and frameworks associated with music composition and metacomposition.

Klotho adapts to multiple Python workflows, supporting traditional scripting, interactive notebook environments, and immediate computational tasks through the interpreter.

---

## Companion Book

An interactive Jupyter Book exploring the theory, mathematics, and CAC practice behind Klotho — foundational graph structures, formal grammars, evolutionary algorithms, quantum fields, and beyond.

Readable directly in your browser with no installation required.

**Read online:** <a href="https://kr4g.github.io/klotho-book/" target="_blank">https://kr4g.github.io/klotho-book/</a>

---

## About

Klotho extends from a lineage of computer-assisted composition (CAC) theories, practices, and software environments. It draws particular influence from the computational paradigms explored in patching-based systems such as [OpenMusic](https://openmusic-project.github.io/) and the [Bach](https://www.bachproject.net/)/[Cage](https://www.bachproject.net/cage/) ecosystem, while diverging from visual patching in favor of a scripting-first workflow.

In that sense, Klotho overlaps with the motivation behind [OpusModus](https://opusmodus.com/)—bringing “patch-like” compositional thinking into text—but takes a different path: Klotho is free and open source, and it uses Python as its authoring language. This makes it possible to work directly within Python’s broader ecosystem (e.g., [music21](https://web.mit.edu/music21/), [librosa](https://librosa.org/), [pyo](https://ajaxsoundstudio.com/software/pyo/)) and to combine computational composition with analytical and data-oriented workflows, without adopting a dedicated proprietary language for a single domain.

While Klotho supports conventional musical materials, its strengths are best realized when working with complex, abstract, or otherwise unconventional structures that are awkward to express—or difficult to iterate on—within traditional notation software or digital audio workstations.

---

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install klotho-cac
```

That's it. You're ready to go.

### Option 2: Install from Source

Clone the repository to get a local copy of the Klotho source code, then install in editable mode:

```bash
git clone https://github.com/kr4g/Klotho.git
cd Klotho/
pip install -e .
```

Editable mode (`-e`) means changes you make to the source are immediately reflected without reinstalling.

> **For contributors:** To also install testing and documentation tools, run `pip install -e .[dev]` instead.

---

## Integration with SuperCollider

To use Klotho with SuperCollider, see the `Klotho-SC` extension package: <a href="https://github.com/kr4g/Klotho-SC.git" target="_blank">https://github.com/kr4g/Klotho-SC.git</a>.

---


## Documentation

**📖 Online Documentation:** <a href="https://klotho.readthedocs.io/" target="_blank">https://klotho.readthedocs.io/</a>

The complete documentation is available online and includes:
- Complete API reference for all modules
- Usage examples and tutorials  
- NumPy-style docstring documentation

**🛠️ Build Documentation Locally (Optional):**

For developers who want to build the documentation locally or preview changes:

```bash
pip install klotho-cac[docs]
cd docs
make dev
```

---

<!-- ## Architecture

Klotho is organized into six primary modules, each addressing fundamental aspects of musical composition and computation:

### **Topos**
The foundation of musical topology in its most abstract form. Topos operates independently of specific musical parameters or numerical constraints, modeling pure structural relationships, patterns, and processes. Topos provides topological scaffolding that can be instantiated into any musical context.

### **Chronos**
Encompasses all temporal materials from microscopic rhythmic gestures to macroscopic formal architectures. Beyond local rhythm, Chronos provides frameworks for temporal formalism across time scales, handling complex and unconventional rhythmic techniques such as nested tuplets, irrational time signatures, metric modulation, poly-meter, and poly-tempi.

### **Tonos**
Handles all aspects of pitch and harmonic material including individual tones, pitch collections, scales, chords, harmonic systems and spaces, interval relationships, and frequency-based transformations. Tonos includes traditional and extended approaches to pitch organization and harmonic analysis, supporting arbitrary n-TET and n-EDO systems, extended Just Intonation frameworks, and n-dimensional microtonal lattices and scale systems.

### **Dynatos**
Dedicated to dynamics, articulations, and expressive envelopes. This module handles the conversion of symbolic dynamics (p, mf, ff, etc.) into precise dB/amplitude values, mapping of symbolic articulations to parametric envelopes, and designing custom expressive curves ranging from standard attack-decay-sustain-release models to polynomial functions for more complex shapes.

### **Thetos**
The compositional complement to Topos, Thetos handles the concrete assembly and combination of musical materials across all dimensions—temporal, tonal, dynamic, instrumental, and parametric. It manages the systematic composition and positioning of musical elements into coherent structures.

### **Semeios**
Manages all forms of musical representation including visualization, notation, plotting, animation, and multimedia output. Semeios converts computational processes into human-readable and performable representations as well as automated formats. -->

## License

<a href="https://github.com/kr4g/Klotho" target="_blank">Klotho</a> © 2023–2026 by Ryan Millett is licensed under <a href="http://creativecommons.org/licenses/by-sa/4.0/" target="_blank">CC BY-SA 4.0</a>.

![CC Icon](https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1)
![BY Icon](https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1)
![SA Icon](https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1)
