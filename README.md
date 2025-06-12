# Klotho
`Klotho` is an open source computer-assisted composition toolkit implemented in Python.  It is designed to work in tandem with external synthesis applications and as a general resource for the methods, models, works, and frameworks associated with the art and craft of music composition and metacomposition.

---

## Installation

Klotho works as both a Python scripting toolkit and 'on-the-fly' via a Python interpreter.

### Option 1: Install from PyPI (Recommended)

```bash
pip install klotho-cac
```

### Option 2: Install from Source

1. **Clone the Repository**:

   First, clone the Klotho repository by running the following command in your terminal or command prompt:
   
   ```
   git clone https://github.com/kr4g/Klotho.git
   ```

2. **Navigate to the `Klotho/` Directory**:
   
    ```
    cd Klotho/
    ```

3. **Install in Development Mode**:

    Install Klotho in development mode (recommended for development):
    
    ```
    pip install -e .
    ```
    
    Or install the required dependencies separately:
    
    ```
    pip install -r requirements.txt
    ```

<!-- 4. **Install Klotho (Development Mode)**:

    To install Klotho in development mode, which allows you to modify the source code and have the changes reflected immediately:

    ```
    pip install -e .
    ```

5. **Play**:

    To work with Klotho as an 'on-the-fly' compositional-aid, initiate a Python interpreter from within the `Klotho/` directory by running the command:

    ```
    Python
    ```

    Once the interpreter loads, import from `klotho` as needed. -->

## About

Klotho extends from a lineage of CAC-oriented theories and softwares.  This means that, while Klotho provides many classes and functions for 'standard' music materials, its strengths are best utilized when working with more complex, abstract, or otherwise unconventional materials not easily accessible with standard notation softwares.  

The ethos of Klotho draws heavily from the concepts and computations possible with patching-based softwares like [OpenMusic](https://openmusic-project.github.io/) (which also influenced [Bach](https://www.bachproject.net/) and [Cage](https://www.bachproject.net/cage/) for Max).

Klotho seeks to avoid this patching paradigm in favor of a high-level scripting syntax that more closely resembles the underlying mathematical expressions at play when working with computational composition tools.  Many of Klotho's core features, particularly in the implementation of Rhythm Trees, adhere to a "LISP-like" presentation and programming paradigm inspired by the underlying Common LISP source code for OpenMusic.  It is then also closer to the abstract, algebraic language of music in its symbolic representations.

## License

[Klotho](https://github.com/kr4g/Klotho) by Ryan Millett is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/?ref=chooser-v1).

![CC Icon](https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1)
![BY Icon](https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1)
![SA Icon](https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1)

Klotho © 2023 by Ryan Millett is licensed under CC BY-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

---
