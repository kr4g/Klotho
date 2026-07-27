"""
Register bounds and voice leading for relative pitch collections.

:func:`fold` octave-displaces each degree of a chord until its sounding
pitch lies within a register window; :func:`voice_lead` connects a chord
sequence with assignment-based minimal total motion: for each transition
the equave displacements of the incoming chord's degrees are chosen by
solving an optimal-assignment problem against the previous sounded
voicing (in log-frequency space), rather than by independent per-degree
snapping. Both work uniformly over ratio- and cents-based collections
(all comparison happens in Hz; displacement happens in each chord's
native domain, so exact ``Fraction`` degrees stay exact).
"""

import math
from fractions import Fraction
from typing import Iterable, List, Optional, Union

from ..pitch import Pitch
from ..pitch.pitch_collections import RelativePitchCollection
from ..utils.interval_normalization import equave_reduce
from ..utils.intervals import _indigestibility_cached
from .chord import Voicing

__all__ = ['fold', 'voice_lead']

# Tolerance in equave-exponent space (~0.1 cents for an octave equave):
# Pitch frequencies are rounded, so boundary placements need slack.
_EPS = 1e-4

# Weights for the secondary cost terms, in log-frequency units (ln 2 = one
# octave). These are deliberately module constants, not API parameters.
_SPREAD_WEIGHT = 0.25     # non-cyclic (Voicing) spread-preservation penalty
_DOUBLING_WEIGHT = 0.15   # harmonic doubling-quality term (voices= mode)
_COMMON_TONE_BONUS = 1e-6

# Rational-inference table (cents-mode doubling scores): candidate ratios
# p/q in lowest terms with 1 <= p/q < 4 and p*q bounded, matched by cents
# with a Gaussian mistuning discount.
_TABLE_MAX_PRODUCT = 1000
_CENTS_SIGMA = 15.0
_CENTS_TOLERANCE = 30.0
_RATIO_TABLE = None  # lazy: sorted list of (cents, simplicity)


def _check_collection(collection, fn_name):
    from ..scales.scale import Scale
    if isinstance(collection, Scale):
        raise TypeError(
            f"{fn_name} does not accept a Scale (scale degrees are a gamut, "
            f"not a sonority); build a Chord or Voicing from its pitches first"
        )
    if not isinstance(collection, RelativePitchCollection):
        raise TypeError(
            f"{fn_name} requires a relative collection (Chord, Voicing, or "
            f"RelativePitchCollection); got {type(collection).__name__}"
        )


def _resolve_bound(bound, reference: Pitch, name: str) -> Optional[float]:
    """Resolve a register bound to Hz (relative bounds resolve against *reference*)."""
    from ..types import Frequency, Cent, Ratio
    if bound is None:
        return None
    if isinstance(bound, Pitch):
        return bound.freq
    if isinstance(bound, str):
        return Pitch(bound).freq
    if isinstance(bound, Frequency):
        return float(bound.magnitude)
    if isinstance(bound, Cent):
        return reference.freq * (2.0 ** (float(bound.magnitude) / 1200.0))
    if isinstance(bound, Ratio):
        return reference.freq * float(Fraction(bound.magnitude.item()))
    if isinstance(bound, (int, float)):
        raise TypeError(
            f"Bare number for '{name}' is ambiguous. Use a note name ('G3'), "
            f"a Pitch, frequency(hz), cent(c), or ratio('1/2')."
        )
    raise TypeError(f"Cannot interpret {name}={bound!r} as a register bound")


def _degree_hz(degree, mode: str, ref_hz: float) -> float:
    if mode == "cents":
        return ref_hz * (2.0 ** (float(degree) / 1200.0))
    return ref_hz * float(degree)


def _equave_factor(equave, mode: str) -> float:
    if mode == "cents":
        cents = equave if isinstance(equave, float) else 1200.0
        return 2.0 ** (cents / 1200.0)
    return float(equave)


def _displace(degree, k: int, equave, mode: str):
    if k == 0:
        return degree
    if mode == "cents":
        cents = equave if isinstance(equave, float) else 1200.0
        return float(degree) + k * cents
    ratio = equave if isinstance(equave, Fraction) else Fraction(2, 1)
    return degree * (ratio ** k)


