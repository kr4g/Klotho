from typing import List, Union, Tuple, Optional, Iterable, Literal
from fractions import Fraction
import warnings
import sympy as sp
from sympy import prime as sympy_prime, isprime

from klotho.topos.graphs.lattices import Lattice
from klotho.utils.algorithms.factors import to_factors


class ToneLatticeLookupWarning(RuntimeWarning):
    """Warning emitted when inverse ratio lookup is ambiguous or unresolved in a ``ToneLattice``."""
    pass


class ToneLattice(Lattice):
    """
    Lattice of ratios represented by integer coordinates in generator space.

    Coordinates are exponent vectors over an ordered generator list:
    ``ratio = g1**x1 * g2**x2 * ...``.

    Construction modes
    ------------------
    - ``ToneLattice(...)`` builds a default prime-generator basis from dimensionality.
    - ``ToneLattice.from_generators(...)`` uses explicit generators.

    Equave behavior
    ---------------
    - If ``equave_reduce`` is False, ratios are not reduced.
    - If ``equave_reduce`` is True, output ratios are reduced by equave and any
      generator exactly equal to ``equave`` is removed as an axis.
    - Reduction window is controlled by ``bipolar``:
      - ``bipolar=True``  -> ``(1/equave, equave)``
      - ``bipolar=False`` -> ``[1, equave)``

    Parameters
    ----------
    dimensionality : int, optional
        Number of generator axes. Default is 2.
    resolution : int or list of int, optional
        Per-axis coordinate bounds. Default is 10.
    bipolar : bool, optional
        Whether coordinates span negative values and which equave
        reduction window to use. Default is True.
    equave_reduce : bool, optional
        Whether to reduce output ratios by equave. Default is True.
    equave : int, Fraction, or str, optional
        Equivalence interval. Floats are rejected. Default is 2.
    """
    
    def __init__(
        self,
        dimensionality: int = 2,
        resolution: Union[int, List[int]] = 10,
        bipolar: bool = True,
        equave_reduce: bool = True,
        equave: Union[int, Fraction, str] = 2,
    ):
        self._equave_reduce = equave_reduce
        self._equave = self._parse_equave(equave)

        generators = self._default_prime_generators(
            dimensionality=dimensionality,
            equave=self._equave,
            equave_reduce=equave_reduce,
        )
        self._set_generator_state(generators=generators, equave=self._equave, equave_reduce=equave_reduce)

        super().__init__(
            dimensionality=len(self._generators),
            resolution=resolution,
            bipolar=bipolar,
            periodic=False,
        )

    @classmethod
    def from_generators(
        cls,
        generators: Iterable[Union[int, Fraction, str]],
        resolution: Union[int, List[int]] = 10,
        bipolar: bool = True,
        equave_reduce: bool = True,
        equave: Union[int, Fraction, str] = 2,
    ) -> "ToneLattice":
        """
        Build a ToneLattice from an explicit generator basis.

        Parameters
        ----------
        generators : Iterable[int | Fraction | str]
            Ordered generator ratios defining the coordinate axes.
        resolution : int or list[int], optional
            Per-axis coordinate bounds passed to the base lattice.
        bipolar : bool, optional
            Coordinate sign mode and equave reduction window selector.
        equave_reduce : bool, optional
            Whether to equave-reduce represented ratios. If True and an equave
            generator is present, that generator axis is removed.
        equave : int | Fraction | str, optional
            Equivalence interval used for reduction.
        """
        equave_fraction = cls._parse_equave(equave)

        parsed_generators = [cls._parse_generator(g) for g in generators]
        if not parsed_generators:
            raise ValueError("generators must not be empty")

        self = cls.__new__(cls)
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
        return self

    @staticmethod
    def _parse_generator(value: Union[int, Fraction, str]) -> Fraction:
        if isinstance(value, float):
            raise TypeError("Generators do not accept float values; use int, Fraction, or str")
        parsed = Fraction(value)
        if parsed <= 0:
            raise ValueError("Generators must be positive")
        if parsed == 1:
            raise ValueError("Generator 1 is not allowed")
        return parsed

    @staticmethod
    def _parse_equave(value: Union[int, Fraction, str]) -> Fraction:
        if isinstance(value, float):
            raise TypeError("equave does not accept float values; use int, Fraction, or str")
        parsed = Fraction(value)
        if parsed <= 1:
            raise ValueError("equave must be greater than 1")
        return parsed

    @staticmethod
    def _default_prime_generators(
        dimensionality: int,
        equave: Fraction,
        equave_reduce: bool,
    ) -> List[Fraction]:
        if dimensionality <= 0:
            raise ValueError("dimensionality must be positive")
        generators: List[Fraction] = []
        i = 1
        while len(generators) < dimensionality:
            p = sympy_prime(i)
            i += 1
            if equave_reduce and Fraction(p) == equave:
                continue
            generators.append(Fraction(p))
        return generators

    def _set_generator_state(
        self,
        generators: Iterable[Fraction],
        equave: Fraction,
        equave_reduce: bool,
    ) -> None:
        parsed_generators = [self._parse_generator(g) for g in generators]
        if len(set(parsed_generators)) != len(parsed_generators):
            raise ValueError("Generators must be unique")
        equave_indices = [i for i, g in enumerate(parsed_generators) if g == equave]
        if len(equave_indices) > 1:
            raise ValueError("Generator set contains duplicate equave generators")
        if equave_reduce and equave_indices:
            parsed_generators = [g for i, g in enumerate(parsed_generators) if i != equave_indices[0]]
        if not parsed_generators:
            raise ValueError("No generators remain after equave reduction")
        if len(set(parsed_generators)) != len(parsed_generators):
            raise ValueError("Generators must be unique after equave-axis dropping")

        self._generators = parsed_generators
        self._ratio_match_index: Optional[dict[Fraction, List[Tuple[int, ...]]]] = None
        self._warned_lookup_messages: set[str] = set()
        basis_primes = set()
        self._generator_factors = [to_factors(g) for g in self._generators]
        for factors in self._generator_factors:
            basis_primes.update(factors.keys())
        self._basis_primes = sorted(basis_primes)
        self._generator_matrix = sp.Matrix(
            [
                [factors.get(p, 0) for factors in self._generator_factors]
                for p in self._basis_primes
            ]
        )
        self._generator_symbols = sp.symbols(f"y0:{len(self._generators)}", integer=True)
        self._is_monzo_basis = (
            len(self._generators) > 0
            and all(g.denominator == 1 and isprime(int(g)) for g in self._generators)
        )
    
    def _custom_equave_reduce(self, interval: Union[int, float, Fraction, str]) -> Fraction:
        interval = Fraction(interval)
        equave = self._equave
        if self._bipolar:
            lower = Fraction(1, 1) / equave
            while interval <= lower:
                interval *= equave
            while interval >= equave:
                interval /= equave
        else:
            while interval < 1:
                interval *= equave
            while interval >= equave:
                interval /= equave
        return interval
        
    def _populate_missing_ratio_data(self, coords: Optional[List[Tuple[int, ...]]] = None):
        """Populate missing ratio data for provided coordinates."""
        target_coords = self.coords if coords is None else coords
        for coord in target_coords:
            node_id = self._get_node_for_coord(coord)
            if node_id is not None:
                node_data = self._graph.get_node_data(node_id)
                if isinstance(node_data, dict) and 'ratio' not in node_data:
                    ratio = self._coord_to_ratio(coord)
                    node_data['ratio'] = ratio
    
    def _coord_to_ratio(self, coord: Tuple[int, ...]) -> Fraction:
        ratio = Fraction(1, 1)
        for i, exp in enumerate(coord):
            if i >= len(self._generators):
                break
            exp_int = int(exp)
            if exp_int != 0:
                ratio *= self._generators[i] ** exp_int
        if self._equave_reduce:
            ratio = self._custom_equave_reduce(ratio)
        return ratio
    
    def __getitem__(self, coord):
        """Get node data for a coordinate, ensuring ratio is included."""
        node_data = super().__getitem__(coord)
        
        if 'ratio' not in node_data:
            node_data = dict(node_data)
            node_data['ratio'] = self._coord_to_ratio(coord)
            return node_data
        
        return node_data
    
    def get_ratio(self, coord: Tuple[int, ...]) -> Fraction:
        """
        Return the ratio represented by a coordinate.

        The value is computed in generator space and, when ``equave_reduce`` is
        enabled, reduced into the active equave window determined by ``bipolar``.
        """
        if coord not in self:
            raise KeyError(f"Coordinate {coord} not found in lattice")
        node_id = self._get_node_for_coord(coord)
        ratio = None
        if node_id is not None:
            node_data = self._graph.get_node_data(node_id)
            if isinstance(node_data, dict) and 'ratio' in node_data:
                ratio = node_data['ratio']
        if ratio is None:
            ratio = self._coord_to_ratio(coord)
        return ratio
    
    def _sorted_matches_for_ratio(self, ratio: Fraction) -> List[Tuple[int, ...]]:
        if self._ratio_match_index is None:
            ratio_index: dict[Fraction, List[Tuple[int, ...]]] = {}
            for coord in self.coords:
                coord_ratio = self._coord_to_ratio(coord)
                ratio_index.setdefault(coord_ratio, []).append(coord)
            for coords in ratio_index.values():
                coords.sort(key=lambda c: (sum(abs(v) for v in c), c))
            self._ratio_match_index = ratio_index
        return self._ratio_match_index.get(ratio, [])

    def _warn_lookup(self, message: str, warn_once: bool) -> None:
        if warn_once and message in self._warned_lookup_messages:
            return
        warnings.warn(message, ToneLatticeLookupWarning, stacklevel=3)
        if warn_once:
            self._warned_lookup_messages.add(message)

    def _direct_coordinate_for_ratio(self, ratio: Fraction) -> Tuple[int, ...]:
        ratio_factors = to_factors(ratio)
        missing_primes = [p for p, e in ratio_factors.items() if e != 0 and p not in self._basis_primes]
        if missing_primes:
            raise ValueError(
                f"ratio contains primes not present in prime_basis: {sorted(missing_primes)}"
            )
        x = sp.Matrix([ratio_factors.get(p, 0) for p in self._basis_primes])
        solutions = sp.linsolve((self._generator_matrix, x), self._generator_symbols)
        if not solutions:
            raise ValueError("ratio is not representable with provided generators")
        solution = next(iter(solutions))
        if any(expr.free_symbols for expr in solution):
            raise ValueError("ratio does not have a unique integer coordinate in provided generators")
        y = sp.Matrix(solution)
        if any(sp.denom(v) != 1 for v in y):
            raise ValueError("ratio is not representable with integer generator coordinates")
        return tuple(int(v) for v in y[: self.dimensionality])

    def get_coordinates_for_ratio(
        self,
        ratio: Union[int, Fraction, str],
        lookup: Literal["first", "unique", "all"] = "first",
        warn: bool = True,
        warn_once: bool = True,
    ) -> Union[None, Tuple[int, ...], List[Tuple[int, ...]]]:
        """
        Resolve coordinate(s) for a target ratio under the current lattice state.

        Parameters
        ----------
        ratio : int | Fraction | str
            Target ratio.
        lookup : {"first", "unique", "all"}, optional
            Resolution mode:
            - ``"first"``: return one deterministic coordinate match.
            - ``"unique"``: return coordinate only when exactly one match exists.
            - ``"all"``: return all matches in current lattice bounds.
        warn : bool, optional
            Emit ``ToneLatticeLookupWarning`` when lookup fails or is ambiguous.
        warn_once : bool, optional
            When True, suppress repeated identical warning messages per instance.

        Returns
        -------
        tuple[int, ...] | list[tuple[int, ...]] | None
            Coordinate result according to ``lookup`` mode, or ``None`` when
            unresolved.
        """
        if lookup not in ("first", "unique", "all"):
            raise ValueError("lookup must be one of: 'first', 'unique', 'all'")

        ratio = Fraction(ratio)
        if self._equave_reduce:
            ratio = self._custom_equave_reduce(ratio)

        reason = "ratio is not present in the current lattice coordinates"
        direct_coord: Optional[Tuple[int, ...]] = None
        try:
            candidate_coord = self._direct_coordinate_for_ratio(ratio)
            if candidate_coord in self and self._coord_to_ratio(candidate_coord) == ratio:
                direct_coord = candidate_coord
            else:
                reason = (
                    f"ratio maps to coordinate {candidate_coord}, "
                    "but that coordinate is outside the current lattice bounds/resolution"
                )
        except ValueError as exc:
            reason = str(exc)

        if lookup == "first":
            if direct_coord is not None:
                return direct_coord
            matches = self._sorted_matches_for_ratio(ratio)
            if matches:
                return matches[0]
            if warn:
                self._warn_lookup(
                    f"Could not resolve ratio {ratio} in this ToneLattice: {reason}",
                    warn_once=warn_once,
                )
            return None

        matches = self._sorted_matches_for_ratio(ratio)
        if lookup == "all":
            if matches:
                return matches
            if warn:
                self._warn_lookup(
                    f"Could not resolve ratio {ratio} in this ToneLattice: {reason}",
                    warn_once=warn_once,
                )
            return None

        # lookup == "unique"
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            if warn:
                self._warn_lookup(
                    (
                        f"Could not resolve ratio {ratio} uniquely in this ToneLattice: "
                        f"found {len(matches)} matching coordinates {matches}"
                    ),
                    warn_once=warn_once,
                )
            return None
        if warn:
            self._warn_lookup(
                f"Could not resolve ratio {ratio} in this ToneLattice: {reason}",
                warn_once=warn_once,
            )
        return None
        
    @property
    def prime_basis(self) -> List[int]:
        """Sorted prime support inferred from active generators."""
        return self._basis_primes.copy()

    @property
    def generators(self) -> List[Fraction]:
        """Active generator basis used by coordinate axes."""
        return self._generators.copy()

    @property
    def coord_label(self) -> str:
        """Plot label for coordinates: ``Monzo`` for pure prime bases, else ``Coordinate``."""
        return "Monzo" if self._is_monzo_basis else "Coordinate"
    
    @property
    def equave_reduce(self) -> bool:
        """Whether this lattice applies equave reduction to represented ratios."""
        return self._equave_reduce
    
    def __str__(self) -> str:
        """String representation of the tone lattice."""
        base_str = super().__str__()
        generators_str = ', '.join(str(g) for g in self._generators)
        equave_str = "equave-reduced" if self._equave_reduce else "full"
        return f"Tone{base_str[:-1]}, generators=[{generators_str}], {equave_str})"
