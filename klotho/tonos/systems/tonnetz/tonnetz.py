from fractions import Fraction
from typing import Iterable, List, Tuple, Union

from klotho.topos.shapes.polyominoes import Shape
from ..tone_lattices.tone_lattices import ToneLattice

__all__ = ['Tonnetz']


# 60-degree rotation and the mirror fixing the first axis, in axial
# coordinates. Together they generate the D6 point group of the
# triangular lattice (matrices A with A^T G A = G for the oblique
# metric G = [[1, 1/2], [1/2, 1]]).
_R60 = ((0, -1), (1, 1))
_F = ((1, 1), (0, -1))
_IDENTITY = ((1, 0), (0, 1))


def _matmul(a, b):
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2))
        for i in range(2)
    )


def _matvec(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(2)) for i in range(2))


def _affine(m, cells, about):
    p, q = about
    return Shape(
        tuple(x + o for x, o in zip(_matvec(m, (c[0] - p, c[1] - q)), (p, q)))
        for c in cells
    )


def _primitive(v):
    from math import gcd
    g = gcd(abs(v[0]), abs(v[1]))
    if g == 0:
        raise ValueError("direction must be a nonzero vector")
    return (v[0] // g, v[1] // g)


class Tonnetz(ToneLattice):
    """
    A Tonnetz: a two-generator tone lattice with triangular geometry.

    Three layers, kept distinct:

    1. **Abstract lattice** — axial coordinates ``(q, r)`` in the integer
       plane, with *triangular* adjacency: three unit interval directions
       arise from only two independent generators (the lattice has rank 2)::

           e1 = (1, 0)            first generator   (default 3/2)
           e2 = (0, 1)            second generator  (default 5/4)
           e3 = e1 - e2 = (1, -1) derived direction (default 6/5)

       Every interior vertex has six neighbors (±e1, ±e2, ±e3). Any two
       of the three directions generate the lattice; the third is always
       their quotient. See :attr:`directions`.
    2. **Musical labeling** — inherited from :class:`ToneLattice`:
       ``(q, r) -> g1**q * g2**r``, equave-reduced to exact fractions.
       Because labels are exact, progressions that return to the "same"
       chord after a cycle of moves may land a comma away — the drift is
       visible rather than hidden. (An equal-tempered labeling
       ``(a*q + b*r) mod N`` would quotient the lattice onto a torus and
       close such cycles; that labeling mode is intentionally not
       implemented here.)
    3. **Euclidean embedding** — for display and geometry only: the
       isometric map ``x = q + r/2, y = (sqrt(3)/2) r`` renders the
       lattice as equilateral triangles. Its point group is D6 (six
       rotations, six mirrors), exposed by :meth:`symmetries` — *not*
       the square-lattice group that :func:`~klotho.topos.shapes.rotations`
       uses by default.

    Shapes on a Tonnetz are ordinary coordinate groups
    (:class:`~klotho.topos.shapes.Shape` or any iterable of ``(q, r)``
    tuples): a triad is just a three-cell shape. :meth:`reflect`,
    :meth:`rotate`, and :func:`~klotho.topos.shapes.translate` transform
    any shape; ``chord(shape)`` sounds it. :meth:`flip` performs the
    named triangle moves (``'P'``, ``'R'``, ``'L'`` — reflections across
    a shape's own fifth, major-third, and minor-third edges — and
    ``'S'``, the half-turn about the third vertex); :meth:`perform`
    folds a whole instruction list into a shape history.

    Parameters
    ----------
    generators : iterable of int, Fraction, or str, optional
        Exactly two independent interval generators (after equave-axis
        dropping). Default ``('3/2', '5/4')``.
    resolution : int or list of int, optional
        Per-axis coordinate bounds. Default 6.
    bipolar : bool, optional
        Whether coordinates span negative values. Default True.
    equave_reduce : bool, optional
        Whether represented ratios are equave-reduced. Default True.
    equave : int, Fraction, or str, optional
        Interval of equivalence. Default 2.
    """

    # Hooks consumed by the plotting layer: neighbor offsets defining the
    # board's edge families, the preferred plot layout, and the default
    # shape-coloring policy (every orientation its own color).
    _edge_offsets = ((1, 0), (0, 1), (1, -1))
    _plot_layout = 'tonnetz'
    _plot_shape_color = 'fixed'

    # Letter shorthands for the triad moves, named for the default
    # fifths-by-thirds configuration: each maps to the edge direction held
    # during the flip ('S' is special-cased: it holds a vertex instead).
    _TRIAD_FLIPS = {'P': (1, 0), 'R': (0, 1), 'L': (1, -1)}
    _TRIAD_UP = ((0, 0), (0, 1), (1, 0))
    _TRIAD_DOWN = ((0, 1), (1, 0), (1, 1))

    def __init__(
        self,
        generators: Iterable[Union[int, Fraction, str]] = ('3/2', '5/4'),
        resolution: Union[int, List[int]] = 6,
        bipolar: bool = True,
        equave_reduce: bool = True,
        equave: Union[int, Fraction, str] = 2,
    ):
        equave_fraction = self._parse_equave(equave)
        parsed_generators = [self._parse_generator(g) for g in generators]
        if not parsed_generators:
            raise ValueError("generators must not be empty")

        self._equave_reduce = equave_reduce
        self._equave = equave_fraction
        self._set_generator_state(
            generators=parsed_generators,
            equave=equave_fraction,
            equave_reduce=equave_reduce,
        )
        super(ToneLattice, self).__init__(
            dimensionality=len(self._generators),
            resolution=resolution,
            bipolar=bipolar,
            periodic=False,
        )
        self._weave()

    @classmethod
    def from_generators(
        cls,
        generators: Iterable[Union[int, Fraction, str]],
        resolution: Union[int, List[int]] = 6,
        bipolar: bool = True,
        equave_reduce: bool = True,
        equave: Union[int, Fraction, str] = 2,
    ) -> "Tonnetz":
        """Build a Tonnetz from an explicit two-generator basis."""
        self = super().from_generators(
            generators,
            resolution=resolution,
            bipolar=bipolar,
            equave_reduce=equave_reduce,
            equave=equave,
        )
        self._weave()
        return self

    def with_generators(
        self,
        generators: Iterable[Union[int, Fraction, str]],
    ) -> "Tonnetz":
        """
        Return a new Tonnetz with the same board but a new generator basis.

        Resolution, polarity, equave, and reference pitch carry over, so
        every coordinate (and shape) valid on this Tonnetz remains valid
        on the result — only the represented ratios change.
        """
        new = type(self).from_generators(
            generators,
            resolution=self.resolution,
            bipolar=self.bipolar,
            equave_reduce=self.equave_reduce,
            equave=self.equave,
        )
        if new.dimensionality != self.dimensionality:
            raise ValueError(
                f"New generator basis yields dimensionality {new.dimensionality}, "
                f"but this lattice is {self.dimensionality}D; coordinate groups "
                f"would not carry over"
            )
        new._reference_pitch = self._reference_pitch
        return new

    # ------------------------------------------------------------------
    # Board
    # ------------------------------------------------------------------
    def _weave(self) -> None:
        """Add the third-direction edges ``(q, r) -- (q+1, r-1)`` to the grid.

        Both construction paths (``__init__`` and ``from_generators``)
        finish here, turning the rectangular grid into a triangular one.
        """
        if self.dimensionality != 2:
            raise ValueError(
                f"Tonnetz requires exactly 2 generator axes, got {self.dimensionality} "
                f"(note that a generator equal to the equave is dropped when "
                f"equave_reduce is True)"
            )
        for q, r in self.coords:
            other = (q + 1, r - 1)
            if other in self:
                u = self._get_node_for_coord((q, r))
                v = self._get_node_for_coord(other)
                if not self._rx.has_edge(u, v):
                    self._rx.add_edge(u, v, None)

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------
    @property
    def directions(self) -> dict:
        """
        The three unit interval directions, as ``{ratio: vector}``.

        Two generators span the lattice; the third direction is their
        quotient ``g1/g2`` at ``(1, -1)``. Negative vectors represent the
        reciprocal intervals.
        """
        g1, g2 = self._generators
        third = g1 / g2
        if self._equave_reduce:
            third = self._custom_equave_reduce(third)
        return {g1: (1, 0), g2: (0, 1), third: (1, -1)}

    def symmetries(self, reflections=False):
        """
        The D6 point group of the triangular lattice, as integer matrices.

        Every returned matrix ``A`` satisfies ``A^T G A = G`` for the
        oblique metric ``G = [[1, 1/2], [1/2, 1]]`` of the isometric
        embedding: rotations by multiples of 60 degrees, plus (when
        *reflections* is True) the six mirrors.

        Parameters
        ----------
        reflections : bool, optional
            Include the mirrors (default False: rotations only).

        Returns
        -------
        list of tuple of tuple of int
            Matrices whose rows act on ``(q, r)`` coordinates, suitable
            for ``rotations(cells, group=...)``.
        """
        mats = []
        m = _IDENTITY
        for _ in range(6):
            mats.append(m)
            m = _matmul(_R60, m)
        if reflections:
            mats += [_matmul(rot, _F) for rot in mats[:6]]
        return mats

    def _mirror_for_direction(self, direction: Tuple[int, int]):
        d = _primitive(direction)
        for m in self.symmetries(reflections=True)[6:]:
            if _matvec(m, d) == d:
                return m
        valid = sorted({_primitive(_matvec(rot, (1, 0))) for rot in self.symmetries()}
                       | {_primitive(_matvec(rot, (1, 1))) for rot in self.symmetries()})
        raise ValueError(
            f"{direction} is not a mirror direction of the triangular lattice; "
            f"valid directions (up to sign): {valid}"
        )

    def _resolve_axis(self, axis) -> Tuple[int, int]:
        if isinstance(axis, (tuple, list)) and len(axis) == 2 \
                and all(isinstance(x, int) for x in axis):
            return tuple(axis)
        target = Fraction(axis)
        for ratio, vector in self.directions.items():
            if target == ratio:
                return vector
            if self._equave_reduce and self._canonical_class(target) == self._canonical_class(ratio):
                return vector
        raise ValueError(
            f"axis {axis!r} is neither a coordinate vector nor one of this "
            f"Tonnetz's interval directions {sorted(self.directions)}"
        )

    # ------------------------------------------------------------------
    # Shape operations
    # ------------------------------------------------------------------
    def reflect(self, cells, edge=None, *, axis=None, through=(0, 0)) -> Shape:
        """
        Reflect a shape across a mirror line of the lattice.

        Two calling forms:

        - ``reflect(shape, edge=(v1, v2))`` — flip across the line through
          two lattice points (the "flip over an edge" form; reflecting a
          triangle across each of its three edges gives the neo-Riemannian
          P, L, and R moves).
        - ``reflect(shape, axis=direction, through=point)`` — flip across
          the mirror line with the given direction passing through a
          lattice point. *axis* may be a coordinate vector or an interval
          (ratio, string, or Fraction) resolved via :attr:`directions`.

        The line's direction must be one of the six mirror directions of
        the triangular lattice (the three interval directions and their
        three bisectors).

        Parameters
        ----------
        cells : iterable of tuple of int
            The shape to reflect.
        edge : tuple of two coordinate tuples, optional
            Two lattice points defining the mirror line.
        axis : tuple, int, Fraction, or str, optional
            Mirror direction (used with *through*).
        through : tuple of int, optional
            A lattice point on the mirror line (default origin).

        Returns
        -------
        Shape
            The reflected shape.
        """
        if (edge is None) == (axis is None):
            raise ValueError("pass exactly one of edge= or axis=")
        if edge is not None:
            v1, v2 = (tuple(v) for v in edge)
            direction = (v2[0] - v1[0], v2[1] - v1[1])
            through = v1
        else:
            direction = self._resolve_axis(axis)
            through = tuple(through)
        mirror = self._mirror_for_direction(direction)
        return _affine(mirror, cells, through)

    def rotate(self, cells, n: int = 1, about=(0, 0)) -> Shape:
        """
        Rotate a shape by ``n`` sixths of a turn about a lattice vertex.

        Parameters
        ----------
        cells : iterable of tuple of int
            The shape to rotate.
        n : int, optional
            Number of 60-degree steps (default 1; negative for clockwise).
        about : tuple of int, optional
            The fixed vertex (default origin).

        Returns
        -------
        Shape
            The rotated shape.
        """
        m = _IDENTITY
        for _ in range(n % 6):
            m = _matmul(_R60, m)
        return _affine(m, cells, tuple(about))

    # ------------------------------------------------------------------
    # Triangle moves
    # ------------------------------------------------------------------
    def _triangle_orientation(self, cells) -> str:
        """``'up'`` or ``'down'`` for a unit triangle; raises otherwise."""
        from klotho.topos.shapes.polyominoes import normalize
        form = tuple(normalize(cells))
        if form == self._TRIAD_UP:
            return 'up'
        if form == self._TRIAD_DOWN:
            return 'down'
        raise ValueError(f"not a unit triangle: {tuple(cells)}")

    def flip(self, cells, move) -> Shape:
        """
        Reflect a shape across its own edge, or slide a triangle.

        For the letter moves (named for the default fifths-by-thirds
        configuration; each is an involution):

        - ``'P'`` (*parallel*) — flip across the shape's fifth edge
          (direction ``(1, 0)``): major <-> minor on the same root.
        - ``'R'`` (*relative*) — flip across the major-third edge
          (``(0, 1)``): C major <-> A minor.
        - ``'L'`` (*leading-tone*) — flip across the minor-third edge
          (``(1, -1)``): C major <-> E minor.
        - ``'S'`` (*slide*) — hold the triangle's third vertex and turn
          the triangle half-way around it: C major <-> C-sharp minor,
          C minor <-> B major. Triangles only.

        Any other *move* is an axis for the edge search: a direction
        vector or an interval resolved via :attr:`directions`. The shape
        must have exactly one edge parallel to it (a triangle always
        does; e.g. a 2x2 cell has two, and :meth:`reflect` with an
        explicit ``edge=`` disambiguates).

        Parameters
        ----------
        cells : iterable of tuple of int
            The shape to move.
        move : str or tuple
            ``'P'``, ``'R'``, ``'L'``, ``'S'``, an interval (ratio or
            string), or a direction vector.

        Returns
        -------
        Shape
            The moved shape.
        """
        if isinstance(move, str) and move.upper() == 'S':
            anchor = min(tuple(c) for c in cells)
            if self._triangle_orientation(cells) == 'up':
                third = (anchor[0], anchor[1] + 1)
            else:
                third = (anchor[0] + 1, anchor[1] - 1)
            return self.rotate(cells, 3, about=third)

        if isinstance(move, str) and move.upper() in self._TRIAD_FLIPS:
            direction = self._TRIAD_FLIPS[move.upper()]
        else:
            direction = self._resolve_axis(move)

        points = [tuple(c) for c in cells]
        point_set = set(points)
        edges = [
            (a, (a[0] + direction[0], a[1] + direction[1]))
            for a in points
            if (a[0] + direction[0], a[1] + direction[1]) in point_set
        ]
        if len(edges) == 0:
            raise ValueError(
                f"shape has no edge in direction {direction}; "
                f"nothing to flip across"
            )
        if len(edges) > 1:
            raise ValueError(
                f"shape has {len(edges)} parallel edges in direction "
                f"{direction}; use reflect(cells, edge=...) to pick one"
            )
        return self.reflect(cells, edge=edges[0])

    def perform(self, cells, moves) -> List[Shape]:
        """
        Fold a sequence of moves over a shape, keeping every step.

        Each move is either a string (a :meth:`flip` move: ``'P'``,
        ``'R'``, ``'L'``, ``'S'``, or an interval) or a ``(dq, dr)``
        vector (a slide, via :func:`~klotho.topos.shapes.translate`).

        Parameters
        ----------
        cells : iterable of tuple of int
            The starting shape.
        moves : iterable of str or tuple
            The instructions, in order.

        Returns
        -------
        list of Shape
            Every shape along the way, the starting shape included.
        """
        from klotho.topos.shapes.polyominoes import translate
        shape = Shape(cells)
        history = [shape]
        for move in moves:
            if isinstance(move, str):
                shape = self.flip(shape, move)
            else:
                shape = translate(shape, move)
            history.append(shape)
        return history
