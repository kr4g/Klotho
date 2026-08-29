"""Seed coercion for every random draw in Klotho.

This module holds the single definition of :func:`_coerce_rng`. It was
duplicated in five modules across ``utils``, ``topos`` and ``tonos`` — three
naming the parameter ``seed`` and two naming it ``rng`` — with no behavioural
difference between the copies. Consolidating them removes the standing risk
that one copy drifts and silently changes the draws in one subpackage only.

It deliberately imports nothing from Klotho, so any module may import it
without regard to package initialisation order.
"""

import random as _random

__all__ = []


def _coerce_rng(seed):
    """Return a random source for ``seed``.

    ``None`` (or the :mod:`random` module itself) draws from the global
    ``random`` stream, as these draws always have. A :class:`random.Random`
    is passed through unchanged. Any other value is used as a seed for a new
    :class:`random.Random`, so a reproducible draw does not reseed the
    caller's global stream as a side effect. Seeded output is unchanged from
    the module-level ``random`` functions, which are bound methods of one
    such instance.
    """
    if seed is None or seed is _random:
        return _random
    if isinstance(seed, _random.Random):
        return seed
    return _random.Random(seed)