def _clamp_k(hz: float, k: int, eq: float,
             lo: Optional[float], hi: Optional[float]) -> int:
    """Clamp a displacement so ``hz * eq**k`` lands inside ``[lo, hi]``.

    When the window is narrower than one equave and no placement fits, the
    nearest placement (smallest log-distance outside the window) wins.
    """
    log_eq = math.log(eq)
    k_lo = None if lo is None else math.ceil(math.log(lo / hz) / log_eq - _EPS)
    k_hi = None if hi is None else math.floor(math.log(hi / hz) / log_eq + _EPS)
    if k_lo is not None and k_hi is not None:
        if k_lo <= k_hi:
            return min(max(k, k_lo), k_hi)
        below = math.log(lo / (hz * eq ** k_hi))
        above = math.log((hz * eq ** k_lo) / hi)
        return k_hi if below <= above else k_lo
    if k_lo is not None:
        return max(k, k_lo)
    if k_hi is not None:
        return min(k, k_hi)
    return k


def _fold_degrees(collection, lo_hz, hi_hz):
    mode = collection._interval_type_mode
    ref_hz = collection.reference_pitch.freq
    eq = _equave_factor(collection.equave, mode)
    out = []
    for degree in collection._degrees:
        hz = _degree_hz(degree, mode, ref_hz)
        k = _clamp_k(hz, 0, eq, lo_hz, hi_hz)
        out.append(_displace(degree, k, collection.equave, mode))
    return out


def fold(collection, lo=None, hi=None) -> Voicing:
    """
    Octave-displace each degree until its pitch lies within ``[lo, hi]``.

    Displacement is by whole equaves of the collection. If the window is
    narrower than one equave and a degree cannot fit, the placement nearest
    the window is used.

    Parameters
    ----------
    collection : Chord, Voicing, or RelativePitchCollection
        The sonority to fold. ``Scale`` and absolute collections are
        rejected.
    lo, hi : optional
        Register bounds; either may be omitted. Each may be a note name
        (``'G3'``), a :class:`Pitch`, ``frequency(hz)`` (absolute), or
        ``cent(c)`` / ``ratio('1/2')`` (relative to the collection's
        reference pitch). Bare numbers are rejected as ambiguous.

    Returns
    -------
    Voicing
        The folded sonority (out-of-equave degrees are legal in a Voicing).

    Examples
    --------
    >>> fold(Chord(['1/1', '5/4', '3/2'], reference_pitch='C5'), lo='G3', hi='G4')
    """
    _check_collection(collection, 'fold')
    ref = collection.reference_pitch
    lo_hz = _resolve_bound(lo, ref, 'lo')
    hi_hz = _resolve_bound(hi, ref, 'hi')
    if lo_hz is not None and hi_hz is not None and lo_hz > hi_hz:
        raise ValueError(f"lo bound ({lo_hz:.2f} Hz) is above hi bound ({hi_hz:.2f} Hz)")
    degrees = _fold_degrees(collection, lo_hz, hi_hz)
    return Voicing(degrees, collection._interval_type_mode,
                   collection.equave, ref)


# ---------------------------------------------------------------------------
# Doubling quality (Barlow-derived interval simplicity)
# ---------------------------------------------------------------------------

def _bounded_simplicity(p: int, q: int) -> float:
    """Bounded Barlow simplicity of p/q: 1/(1 + xi(p) + xi(q)) in (0, 1]."""
    return 1.0 / (1.0 + _indigestibility_cached(p) + _indigestibility_cached(q))


def _ratio_table():
    """Sorted (cents, simplicity) candidates for rational inference."""
    global _RATIO_TABLE
    if _RATIO_TABLE is None:
        entries = []
        seen = set()
        q = 1
        while q * q <= _TABLE_MAX_PRODUCT * 4:
            for p in range(q, 4 * q):
                if p * q > _TABLE_MAX_PRODUCT:
                    break
                f = Fraction(p, q)
                if f in seen or not (1 <= f < 4):
                    continue
                seen.add(f)
                cents = 1200.0 * math.log2(p / q)
                entries.append((cents, _bounded_simplicity(f.numerator, f.denominator)))
            q += 1
        entries.sort()
        _RATIO_TABLE = entries
    return _RATIO_TABLE


