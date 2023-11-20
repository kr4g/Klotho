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

    To work with AlloPy as an 'on-the-fly' compositional-aid, initiate a Python interpreter from within the `AlloPy/` directory by running the command:

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
    >>> # returns a list of products and a list of octave-reduced scale ratios
    >>> hexany
    ([3, 5, 7, 15, 21, 35], [1.09375, 1.25, 1.3125, 1.5, 1.75, 1.875])
    >>> # multiply these ratios by a root frequency to create scales
    >>> [freq * ratio for ratio in hexany.ratios]
    [472.4363178375006, 539.927220385715, 566.9235814050007, 647.912664462858, 755.898108540001, 809.8908305785725]
    ```

    AlloPy supports [Rhythm Trees](https://support.ircam.fr/docs/om/om6-manual/co/RT1.html), as implemented in the [OpenMusic](https://openmusic-project.github.io/) composition software.
    ```
    >>> from allopy.chronos import rhythm_trees as rt
    >>> # tree-graph representation using LISP-like syntax
    >>> subdivisions = (1,1,1,1,1)
    >>> r_tree = rt.RT(('?', ((4, 4), subdivisions)))
    >>> m_ratios = rt.measure_ratios(r_tree) # evaluates to a list of metric proportions dividing an abstract unit of time
    >>> [str(ratio) for ratio in m_ratios]
    ['1/5', '1/5', '1/5', '1/5', '1/5']
    >>> float(sum([r for r in r_ratios]))
    1.0
    >>> # add "branches"
    >>> subdivisions = (1,1,(1,(1,1,1)),1,1)
    >>> r_tree = rt.RT(('?', ((4, 4), )))
    >>> m_ratios = rt.measure_ratios(r_tree)
    >>> [str(ratio) for ratio in m_ratios]
    ['1/5', '1/5', '1/15', '1/15', '1/15', '1/5', '1/5']
    >>> # add more branches and change leaf-node proportions
    >>> subdivisions = (7,2,(3,(1,3,2)),5,(3, (2,3,1)),11)
    >>> r_tree = rt.RT(('?', ((4, 4), subdivisions)))
    >>> m_ratios = rt.measure_ratios(r_tree)
    >>> [str(ratio) for ratio in m_ratios]
    ['7/31', '2/31', '1/62', '3/62', '1/31', '5/31', '1/31', '3/62', '1/62', '11/31']
    >>> # the tree will always sum to 1
    >>> float(sum([r for r in r_ratios]))
    1.0
    >>> from allopy import chronos
    >>> # when given a reference tempo in bpm, `Chronos` can convert these ratios into durations in seconds
    >>> durations = [chronos.beat_duration(ratio=ratio, bpm=66) for ratio in r_ratios]
    >>> [round(dur, 3) for dur in durations]
    [0.821, 0.235, 0.059, 0.176, 0.117, 0.587, 0.117, 0.176, 0.059, 1.29]
    ```

    Abstract tools for metacomposition:
    ```
    >>> from allopy import topos
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
    >>> # encoding / decoding
    >>> from allopy.topos.random import rando
    >>> cy_s1 = rando.rand_encode(s1, tonos.PITCH_CLASSES.N_TET_12.names.as_sharps[::2])
    >>> proportions = tuple(set([str(ratio) for ratio in m_ratios])) # from the previous example
    >>> proportions
    ('1/6', '1/30', '1/12', '1/4', '1/60')
    >>> cy_s2 = rando.rand_encode(s2, [str(ratio) for ratio in proportions])
    >>> # ciphers:  musical pitch names, metric or "beat" ratios
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
    >>> # take the cumulative sum of the ratios in the first line...
    >>> import numpy as np
    >>> cantus = [0] + [topos.Fraction(cy_s2[p[1]]) for p in iso[:len(kleis) - 1]]
    >>> offsets = [str(r) for r in np.cumsum(cantus)]
    >>> cy_kleis = rando.lin_encode(kleis, offsets)
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
    >>> # for each offset time, compute a scaling factor for the paired ratios
    >>> cantus_sum = np.sum([meas for meas in cantus])
    >>> str(cantus_sum)
    '17/30'
    >>> # based offset times, compute a corresponding scaling factor...  
    >>> offsets = [topos.Fraction(r) for r in offsets] # back to Fractions for the computation...
    >>> prolations = [(cantus_sum - offsets[i]) / cantus_sum if offsets[i] != 0 else 1 for i, r in enumerate(offsets)]
    >>> cy_kleis = rando.lin_encode(kleis, [(off, prol) for off, prol in zip(offsets, prolations)])
    >>> for e in rando.decode(h_map, {**cy_s1, **cy_s2, **cy_kleis}): print(e)
    ... 
    (('0', '1'), (('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30')))
    (('1/4', '19/34'), (('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4')))
    (('4/15', '9/17'), (('A#', '1/30'), ('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60')))
    (('3/10', '8/17'), (('D', '1/4'), ('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30')))
    (('11/20', '1/34'), (('A#', '1/60'), ('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4')))
    (('17/30', '0'), (('D', '1/30'), ('A#', '1/4'), ('D', '1/60'), ('A#', '1/30'), ('D', '1/4'), ('A#', '1/60')))
    >>> # convert all the metric ratios into durations in seconds...
    >>> # computed elsewhere...
    >>> for e in rando.decode(h_map, {**cy_s1, **cy_s2, **cy_kleis}): print(e)
    ... 
    ((0.0, '1'), (('A#', 0.909), ('D', 0.061), ('A#', 0.121), ('D', 0.909), ('A#', 0.061), ('D', 0.121)))
    ((0.909, '19/34'), (('D', 0.061), ('A#', 0.121), ('D', 0.909), ('A#', 0.061), ('D', 0.121), ('A#', 0.909)))
    ((0.97, '9/17'), (('A#', 0.121), ('D', 0.909), ('A#', 0.061), ('D', 0.121), ('A#', 0.909), ('D', 0.061)))
    ((1.091, '8/17'), (('D', 0.909), ('A#', 0.061), ('D', 0.121), ('A#', 0.909), ('D', 0.061), ('A#', 0.121)))
    ((2.0, '1/34'), (('A#', 0.061), ('D', 0.121), ('A#', 0.909), ('D', 0.061), ('A#', 0.121), ('D', 0.909)))
    ((2.061, '0'), (('D', 0.121), ('A#', 0.909), ('D', 0.061), ('A#', 0.121), ('D', 0.909), ('A#', 0.061)))
    >>> # convert all the scaling ratios into normalized floats and pitch names into frequencies...
    >>> # computed elsewhere...
    >>> for e in rando.decode(h_map, {**cy_s1, **cy_s2, **cy_kleis}): print(e)
    .. 
    ((0.0, 1.0), ((466.16, 0.909), (293.66, 0.061), (466.16, 0.121), (293.66, 0.909), (466.16, 0.061), (293.66, 0.121)))
    ((0.909, 0.5588), ((293.66, 0.061), (466.16, 0.121), (293.66, 0.909), (466.16, 0.061), (293.66, 0.121), (466.16, 0.909)))
    ((0.97, 0.5294), ((466.16, 0.121), (293.66, 0.909), (466.16, 0.061), (293.66, 0.121), (466.16, 0.909), (293.66, 0.061)))
    ((1.091, 0.4706), ((293.66, 0.909), (466.16, 0.061), (293.66, 0.121), (466.16, 0.909), (293.66, 0.061), (466.16, 0.121)))
    ((2.0, 0.0294), ((466.16, 0.061), (293.66, 0.121), (466.16, 0.909), (293.66, 0.061), (466.16, 0.121), (293.66, 0.909)))
    ((2.061, 0.0), ((293.66, 0.121), (466.16, 0.909), (293.66, 0.061), (466.16, 0.121), (293.66, 0.909), (466.16, 0.061)))
    >>> # this generates a prolation canon with scaling of each voice relative to the cantus
    >>> # see `AlloPy/examples/`
    >>> # we could then revise our initial abstraction to include the addition of a scaling factor,
    >>> # but, now, "re-abstracted" into a new generalization which itself can be re-interpreted...
    ...
    (('∆', 'λ'), (('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫')))
    (('Σ', 'ε'), (('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝')))
    (('Ψ', 'ψ'), (('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴')))
    (('∐', 'π'), (('Ξ', '∝'), ('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫')))
    (('Ω', 'φ'), (('Θ', '∴'), ('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝')))
    (('ζ', 'Ϡ'), (('Ξ', '∫'), ('Θ', '∝'), ('Ξ', '∴'), ('Θ', '∫'), ('Ξ', '∝'), ('Θ', '∴')))
    >>>
    >>> # we could also perform more transformation and create a new encoding...
    >>> h_map_hyper = tuple(topos.homotopic_map(topos.cartesian_iso_pairs(s1,
                                                                          kleis_l[:4]),
                                                                          topos.iso_pairs(s2,
                                                                                          kleis_r[:5])))
    >>> h_map_hyper
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
    >>> # and so on...
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

