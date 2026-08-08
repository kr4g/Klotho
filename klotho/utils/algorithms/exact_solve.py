"""Exact rational linear solving with a precomputed elimination transform.

Replaces per-query ``sympy.linsolve`` in ratio->coordinate lookups (the
generator matrix is fixed per lattice; only the right-hand side varies —
sympy cost was ~14.5ms per queried ratio). The transform is computed once
with Fraction Gauss-Jordan elimination on ``[A | I]``; each solve is then
a Fraction matrix-vector multiply plus consistency checks.
"""
from fractions import Fraction

__all__ = ['precompute_exact_solver', 'solve_exact']


def precompute_exact_solver(rows):
    """Precompute the elimination transform for matrix *rows* (m x n).

    Returns an opaque state dict for :func:`solve_exact`.
    """
    m = len(rows)
    n = len(rows[0]) if m else 0
    A = [[Fraction(v) for v in row]
         + [Fraction(1) if i == j else Fraction(0) for j in range(m)]
         for i, row in enumerate(rows)]
    pivots = []
    r = 0
    for c in range(n):
        pr = next((i for i in range(r, m) if A[i][c] != 0), None)
        if pr is None:
            continue
        A[r], A[pr] = A[pr], A[r]
        pv = A[r][c]
        A[r] = [v / pv for v in A[r]]
        for i in range(m):
            if i != r and A[i][c] != 0:
                f = A[i][c]
                A[i] = [a - f * b for a, b in zip(A[i], A[r])]
        pivots.append(c)
        r += 1
        if r == m:
            break
    rank = r
    return {
        'n': n,
        'pivots': tuple(pivots),
        'free_cols': tuple(c for c in range(n) if c not in pivots),
        'T_sol': [row[n:] for row in A[:rank]],
        'T_chk': [row[n:] for row in A[rank:]],
    }


def solve_exact(state, rhs):
    """Solve ``A y = rhs`` for the precomputed *state*.

    Returns ``('inconsistent', None)`` when no solution exists,
    ``('non_unique', None)`` when free variables remain, else
    ``('ok', [Fraction, ...])`` with the length-n solution vector.
    """
    for row in state['T_chk']:
        if sum(t * x for t, x in zip(row, rhs) if x) != 0:
            return ('inconsistent', None)
    if state['free_cols']:
        return ('non_unique', None)
    y = [Fraction(0)] * state['n']
    for k, c in enumerate(state['pivots']):
        y[c] = sum(t * x for t, x in zip(state['T_sol'][k], rhs) if x)
    return ('ok', y)
