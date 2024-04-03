# AlloPy
`AlloPy` is an open source Python package designed to work as both a stand-alone software and in tandem with external synthesis applications as a computer-assisted composition toolkit, work environment, notation editor, and general educational resource for the methods, models, works, and frameworks associated with the art and craft of multimedia composition and metacomposition.

Developed and maintained by MAT graduate student [Ryan Millett](https://www.mat.ucsb.edu/students/#rmillett) as part of the AlloSphere Research Group, under the supervision of Dr. Kuchera-Morin, at the University of California, Santa Barbara.

[The AlloSphere Research Group](https://github.com/AlloSphere-Research-Group)

AlloPy [integrates](https://github.com/kr4g/AlloPy/tree/main#integration-with-allolib-playground) with AlloLib Playground, a C++ application development space for working with `AlloLib` and `Gamma`, audiovisual and sound synthesis libraries developed by The AlloSphere Research Group.

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

    To work with AlloPy as an 'on-the-fly' compositional-aid, initiate a Python interpreter from within the `AlloPy/` directory by running the command:

    ```
    Python
    ```

    Once the interpreter loads, import from `allopy` as needed.

## Feature Overview

AlloPy extends from a lineage of CAC-oriented theories and softwares.  This means that, while AlloPy provides many classes and functions for 'standard' music materials, its strengths are best utilized when working with more complex, abstract, or otherwise unconventional materials not easily accessible with standard notation softwares.  

The ethos of AlloPy draws heavily from the concepts and computations possible with patching-based softwares like [OpenMusic](https://openmusic-project.github.io/) (which also influenced [Bach](https://www.bachproject.net/) and [Cage](https://www.bachproject.net/cage/) for Max).

AlloPy seeks to avoid this patching paradigm in favor of a high-level scripting syntax that more closely resembles the underlying mathematical expressions at play when working with computational composition tools.  Many of AlloPy's core features, particularly in the implementation of Rhythm Trees, adhere to a "LISP-like" presentation and programming paradigm inspired by the underlying Common LISP source code for OpenMusic.  It is then also closer to the abstract, algebraic language of music in its symbolic representations.

Examples from each AlloPy module, here used in an 'on-the-fly' context via the Python interpreter:

### Rhythm Trees

### Microtonality

### Abstract tools for metacomposition:

### Formal Grammars:

---   

### `Chronos` 

***Lord of Time:***  *knower of all things temporal*

Cognitor of the clock, `Chronos` contains calculations and computations for both [conceptual (i.e., *chronometric*) and perceptual (i.e., *psychological*) time](https://www.scribd.com/document/45643859/Grisey-Tempus-ex-machina).

The `chronos.py` base module contains basic calculation tools for converting between musical time units and chronometric units (e.g., beat durations in seconds) as well as other time-based utilities.  The submodules contain materials oriented around more abstract representations and interpretations of musical time deeply inspired by the [ancient practices](https://en.wikipedia.org/wiki/Canon_(music)) of temporal counterpoint through, and beyond, the [*New Complexity*](https://en.wikipedia.org/wiki/New_Complexity).

For example, Chronos fully supports the use of [Rhythm Trees](https://support.ircam.fr/docs/om/om6-manual/co/RT1.html) (`rhythm_trees.py`) as featured in the [OpenMusic](https://openmusic-project.github.io/) computer-assisted composition software as well as modules for working with [*L’Unité Temporelle*](https://hal.science/hal-03961183/document) (`temporal_units.py`), an algebraic formalization of temporal proportion and a generalization of rhythm trees, posited by Karim Haddad.

### `Tonos` 

***Teacher of Tones:***  *zygós of pitch and frequency*

Though structured as discrete modules, Chronos and `Tonos` are deeply entwined (as the sensation of tone is, at its foundation, an artifact of time) and so their respective abstractions are designed to flow fluidly between one another.  For instance, the fractional decomposition used to calculate the temporal ratios partitioning blocks of time, as in the case of Rhythm Trees, could also be thought of as a means of dividing a stretch of pitch-space—and *vise versa*.

As with his chronometric companion, the `tonos.py` base module consists of a toolkit for general pitch- and frequency-based calculations and conversions.  Specialized modules emphasize more conceptual tone-based abstractions such as [*Hexany*](https://en.wikipedia.org/wiki/Hexany) as well as other [n-EDO](https://en.xen.wiki/w/EDO) and [Just](https://en.xen.wiki/w/Just_intonation) microtonal paradigms.

Tonos also supports the use of `Scala` (.scl) tuning files as implemented in the [Scala](https://www.huygens-fokker.org/scala/) microtonality software.  Any scale from the [Scala archive](https://www.huygens-fokker.org/scala/downloads.html) (consisting of more than **5,200** unique scales) can be imported into AlloPy as well as support for generating and saving your own, custom .scl scale and tuning files.

### `Topos`

***Master of Music Mysterium:***  *mentor in musimathics*

The `Topos` is the most abstract and, thus, most mysterious of the AlloPy modules and is the only one that does not work with music or sound synthesis materials directly—that is, if you so desire.  Instead, The Topos deals with the abstract topology, the [`Topos`](https://link.springer.com/book/10.1007/978-3-0348-8141-8) of Music.

The `topos.py` base module contains a multitude of abstract "puzzle" functions deeply inspired by Category Theory, Topology, and abstract algebra in general.  These functions are data-type agnostic and work entirely in a functional, LISP-like paradigm inspired by the [OpenMusic](https://openmusic-project.github.io/) software, implemented in Common LISP.

Every `topos.py` function is inherently recursive and all work with the same input and output type—the tuple.  This means that outputs can feedback into inputs and/or pipe into the inputs of other functions, etc., allowing for the construction of highly complex abstract structures from the interweaving of very simple base operations.

The Topos module, like the other AlloPy modules, also contains specialized submodules such as formal grammars, including basic rewrite rule generation and a library of ancient [graphemes](https://en.wikipedia.org/wiki/Grapheme)—useful when working with categorical, algebraic abstractions.

Consult The Topos for guidance and you will receive it, but know that The Topos speaks and answers only in riddle.  Though, in solving the riddle, will you ultimately attain the answer to your question.

### `Aikous` 

***Goddess of Perception and Practicality:*** *the threader of musical algebra and synthesis reality*

`Aikous` interlaces the higher-order symbolic representations of musical expression with the working reality of sound synthesis.  While The Topos arbitrates over the algebra, Aikous conceives the calculus.

Aikous contains basic tools for converting between *conceptual* units (e.g., musical dynamics such as `mp` and `fff`) and *concrete* synthesis units (e.g., amplitude and deicibel values) as well as functions for creating smooth curves and interpolations between discrete musical elements.  Aikous is then best suited for the score-writing aspect of the compositional process, as she performs the computations necessary to weave a sense of continuous expression across the succession of discrete events.

### `Skora` 

***The Scribe:***  *keeper of scores, numen of notation*

Silent and often sullen, `Skora` the scribe sombers in sanctuary situated just above the substratum of synthesis.

The `Gamma` synth instruments in `AlloLib` use a [standard numeric](https://www.csounds.com/manual/html/ScoreTop.html) notation [system](https://flossmanual.csound.com/miscellanea/methods-of-writing-csound-scores) similar to [`Csound`](https://csound.com/).  These "note lists" consist of discrete commands organized by *pfields*.  Skora converts this tabular format into a data structure known as a [`DataFrame`](https://pandas.pydata.org/).  When abstracted into this format, AlloLib score files can be exposed to the higher-order computations available in the "data science" paradigm.

(*A short tutorial note list basics, including pfields, can be found [here]()*)

Skora then also leverages the power of `Numpy` to perform complex computations on any slice of the *Score DataFrame*.  This allows for a more fluid approach to editing and, most interesting, *generating*  note lists dynamically.  AlloPy can then function as both a computational composition aid or a data sonification tool—and everything in between.

The Skora module also provides tools for managing and merging multiple separate parts, making larger-scale arrangements easier to maintain.

Integration with [`abjad`](https://abjad.github.io/) and [`LilyPond`](https://lilypond.org/development.html) are presently in development.

---

## Integration with AlloLib Playground

AlloPy is designed to integrate directly with the AlloLib Playground in any IDE of choice.  This means that, for example, note lists can be generated, edited, and merged freely with changes appearing in realtime from within your running AlloLib app—*no need to close and re-run the application when making changes to your scores.*

---   

## License

[AlloPy](https://github.com/kr4g/AlloPy) by Ryan Millett is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/?ref=chooser-v1).

![CC Icon](https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1)
![BY Icon](https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1)
![SA Icon](https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1)

AlloPy © 2023 by Ryan Millett is licensed under CC BY-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

---
