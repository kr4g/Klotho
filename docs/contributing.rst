Contributing
============

Contributions of all kinds are welcome — whether it's code, bug reports, documentation
improvements, or ideas for new features.

How to Contribute
-----------------

1. Fork the `repository <https://github.com/kr4g/Klotho>`_.
2. Create a branch for your changes.
3. Open a pull request.

For bugs or suggestions, open an issue on
`GitHub Issues <https://github.com/kr4g/Klotho/issues>`_.

All contributions are accepted under the same
`CC BY-SA 4.0 <https://creativecommons.org/licenses/by-sa/4.0/>`_ license,
and contributors are credited through Git history.

Development Setup
-----------------

Clone the repository and install in development mode:

.. code-block:: bash

   git clone https://github.com/kr4g/Klotho.git
   cd Klotho/
   pip install -e .[dev]

This installs all core dependencies plus testing (pytest) and documentation (Sphinx) tools.

Documentation Standards
-----------------------

This project uses NumPy-style docstrings. Please follow this format when documenting your code:

.. code-block:: python

   def example_function(param1, param2):
       """
       Brief description of the function.

       More detailed description if needed.

       Parameters
       ----------
       param1 : type
           Description of param1.
       param2 : type
           Description of param2.

       Returns
       -------
       type
           Description of return value.

       Examples
       --------
       >>> example_function(1, 2)
       3
       """
       return param1 + param2

See the full style guide in ``docs/numpy_docstring_guide.md``.
