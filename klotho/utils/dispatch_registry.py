"""MRO-walking type registry for single-dispatch tables.

Klotho's user-facing entry points (``plot``, the playback converters)
dispatch on the type of one object. A :class:`TypeRegistry` replaces the
match/isinstance ladders those entry points used to carry: handlers are
registered per type, and lookup walks ``type(obj).__mro__``, so a
subclass handler always wins over its base's handler *regardless of
registration order* (``ParameterField`` before ``Lattice``,
``CompositionalUnit`` before ``TemporalUnit``, ``RhythmTree`` before
``Tree`` — all automatic). Duck-typed fallbacks (e.g. "anything with
``nodes`` and ``edges`` plots as a graph") register as predicates, which
are consulted only after every MRO miss.
"""

__all__ = ['TypeRegistry']


class TypeRegistry:
    """A single-dispatch table keyed by type, resolved through the MRO.

    Parameters
    ----------
    name : str
        Human-readable purpose, used in the ``TypeError`` raised for
        unsupported objects (e.g. ``'plotting'``).
    """

    def __init__(self, name: str):
        self._name = name
        self._by_type = {}
        self._predicates = []

    def register(self, *types):
        """Decorator: register the function for one or more exact types.

        Subclasses inherit the handler through MRO lookup unless they
        register their own.
        """
        def deco(fn):
            for t in types:
                self._by_type[t] = fn
            return fn
        return deco

    def register_predicate(self, predicate):
        """Decorator: register a duck-typed fallback handler.

        Predicates run in registration order, only when no type in the
        object's MRO is registered.
        """
        def deco(fn):
            self._predicates.append((predicate, fn))
            return fn
        return deco

    def lookup(self, obj):
        """Return the handler for *obj*, or ``None`` if unsupported."""
        for cls in type(obj).__mro__:
            handler = self._by_type.get(cls)
            if handler is not None:
                return handler
        for predicate, handler in self._predicates:
            if predicate(obj):
                return handler
        return None

    def dispatch(self, obj, /, **kwargs):
        """Call the registered handler for *obj*.

        Raises
        ------
        TypeError
            If no registered type appears in the object's MRO and no
            predicate matches.
        """
        handler = self.lookup(obj)
        if handler is None:
            raise TypeError(
                f"Unsupported object type for {self._name}: {type(obj)}")
        return handler(obj, **kwargs)
