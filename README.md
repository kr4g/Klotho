# AlloPy
`AlloPy` is an open source Python package designed to work as both a stand-alone software and in tandem with other synthesis applications as a computer-assisted composition toolkit, work environment, notation editor, and general educational resource for the methods, models, works, and frameworks associated with the art and craft of *extemporal* multimedia metacomposition.

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

## Introduction to the World of AlloPy

Lo there, friend.  *Friður sé með þér!*  

Welcome to the world of `AlloPy`.

Whether you know the path in which you seek or if you are but a curious wanderer, the five spirits of AlloPy will guide you in your journey.

Know their names, know their powers.  Discover how, from their internal harmony, you can marshal the forces of computation and learn the ways of *extemporal* multimedia metacomposition.

#### The Five Modules

The `AlloPy` Python package is composed of five modules ruled by the five dæmons of music composition and synthesis:  *Chronos, Tonos, Topos, Aikous,* and *Skora*.

Each of the five modules contains a base module named after itself as well as various other submodules that specialize in some aspect of their general domain.

### `Chronos` 

***Lord of Time:***  *knower of all things temporal*

First, there was only `Chronos`.  Cognitor of the clock, `Chronos` contains calculations and computations for both [conceptual (i.e., *chronometric*) and perceptual (i.e., *psychological*) time](https://www.scribd.com/document/45643859/Grisey-Tempus-ex-machina).

(examples)

The `chronos.py` base module contains basic calculation tools for converting between musical time units and chronometric units (e.g., beat durations in seconds) as well as other time-based utilities.  The submodules contain materials oriented around more abstract representations and interpretations of musical time deeply inspired by the [ancient practices](https://en.wikipedia.org/wiki/Canon_(music)) of temporal counterpoint through, and beyond, the [*New Complexity*](https://en.wikipedia.org/wiki/New_Complexity).

(examples)

For example, `Chronos` fully supports the use of [Rhythm Trees](https://support.ircam.fr/docs/om/om6-manual/co/RT1.html) (`rhythm_trees.py`) as featured in the [OpenMusic](https://openmusic-project.github.io/) computer-assisted composition software as well as modules for working with [*L’Unité Temporelle*](https://hal.science/hal-03961183/document) (`temporal_units.py`), an algebraic formalization of temporal proportion and a generalization of rhythm trees, posited by Karim Haddad.

(examples)

### `Tonos` 

***Teacher of Tones:***  *zygós of pitch and frequency*

Consequently and soon thereafter, was `Tonos`.  Though structured as discrete modules, `Chronos` and `Tonos` are deeply entwined (as the sensation of tone is, at its foundation, an artifact of time) and so their respective abstractions are designed to flow fluidly between one another.  For instance, the fractional decomposition used to calculate the temporal ratios partitioning blocks of time, as in the case of Rhythm Trees, could also be thought of as a means of dividing a stretch of pitch-space—and *vise versa*.  

(examples)

As with his chronometric companion, the `tonos.py` base module consists of a toolkit for general pitch- and frequency-based calculations and conversions.  Specialized modules emphasize more conceptual tone-based abstractions such as [*Hexany*](https://en.wikipedia.org/wiki/Hexany) as well as other [n-EDO](https://en.xen.wiki/w/EDO) and [Just](https://en.xen.wiki/w/Just_intonation) microtonal paradigms.

(examples)

`Tonos` also supports the use of `Scala` (.scl) tuning files as implemented in the [Scala](https://www.huygens-fokker.org/scala/) microtonality software.  Any scale from the [Scala archive](https://www.huygens-fokker.org/scala/downloads.html) (consisting of more than **5,200** unique scales) can be imported into `AlloPy` as well as support for generating and saving your own, custom .scl scale and tuning files.

(examples)

### `Topos`

***Master of Music Mysterium:***  *mentor in musimathics*

The `Topos` is the most abstract and, thus, most mysterious of the `AlloPy` modules and is the only one that does not work with music or sound synthesis materials directly—that is, if you so desire.  Instead, The `Topos` deals with the abstract topology, the [`Topos`](https://link.springer.com/book/10.1007/978-3-0348-8141-8) of Music.

The `topos.py` base module contains a multitude of abstract "puzzle" functions deeply inspired by Category Theory, Topology, and abstract algebra in general.  These functions are data-type agnostic and work entirely in a functional, LISP-like paradigm inspired by the [OpenMusic](https://openmusic-project.github.io/) software, implemented in Common LISP.

(examples)

Every `topos.py` function is inherently recursive and all work with the same input and output type—the tuple.  This means that outputs can feedback into inputs and/or pipe into the inputs of other functions, etc., allowing for the construction of highly complex abstract structures from the interweaving of very simple base operations.

(examples)

The `Topos` module, like the other `AlloPy` modules, also contains specialized submodules such as formal grammars, including basic rewrite rule generation and a library of ancient [graphemes](https://en.wikipedia.org/wiki/Grapheme)—useful when working with categorical, algebraic abstractions.

(examples)

Consult The Topos for guidance and you will receive it, but know that The Topos speaks and answers only in riddle.  Though, in solving the riddle, will you ultimately attain the answer to your question.

### `Aikous` 

***Goddess of Perception and Practicality:*** *the threader of musical algebra and synthesis reality*

Throughout the synapses of this hyper-network of conceptual abstraction, flows the mana of `Aikous`, who interlaces the higher-order symbolic representations of musical expression with the working reality of sound synthesis.  While The `Topos` arbitrates over the algebra, `Aikous` conceives the calculus.

`Aikous` contains basic tools for converting between *conceptual* units (e.g., musical dynamics such as `mp` and `fff`) and *concrete* synthesis units (e.g., amplitude and deicibel values) as well as functions for creating smooth curves and interpolations between discrete musical elements—e.g., *crescendi* and *diminuendi*.  `Aikous` is then best suited for the score-writing aspect of the compositional process, as she performs the computations necessary to weave a sense of continuous expression across the succession of discrete events.

(examples)

### `Skora` 

***The Scribe:***  *keeper of scores, numen of notation*

Silent and often sullen, `Skora` the scribe sombers in sanctuary situated just above the substratum of synthesis.  That is to say, `Skora` is keeper of record for all musical events as they must be known and as they must be tublated for The Machines.

The `Gamma` synth instruments in `AlloLib` use a [standard numeric](https://www.csounds.com/manual/html/ScoreTop.html) notation [system](https://flossmanual.csound.com/miscellanea/methods-of-writing-csound-scores) similar to [`Csound`](https://csound.com/).  These "note lists" consist of discrete commands organized by *pfields*.  `Skora` converts this tabular format into a data structure known as a [`DataFrame`](https://pandas.pydata.org/).  When abstracted into this format, AlloLib score files can be exposed to the higher-order computations available in the "data science" paradigm.

(*A short tutorial note list basics, including pfields, can be found [here]()*)

(examples)

`Skora` then also leverages the power of `Numpy` to perform complex computations on any slice of the *Score DataFrame*.  This allows for a more fluid approach to editing and, most interesting, *generating*  note lists dynamically.  `AlloPy` can then function as both a computational composition aid or a data sonification tool—and everything in between.

The `Skora` module also provides tools for managing and merging multiple separate parts, making larger-scale arrangements easier to maintain.

(examples)

Integration with [`abjad`](https://abjad.github.io/) and [`LilyPond`](https://lilypond.org/development.html) are presently in development.

(examples)

---

## Feature Overview

`AlloPy` extends from a lineage of CAC-oriented theories and softwares.  This means that, while AlloPy provides many classes and functions for 'standard' music materials, its strengths are best utilized when working with more 'advanced' materials not easily acheivable in conventional notation softwares.

Basic examples from each AlloPy module, here used in an 'on-the-fly' context via the Python interpreter:

### Rhythm Trees

AlloPy supports [Rhythm Trees](https://support.ircam.fr/docs/om/om6-manual/co/RT1.html), as implemented in the [OpenMusic](https://openmusic-project.github.io/) composition software.
```
>>> from allopy.chronos import rhythm_trees as rt
>>> # tree-graph representation using LISP-like syntax
>>> subdivisions = (1,1,1,1,1) # initial tree proportions (no branches yet)
>>> r_tree = rt.RT(('?', ((4, 4), subdivisions)))
>>> m_ratios = rt.measure_ratios(r_tree) # evaluates to a list of metric proportions dividing an abstract unit of time
>>> [str(ratio) for ratio in m_ratios]
['1/5', '1/5', '1/5', '1/5', '1/5']
>>>
>>> sum(m_ratios) # the tree will always sum to 1
Fraction(1, 1)
>>> # add "branches"
>>> subdivisions = (1,1,(1,(1,1,1)),1,1)
>>> r_tree = rt.RT(('?', ((4, 4), subdivisions)))
>>> m_ratios = rt.measure_ratios(r_tree)
>>> [str(ratio) for ratio in m_ratios]
['1/5', '1/5', '1/15', '1/15', '1/15', '1/5', '1/5']
>>>
>>> sum(m_ratios) # the tree will always sum to 1
Fraction(1, 1)
>>> # add more branches and change leaf-node proportions
>>> subdivisions = (7,2,(3,(1,3,2)),5,(3, (2,3,1)),11)
>>> r_tree = rt.RT(('?', ((4, 4), subdivisions)))
>>> m_ratios = rt.measure_ratios(r_tree)
>>> [str(ratio) for ratio in m_ratios]
['7/31', '2/31', '1/62', '3/62', '1/31', '5/31', '1/31', '3/62', '1/62', '11/31']
>>>
>>> sum(m_ratios) # the tree will always sum to 1
Fraction(1, 1)
>>> # when given a reference tempo in bpm, `Chronos` can convert these ratios into durations in seconds
>>> from allopy import chronos
>>> durations = [chronos.beat_duration(ratio=ratio, bpm=66) for ratio in r_ratios]
>>> [round(dur, 3) for dur in durations]
[0.821, 0.235, 0.059, 0.176, 0.117, 0.587, 0.117, 0.176, 0.059, 1.29]
```

### Microtonality

AlloPy supports both *n*-TET and JI-based tuning systems.
```
>>> from allopy import tonos
>>> tonos.midicents_to_freq(6900)
440.0
>>> tonos.freq_to_pitchclass(440.0)
'A4'
>>> freq = tonos.pitchclass_to_freq('A4', cent_offset = -32)
>>> freq
431.941776308572
>>>
>>> # make a Hexany from some prime factors...
>>> primes = (1,3,5,7)
>>> hexany = tonos.scales.hexany(primes, 2)
>>> # returns a list of products and a list of octave-reduced scale ratios
>>> # (CP factors), (scale ratios)
>>> hexany.primes, hexany.ratios
(3, 5, 7, 15, 21, 35), ('35/32', '5/4', '21/16', '3/2', '7/4', '15/8')
>>> 
>>> # same prime factors but with 3-wise combination products...
>>> tonos.scales.hexany(primes, 3)
>>> (15, 21, 35, 105), ('35/32', '21/16', '105/64', '15/8')
>>> 
>>> # multiply these ratios by a root frequency to create scales
>>> scale_freqs = [round(freq * ratio, 2) for ratio in hexany.ratios]
>>> scale_freqs
[481.25, 550.0, 577.5, 660.0, 770.0, 825.0]
>>> # see the scale degrees as pitch classes with offset in cents...
>>> for pc, cents in [tonos.freq_to_pitchclass(f) for f in scale_freqs]: print(pc, round(cents,2))
... 
B4 -44.86
C#5 -13.69
D5 -29.22
E5 1.96
G5 -31.17
G#5 -11.73
```

*n*-TET tunings are not limited to octave divisions.  `Tonos` can compute any *n*-divisions of any arbitrary interval, i.e., non-octave scales and tunings such as Bohlen-Pierce:
```
...
```

### Abstract tools for metacomposition:

Create intricate mappings from symbolic, non-typed elements
```
>>> from allopy import topos
>>> 
>>> s1, s2 = ('Θ', 'Ξ'), ('∝', '∴', '∫')
>>> iso = topos.iso_pairs(s1, s2)
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
```

Reduce symbolic abstractions to musical abstractions
```
>>> # encoding / decoding
>>> from allopy.topos.random import rando
>>> cy_s1 = rando.rand_encode(s1, tonos.PITCH_CLASSES.N_TET_12.names.as_sharps[::2])
>>> proportions = tuple(set(m_ratios)) # `m_ratios` from the previous example
>>> [str(ratio) for ratio in proportions]
['1/6', '1/30', '1/12', '1/4', '1/60']
>>> cy_s2 = rando.rand_encode(s2, [str(ratio) for ratio in proportions])
>>> # ciphers -->  {musical pitch names}, {metric or "beat" ratios}
>>> cy_s1, cy_s2
({'Θ': 'A#', 'Ξ': 'D'}, {'∝': '1/4', '∴': '1/60', '∫': '1/30'})
>>> for e in rando.decode(h_map, {**cy_s1, **cy_s2}): print(e)
... 
('∆', (('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30')))
('Σ', (('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4')))
('Ψ', (('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60')))
('∐', (('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30')))
('Ω', (('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4')))
('ζ', (('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60')))
>>>
>>> # take the cumulative sum of the ratios in the first line...
>>> import numpy as np
>>> cantus = [0] + [topos.Fraction(cy_s2[p[1]]) for p in iso[:len(kleis) - 1]]
>>> offsets = [r for r in np.cumsum(cantus)]
>>> cy_kleis = rando.lin_encode(kleis, [str(r) for r in offsets])
>>> cy_kleis
{'∆': '1/60', 'Σ': '1/4', 'Ψ': '1/60', '∐': '1/4', 'Ω': '1/30', 'ζ': '0'}
>>> for e in rando.decode(h_map, {**cy_s1, **cy_s2, **cy_kleis}): print(e)
... 
('0', (('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30')))
('1/4', (('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4')))
('4/15', (('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60')))
('3/10', (('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30')))
('11/20', (('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4')))
('17/30', (('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60')))
```

Expand the underlying mappings
```    
>>> # for each offset time, compute a scaling factor for the paired ratios
>>> cantus_sum = np.sum([meas for meas in cantus])
>>> str(cantus_sum)
'17/30'
>>> # based offset times, compute a corresponding scaling factor...  
>>> prolations = [cantus_sum - offset for offset in offsets]
>>> cy_kleis = rando.lin_encode(kleis, [(off, prol) for off, prol in zip(offsets, prolations)])
>>> for e in rando.decode(h_map, {**cy_s1, **cy_s2, **cy_kleis}): print(e)
... 
(('0', '1'), (('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30')))
(('1/4', '23/60'), (('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4')))
(('4/15', '31/60'), (('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60')))
(('3/10', '7/15'), (('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30')))
(('11/20', '3/10'), (('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4')))
(('17/30', '8/15'), (('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60')))
>>> # convert all the metric ratios into durations in seconds...
>>> # computed elsewhere...
>>> for e in rando.decode(h_map, {**cy_s1, **cy_s2, **cy_kleis}): print(e)
... 
((0.0, '1'), (('A#', 0.909), ('D', 0.061), ('A#', 0.121), ('D', 0.909), ('A#', 0.061), ('D', 0.121)))
((0.909, '23/60'), (('D', 0.061), ('A#', 0.121), ('D', 0.909), ('A#', 0.061), ('D', 0.121), ('A#', 0.909)))
((0.97, '31/60'), (('A#', 0.121), ('D', 0.909), ('A#', 0.061), ('D', 0.121), ('A#', 0.909), ('D', 0.061)))
((1.091, '7/15'), (('D', 0.909), ('A#', 0.061), ('D', 0.121), ('A#', 0.909), ('D', 0.061), ('A#', 0.121)))
((2.0, '3/10'), (('A#', 0.061), ('D', 0.121), ('A#', 0.909), ('D', 0.061), ('A#', 0.121), ('D', 0.909)))
((2.061, '8/15'), (('D', 0.121), ('A#', 0.909), ('D', 0.061), ('A#', 0.121), ('D', 0.909), ('A#', 0.061)))
```

Further reduce musical abstractions to synthesis parameters (e.g., pitchclass names become frequencies in Hertz, beat ratios become durations in seconds...)
```
>>> # convert all the scaling ratios into normalized floats and pitch names into frequencies...
>>> # computed elsewhere...
>>> for e in rando.decode(h_map, {**cy_s1, **cy_s2, **cy_kleis}): print(e)
...
((0.0, 1.0), ((466.16, 0.909), (293.66, 0.061), (466.16, 0.121), (293.66, 0.909), (466.16, 0.061), (293.66, 0.121)))
((0.909, 0.383), ((293.66, 0.061), (466.16, 0.121), (293.66, 0.909), (466.16, 0.061), (293.66, 0.121), (466.16, 0.909)))
((0.97, 0.517), ((466.16, 0.121), (293.66, 0.909), (466.16, 0.061), (293.66, 0.121), (466.16, 0.909), (293.66, 0.061)))
((1.091, 0.467), ((293.66, 0.909), (466.16, 0.061), (293.66, 0.121), (466.16, 0.909), (293.66, 0.061), (466.16, 0.121)))
((2.0, 0.3), ((466.16, 0.061), (293.66, 0.121), (466.16, 0.909), (293.66, 0.061), (466.16, 0.121), (293.66, 0.909)))
((2.061, 0.533), ((293.66, 0.121), (466.16, 0.909), (293.66, 0.061), (466.16, 0.121), (293.66, 0.909), (466.16, 0.061)))
>>> # this generates a prolation canon with scaling of each voice relative to the cantus
>>> # see `AlloPy/examples/`
```

Permute the symbolic abstractions into new forms
```
>>> # we could then revise our initial abstraction to include the addition of a scaling factor,
>>> # but, now, "re-abstracted" into a new generalization which itself can be re-interpreted...
>>> for e in h_map: print(e)
...
(('∆', 'λ'), (('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫')))
(('Σ', 'ε'), (('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝')))
(('Ψ', 'ψ'), (('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴')))
(('∐', 'π'), (('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫')))
(('Ω', 'φ'), (('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝')))
(('ζ', 'Ϡ'), (('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴')))
>>>
>>> # we could also perform more transformation and create a new encoding...
>>> h_map_hyper = tuple(topos.homotopic_map(topos.cartesian_iso_pairs(s1, kleis_l[:4]), topos.iso_pairs(s2, kleis_r[:5])))
>>> for e in h_map_hyper: print(e)
...
((('Θ', 'Θ'), '∆'), (('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ')))
((('Θ', 'Ξ'), 'Σ'), (('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ')))
((('Ξ', 'Θ'), 'Ψ'), (('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε')))
((('Ξ', 'Ξ'), '∐'), (('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ')))
((('Θ', 'Θ'), '∆'), (('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π')))
((('Θ', 'Ξ'), 'Σ'), (('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ')))
((('Ξ', 'Θ'), 'Ψ'), (('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ')))
((('Ξ', 'Ξ'), '∐'), (('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε')))
((('Θ', 'Θ'), '∆'), (('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ')))
((('Θ', 'Ξ'), 'Σ'), (('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π')))
((('Ξ', 'Θ'), 'Ψ'), (('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ')))
((('Ξ', 'Ξ'), '∐'), (('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ')))
((('Θ', 'Θ'), '∆'), (('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε')))
((('Θ', 'Ξ'), 'Σ'), (('∴', 'π'), ('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ')))
((('Ξ', 'Θ'), 'Ψ'), (('∫', 'φ'), ('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π')))
((('Ξ', 'Ξ'), '∐'), (('∝', 'λ'), ('∴', 'ε'), ('∫', 'ψ'), ('∝', 'π'), ('∴', 'φ'), ('∫', 'λ'), ('∝', 'ε'), ('∴', 'ψ'), ('∫', 'π'), ('∝', 'φ'), ('∴', 'λ'), ('∫', 'ε'), ('∝', 'ψ'), ('∴', 'π'), ('∫', 'φ')))
>>>
>>> # and so on...
```

### Formal Grammars:

Generate replacement rules for any alphabet
```
>>> from allopy.topos import formal_grammars as frgr
>>> S1 = ('F','f','G','+','-')
>>> random_rules = frgr.grammars.rand_rules(S1, word_length_max=5)
>>> for axiom, sub in random_rules.items(): print(f'{axiom} : {sub}')
... 
F : -FF-+-f
f : -Gf+G
G : fF-Ff-
+ : --fG
- : fGff
```

Rules can be modified with conditional constraints
```
>>> S2 = ('#','&','!')
>>> constraints = {a: np.random.choice(S2) for a in alpha[:len(alpha)//2]}
>>> constraints
{'F': '!', 'f': '&', 'G': '!', '+': '#', '-': '#'}
>>> random_rules = frgr.grammars.constrain_rules(random_rules, constraints)
>>> for axiom, sub in random_rules.items(): print(f'{axiom} : {sub}')
... 
F : -FF-+-!
f : -&f+G
G : f!-Ff-
+ : -#fG
- : fG#f
```

Generate word strings by applying the grammar to an initial axiom
```
>>> random_rules = {k: v + ' ' for k, v in random_rules.items()}
>>> gens = 11
>>> # generate string starting from random initial axiom
>>> l_str_gens = frgr.grammars.gen_str(generations=gens, axiom=np.random.choice(alpha), rules=random_rules)
>>> for i in range(0,5): print(f'Gen {i}:\n',l_str_gens[i])
... 
Gen 0:
G
Gen 1:
f!-Ff- 
Gen 2:
-&f+G fG#f -FF-+-! -&f+G fG#f 
Gen 3:
fG#f -&f+G -#fG f!-Ff- -&f+G f!-Ff- -&f+G fG#f -FF-+-! -FF-+-! fG#f -#fG fG#f fG#f -&f+G -#fG f!-Ff- -&f+G f!-Ff- -&f+G 
Gen 4:
-&f+G f!-Ff- -&f+G fG#f -&f+G -#fG f!-Ff- fG#f -&f+G f!-Ff- -&f+G fG#f -FF-+-! -&f+G fG#f fG#f -&f+G -#fG f!-Ff- -&f+G fG#f -FF-+-! -&f+G fG#f fG#f -&f+G -#fG f!-Ff- -&f+G f!-Ff- -&f+G fG#f -FF-+-! -FF-+-! fG#f -#fG fG#f fG#f -FF-+-! -FF-+-! fG#f -#fG fG#f -&f+G f!-Ff- -&f+G fG#f -&f+G f!-Ff- -&f+G f!-Ff- -&f+G -&f+G f!-Ff- -&f+G fG#f -&f+G -#fG f!-Ff- fG#f -&f+G f!-Ff- -&f+G fG#f -FF-+-! -&f+G fG#f fG#f -&f+G -#fG f!-Ff- -&f+G fG#f -FF-+-! -&f+G fG#f fG#f -&f+G -#fG f!-Ff- 
```

---   

### Integration with AlloLib Playground

Even in this 'on-the-fly', interpreter-based paradigm, AlloPy is designed to integrate directly with the AlloLib Playground in any IDE of choice.  

This means that, for example, note lists can be generated, edited, and merged freely with changes appearing in realtime from within your running AlloLib app—*no need to close and re-run the application when making changes to your scores.*  

See VS Code integration section for more details.

---

## Education

### **Into the AlloVerse:**  *an Audiovisual Synthesis and Metacomposition tutorial series for working with AlloLib Playground and AlloPy*

The AlloLib Playground is an application development space for working with the classes and functions of the `AlloLib` and `Gamma` C++ libraries.  The Playground thus sits "close to the metal" and allows users to work directly at the sample-level of audio synthesis and at the framerate of graphics rendering.

`AlloPy`, implemented in Python, exists "above the metal" and serves as an abstract toolkit for working with low-level distributed systems such as AlloLib.

When used in concert, AlloLib Playground and AlloPy form a computer-assisted composition framework for working with poly-sensory metacompositional materials and realizing the results with an audiovisual application.  Students, artists, composers, and researchers can then move freely between all levels of a distributed, multimedia composition system.

*Coming soon...*

---

## License

[AlloPy](https://github.com/kr4g/AlloPy) by Ryan Millett is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/?ref=chooser-v1).

![CC Icon](https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1)
![BY Icon](https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1)
![SA Icon](https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1)

AlloPy © 2023 by Ryan Millett is licensed under CC BY-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

---