def _cents_simplicity(cents: float) -> float:
    """Best-matching rational simplicity for an interval in cents.

    The nearest table candidate within ``_CENTS_TOLERANCE`` wins, its
    simplicity discounted by a Gaussian in the mistuning; no candidate
    means no harmonic preference (0.0).
    """
    import bisect
    table = _ratio_table()
    cents = abs(cents)
    lo_i = bisect.bisect_left(table, (cents - _CENTS_TOLERANCE, -1.0))
    hi_i = bisect.bisect_right(table, (cents + _CENTS_TOLERANCE, 2.0))
    best = 0.0
    for i in range(lo_i, hi_i):
        err = abs(table[i][0] - cents)
        if err <= _CENTS_TOLERANCE:
            score = table[i][1] * math.exp(-0.5 * (err / _CENTS_SIGMA) ** 2)
            best = max(best, score)
    return best


def _interval_class_simplicity(a, b, mode: str, equave, eq: float) -> float:
    """Simplicity of the interval class between two degrees of a collection."""
    if mode == "ratios" and isinstance(a, Fraction) and isinstance(b, Fraction):
        if a == 0 or b == 0:
            return 0.0
        iv = b / a if b >= a else a / b
        if isinstance(equave, Fraction) and equave > 1:
            iv = equave_reduce(iv, equave)
        return _bounded_simplicity(iv.numerator, iv.denominator)
    cents = abs(1200.0 * math.log2(
        _degree_hz(b, mode, 1.0) / _degree_hz(a, mode, 1.0)))
    eq_cents = 1200.0 * math.log2(eq)
    if eq_cents > 0:
        cents = cents % eq_cents
    return _cents_simplicity(cents)


def _doubling_scores(collection) -> List[float]:
    """Normalized doubling quality per degree (1.0 = best candidate).

    A degree's raw score is the summed Barlow-derived simplicity of its
    interval classes to every other member: the tone forming the simplest
    relations with the whole sonority is the most stable, hence the most
    natural doubling. For 4:5:6 this ranks root > fifth > third with no
    style flags; cents-mode chords go through rational inference.
    """
    degs = collection._degrees
    n = len(degs)
    if n <= 1:
        return [1.0] * n
    mode = collection._interval_type_mode
    eq = _equave_factor(collection.equave, mode)
    raw = []
    for i in range(n):
        total = 0.0
        for j in range(n):
            if i != j:
                total += _interval_class_simplicity(degs[i], degs[j], mode,
                                                    collection.equave, eq)
        raw.append(total)
    lo, hi = min(raw), max(raw)
    if hi - lo < 1e-12:
        return [1.0] * n
    return [(x - lo) / (hi - lo) for x in raw]


# ---------------------------------------------------------------------------
# Assignment-based voice leading
# ---------------------------------------------------------------------------

def _normalize_anchor(anchor, length: int) -> frozenset:
    if anchor is None:
        return frozenset()
    if isinstance(anchor, int):
        anchor = (anchor,)
    out = set()
    for a in anchor:
        a = int(a)
        idx = a + length if a < 0 else a
        if not 0 <= idx < length:
            raise IndexError(
                f"anchor index {a} out of range for a {length}-chord sequence")
        out.add(idx)
    return frozenset(out)


def _normalize_doubling(doubling, cardinality: int):
    """Return ('harmonic'|'nearest'|'explicit', indices or None)."""
    if doubling == 'harmonic':
        return 'harmonic', None
    if doubling == 'nearest':
        return 'nearest', None
    if isinstance(doubling, int):
        doubling = (doubling,)
    if isinstance(doubling, Iterable) and not isinstance(doubling, str):
        idx = []
        for d in doubling:
            d = int(d)
            i = d + cardinality if d < 0 else d
            if not 0 <= i < cardinality:
                raise IndexError(
                    f"doubling index {d} out of range for a "
                    f"{cardinality}-note chord")
            idx.append(i)
        if not idx:
            raise ValueError("doubling index list may not be empty")
        return 'explicit', idx
    raise ValueError(
        f"doubling must be 'harmonic', 'nearest', or member indices; "
        f"got {doubling!r}")


