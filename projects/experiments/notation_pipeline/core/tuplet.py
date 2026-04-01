"""Tuplet detection from RhythmTree structure.

Handles both standard tuplets (non-binary child count, e.g. triplets)
and proportion tuplets (unequal weights whose sum is non-power-of-2,
e.g. (1,2,3,4) → 10:8 = 5:4).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

from ..models import NoteType, TupletBracket, NOTE_TYPE_DURATIONS
from .duration import classify_duration


def largest_power_of_2_leq(n: int) -> int:
    """Return the largest power of 2 <= n."""
    if n <= 0:
        return 0
    p = 1
    while p * 2 <= n:
        p *= 2
    return p


def _is_power_of_2(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _is_binary(dur: Fraction) -> bool:
    """OM ``is-binaire?``: numerator == 1 and denominator is power of 2."""
    return dur.numerator == 1 and _is_power_of_2(dur.denominator)


def _is_ternary(dur: Fraction) -> bool:
    """OM ``is-ternaire?``: numerator == 3 and denominator is binary."""
    return dur.numerator == 3 and _is_power_of_2(dur.denominator)


_BINARY_DENOM = {
    3: 2, 4: 4, 5: 4, 6: 4, 7: 4, 8: 8,
    9: 8, 10: 8, 11: 8, 12: 8, 13: 8, 14: 8,
    15: 16, 16: 16,
}

_TERNARY_DENOM = {
    2: 3, 3: 3, 4: 3,
    5: 6, 6: 6, 7: 6, 8: 6, 9: 6,
    10: 12, 11: 12, 12: 12, 13: 12, 14: 12, 15: 12, 16: 12, 17: 12,
}


def _bracketing_powers_of_2(n: int) -> tuple[int, int]:
    exp = 0
    while n >= 2 ** exp:
        exp += 1
    return (2 ** (exp - 1), 2 ** exp)


def _bracketing_powers_of_3(n: int) -> tuple[int, int]:
    exp = 3
    while n >= exp:
        exp *= 2
    return (exp // 2, exp)


def _beat_unit_from_meas(meas) -> Fraction:
    """Derive the beat unit from a time signature for binary/ternary context.

    Compound meters (numerator >= 6 and divisible by 3) have ternary beats
    (e.g. 6/8 → 3/8).  All others have binary beats (e.g. 3/4 → 1/4).
    """
    if meas is None:
        return Fraction(1, 4)
    num, den = meas.numerator, meas.denominator
    if num >= 6 and num % 3 == 0:
        return Fraction(3, den)
    return Fraction(1, den)


def find_tuplet_denom(num: int, beat_unit: Fraction) -> int:
    """Context-aware tuplet denominator, port of OM ``find-denom``.

    Parameters
    ----------
    num : int
        Actual number of children (or proportion sum).
    beat_unit : Fraction
        Beat unit derived from the time signature (used to detect
        binary/ternary context).
    """
    if _is_binary(beat_unit) or _is_power_of_2(beat_unit.numerator):
        if num in _BINARY_DENOM:
            return _BINARY_DENOM[num]
        lo, hi = _bracketing_powers_of_2(num)
        return hi if (num - lo) > (hi - num) else lo
    elif _is_ternary(beat_unit):
        if num in _TERNARY_DENOM:
            return _TERNARY_DENOM[num]
        lo, hi = _bracketing_powers_of_3(num)
        return hi if (num - lo) > (hi - num) else lo
    else:
        durtot_num = beat_unit.numerator
        if num == durtot_num or num + 1 == durtot_num:
            return durtot_num
        if num < durtot_num:
            return durtot_num
        lo, hi = _bracketing_powers_of_2(num)
        return hi if (num - lo) > (hi - num) else lo


def _node_ratio(node_id, rt, beat_unit: Fraction = Fraction(1, 4)) -> Optional[tuple[int, int]]:
    """Compute the candidate tuplet ratio (actual, normal) for a node.

    Uses OM-style context-aware denominator lookup (``find-denom``) to
    determine the "normal" count based on binary/ternary/other context.

    Returns None if the ratio is 1:1 (no tuplet needed).
    """
    children = list(rt.successors(node_id))
    N = len(children)
    if N <= 1:
        return None

    props = [int(abs(rt[c].get('proportion', 1))) for c in children]
    P = sum(props)

    if len(set(props)) == 1:
        M = find_tuplet_denom(N, beat_unit)
        if N == M:
            return None
        return (N, M)
    else:
        M_p = find_tuplet_denom(P, beat_unit)
        if P == M_p:
            return None
        return (P, M_p)


def _node_is_tuplet(node_id, rt, ancestor_scale: Fraction,
                    beat_unit: Fraction = Fraction(1, 4)) -> Optional[tuple[int, int]]:
    """Determine if a node should generate a tuplet bracket, given ancestor context.

    Returns (actual, normal) if this node IS a tuplet, else None.
    """
    ratio = _node_ratio(node_id, rt, beat_unit=beat_unit)
    if ratio is None:
        return None

    actual, normal = ratio

    # Check: are all children's durations already engravable with the ancestor scale?
    children = list(rt.successors(node_id))
    props = [int(abs(rt[c].get('proportion', 1))) for c in children]
    P = sum(props)
    parent_dur = abs(Fraction(rt[node_id].get('metric_duration', 0)))
    if parent_dur <= 0:
        return None

    eff_scale = ancestor_scale if ancestor_scale != Fraction(1) else None

    all_engravable_already = True
    for child in children:
        child_prop = abs(rt[child].get('proportion', 1))
        child_dur = parent_dur * Fraction(int(child_prop), P)
        if child_dur > 0 and classify_duration(child_dur, tuplet_scale=eff_scale) is None:
            all_engravable_already = False
            break

    if all_engravable_already:
        return None  # Ancestor scale already handles it

    return (actual, normal)


def _tuplet_inner_note_type(parent_dur: Fraction, M: int) -> Optional[NoteType]:
    """Determine the note type for M equal subdivisions of parent_dur.

    For example: parent_dur=1/2 (half note), M=2 -> quarter note.
    parent_dur=1/2, M=4 -> eighth note.
    """
    if parent_dur <= 0 or M <= 0:
        return None
    inner_dur = parent_dur / M
    result = classify_duration(inner_dur)
    if result is not None:
        return result[0]
    # If not directly engravable, find the nearest power-of-two note type
    for note_type, base_dur in NOTE_TYPE_DURATIONS.items():
        if base_dur <= inner_dur:
            return note_type
    return NoteType.N128TH


def collect_tuplets(rt) -> tuple[list[TupletBracket], dict[int, tuple[int, int]]]:
    """Walk the RhythmTree top-down and collect all tuplet contexts.

    Uses a depth-first pre-order traversal so that ancestor tuplet scales
    are known before processing descendants. This prevents false inner
    tuplets when an ancestor's proportion ratio already normalises leaves.

    Parameters
    ----------
    rt : RhythmTree
        The tree to inspect.

    Returns
    -------
    (list[TupletBracket], dict)
        Tuplet brackets found (ordered by tree traversal) and
        the internal cache mapping node_id -> (actual, normal).
    """
    beat_unit = _beat_unit_from_meas(rt.meas)

    tuplets: list[TupletBracket] = []
    _tuplet_cache: dict[int, tuple[int, int]] = {}

    def _ancestor_scale(node_id) -> Fraction:
        scale = Fraction(1)
        current = rt.parent(node_id)
        while current is not None:
            if current in _tuplet_cache:
                a, n = _tuplet_cache[current]
                scale *= Fraction(n, a)
            current = rt.parent(current)
        return scale

    def _visit(node_id):
        if rt.out_degree(node_id) == 0:
            return

        anc_scale = _ancestor_scale(node_id)
        result = _node_is_tuplet(node_id, rt, anc_scale, beat_unit=beat_unit)

        if result is not None:
            actual, normal = result
            _tuplet_cache[node_id] = (actual, normal)

            parent_dur = abs(Fraction(rt[node_id].get('metric_duration', 0)))
            inner_note_type = _tuplet_inner_note_type(parent_dur, normal)

            tuplets.append(TupletBracket(
                actual=actual,
                normal=normal,
                inner_note_type=inner_note_type,
                event_indices=[],
                group_node_id=node_id,
            ))

        # Recurse into children (DFS pre-order)
        for child in rt.successors(node_id):
            _visit(child)

    _visit(rt.root)
    return tuplets, _tuplet_cache


def get_tuplet_scale_for_leaf(leaf_node_id: int, rt, _tuplet_cache: Optional[dict] = None) -> Optional[Fraction]:
    """Compute the cumulative tuplet scaling factor for a leaf.

    The scaling factor is the product of (normal/actual) for each
    ancestor that creates a genuine tuplet context. This is used for
    duration classification inside tuplets.

    Returns None if the leaf is not inside any tuplet.
    """
    scale = Fraction(1, 1)
    has_tuplet = False

    beat_unit = _beat_unit_from_meas(rt.meas)

    current = rt.parent(leaf_node_id)
    while current is not None:
        ratio = _node_ratio(current, rt, beat_unit=beat_unit)
        if ratio is not None:
            actual, normal = ratio
            # We need to check if this ancestor actually SHOULD be a tuplet.
            # Recompute using the same logic as collect_tuplets.
            # For efficiency, callers can pass the cache from collect_tuplets.
            if _tuplet_cache is not None:
                if current in _tuplet_cache:
                    a, n = _tuplet_cache[current]
                    scale *= Fraction(n, a)
                    has_tuplet = True
            else:
                # Fallback: simple check without ancestor context
                # (used when cache not available)
                children = list(rt.successors(current))
                props = [abs(rt[c].get('proportion', 1)) for c in children]
                P = sum(props)
                parent_dur = abs(Fraction(rt[current].get('metric_duration', 0)))
                if parent_dur > 0:
                    any_non_engravable = False
                    for child in children:
                        cp = abs(rt[child].get('proportion', 1))
                        cd = parent_dur * Fraction(cp, P)
                        if cd > 0 and classify_duration(cd) is None:
                            any_non_engravable = True
                            break
                    if any_non_engravable:
                        scale *= Fraction(normal, actual)
                        has_tuplet = True
        current = rt.parent(current)

    return scale if has_tuplet else None
