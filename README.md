# AlloPy
AlloPy is an open source Python package designed to work as both a stand-alone software and in tandem with AlloLib Playground as a computer-assisted toolkit, work environment, notation editor, and general educational resource for the methods, models, works, and frameworks associated with the art and craft of transmodal metacomposition.

Download AlloLib Playground here:  https://github.com/AlloSphere-Research-Group/allolib_playground


Developed by Ryan Millett as part of the AlloSphere Research Group under the supervision of Dr. Kuchera-Morin.

[The AlloSphere Research Group](https://github.com/AlloSphere-Research-Group)

---

## Installation

AlloPy works as both a Python scripting toolkit and 'on-the-fly' via a Python interpreter.

If you want to use AlloPy with AlloLib Playground, first install AlloLib Playground [https://github.com/AlloSphere-Research-Group/allolib_playground](here).

1. **Clone the Repository**:

   First, clone the AlloPy repository (into the `/allolib_playground/` directory of your system if you want to work with AlloLib/Gamma) by running the following command in your terminal or command prompt:
   
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

    To work with `AlloPy` as a scripting tool, create a directory within the `/AlloPy/` directory and save your scripts there.``

    The `AlloPy/examples/` directory contains examples of how to use the modules in the `AlloPy` package as a scripting tool.

    To use `AlloPy` as an 'on-the-fly' compositional-aid, initiate a Python interpreter from within the `/AlloPy/` directory by running the command:

    ```
    Python
    ```

    Then, once the interpreter loads, import from `allopy` as needed.  For example:

    ```
    >>> from allopy import tonos
    >>> tonos.midicents_to_freq(6900)
    440.0
    >>> tonos.scales.hexany([1,3,5,7], 2)
    ([3, 5, 7, 15, 21, 35], [1.09375, 1.25, 1.3125, 1.5, 1.75, 1.875])
    >>> tonos.pitchclass_to_freq('A4')
    440.0
    >>> tonos.pitchclass_to_freq('A4', -32)
    431.941776308572
    ```

    `AlloPy` supports [https://support.ircam.fr/docs/om/om6-manual/co/RT1.html](Rhythm Trees), as implemented in the [https://openmusic-project.github.io/](OpenMusic) composition software.
    ```
    >>> from allopy.chronos import rhythm_trees as rt
    >>> r_tree = rt.RT(('?', ((4, 4), (1, (2, (1, 1, 1)), (1, (1, (1, (2, 1, 2)), 1))))))
    >>> [str(r) for r in rt.measure_ratios(r_tree)]
    ['1/4', '1/6', '1/6', '1/6', '1/12', '1/30', '1/60', '1/30', '1/12']
    ```

    ```
    >>> from allopy import topos
    >>> iso = topos.iso_pairs(('⚛', '∿', '♢'), ('Ξ', '≈'))
    >>> iso
    (('⚛', 'Ξ'), ('∿', '≈'), ('♢', 'Ξ'), ('⚛', '≈'), ('∿', 'Ξ'), ('♢', '≈'))
    >>> kleis = ('∆','Σ','Ψ','Ω','ζ')
    >>> topos.homotopic_map(kleis, iso)
    (('∆', (('⚛', 'Ξ'), ('∿', '≈'), ('♢', 'Ξ'), ('⚛', '≈'), ('∿', 'Ξ'), ('♢', '≈'))), ('Σ', (('∿', '≈'), ('♢', 'Ξ'), ('⚛', '≈'), ('∿', 'Ξ'), ('♢', '≈'), ('⚛', 'Ξ'))), ('Ψ', (('♢', 'Ξ'), ('⚛', '≈'), ('∿', 'Ξ'), ('♢', '≈'), ('⚛', 'Ξ'), ('∿', '≈'))), ('Ω', (('⚛', '≈'), ('∿', 'Ξ'), ('♢', '≈'), ('⚛', 'Ξ'), ('∿', '≈'), ('♢', 'Ξ'))), ('ζ', (('∿', 'Ξ'), ('♢', '≈'), ('⚛', 'Ξ'), ('∿', '≈'), ('♢', 'Ξ'), ('⚛', '≈'))))
    ```

    Or import the entire package:
    ```
    >>> import allopy as al
    >>> al.aikous.Dynamics.mf
    0.2512
    >>> al.chronos.beat_duration(metric_ratio=1/4, bpm=120)
    0.5
    >>> score_df = al.skora.make_score_df(pfields=('start', 'dur', 'synthName', 'amplitude', 'frequency'))
    >>> frequency = al.tonos.pitchclass_to_freq('D3', cent_offset = -16) 
    >>> ratio = al.tonos.cents_to_ratio(386)
    >>> rows = [{
            'start'      : 0.0,
            'dur'        : al.chronos.beat_duration(1/9, 76),
            'synthName'  : 'mySynth',
            'amplitude'  : al.aikous.Dynamics.ff,
            'frequency'  : frequency * ratio**i,
        } for i in range(9)]
    >>> score_df = skora.concat_rows(score_df, rows)
    >>> skora.df_to_synthSeq(score_df, 'path/to/score/dir/my_score.synthSequence')
    ```
---

## License

[AlloPy](https://github.com/kr4g/AlloPy) by Ryan Millett is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/?ref=chooser-v1).

![CC Icon](https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1)
![BY Icon](https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1)
![SA Icon](https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1)

AlloPy © 2023 by Ryan Millett is licensed under CC BY-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

---