def _candidate_ks(hz: float, prev_ln: List[float], eq: float, log_eq: float,
                  lo_hz: Optional[float], hi_hz: Optional[float]) -> List[int]:
    """Legal equave displacements for one degree.

    With both bounds and a window at least one equave wide, the candidate
    set is exactly the displacements landing inside the window (bounds
    constrain the search; they are never applied as a post-hoc clamp,
    which is what destroyed minimal motion in the pre-10.13 algorithm).
    Otherwise candidates cluster around each previous voice and are
    clamped by whichever bounds exist.
    """
    ln_hz = math.log(hz)
    if lo_hz is not None and hi_hz is not None:
        k_lo = math.ceil(math.log(lo_hz / hz) / log_eq - _EPS)
        k_hi = math.floor(math.log(hi_hz / hz) / log_eq + _EPS)
        if k_lo <= k_hi:
            return list(range(k_lo, k_hi + 1))
    pool = set()
    for t_ln in prev_ln:
        base = round((t_ln - ln_hz) / log_eq)
        pool.update((base - 1, base, base + 1))
    if not pool:
        pool.add(0)
    return sorted({_clamp_k(hz, k, eq, lo_hz, hi_hz) for k in pool})


def _verbatim_degrees(collection):
    return list(collection._degrees)


def _realized_hz(degrees, mode, ref_hz):
    return sorted(_degree_hz(d, mode, ref_hz) for d in degrees)


def _extend_to_voices(degrees, collection, n_target: int,
                      lo_hz, hi_hz, mode: str, eq: float,
                      doubling_mode: str, doubling_idx):
    """Extend *degrees* to ``n_target`` voices by doubling (never moving).

    Doubles are placed one equave up when that stays under ``hi``, else
    one equave down when that stays over ``lo``, else in unison.
    """
    if len(degrees) >= n_target or not degrees:
        return list(degrees)
    order = list(range(len(degrees)))
    if doubling_mode == 'harmonic':
        scores = _doubling_scores(collection)
        order.sort(key=lambda i: (-scores[i], i))
    elif doubling_mode == 'explicit':
        order = list(doubling_idx)
    out = list(degrees)
    ref_hz = collection.reference_pitch.freq
    i = 0
    while len(out) < n_target:
        j = order[i % len(order)]
        i += 1
        base = degrees[j]
        hz = _degree_hz(base, mode, ref_hz)
        if hi_hz is None or hz * eq <= hi_hz * (1 + _EPS):
            k = 1
        elif lo_hz is None or hz / eq >= lo_hz * (1 - _EPS):
            k = -1
        else:
            k = 0
        out.append(_displace(base, k, collection.equave, mode))
    return out


def _assign(cost_rows):
    """Optimal assignment on an m x n cost matrix (rows=degrees).

    Returns a dict row -> col covering min(m, n) rows.
    """
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    C = np.asarray(cost_rows, dtype=float)
    rows, cols = linear_sum_assignment(C)
    return dict(zip(rows.tolist(), cols.tolist()))


