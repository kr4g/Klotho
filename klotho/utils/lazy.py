"""Lazy module loading for heavy optional dependencies.

``import klotho`` used to pay for matplotlib, plotly, and sklearn at
import time even though they are only needed when a plot is actually
drawn. A ``LazyModule`` defers the real import to first attribute
access while keeping call sites written as ordinary module usage
(``plt.figure(...)``).
"""
import importlib


class LazyModule:
    """Module proxy that imports the target on first attribute access."""

    __slots__ = ('_lazy_name', '_lazy_mod')

    def __init__(self, name):
        object.__setattr__(self, '_lazy_name', name)
        object.__setattr__(self, '_lazy_mod', None)

    def _lazy_load(self):
        mod = object.__getattribute__(self, '_lazy_mod')
        if mod is None:
            mod = importlib.import_module(
                object.__getattribute__(self, '_lazy_name'))
            object.__setattr__(self, '_lazy_mod', mod)
        return mod

    def __getattr__(self, attr):
        return getattr(self._lazy_load(), attr)

    def __dir__(self):
        return dir(self._lazy_load())

    def __repr__(self):
        name = object.__getattribute__(self, '_lazy_name')
        loaded = object.__getattribute__(self, '_lazy_mod') is not None
        return f"<LazyModule {name!r} ({'loaded' if loaded else 'not loaded'})>"