The `topos.py` base module contains a multitude of abstract "puzzle" functions deeply inspired by Category Theory, Topology, and abstract algebra in general.  These functions are data-type agnostic and work entirely in a functional, LISP-like paradigm inspired by the [OpenMusic](https://openmusic-project.github.io/) software implemented in Common LISP.

(examples)

Every `topos.py` function is inherently recursive and all work with the same input and output type—the tuple.  This means that outputs can feedback into inputs and/or pipe into the inputs of other functions, etc., allowing for the construction of highly complex abstract structures from the interweaving of very simple base operations.

(examples)

The `Topos` module, like the other `AlloPy` modules, also contains specialized submodules such as formal grammars, including basic rewrite rule generation and a library of ancient [graphemes](https://en.wikipedia.org/wiki/Grapheme)—useful when working with categorical, algebraic abstractions.

(examples)

Consult The Topos for guidance and you will receive it, but know that The Topos speaks and answers only in riddle.  Though, in solving the riddle, will you ultimately attain the answer to your question.

### `Aikous` 

***Goddess of Perception and Practicality:*** *the threader of musical algebra and synthesis reality*

Throughout the synapses of this hyper-network of conceptual abstraction, flows the mana of `Aikous`, who interlaces the higher-order symbolic representations of musical expression with the working reality of sound synthesis.  While The `Topos` arbitrates over the algebra, `Aikous` conceives the calculus.

`Aikous` contains basic tools for converting between *conceptual* units (e.g., musical dynamics such as `mp` and `fff`) and *concrete* synthesis units (e.g., amplitude and deicibel values) as well as functions for creating smooth curves and interpolations between discrete musical elements—i.e., *crescendi* and *diminuendi*.  `Aikous` is then best suited for the score-writing aspect of the compositional process, as she performs the computations necessary to weave a sense of continuous expression across the succession of discrete events.

(examples)

### `Skora` 

***The Scribe:***  *keeper of scores, numen of notation*

Silent and often sullen, `Skora` the scribe sombers in sanctuary situated just above the substratum of synthesis.  That is to say, `Skora` is keeper of record for all musical events as they must be known and tublated for processing by The Machines.

The `Gamma` synth instruments in `AlloLib` use a [command-line](https://www.csounds.com/manual/html/ScoreTop.html) notation [system](https://flossmanual.csound.com/miscellanea/methods-of-writing-csound-scores) similar to [`Csound`](https://csound.com/).  These "note lists" consist of discrete commands organized by *pfields*.  `Skora` converts this tabular format into an data structure known as a [`DataFrame`](https://pandas.pydata.org/).  When abstracted into this format, AlloLib score files can be exposed to the higher-order computation functions available in the "data science" computing paradigm.

(*A short tutorial note list basics, including pfields, can be found [here]()*)

(examples)

`Skora` then also leverages the power of `Numpy` to perform complex computations on any slice of the *Score DataFrame*.  This allows for a more fluid approach to editing and, most interesting, *generating* `AlloLib` note lists dynamically.  `AlloPy` can then function as both a computational composition aid or a data sonification tool—and everything in between.

The `Skora` module also provides tools for managing and merging multiple separate parts, making larger-scale arrangements easier to maintain.

(examples)

Integration with [`abjad`](https://abjad.github.io/) and [`LilyPond`](https://lilypond.org/development.html) are presently in development.

(examples)

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