def _transition(collection, prev_hz, lo, hi, *, drift=None,
                voices=None, doubling_mode='harmonic', doubling_idx=None):
    """Voice-lead one chord against the previous sounded pitches.

    Returns the displaced degree list (native domain).
    """
    ref = collection.reference_pitch
    lo_hz = _resolve_bound(lo, ref, 'lo')
    hi_hz = _resolve_bound(hi, ref, 'hi')
    if lo_hz is not None and hi_hz is not None and lo_hz > hi_hz:
        raise ValueError(f"lo bound ({lo_hz:.2f} Hz) is above hi bound ({hi_hz:.2f} Hz)")

    mode = collection._interval_type_mode
    ref_hz = ref.freq
    eq = _equave_factor(collection.equave, mode)
    log_eq = math.log(eq)
    degrees = list(collection._degrees)
    m = len(degrees)
    n = len(prev_hz)
    if m == 0:
        return []
    if n == 0:
        return _fold_degrees(collection, lo_hz, hi_hz)

    # Between anchors, motion is measured inside a register frame that
    # drifts by the per-step share of the anchors' centroid gap: minimal
    # motion relative to the drifting frame IS the evenly distributed
    # climb, so no weight tuning is involved. With no anchors the frame
    # is stationary and this is ordinary motion against the previous
    # voicing.
    frame_shift = drift if drift is not None else 0.0
    prev_ln = [math.log(p) + frame_shift for p in prev_hz]
    hzs = [_degree_hz(d, mode, ref_hz) for d in degrees]
    ln_hzs = [math.log(h) for h in hzs]
    cand = [_candidate_ks(h, prev_ln, eq, log_eq, lo_hz, hi_hz) for h in hzs]

    cyclic = bool(getattr(collection, '_equave_cyclic', False))
    if cyclic:
        k_bases = [None]
    else:
        mu_prev = sum(prev_ln) / n
        mu_nat = sum(ln_hzs) / m
        b = (mu_prev - mu_nat) / log_eq
        k_bases = sorted({math.floor(b), round(b), math.ceil(b)})

    best = None
    for k_base in k_bases:
        # cost[j][i] and the displacement that achieves it
        cost = [[0.0] * n for _ in range(m)]
        kmemo = [[0] * n for _ in range(m)]
        for j in range(m):
            for i in range(n):
                c_best, k_best = None, 0
                for k in cand[j]:
                    x = ln_hzs[j] + k * log_eq
                    motion = abs(x - prev_ln[i])
                    c = motion
                    if motion < 1e-9:
                        c -= _COMMON_TONE_BONUS
                    if k_base is not None:
                        c += _SPREAD_WEIGHT * abs(k - k_base) * log_eq
                    if c_best is None or c < c_best:
                        c_best, k_best = c, k
                cost[j][i] = c_best
                kmemo[j][i] = k_best

        assignment = _assign(cost)
        chosen = {}       # degree index -> k
        total = 0.0
        for j, i in assignment.items():
            chosen[j] = kmemo[j][i]
            total += cost[j][i]

        extras = []       # (degree index, k) doublings / entering voices
        if voices is None:
            for j in range(m):
                if j not in chosen:
                    # entering voice: global cheapest placement
                    i = min(range(n), key=lambda i_: cost[j][i_])
                    chosen[j] = kmemo[j][i]
                    total += cost[j][i]
        else:
            free_cols = [i for i in range(n) if i not in assignment.values()]
            if doubling_mode == 'harmonic':
                scores = _doubling_scores(collection)
                pen = [_DOUBLING_WEIGHT * (1.0 - s) for s in scores]
            else:
                pen = [0.0] * m
            pool = doubling_idx if doubling_mode == 'explicit' else range(m)
            for i in free_cols:
                j = min(pool, key=lambda j_: cost[j_][i] + pen[j_])
                extras.append((j, kmemo[j][i]))
                total += cost[j][i] + pen[j]

        if best is None or total < best[0]:
            best = (total, chosen, extras)

    _, chosen, extras = best
    out = [_displace(degrees[j], chosen[j], collection.equave, mode)
           for j in range(m)]
    out.extend(_displace(degrees[j], k, collection.equave, mode)
               for j, k in extras)
    return out


