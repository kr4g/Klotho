"""
Procedural generation of polyominoes (2D) and polycubes (3D+) on integer lattices.

A *shape* is a tuple of integer coordinate tuples, sorted and normalized so its
minimum corner sits at the origin. Shapes in this form are directly usable as
node groups for ``plot(lattice, shape=...)`` and ``lattice.chord(group)``.

Three equivalence classes are supported:

- ``'fixed'``: shapes are distinct under translation only.
- ``'one-sided'``: shapes are distinct up to rotation (mirror images distinct) —
  the Tetris convention (7 tetrominoes, 8 tetracubes).
- ``'free'``: shapes are distinct up to rotation and reflection
  (5 tetrominoes, 7 tetracubes).
"""
import colorsys
import hashlib
from functools import lru_cache
from itertools import permutations, product

__all__ = [
    'Shape', 'polyominoes', 'normalize', 'translate', 'rotations',
    'center', 'fits', 'placements', 'overlap', 'contact',
]

_KINDS = ('fixed', 'one-sided', 'free')


def _perm_parity(perm):
    parity = 1
    seen = [False] * len(perm)
    for i in range(len(perm)):
        if seen[i]:
            continue
        j = i
        length = 0
        while not seen[j]:
            seen[j] = True
            j = perm[j]
            length += 1
        if length % 2 == 0:
            parity = -parity
    return parity


def _orientation_group(dims, reflections=False):
    """Signed permutations of the axes; det=+1 subgroup = rotations."""
    ops = []
    for perm in permutations(range(dims)):
        parity = _perm_parity(perm)
        for signs in product((1, -1), repeat=dims):
            det = parity
            for s in signs:
                det *= s
            if reflections or det == 1:
                ops.append((perm, signs))
    return ops


def _apply(op, cells):
    perm, signs = op
    return tuple(tuple(s * c[p] for p, s in zip(perm, signs)) for c in cells)


def _op_matrix(op):
    """Integer matrix form of a signed axis permutation (rows act on coords)."""
    perm, signs = op
    dims = len(perm)
    return tuple(
        tuple(signs[i] if perm[i] == j else 0 for j in range(dims))
        for i in range(dims)
    )


def _apply_matrix(matrix, cells):
    rows = [tuple(int(x) for x in row) for row in matrix]
    return tuple(
        tuple(sum(m * ci for m, ci in zip(row, c)) for row in rows)
        for c in cells
    )


class Shape(tuple):
    """
    A polyomino/polycube: an immutable, sorted tuple of integer cells.

    Behaves exactly like the plain tuple-of-coordinate-tuples used across
    Klotho (indexing, iteration, equality, hashing), and adds shape
    *identity*: a canonical form invariant under rotation and translation,
    and a stable ``color`` shared by every rotation and translation of the
    same one-sided shape (mirror images keep distinct colors, matching the
    Tetris convention). Plot functions recognize ``color`` on shape groups
    and use it instead of the cycling palette.
    """

    def __new__(cls, cells):
        return super().__new__(
            cls, sorted(tuple(int(x) for x in c) for c in cells)
        )

    @property
    def dims(self):
        """Number of lattice dimensions the cells live in."""
        return len(self[0]) if len(self) else 0

    @property
    def canonical(self):
        """The lexicographically smallest rotated+normalized form (one-sided identity)."""
        cached = getattr(self, '_canonical_cache', None)
        if cached is None:
            group = _orientation_group(self.dims)
            cached = min(normalize(_apply(op, normalize(self))) for op in group)
            self._canonical_cache = cached
        return cached

    @property
    def color(self):
        """Stable hex color derived from the canonical form.

        Shapes that appear in the one-sided enumeration of their size get
        evenly spaced hues (maximally distinct within a piece set); any
        other cell group falls back to a hashed hue.
        """
        cached = getattr(self, '_color_cache', None)
        if cached is None:
            cached = _shape_color(self.canonical, len(self), self.dims)
            self._color_cache = cached
        return cached


@lru_cache(maxsize=32)
def _one_sided_index_map(n, dims):
    """{canonical form: index} over the one-sided enumeration of size n."""
    forms = polyominoes(n, dims, 'one-sided')
    return {tuple(f): i for i, f in enumerate(forms)}, len(forms)


def _shape_color(canonical, n, dims):
    if 1 <= n <= 6 and 1 <= dims <= 3:
        index_map, count = _one_sided_index_map(n, dims)
        idx = index_map.get(tuple(canonical))
        if idx is not None:
            hue = idx / count
            r, g, b = colorsys.hsv_to_rgb(hue, 0.62, 0.95)
            return f'#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}'
    digest = hashlib.md5(repr(tuple(canonical)).encode()).hexdigest()
    hue = (int(digest[:8], 16) % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.55, 0.9)
    return f'#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}'


def normalize(cells):
    """
    Translate a shape so its minimum corner is at the origin and sort its cells.

    Parameters
    ----------
    cells : iterable of tuple of int
        Coordinate tuples (any translation, any order).

    Returns
    -------
    Shape
        The normalized shape.
    """
    cells = [tuple(c) for c in cells]
    dims = len(cells[0])
    mins = [min(c[i] for c in cells) for i in range(dims)]
    return Shape(
        tuple(ci - mi for ci, mi in zip(c, mins)) for c in cells
    )


def translate(cells, offset):
    """
    Translate a shape by an integer offset vector.

    Parameters
    ----------
    cells : iterable of tuple of int
        The shape to move.
    offset : tuple of int
        Per-axis displacement.

    Returns
    -------
    Shape
        The translated shape (sorted).
    """
    return Shape(
        tuple(ci + oi for ci, oi in zip(c, offset)) for c in cells
    )


