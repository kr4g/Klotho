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

The read set a Bind sees is the leaf descendants of the node holding the raw
override, so where you store it decides what ``ctx.index``/``ctx.total``
mean. ``subdivide`` therefore does not copy a Bind down onto the nodes it
creates -- they inherit it from wherever it really lives, which is what keeps
the read set whole.
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

    __slots__ = ('fn', 'reads_selection')

    def __init__(self, fn, reads_selection=False):
        if not callable(fn):
            raise TypeError(f"Bind expects a callable, got {type(fn).__name__}")
        self.fn = fn
        #: True when the callable reads ``ctx.index``/``ctx.total``, which are
        #: meaningless unless the read set spans more than one node. Set by
        #: :meth:`index`; a hand-written Bind that reads them cannot be
        #: detected, so it keeps the old silent behaviour.
        self.reads_selection = reads_selection

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

        The read set is the leaf descendants of the node the Bind is stored
        on, so store it on the common ancestor of the nodes you want to
        spread across — usually ``uc.root``. Storing it directly on a leaf
        makes that leaf its own read set, so every leaf would read index 0 of
        1; that is refused rather than silently resolving to a constant.
        """
        if map is None:
            return cls(lambda c: c.index, reads_selection=True)
        return cls(lambda c: map(c.index, c.total), reads_selection=True)

    def __repr__(self):
        name = getattr(self.fn, '__name__', None)
        return f"Bind({name})" if name and name != '<lambda>' else "Bind(<fn>)"
