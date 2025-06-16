# Klotho
`Klotho` is an open source computer-assisted composition toolkit implemented in Python. It is designed to work in tandem with external synthesis applications and as a resource for the methods, models, works, and frameworks associated with music composition and multi-media metacomposition.

Klotho adapts to multiple Python workflows, supporting traditional scripting, interactive notebook environments, and immediate computational tasks through the interpreter.

---

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install klotho-cac
```

### Option 2: Install from Source

1. **Clone the Repository**:

   Clone the Klotho repository:
   
   ```
   git clone https://github.com/kr4g/Klotho.git
   ```

2. **Navigate to the `Klotho/` Directory**:
   
    ```
    cd Klotho/
    ```

3. **Install in Development Mode**:
    
    ```
    pip install -e .
    ```
    
    Or install the required dependencies separately:
    
    ```
    pip install -r requirements.txt
    ```

## About

Klotho extends from a lineage of computer-assisted composition (CAC) theories, practices, and software environments. While it provides support for conventional musical materials, its strengths are best utilized when working with complex, abstract, and unconventional musical structures not easily accessible with traditional notation software or digital audio workstations.

While drawing from the computational paradigms found in patching-based environments like [OpenMusic](https://openmusic-project.github.io/), [Bach](https://www.bachproject.net/), and [Cage](https://www.bachproject.net/cage/), Klotho diverges from the visual patching paradigm in favor of a high-level, text-based scripting syntax. As such, Klotho is closer in spirit to [OpusModus](https://opusmodus.com/), which also favors text-based scripting over visual patching, though its LISP-based proprietary language creates unnecessary barriers to entry and forecloses access to Python's diverse ecosystem—libraries like Librosa, Music21, and Pyo, as well as scientific tools that enable more analytical and data-oriented approaches to music generation. While such libraries operate outside Klotho's scope, they interface with it naturally—allowing Klotho to embody the underlying mathematical expressions governing musical materials from topological, algebraic, and computational perspectives.

## Architecture

Klotho is organized into six primary modules, each addressing fundamental aspects of musical composition and computation:

### **Topos** (*τόπος*) - "place, location"
The foundation of musical topology in its most abstract form. Topos operates independently of specific musical parameters or numerical constraints, modeling pure structural relationships, patterns, and processes. This module provides topological scaffolding that can be instantiated into any musical context.

### **Chronos** (*χρόνος*) - "time"
Encompasses all temporal materials from microscopic rhythmic gestures to macroscopic formal architectures. Beyond local rhythm, Chronos provides frameworks for temporal formalism across time scales, handling complex and unconventional rhythmic techniques such as nested tuplets, irrational time signatures, metric modulation, poly-meter, and poly-tempi.

### **Tonos** (*τόνος*) - "tone, tension"
Handles all aspects of pitch and harmonic material including individual tones, pitch collections, scales, chords, harmonic systems and spaces, interval relationships, and frequency-based transformations. Tonos includes traditional and extended approaches to pitch organization and harmonic analysis, supporting arbitrary n-TET and n-EDO systems, extended Just Intonation frameworks, and n-dimensional microtonal lattices and scale systems.

### **Dynatos** (*δυνατός*) - "powerful, capable"
Dedicated to dynamics, articulations, and expressive envelopes. This module handles the conversion of symbolic dynamics (p, mf, ff, etc.) into precise dB/amplitude values, mapping of symbolic articulations to parametric envelopes, and designing custom expressive curves and envelopes ranging from standard ADSR models to polynomial functions for more complex shapes.

### **Thetos** (*θετός*) - "placed, positioned"
The compositional complement to Topos, Thetos handles the concrete assembly and combination of musical materials across all dimensions—temporal, tonal, dynamic, instrumental, and parametric. It manages the systematic composition and positioning of musical elements into coherent structures.

### **Semeios** (*σημεῖον*) - "sign, mark"
Manages all forms of musical representation including visualization, notation, plotting, animation, and multimedia output. Semeios converts computational processes into human-readable and performable representations as well as automated formats.

## License

[Klotho](https://github.com/kr4g/Klotho) by Ryan Millett is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/?ref=chooser-v1).

![CC Icon](https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1)
![BY Icon](https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1)
![SA Icon](https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1)

Klotho © 2023 by Ryan Millett is licensed under CC BY-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/
