import itertools
import math
import random
from fractions import Fraction
from typing import Union, List, Optional
import pandas as pd
import sympy as sp

from klotho.utils.algorithms.ratios import is_superparticular, superparticular_base, validate_primes
from klotho.utils.algorithms.basis import basis_matrix, monzo_from_ratio
from klotho.tonos.utils.intervals import ratio_to_cents, fold_cents_symmetric
from klotho.tonos.utils.interval_normalization import equave_reduce

__all__ = [
    'find_generator_basis',
]


def _ratio_from_exps(exps: List[int], primes: List[int]) -> Fraction:
    """Convert prime exponents to a ratio."""
    numerator = 1
    denominator = 1
    for e, p in zip(exps, primes):
        e = int(e)
        if e > 0:
            numerator *= p ** e
        elif e < 0:
            denominator *= p ** (-e)
    return Fraction(numerator, denominator)


def _octave_reduce_exps(
    exps: List[int], 
    primes: List[int], 
    lo: Fraction = Fraction(1, 1), 
    hi: Fraction = Fraction(2, 1)
) -> tuple:
    """Octave-reduce a ratio (by adjusting its 2-exponent) into [lo, hi)."""
    if 2 not in primes:
        raise ValueError("octave reduction requires prime 2 to be present in primes")
    
    i2 = primes.index(2)
    exps = list(map(int, exps))
    r = _ratio_from_exps(exps, primes)
    
    if r <= 0:
        raise ValueError("ratio must be positive")
    
    two = Fraction(2, 1)
    while r >= hi:
        exps[i2] -= 1
        r /= two
    while r < lo:
        exps[i2] += 1
        r *= two
    
    return tuple(exps), r


def _pow_curve(x: float, curve: float) -> float:
    """Apply power curve transformation."""
    if curve == 1.0:
        return x
    return x ** curve


def _generator_complexity(
    ratio: Fraction, 
    monzo: sp.Matrix,
    size_weight: float = 1.0,
    size_curve: float = 1.0,
    monzo_weight: float = 0.15,
    monzo_curve: float = 1.0
) -> float:
    """Compute complexity/simplicity score for a single generator."""
    p, q = ratio.numerator, ratio.denominator
    size = math.log2(p) + math.log2(q)
    l1 = sum(abs(int(v)) for v in monzo)
    return size_weight * _pow_curve(size, size_curve) + monzo_weight * _pow_curve(l1, monzo_curve)


def _build_candidates(
    primes: List[int],
    exp_bound: int,
    max_int: int,
    octave_reduce: bool,
    ratio_lo: Fraction,
    ratio_hi: Fraction,
    candidate_cap: int,
    include_octave: bool,
    size_weight: float,
    size_curve: float,
    monzo_weight: float,
    monzo_curve: float
) -> List[dict]:
    """Build the candidate pool of potential generator intervals."""
    n = len(primes)
    seen = set()
    candidates = []

    if include_octave and 2 in primes:
        r2 = Fraction(2, 1)
        m2 = monzo_from_ratio(r2, primes)
        candidates.append({
            "ratio": r2,
            "monzo": m2,
            "cents": ratio_to_cents(r2),
        })
        seen.add((2, 1))

    ranges = [range(-exp_bound, exp_bound + 1) for _ in primes]
    for exps in itertools.product(*ranges):
        if all(int(e) == 0 for e in exps):
            continue
        exps = tuple(int(e) for e in exps)
        
        if octave_reduce:
            if 2 not in primes:
                raise ValueError("octave_reduce=True but 2 not in primes")
            i2 = primes.index(2)
            exps0 = list(exps)
            exps0[i2] = 0
            exps_red, r = _octave_reduce_exps(tuple(exps0), primes, lo=ratio_lo, hi=ratio_hi)
        else:
            r = _ratio_from_exps(exps, primes)
            if not (ratio_lo <= r < ratio_hi):
                continue
            exps_red = exps

        if r.numerator > max_int or r.denominator > max_int:
            continue

        key = (r.numerator, r.denominator)
        if key in seen:
            continue
        seen.add(key)

        m = sp.Matrix(exps_red)
        candidates.append({
            "ratio": r,
            "monzo": m,
            "cents": ratio_to_cents(r),
        })

    for c in candidates:
        c["simplicity"] = _generator_complexity(
            c["ratio"], c["monzo"],
            size_weight=size_weight, size_curve=size_curve,
            monzo_weight=monzo_weight, monzo_curve=monzo_curve
        )

    candidates.sort(key=lambda d: (d["simplicity"], d["ratio"].numerator + d["ratio"].denominator))
    
    if candidate_cap > 0 and len(candidates) > candidate_cap:
        candidates = candidates[:candidate_cap]
    
    return candidates


