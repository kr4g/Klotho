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

2. **Navigate to the AlloPy Directory**:
    Navigate to the `/AlloPy/` directory within the `/allolib_playground/` folder:
   
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

    The `./allolib_playground/AlloPy/examples/` directory contains examples of how to use the modules in the `AlloPy` package as a scripting tool.

    To use `AlloPy` as an 'on-the-fly' compositional-aid, initiate a Python interpreter from within the `/AlloPy/` directory by running the command:

    ```
    Python
    ```

    Then, once the interpreter loads, import from `allopy` as needed.  For example:

    ```
    >>> from allopy import tonos
    >>> tonos.midicents_to_freq(6900)
    440.0
    ```

    ```
    >>> from allopy.chronos import rhythm_trees as rt
    >>> rt.measure_ratios(rt.RT(('?', ((4, 4), (1, (2, (1, 1, 1)), (1, (1, (1, (2, 1, 2)), 1)))))))
    [Fraction(1, 4), Fraction(1, 6), Fraction(1, 6), Fraction(1, 6), Fraction(1, 12), Fraction(1, 30), Fraction(1, 60), Fraction(1, 30), Fraction(1, 12)]
    >>> 
    ```

    ```
    >>> from allopy import topos
    >>> topos.iso_pairs(('⚛', '∿', '♢'), ('Ξ', '≈'))
    (('⚛', 'Ξ'), ('∿', '≈'), ('♢', 'Ξ'), ('⚛', '≈'), ('∿', 'Ξ'), ('♢', '≈'))
    ```

    Or import the entire package:
    ```
    >>> import allopy as al
    >>> al.aikous.Dynamics.mf
    0.2512
    >>> aikous.Tempo.Largo
    (40, 66)
    ```

---

## License

[AlloPy](https://github.com/kr4g/AlloPy) by Ryan Millett is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/?ref=chooser-v1).

![CC Icon](https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1)
![BY Icon](https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1)
![SA Icon](https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1)

AlloPy © 2023 by Ryan Millett is licensed under CC BY-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

---
