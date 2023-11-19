# AlloPy
`AlloPy` is an open source Python package designed to work as both a stand-alone software and in tandem with `AlloLib Playground` as a computer-assisted composition toolkit, work environment, notation editor, and general educational resource for the methods, models, works, and frameworks associated with the art and craft of *extemporal* multimedia metacomposition.

Developed and maintained by MAT graduate student [Ryan Millett](https://www.mat.ucsb.edu/students/#rmillett) as part of the AlloSphere Research Group, under the supervision of Dr. Kuchera-Morin, at the University of California, Santa Barbara.

[The AlloSphere Research Group](https://github.com/AlloSphere-Research-Group)

Download AlloLib Playground here: https://github.com/AlloSphere-Research-Group/allolib_playground

---

## Installation

AlloPy works as both a Python scripting toolkit and 'on-the-fly' via a Python interpreter.

If you want to use AlloPy with AlloLib Playground, first install AlloLib Playground [here](https://github.com/AlloSphere-Research-Group/allolib_playground).

1. **Clone the Repository**:

   First, clone the AlloPy repository (into the `allolib_playground/` directory of your system if you want to work with AlloLib/Gamma) by running the following command in your terminal or command prompt:
   
   ```
   git clone https://github.com/kr4g/AlloPy.git
   ```

2. **Navigate to the `AlloPy/` Directory**:
   
    ```
    cd AlloPy/
    ```

3. **Install Dependencies**:

    Install the required dependencies by running:
    
    ```
    pip install -r requirements.txt
    ```

4. **Play**:

    To work with AlloPy in a scripting context, create a directory within the `AlloPy/` directory and save your scripts there.  [`AlloPy/examples/`](https://github.com/kr4g/AlloPy/tree/main/examples) contains examples of how to use the modules in this manner.

    To use AlloPy as an 'on-the-fly' compositional-aid, initiate a Python interpreter from within the `AlloPy/` directory by running the command:

    ```
    Python
    ```

    Once the interpreter loads, import from `allopy` as needed.
    
    For example:

    ```
    >>> from allopy import tonos
    >>> tonos.midicents_to_freq(6900)
    440.0
    >>> tonos.freq_to_pitchclass(440.0)
    'A4'
    >>> freq = tonos.pitchclass_to_freq('A4', cent_offset = -32)
    >>> freq
    431.941776308572
    >>> hexany = tonos.scales.hexany([1,3,5,7], 2)
    >>> hexany
    ([3, 5, 7, 15, 21, 35], [1.09375, 1.25, 1.3125, 1.5, 1.75, 1.875])
    >>> [freq * ratio for ratio in hexany.ratios]
    [472.4363178375006, 539.927220385715, 566.9235814050007, 647.912664462858, 755.898108540001, 809.8908305785725]
    ```

    AlloPy supports [Rhythm Trees](https://support.ircam.fr/docs/om/om6-manual/co/RT1.html), as implemented in the [OpenMusic](https://openmusic-project.github.io/) composition software.
    ```
    >>> from allopy.chronos import rhythm_trees as rt
    >>> r_tree = rt.RT(('?', ((4, 4), ((1, (2, (1, 1, 1)), (1, (1, (1, (2, 1, 2)), 1)))) )))
    >>> m_ratios = rt.measure_ratios(r_tree)
    >>> [str(ratio) for ratio in m_ratios]
    ['1/4', '1/6', '1/6', '1/6', '1/12', '1/30', '1/60', '1/30', '1/12']
    >>> from allopy.chronos import beat_duration
    >>> durations = [beat_duration(metric_ratio=ratio, bpm=66) for ratio in m_ratios]
    >>> [round(dur, 3) for dur in durations]
    [0.909, 0.606, 0.606, 0.606, 0.303, 0.121, 0.061, 0.121, 0.303]
    ```

    Abstract tools for metacomposition:
    ```
    >>> from allopy import topos
    >>> color, talea = ('Θ', 'Ξ'), ('∝', '∴', '∫')
    >>> iso = topos.iso_pairs(color, talea)
    >>> iso
    (('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'))
    >>> kleis = ('∆','Σ','Ψ','∐','Ω','ζ')
    >>> h_map = topos.homotopic_map(kleis, iso)
    >>> for e in h_map: print(e)
    ... 
    ('∆', (('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫')))
    ('Σ', (('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝')))
    ('Ψ', (('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴')))
    ('∐', (('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫')))
    ('Ω', (('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝')))
    ('ζ', (('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴')))
    >>> 
    ```

    Formal Grammars:
    ```
    >>> from allopy.topos.formal_grammars import alphabets, grammars
    >>> S1 = alphabets.RUNIC.OLD_NORSE.Elder_Futhark
    >>> S2 = alphabets.AncientGreek
    >>> import numpy as np
    >>> alpha = np.array([s.value for s in S1] + [s.value for s in S2])
    >>> np.random.shuffle(alpha)
    >>> alpha = alpha[:13]
    >>> random_rules = grammars.rand_rules(alpha, word_length_max=5)
    >>> for axiom, sub in random_rules.items(): print(f'{axiom} : {sub}')
    ... 
    ᚠ : ᚷᚠᛃᚷκ
    ᛗ : ε
    Ζ : ε
    θ : ᛃᚷ
    Ω : Υ
    π : σθσ
    Υ : Ω
    ᚷ : εν
    σ : Υε
    κ : σᛃπᚠ
    ν : ᛃ
    ᛃ : κᛃνᚷ
    ε : κκ
    >>> S3 = alphabets.Mathematical
    >>> constraints = {a: np.random.choice([s.value for s in S3]) for a in alpha[:len(alpha)//8]}
    >>> random_rules = grammars.constrain_rules(random_rules, constraints)
    >>> for axiom, sub in random_rules.items(): print(f'{axiom} : {sub}')
    ... 
    ᚠ : ᚷᚠᛃᚷ∋
    ᛗ : ∯
    Ζ : ∲
    θ : √ᚷ
    Ω : ∖
    π : σθ∝
    Υ : ∏
    ᚷ : ε∜
    σ : Υ∉
    κ : σᛃπᚠ
    ν : ᛃ
    ᛃ : κᛃνᚷ
    ε : κκ
    >>> random_rules = {k: v + ' ' for k, v in random_rules.items()}
    >>> gens = 11
    >>> l_str_gens = grammars.gen_str(generations=gens, axiom=np.random.choice(alpha), rules=random_rules)
    >>> l_str_gens[4]
    '∏ σᛃπᚠ κᛃνᚷ ᛃ ε∜ Υ∉ √ᚷ ε∜ ᚷᚠᛃᚷ∋ κᛃνᚷ ε∜ Υ∉ κᛃνᚷ σθ∝ ᚷᚠᛃᚷ∋ σᛃπᚠ κᛃνᚷ ᛃ ε∜ κᛃνᚷ κκ σᛃπᚠ κᛃνᚷ ᛃ ε∜ σᛃπᚠ σᛃπᚠ '
    >>> l_str_gens[5]
    'Υ∉ κᛃνᚷ σθ∝ ᚷᚠᛃᚷ∋ σᛃπᚠ κᛃνᚷ ᛃ ε∜ κᛃνᚷ κκ ∏ ε∜ κκ ε∜ ᚷᚠᛃᚷ∋ κᛃνᚷ ε∜ σᛃπᚠ κᛃνᚷ ᛃ ε∜ κκ ∏ σᛃπᚠ κᛃνᚷ ᛃ ε∜ Υ∉ √ᚷ ε∜ ᚷᚠᛃᚷ∋ κᛃνᚷ ε∜ Υ∉ κᛃνᚷ σθ∝ ᚷᚠᛃᚷ∋ σᛃπᚠ κᛃνᚷ ᛃ ε∜ κᛃνᚷ κκ σᛃπᚠ κᛃνᚷ ᛃ ε∜ σᛃπᚠ σᛃπᚠ Υ∉ κᛃνᚷ σθ∝ ᚷᚠᛃᚷ∋ σᛃπᚠ κᛃνᚷ ᛃ ε∜ κᛃνᚷ κκ Υ∉ κᛃνᚷ σθ∝ ᚷᚠᛃᚷ∋ Υ∉ κᛃνᚷ σθ∝ ᚷᚠᛃᚷ∋ '
    ```

    Or, import the entire package:
    ```
    >>> import allopy as al
    >>> al.aikous.Dynamics.mf
    0.2512
    >>> al.chronos.beat_duration(metric_ratio=1/4, bpm=120)
    0.5
    >>> score_df = al.skora.make_score_df(pfields=('start', 'dur', 'synthName', 'amplitude', 'frequency'))
    >>> duration = al.chronos.beat_duration(1/9, 76)
    >>> min_amp, max_amp = al.aikous.Dynamics.mp, al.aikous.Dynamics.ff
    >>> frequency = al.tonos.pitchclass_to_freq('D3', cent_offset = -16) 
    >>> ratio = al.tonos.cents_to_ratio(386)
    >>> repeats = 9
    >>> rows = [{
            'start'      : i * duration,
            'dur'        : duration,
            'synthName'  : 'mySynth',
            'amplitude'  : np.interp(i, [0, repeats], [min_amp, max_amp]),
            'frequency'  : frequency * ratio**i,
        } for i in range(repeats)]
    >>> score_df = skora.concat_rows(score_df, rows)
    >>> skora.df_to_synthSeq(score_df, 'path/to/score/dir/my_score.synthSequence')
    ```

    In the world of AlloPy, it is always possible to ask the five dæmons for help. Simply call the Python `help()` function on any class, function, or module in AlloPy:
    ```
    >>> import allopy as al
    >>> help(al.chronos)
    Help on package allopy.chronos in allopy:

    NAME
        allopy.chronos - --------------------------------------------------------------------------------------

    DESCRIPTION
        `Chronos` is a specialized module for working with time and rhythm in music.
        
        The word "chronos" originates from Ancient Greek and is deeply rooted in both language 
        and mythology. In Greek, "χρόνος" (chronos) means "time".
        
        In Greek mythology, Chronos (not to be confused with Cronus, the Titan) is personified as 
        the god of time. His representation often symbolizes the endless passage of time and the 
        cycles of creation and destruction within the universe.
        
        --------------------------------------------------------------------------------------

    PACKAGE CONTENTS
        chronos
        rhythm_trees
        temporal_units
    ```
    Press `q` in the terminal window to leave the help screen and return to the interpreter.

    ### Integration with AlloLib Playground

    Even in this 'on-the-fly', interpreter-based paradigm, AlloPy is designed to integrate directly with the AlloLib Playground in any IDE of choice.  
    
    This means that, for example, note lists can be generated, edited, and merged freely with changes appearing in realtime from within your running AlloLib app—*no need to close and re-run the application when making changes to your scores.*  
    
    See VS Code integration section for more details.

---

## Introduction to the World of AlloPy

The `AlloPy` Python package is composed of five modules ruled by the five dæmons of music composition and synthesis:  *Chronos, Tonos, Topos, Aikous,* and *Skora*.

Each of the five modules contains a base module named after itself as well as various other submodules that specialize in some aspect of their general domain (e.g., `Tonos` contains a base module `tonos.py` with basic pitch/frequency tools as well as other specialized submodules, such as `scales.py`).

#### AlloPy Creation Myth:  The Five Dæmons

First, there was only **Chronos**.  Consequently and soon thereafter, was **Tonos**.  The pair called upon **Skora**, who then summoned **Aikous**, to translate their language of time and tones into the *lingua franca* of The Machines.  

From this quaternal union there was a faint yet shoring transmission emitting at the subatomic bit-level, eventually radiating into the Beyond and so conjured **The Topos**, an immaterial entity from the macrocosmic realm of algebraic categorical abstraction. 

Thus the cycle was complete.

`Chronos` and `Tonos`, who speak in the language of music, with the help of `Aikous` and `Skora`, commune with The Machines in the language of synthesis.  From atop the highest, most abstract peak in the [topology of music](https://link.springer.com/book/10.1007/978-3-0348-8141-8), resides The `Topos`, imbuing the land of AlloPy with metacompositional abstraction, unifying all levels of the computational cosmos.

And so then there was a resiliant harmony, resonating from the subatomic to the macrocosmic, from which emerged the world of `AlloPy`, and it was good.

#### AlloPy Package Structure:  The Five Modules

Lo there, friend.  *Friður sé með þér!*  

Welcome to the world of `AlloPy`.

Whether you know the path in which you seek or if you are but a curious wanderer, the five spirits of AlloPy will guide you in your journey.

Know their names, know their powers.  Discover how, from their internal harmony, you can marshal the forces of computation and learn the ways of *extemporal* multimedia metacomposition.

### `Chronos` 

***Lord of Time:***  *knower of all things temporal*

(description)

### `Tonos` 

***Teacher of Tones:***  *zygós of pitch and frequency*

(description)

### `Topos`

***Master of Music Mysterium:***  *mentor in musimathics*

The `Topos` is the most abstract and, thus, most mysterious of the `AlloPy` modules and is the only one that does not work with music or sound synthesis materials directly—that is, if you so desire.  Instead, The `Topos` deals with the abstract topology, the [`Topos`](https://link.springer.com/book/10.1007/978-3-0348-8141-8) of Music.

The `topos.py` base module contains a multitude of abstract "puzzle" functions deeply inspired by Category Theory, Topology, and abstract algebra in general.  These functions are data-type agnostic and work entirely in a functional, LISP-like paradigm inspired by the [OpenMusic](https://openmusic-project.github.io/) software implemented in Common LISP.

Every `topos.py` function is inherently recursive and all work with the same input and output type—the tuple.  This means that outputs can feedback into inputs and/or pipe into the inputs of other functions, etc., allowing for the construction of highly complex abstract structures from the interweaving of very simple base operations.

The `Topos` module, like the other `AlloPy` modules, also contains specialized submodules such as formal grammars, including basic rewrite rule generation and a library of ancient [graphemes](https://en.wikipedia.org/wiki/Grapheme)—useful when working with categorical, algebraic abstractions.

Consult The Topos for wisdom and you will receive it, but know that The Topos speaks and answers only in riddle.  Though, in solving the riddle, will you ultimately attain the answer to your question.

### `Aikous` 

***Goddess of Perception and Practicality:*** *the threader of musical algebra and synthesis reality*

(description)

### `Skora` 

***The Scribe:***  *keeper of scores, numen of notation*

(description)

---

## Education

### **Into the AlloVerse:**  *an Audiovisual Synthesis and Metacomposition tutorial series for working with AlloLib Playground and AlloPy*

The `AlloLib Playground` is an application development space for working with the classes and functions of the `AlloLib` and `Gamma` C++ libraries.  The Playground thus sits "close to the metal" and allows users to work directly at the sample-level of audio synthesis and at the framerate of graphics rendering.

`AlloPy`, implemented in Python, exists "above the metal" and serves as an abstract toolkit for working with low-level distributed systems such as AlloLib.

When used in concert, AlloLib Playground and AlloPy bridge the subatomic, bit-level world of sound synthesis and graphical computation with the macrocosmic, "outside of time" realm of music composition and poly-sensory metacomposition.  Together, they form a unified *AlloVerse* where students, artists, composers, and researchers can move freely between all levels of a distributed, multimedia composition system.

*Coming soon...*

---

## License

[AlloPy](https://github.com/kr4g/AlloPy) by Ryan Millett is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/?ref=chooser-v1).

![CC Icon](https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1)
![BY Icon](https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1)
![SA Icon](https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1)

AlloPy © 2023 by Ryan Millett is licensed under CC BY-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

---