def _score_basis(
    primes: List[int],
    generators: List[Fraction],
    A: sp.Matrix,
    size_weight: float,
    size_curve: float,
    monzo_weight: float,
    monzo_curve: float,
    superparticular_weight: float,
    superparticular_severity: float,
    superparticular_curve: float,
    conditioning_max_weight: float,
    conditioning_max_curve: float,
    conditioning_sum_weight: float,
    conditioning_sum_curve: float,
    target_cents: List[float],
    target_weight: float,
    target_scale_cents: float,
    target_curve: float,
    target_fold: bool,
    coverage: bool
) -> Optional[dict]:
    """Score a candidate basis. Returns None if invalid (non-unimodular)."""
    det = int(A.det())
    if det not in (1, -1):
        return None

    Ainv = A.inv()
    max_abs_inv = max(abs(int(x)) for x in Ainv)
    sum_abs_inv = sum(abs(int(x)) for x in Ainv)

    gens = []
    for g in generators:
        m = monzo_from_ratio(g, primes)
        gens.append({
            "ratio": g,
            "monzo": m,
            "cents": ratio_to_cents(g),
            "simplicity": _generator_complexity(
                g, m,
                size_weight=size_weight, size_curve=size_curve,
                monzo_weight=monzo_weight, monzo_curve=monzo_curve
            )
        })

    simp_sum = sum(g["simplicity"] for g in gens)

    sp_term = 0.0
    if superparticular_weight != 0.0:
        others = gens[1:] if (2 in primes and Fraction(2, 1) in generators) else gens
        for g in others:
            if is_superparticular(g["ratio"]):
                n0 = superparticular_base(g["ratio"])
                sp_term -= superparticular_weight * _pow_curve(1.0 / (float(n0) ** superparticular_severity), superparticular_curve)

    cond_term = 0.0
    cond_term += conditioning_max_weight * _pow_curve(float(max_abs_inv), conditioning_max_curve)
    cond_term += conditioning_sum_weight * _pow_curve(float(sum_abs_inv), conditioning_sum_curve)

    target_term = 0.0
    if target_cents and target_weight != 0.0:
        others = gens[1:] if (2 in primes and Fraction(2, 1) in generators) else gens
        
        def proc_c(c):
            return fold_cents_symmetric(c) if target_fold else abs(c) % 1200.0
        
        cs = [proc_c(g["cents"]) for g in others]
        ts = [proc_c(t) for t in target_cents]
        
        if coverage:
            for t in ts:
                d = min(abs(c - t) for c in cs) if cs else float('inf')
                target_term += target_weight * _pow_curve(d / target_scale_cents, target_curve)
        else:
            for c in cs:
                d = min(abs(c - t) for t in ts) if ts else float('inf')
                target_term += target_weight * _pow_curve(d / target_scale_cents, target_curve)

    total = float(simp_sum) + float(cond_term) + float(target_term) + float(sp_term)

    return {
        "generators": [g for g in generators],
        "generator_cents": [ratio_to_cents(g) for g in generators],
        "score": total,
        "simplicity_sum": float(simp_sum),
        "conditioning_max": int(max_abs_inv),
        "conditioning_sum": int(sum_abs_inv),
        "superparticular_term": float(sp_term),
        "target_term": float(target_term),
        "conditioning_term": float(cond_term),
        "det": det,
        "A": A,
        "A_inv": Ainv,
    }


