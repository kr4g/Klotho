.. Klotho documentation master file, created by
   sphinx-quickstart on Tue Jun 17 13:46:57 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Klotho: Graph-Oriented Computer-Assisted Composition
====================================================

**Klotho** is a comprehensive toolkit for complex musical analysis, generation, and visualization implemented in Python.

From the Ancient Greek "Κλωθώ" (Klotho), meaning "to spin".

Overview
--------

Klotho extends from a lineage of computer-assisted composition (CAC) theories, practices, and software environments. While it provides support for conventional musical materials, its strengths are best utilized when working with complex, abstract, and unconventional musical structures not easily accessible with traditional notation software or digital audio workstations.

Core Modules
------------

Klotho is organized into six primary modules plus utilities:

* **topos**: Abstract mathematical and structural foundations
* **chronos**: Temporal structures and rhythm generation
* **tonos**: Tonal systems, pitches, scales, and harmony  
* **thetos**: Musical parameter trees and instrumentation
* **dynatos**: Expression, dynamics, and envelopes
* **semeios**: Visualization, notation, representation, and interactive maquettes
* **utils**: General utilities and helper functions

Installation
------------

**Basic Installation:**

.. code-block:: bash

   pip install klotho-cac

**With Documentation Tools:**

.. code-block:: bash

   pip install klotho-cac[docs]

**For Development:**

.. code-block:: bash

   pip install klotho-cac[dev]

**Install from Source:**

.. code-block:: bash

   git clone https://github.com/kr4g/Klotho.git
   cd Klotho/
   pip install -e .[dev]

API Documentation
-----------------

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   api/topos
   api/chronos
   api/tonos
   api/thetos
   api/dynatos
   api/semeios
   api/utils

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources:

   examples
   contributing
   changelog

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

