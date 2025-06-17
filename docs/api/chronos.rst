chronos
=======

Chronos provides specialized classes and functions for working with time and rhythm in music.

The word "chronos" originates from Ancient Greek and is deeply rooted in both language 
and mythology. In Greek, "χρόνος" (chronos) means "time". In Greek mythology, Chronos 
is personified as the god of time, symbolizing the endless passage of time and the 
cycles of creation and destruction within the universe.

Rhythm Pairs
------------

.. autoclass:: klotho.chronos.rhythm_pairs.rhythm_pair.RhythmPair
   :members:
   :show-inheritance:

Rhythm Trees
------------

.. autoclass:: klotho.chronos.rhythm_trees.rhythm_tree.RhythmTree
   :members:
   :show-inheritance:

.. autoclass:: klotho.chronos.rhythm_trees.meas.Meas
   :members:
   :show-inheritance:

Tree Algorithms
~~~~~~~~~~~~~~~

.. automodule:: klotho.chronos.rhythm_trees.algorithms
   :members:
   :show-inheritance:

Temporal Units
--------------

Core Classes
~~~~~~~~~~~~

.. autoclass:: klotho.chronos.temporal_units.temporal.TemporalUnit
   :members:
   :show-inheritance:

.. autoclass:: klotho.chronos.temporal_units.temporal.TemporalUnitSequence
   :members:
   :show-inheritance:

.. autoclass:: klotho.chronos.temporal_units.temporal.TemporalBlock
   :members:
   :show-inheritance:

.. autoclass:: klotho.chronos.temporal_units.temporal.Chronon
   :members:
   :show-inheritance:

Utilities
---------

Beat Utilities
~~~~~~~~~~~~~~

.. autofunction:: klotho.chronos.utils.beat.cycles_to_frequency

.. autofunction:: klotho.chronos.utils.beat.beat_duration

.. autofunction:: klotho.chronos.utils.beat.calc_onsets

Tempo Utilities
~~~~~~~~~~~~~~~

.. automodule:: klotho.chronos.utils.tempo
   :members:
   :show-inheritance:

Time Conversion
~~~~~~~~~~~~~~~

.. automodule:: klotho.chronos.utils.time_conversion
   :members:
   :show-inheritance: 