def find_generator_basis(
    primes: List[int],
    *,
    exp_bound: int = 3,
    max_int: int = 256,
    candidate_cap: int = 60,
    include_octave: bool = True,
    octave_reduce: bool = True,
    ratio_lo: Union[int, float, Fraction, str] = 1,
    ratio_hi: Union[int, float, Fraction, str] = 2,
    mode: str = "auto",
    random_samples: int = 50000,
    seed: int = 0,
    top_k: int = 20,
    size_weight: float = 1.0,
    size_curve: float = 1.0,
    monzo_weight: float = 0.15,
    monzo_curve: float = 1.0,
    superparticular_weight: float = 0.0,
    superparticular_severity: float = 1.0,
    superparticular_curve: float = 1.0,
    conditioning_max_weight: float = 0.20,
    conditioning_max_curve: float = 1.0,
    conditioning_sum_weight: float = 0.01,
    conditioning_sum_curve: float = 1.0,
    target_cents: Optional[List[float]] = None,
    target_weight: float = 0.0,
    target_scale_cents: float = 50.0,
    target_curve: float = 1.0,
    target_fold: bool = True,
    coverage: bool = True
) -> pd.DataFrame:
    """
    Find optimal generator bases for a prime-limit JI/EJI lattice.
    
    Searches for unimodular generator sets that span the same group as the
    prime basis, ranked by a configurable scoring function that balances
    simplicity, conditioning, superparticular preference, and target intervals.
    
    Parameters
    ----------
    primes : List[int]
        Ordered list of prime numbers defining the prime-limit group.
        Example: [2, 3, 5] for 5-limit, [2, 3, 5, 7] for 7-limit.
    
    Candidate Generation
    --------------------
    exp_bound : int, default 3
        Maximum absolute exponent per prime when generating candidates.
    max_int : int, default 256
        Maximum numerator/denominator allowed in candidate ratios.
    candidate_cap : int, default 60
        Maximum number of candidates to keep (after sorting by simplicity).
    include_octave : bool, default True
        Force 2/1 as the first generator (recommended for pitch-class lattices).
    octave_reduce : bool, default True
        Normalize candidates into [ratio_lo, ratio_hi) by adjusting powers of 2.
    ratio_lo : Fraction-like, default 1
        Lower bound for octave reduction range.
    ratio_hi : Fraction-like, default 2
        Upper bound for octave reduction range.
    
    Search Parameters
    -----------------
    mode : str, default "auto"
        Search strategy: "exhaustive", "random", or "auto".
        "auto" chooses exhaustive for small search spaces, random otherwise.
    random_samples : int, default 50000
        Number of random samples when mode="random".
    seed : int, default 0
        Random seed for reproducibility.
    top_k : int, default 20
        Number of top-scoring bases to return.
    
    Simplicity Scoring
    ------------------
    size_weight : float, default 1.0
        Weight for penalizing large numerator/denominator.
    size_curve : float, default 1.0
        Nonlinearity for size penalty (>1 harsher on large ratios).
    monzo_weight : float, default 0.15
        Weight for penalizing large prime exponents.
    monzo_curve : float, default 1.0
        Nonlinearity for monzo penalty.
    
    Superparticular Preference
    --------------------------
    superparticular_weight : float, default 0.0
        Bonus weight for superparticular generators (negative score contribution).
    superparticular_severity : float, default 1.0
        How strongly to prefer small-n superparticulars over large-n ones.
    superparticular_curve : float, default 1.0
        Nonlinearity for superparticular bonus.
    
    Conditioning Scoring
    --------------------
    conditioning_max_weight : float, default 0.20
        Weight for maximum absolute entry in A_inv.
    conditioning_max_curve : float, default 1.0
        Nonlinearity for max conditioning penalty.
    conditioning_sum_weight : float, default 0.01
        Weight for sum of absolute entries in A_inv.
    conditioning_sum_curve : float, default 1.0
        Nonlinearity for sum conditioning penalty.
    
    Target Interval Matching
    ------------------------
    target_cents : List[float], optional
        List of desired interval sizes in cents to bias toward.
    target_weight : float, default 0.0
        Weight for target matching penalty.
    target_scale_cents : float, default 50.0
        Scale factor for cents distance (smaller = harsher penalty).
    target_curve : float, default 1.0
        Nonlinearity for target penalty.
    target_fold : bool, default True
        If True, fold cents to [0, 600] (interval class equivalence).
    coverage : bool, default True
        If True, penalize for each target not covered by a generator.
        If False, penalize for each generator not near a target.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - generators: List of generator ratios (Fractions)
        - generator_cents: List of generator sizes in cents
        - score: Final composite score (lower is better)
        - simplicity_sum: Sum of generator simplicity terms
        - conditioning_max: Max absolute entry in A_inv
        - conditioning_sum: Sum of absolute entries in A_inv
        - superparticular_term: Superparticular bonus (negative)
        - target_term: Target cents penalty
        - conditioning_term: Conditioning penalty
        - det: Determinant (+/-1 for valid bases)
        - A: Basis matrix
        - A_inv: Inverse basis matrix
        
        Sorted by score (ascending). Use standard DataFrame methods to
        sort/filter by other columns.
    
    Examples
    --------
    Basic 5-limit search:
    
    >>> results = find_generator_basis([2, 3, 5])
    >>> results[['generators', 'score']].head()
    
    Targeting thirds with superparticular preference:
    
    >>> results = find_generator_basis(
    ...     [2, 3, 5],
    ...     target_cents=[315.64, 386.31],
    ...     target_weight=1.5,
    ...     superparticular_weight=2.0
    ... )
    
    7-limit with random search:
    
    >>> results = find_generator_basis(
    ...     [2, 3, 5, 7],
    ...     mode="random",
    ...     random_samples=60000,
    ...     seed=42,
    ...     top_k=10
    ... )
    
    Sort by conditioning instead of score:
    
    >>> results.sort_values('conditioning_max')
    """
    primes = validate_primes(primes)
    ratio_lo = Fraction(ratio_lo)
    ratio_hi = Fraction(ratio_hi)
    target_cents = target_cents or []
    
    n = len(primes)
    
    candidates = _build_candidates(
        primes=primes,
        exp_bound=exp_bound,
        max_int=max_int,
        octave_reduce=octave_reduce,
        ratio_lo=ratio_lo,
        ratio_hi=ratio_hi,
        candidate_cap=candidate_cap,
        include_octave=include_octave,
        size_weight=size_weight,
        size_curve=size_curve,
        monzo_weight=monzo_weight,
        monzo_curve=monzo_curve
    )
    
    include_oct = include_octave and (2 in primes)
    fixed = []
    pool = candidates
    
    if include_oct:
        r2 = Fraction(2, 1)
        if not any(c["ratio"] == r2 for c in candidates):
            raise ValueError("include_octave=True but octave generator not in candidate pool")
        fixed = [r2]
        pool = [c for c in candidates if c["ratio"] != r2]
    
    need = n - len(fixed)
    
    if candidate_cap > 0 and len(pool) > candidate_cap:
        pool = pool[:candidate_cap]
    
    if mode == "auto":
        mode = "exhaustive" if (need <= 3 and len(pool) <= 80) else "random"
    
    results = []
    
    def emit(chosen):
        gens = fixed + [c["ratio"] for c in chosen]
        A = basis_matrix(primes, gens)
        scored = _score_basis(
            primes=primes,
            generators=gens,
            A=A,
            size_weight=size_weight,
            size_curve=size_curve,
            monzo_weight=monzo_weight,
            monzo_curve=monzo_curve,
            superparticular_weight=superparticular_weight,
            superparticular_severity=superparticular_severity,
            superparticular_curve=superparticular_curve,
            conditioning_max_weight=conditioning_max_weight,
            conditioning_max_curve=conditioning_max_curve,
            conditioning_sum_weight=conditioning_sum_weight,
            conditioning_sum_curve=conditioning_sum_curve,
            target_cents=target_cents,
            target_weight=target_weight,
            target_scale_cents=target_scale_cents,
            target_curve=target_curve,
            target_fold=target_fold,
            coverage=coverage
        )
        if scored is not None:
            results.append(scored)
    
    if need < 0:
        raise ValueError("need < 0; check include_octave vs primes dimension")
    
    if need == 0:
        emit([])
    elif mode == "exhaustive":
        for chosen in itertools.combinations(pool, need):
            emit(chosen)
    elif mode == "random":
        random.seed(seed)
        for _ in range(random_samples):
            if len(pool) >= need:
                chosen = random.sample(pool, need)
                emit(chosen)
    else:
        raise ValueError("mode must be one of: auto, exhaustive, random")
    
    results.sort(key=lambda r: (r["score"], abs(r["det"]), r["conditioning_max"], r["simplicity_sum"]))
    results = results[:top_k]
    
    return pd.DataFrame(results)
