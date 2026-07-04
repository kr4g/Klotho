topos
=====

Topos deals with the abstract mathematical and structural foundations of music, providing
topological scaffolding that can be instantiated into any musical context.

Collections
-----------

Patterns
~~~~~~~~

.. automodule:: klotho.topos.collections.patterns
   :members:
   :show-inheritance:

Sequences
~~~~~~~~~

.. automodule:: klotho.topos.collections.sequences
   :members:
   :show-inheritance:

Sets
~~~~

.. automodule:: klotho.topos.collections.sets
   :members:
   :show-inheritance:

Formal Grammars
---------------

Grammars
~~~~~~~~

.. automodule:: klotho.topos.formal_grammars.grammars
   :members:
   :show-inheritance:

Graphs
------

Graph Core
~~~~~~~~~~

The read-only base layer of the graph hierarchy: views, traversal, and queries.

.. automodule:: klotho.topos.graphs.core
   :members:
   :show-inheritance:

Mutable Graphs
~~~~~~~~~~~~~~

.. automodule:: klotho.topos.graphs.graphs
   :members:
   :show-inheritance:

Topology Generators
~~~~~~~~~~~~~~~~~~~

Module-level functions that construct common graph topologies.

.. automodule:: klotho.topos.graphs.generators
   :members:
   :show-inheritance:

Trees
~~~~~

Tree Implementation
^^^^^^^^^^^^^^^^^^^

.. automodule:: klotho.topos.graphs.trees.trees
   :members:
   :show-inheritance:

Tree Layers
^^^^^^^^^^^

Domain behavior attached to trees. A layer owns node-data keys and recompute
rules; the tree notifies attached layers after every mutation.

.. automodule:: klotho.topos.graphs.trees.layers
   :members:
   :show-inheritance:

Group
^^^^^

.. automodule:: klotho.topos.graphs.trees.group
   :members:
   :show-inheritance:

Lattices
~~~~~~~~

Lattice Implementation
^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: klotho.topos.graphs.lattices.lattices
   :members:
   :show-inheritance:

Lattice Algorithms
^^^^^^^^^^^^^^^^^^

.. automodule:: klotho.topos.graphs.lattices.algorithms
   :members:
   :show-inheritance:

Types
-----

.. automodule:: klotho.topos.types
   :members:
   :show-inheritance:
