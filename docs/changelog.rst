Changelog
=========

Version 4.0.5 (Current)
------------------------

* Comprehensive documentation overhaul with NumPy-style docstrings across all modules
* Sphinx docs restructured to match current source tree
* ``conf.py`` version now reads dynamically from ``klotho/__init__.py``
* Added ``plotly`` and ``scikit-learn`` to ``install_requires``
* README cleanup: simplified installation instructions, added badges, updated copyright

Version 4.x
------------

* Major API restructuring across all modules
* Removed ``maquettes``, ``animation``, ``notation``, ``midi``, and ``allolib`` submodules from semeios
* Removed ``fields`` subtree from ``topos.graphs.lattices``
* Added ``tone_lattices`` system to tonos
* Renamed CPS modules (``cps.py`` → ``combination_product_sets.py``, ``nkany.py`` → ``algorithms.py``)
* Added ``Contour`` class to tonos.pitch
* Added ``basis.py`` to utils.algorithms
* Graph backend migrated to RustworkX for performance

Version 3.0.5
--------------

* Documentation infrastructure setup
* Added comprehensive Sphinx documentation
* NumPy-style docstring standards established
* Dependencies added: panel, bokeh, jupyter_bokeh for interactive visualization
* ``klotho.utils.algorithms`` module architecture improvements

Previous Versions
-----------------

See the `GitHub repository <https://github.com/kr4g/Klotho>`_ for full commit history.
