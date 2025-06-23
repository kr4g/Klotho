Changelog
=========

Version 3.0.5 (Current)
------------------------

* Documentation infrastructure setup
* Added comprehensive Sphinx documentation
* NumPy-style docstring standards established
* **NEW:** Added ``klotho.semeios.maquettes`` module for interactive timeline visualization
* **NEW:** Timeline class with web-based GUI for musical maquettes (sketches)
* **NEW:** Clip class for representing time-bounded events
* **NEW:** OSC communication support for real-time clip highlighting
* **NEW:** Multi-track timeline system with DAW-like behavior
* **NEW:** Dependencies added: panel, bokeh, jupyter_bokeh for interactive visualization
* **REFACTORED:** ``klotho.utils.algorithms`` module architecture improvements:
  
  * **NEW:** Added ``graphs.py`` module with flexible ``minimum_cost_path`` function
  * **IMPROVED:** ``cost_matrix`` now returns numpy arrays instead of pandas DataFrames for better performance
  * **RENAMED:** ``cost_matrix_graph`` → ``cost_matrix_to_graph`` for clarity
  * **ENHANCED:** ``minimum_cost_path`` supports arbitrary traversal functions with ``**kwargs``
  * **FIXED:** Import issues with non-existent ``Notelist`` class

Previous Versions
-----------------

Coming soon... 