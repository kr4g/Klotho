"""
Late-bound parameter values.

A :class:`Bind` wraps a callable and rides the parameter-inheritance cascade
as a value: the Bind object itself is stored as the node's raw override and
inherits to descendants like any other value. Resolution happens at read
time, per reading node — so nodes created later (e.g. by ``subdivide``)
inherit the Bind and get fresh evaluations automatically, where a plain
callable would have been evaluated eagerly and frozen at set time.

Evaluations are memoized per ``(node, field)`` on the owning
CompositionalUnit, so stochastic functions are stable: existing nodes keep
their values across structural edits; only new nodes roll fresh ones.
"""

__all__ = ['Bind']


class Bind:
    """
    Marker for a pfield/mfield value that re-evaluates per reading node.

    Parameters
    ----------
    fn : callable
        Evaluated at read time. May take no arguments, or one argument —
        the node's ``DistributionContext`` (same context plain callables
        receive in ``set_pfields``).

    Examples
    --------
    >>> uc.set_pfields(node, freq=Bind(lambda c: c.mfields['chord']))
    """

    __slots__ = ('fn',)

    def __init__(self, fn):
        if not callable(fn):
            raise TypeError(f"Bind expects a callable, got {type(fn).__name__}")
        self.fn = fn

    @classmethod
    def mfield(cls, name, default=None, map=None):
        """
        A Bind that reads the node's mfield *name*.

        Parameters
        ----------
        name : str
            The mfield to read.
        default : optional
            Value when the node has no such mfield.
        map : callable, optional
            Applied to the mfield value — store a rich object once, lower
            it per pfield: ``Bind.mfield('chord', map=lambda v: v.freq)``.

        Examples
        --------
        >>> uc.root.set_pfields(freq=Bind.mfield('chord'))
        """
        if map is None:
            return cls(lambda c: c.mfields.get(name, default))
        return cls(lambda c: map(c.mfields.get(name, default)))

    @classmethod
    def index(cls, map=None):
        """
        A Bind that reads the node's position among the read set.

        Without *map*, resolves to the bare index. With *map*, resolves
        to ``map(index, total)`` — fades, pan spreads, per-node ramps:
        ``Bind.index(map=lambda i, n: i / max(n - 1, 1))``.
        """
        if map is None:
            return cls(lambda c: c.index)
        return cls(lambda c: map(c.index, c.total))

    def __repr__(self):
        name = getattr(self.fn, '__name__', None)
        return f"Bind({name})" if name and name != '<lambda>' else "Bind(<fn>)"
