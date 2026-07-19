"""Chord analysis utilities for just-intonation collections."""
from fractions import Fraction

__all__ = ['root_index', 'chord_root']


def _strip_factor(n, p):
    while p > 1 and n % p == 0:
        n //= p
    return n


def root_index(degrees, equave=2):
    """
    Index of the degree that best explains the others as overtones.

    Each candidate root is scored by measuring every other degree as an
    interval above it and summing the interval's reduced denominator with
    equave factors stripped — the denominator is 1 exactly when that note
    is an (equave-displaced) overtone of the candidate. The candidate with
    the lowest total is the *otonal root*: inversions of an otonal chord
    resolve to the same tone (e.g. ``[1, 6/5, 8/5]`` — a major triad in
    first inversion — roots on ``8/5``, not on ``1``). Purely utonal
    chords (like just minor triads) have no true otonal root; the metric
    then picks the tone requiring the least stretch, ties going to the
    earliest degree.

    Parameters
    ----------
    degrees : iterable of int, str, or Fraction
        Rational chord degrees (JI). Floats are rejected.
    equave : int, optional
        Equivalence interval whose factors are ignored (default 2).

    Returns
    -------
    int
        Index into *degrees* of the root.
    """
    ratios = []
    for d in degrees:
        if isinstance(d, float):
            raise TypeError(
                "root_index requires rational degrees (JI); got a float. "
                "Convert cents-based material to ratios first."
            )
        ratios.append(Fraction(d))
    if not ratios:
        raise ValueError("degrees must not be empty")
    equave = int(equave)

    best_index = 0
    best_score = None
    for i, candidate in enumerate(ratios):
        score = 0
        for j, ratio in enumerate(ratios):
            if j == i:
                continue
            interval = ratio / candidate
            score += _strip_factor(interval.denominator, equave)
        if best_score is None or score < best_score:
            best_index = i
            best_score = score
    return best_index


def chord_root(degrees, equave=2):
    """
    The otonal root of a chord, as a Fraction.

    Convenience wrapper around :func:`root_index`.

    Parameters
    ----------
    degrees : iterable of int, str, or Fraction
        Rational chord degrees (JI).
    equave : int, optional
        Equivalence interval whose factors are ignored (default 2).

    Returns
    -------
    Fraction
        The degree at the root index.
    """
    items = list(degrees)
    return Fraction(items[root_index(items, equave=equave)])