def center(cells):
    """
    Translate a shape so its bounding box centers on the origin.

    Even-length extents land as close to center as an integer grid allows.

    Parameters
    ----------
    cells : iterable of tuple of int
        The shape to center.

    Returns
    -------
    Shape
        The centered shape.
    """
    s = normalize(cells)
    offset = tuple(
        -(max(c[i] for c in s) // 2) for i in range(len(s[0]))
    )
    return translate(s, offset)


def rotations(cells, reflections=False, group=None):
    """
    All distinct orientations of a shape, each normalized.

    Parameters
    ----------
    cells : iterable of tuple of int
        The shape to orient.
    reflections : bool, optional
        Include mirror images (default False: rotations only —
        4 in 2D, 24 in 3D). Ignored when *group* is given.
    group : iterable of matrix, optional
        Transform group to orbit under, as d×d integer matrices (rows act
        on coordinates). Defaults to the square/hyperoctahedral group of
        the shape's dimensionality; a lattice with different geometry
        supplies its own point group (see ``Lattice.symmetries``).

    Returns
    -------
    list of tuple of tuple of int
        Unique normalized orientations, sorted.
    """
    cells = normalize(cells)
    if group is None:
        dims = len(cells[0])
        ops = _orientation_group(dims, reflections)
        return sorted({normalize(_apply(op, cells)) for op in ops})
    return sorted({normalize(_apply_matrix(m, cells)) for m in group})


def _canonical(cells, group):
    return min(normalize(_apply(op, cells)) for op in group)


def polyominoes(n, dims=2, kind='one-sided'):
    """
    Generate all polyominoes (or polycubes) of ``n`` cells.

    Enumeration grows shapes cell by cell from a single seed, reducing each
    candidate to a canonical form under the symmetry group selected by *kind*.

    Parameters
    ----------
    n : int
        Number of cells per shape (n >= 1).
    dims : int, optional
        Lattice dimensionality (default 2; 3 gives polycubes).
    kind : str, optional
        ``'fixed'``, ``'one-sided'`` (default), or ``'free'``.

    Returns
    -------
    list of Shape
        Canonical shapes, deterministically sorted, each carrying a stable
        identity ``color``. E.g. ``polyominoes(4)`` returns the 7 Tetris
        tetrominoes; ``polyominoes(4, dims=3)`` returns the 8 tetracubes.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    if dims < 1:
        raise ValueError("dims must be >= 1")
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}, got {kind!r}")

    if kind == 'fixed':
        group = [(tuple(range(dims)), (1,) * dims)]
    else:
        group = _orientation_group(dims, reflections=(kind == 'free'))

    shapes = {((0,) * dims,)}
    for _ in range(n - 1):
        grown = set()
        for shape in shapes:
            occupied = set(shape)
            for cell in shape:
                for axis in range(dims):
                    for step in (1, -1):
                        neighbor = tuple(
                            ci + step if i == axis else ci
                            for i, ci in enumerate(cell)
                        )
                        if neighbor not in occupied:
                            grown.add(_canonical(tuple(shape) + (neighbor,), group))
        shapes = grown
    return [Shape(s) for s in sorted(shapes)]


def fits(cells, lattice):
    """
    Whether every cell of a placed shape is a valid coordinate of *lattice*.

    Parameters
    ----------
    cells : iterable of tuple of int
        A placed shape (absolute lattice coordinates).
    lattice : Lattice
        The board to test against.

    Returns
    -------
    bool
    """
    return all(tuple(c) in lattice for c in cells)


def placements(piece, lattice, orientations=True):
    """
    Every in-bounds placement of a piece on a lattice.

    Parameters
    ----------
    piece : iterable of tuple of int
        The shape to place (any translation; normalized internally).
    lattice : Lattice
        The board; its per-axis coordinate ranges bound the placements.
    orientations : bool, optional
        Try all rotations of the piece (default True); when False only the
        given orientation is translated.

    Returns
    -------
    list of tuple of tuple of int
        Placed shapes in absolute lattice coordinates.
    """
    piece = normalize(piece)
    dims = len(piece[0])
    if dims != lattice.dimensionality:
        raise ValueError(
            f"piece is {dims}D but lattice is {lattice.dimensionality}D"
        )
    oriented = rotations(piece) if orientations else [piece]
    axis_ranges = lattice._dims
    placed = []
    for shape in oriented:
        spans = [max(c[i] for c in shape) for i in range(dims)]
        offset_ranges = [
            range(r.start, r.stop - span)
            for r, span in zip(axis_ranges, spans)
        ]
        for offset in product(*offset_ranges):
            placed.append(translate(shape, offset))
    return placed


def overlap(a, b):
    """
    Number of cells two placed shapes have in common.

    Parameters
    ----------
    a, b : iterable of tuple of int

    Returns
    -------
    int
    """
    return len({tuple(c) for c in a} & {tuple(c) for c in b})


def contact(a, b):
    """
    Number of adjacent cell pairs (Manhattan distance 1) between two shapes.

    Shared cells do not count as contacts; only touching along a face does.

    Parameters
    ----------
    a, b : iterable of tuple of int

    Returns
    -------
    int
    """
    set_a = {tuple(c) for c in a}
    set_b = {tuple(c) for c in b}
    count = 0
    for cell in set_a:
        for axis in range(len(cell)):
            for step in (1, -1):
                neighbor = tuple(
                    ci + step if i == axis else ci
                    for i, ci in enumerate(cell)
                )
                if neighbor in set_b and neighbor not in set_a:
                    count += 1
    return count