def voice_lead(chords, lo=None, hi=None, *,
               voices: Optional[int] = None,
               anchor: Union[int, Iterable[int], None] = None,
               doubling: Union[str, int, Iterable[int]] = 'harmonic') -> List[Voicing]:
    """
    Voice-lead a chord sequence with assignment-based minimal total motion.

    The first chord keeps its own voicing (folded into bounds if given).
    For each subsequent chord, every degree's candidate equave placements
    inside ``[lo, hi]`` are scored against the previous sounded voicing in
    log-frequency space, and an optimal assignment (no two voices chasing
    the same predecessor) picks the placements with the smallest total
    motion. Common tones are held; register bounds constrain the search
    itself rather than clamping its result.

    Equave-cyclic collections (:class:`Chord`) give every voice free
    register choice. Non-cyclic collections (:class:`Voicing`) carry
    composer-chosen registers, so their internal spread is softly
    preserved: placements deviating from a block transposition of the
    written voicing pay a small penalty and win only when the motion
    saved outweighs it.

    Mixed ratio- and cents-based sequences work uniformly: comparison
    happens in Hz and displacement happens on each chord's own degrees
    (exact ``Fraction`` arithmetic is preserved).

    Parameters
    ----------
    chords : iterable of Chord, Voicing, or RelativePitchCollection
        The progression (a :class:`ChordSequence` works directly).
    lo, hi : optional
        Register bounds, as in :func:`fold`.
    voices : int or None, optional
        Lock the texture to a fixed voice count. Chords with fewer
        members are completed through doublings (added, never moved);
        a chord with more members than ``voices`` raises ``ValueError``.
        The result preserves duplicate pitches (unison doublings).
    anchor : int or iterable of int, optional
        Indices of chords that pass through **verbatim** (a Voicing keeps
        its exact registers; a Chord sounds its literal pitches). Anchors
        are exempt from ``lo``/``hi`` — an anchored chord is a hard
        contract; pre-``fold`` it explicitly if you want it bounded.
        Free chords voice-lead smoothly into and out of anchors, with the
        registral gap between consecutive anchors distributed evenly
        across the chords between them. Negative indices count from the
        end.
    doubling : {'harmonic', 'nearest'} or int or iterable of int, optional
        How ``voices=`` picks which member to double. ``'harmonic'``
        (default) prefers the member forming the simplest Barlow-derived
        interval classes with the rest of the sonority (for 4:5:6 this
        doubles the root — the practice emerges from the arithmetic, not
        from style rules), trading off against motion. ``'nearest'`` uses
        pure motion. Explicit indices restrict doubling to those members.

    Returns
    -------
    list of Voicing
    """
    chords = list(chords)
    if not chords:
        return []
    for c in chords:
        _check_collection(c, 'voice_lead')

    anchors = _normalize_anchor(anchor, len(chords))
    if voices is not None:
        voices = int(voices)
        if voices < 1:
            raise ValueError(f"voices must be a positive integer, got {voices}")
        for idx, c in enumerate(chords):
            if len(c._degrees) > voices:
                raise ValueError(
                    f"chord {idx} has {len(c._degrees)} members, more than "
                    f"voices={voices}")

    max_card = max((len(c._degrees) for c in chords), default=0)
    doubling_mode, doubling_idx_raw = _normalize_doubling(doubling, max(max_card, 1))

    # Anchor centroids (verbatim, so computable upfront) for the drift bias.
    anchor_centroid = {}
    for idx in anchors:
        c = chords[idx]
        hzs = _realized_hz(c._degrees, c._interval_type_mode,
                           c.reference_pitch.freq)
        if hzs:
            anchor_centroid[idx] = sum(math.log(h) for h in hzs) / len(hzs)
    sorted_anchors = sorted(anchors)

    def _drift_for(i):
        """Per-step centroid drift for the transition into chord i."""
        left = max((a for a in sorted_anchors if a < i), default=None)
        right = min((a for a in sorted_anchors if a >= i), default=None)
        if left is None or right is None or right == left:
            return None
        if left not in anchor_centroid or right not in anchor_centroid:
            return None
        return (anchor_centroid[right] - anchor_centroid[left]) / (right - left)

    def _clamp_doubling_idx(c):
        if doubling_mode != 'explicit':
            return None
        card = len(c._degrees)
        return [i for i in doubling_idx_raw if i < card] or list(range(card))

    result = []
    prev_hz: List[float] = []
    for i, c in enumerate(chords):
        mode = c._interval_type_mode
        eq = _equave_factor(c.equave, mode)
        ref = c.reference_pitch
        d_idx = _clamp_doubling_idx(c)
        if i in anchors:
            degrees = _verbatim_degrees(c)
            if voices is not None:
                degrees = _extend_to_voices(degrees, c, voices, None, None,
                                            mode, eq, doubling_mode, d_idx)
        elif not prev_hz:
            lo_hz = _resolve_bound(lo, ref, 'lo')
            hi_hz = _resolve_bound(hi, ref, 'hi')
            if lo_hz is not None and hi_hz is not None and lo_hz > hi_hz:
                raise ValueError(
                    f"lo bound ({lo_hz:.2f} Hz) is above hi bound ({hi_hz:.2f} Hz)")
            degrees = _fold_degrees(c, lo_hz, hi_hz)
            if voices is not None:
                degrees = _extend_to_voices(degrees, c, voices, lo_hz, hi_hz,
                                            mode, eq, doubling_mode, d_idx)
        else:
            degrees = _transition(c, prev_hz, lo, hi, drift=_drift_for(i),
                                  voices=voices, doubling_mode=doubling_mode,
                                  doubling_idx=d_idx)

        voicing = Voicing(degrees, mode, c.equave, ref, dedupe=False)
        result.append(voicing)
        sounded = sorted(p.freq for p in voicing.pitches)
        if sounded:
            prev_hz = sounded

    return result
