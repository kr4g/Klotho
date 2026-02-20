import math
import sympy as sp
import numpy as np

__all__ = [
    'MasterSet',
    'MASTER_SETS',
]

_ALPHA = {chr(65 + i): sp.Symbol(chr(65 + i)) for i in range(26)}


class MasterSet:
    def __init__(self, positions, edges, name=None, factors=None):
        self._positions = {}
        for k, v in positions.items():
            if len(v) >= 3:
                self._positions[k] = (float(v[0]), float(v[1]), float(v[2]))
            else:
                self._positions[k] = (float(v[0]), float(v[1]), 0.0)
        self._edge_pairs = list(edges)
        self._name = name
        self._n_factors = len(positions)
        self._factors = tuple(sorted(factors)) if factors else None
        self._aliases = sorted(positions.keys())
        self._factor_to_alias = None
        self._alias_to_factor = None
        if self._factors is not None:
            if len(self._factors) != self._n_factors:
                raise ValueError(
                    f"Expected {self._n_factors} factors, got {len(self._factors)}")
            self._factor_to_alias = {f: a for f, a in zip(self._factors, self._aliases)}
            self._alias_to_factor = {a: f for f, a in self._factor_to_alias.items()}
        self._relationship_dict = self._build_relationship_dict()

    def _build_relationship_dict(self):
        rd = {}
        for fr, to in self._edge_pairs:
            x1, y1, z1 = self._positions[fr]
            x2, y2, z2 = self._positions[to]
            dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
            angle = math.atan2(dy, dx)
            horiz = math.sqrt(dx * dx + dy * dy)
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            elev = math.atan2(dz, horiz) if dist > 1e-12 else 0.0
            sym_fwd = _ALPHA[fr] / _ALPHA[to]
            sym_rev = _ALPHA[to] / _ALPHA[fr]
            rd[sym_fwd] = {'angle': angle, 'distance': dist, 'elevation': elev}
            rd[sym_rev] = {'angle': angle + math.pi, 'distance': dist, 'elevation': -elev}
        return rd

    @property
    def dimensionality(self):
        return 3 if any(abs(p[2]) > 1e-12 for p in self._positions.values()) else 2

    @property
    def relationship_dict(self):
        return self._relationship_dict

    @property
    def positions(self):
        return dict(self._positions)

    @property
    def n_factors(self):
        return self._n_factors

    @property
    def name(self):
        return self._name

    @property
    def edges(self):
        return list(self._edge_pairs)

    @property
    def factors(self):
        return self._factors

    @property
    def factor_to_alias(self):
        return dict(self._factor_to_alias) if self._factor_to_alias else None

    @property
    def alias_to_factor(self):
        return dict(self._alias_to_factor) if self._alias_to_factor else None

    @property
    def aliases(self):
        return list(self._aliases)

    @property
    def ratios(self):
        if self._factors is None:
            return None
        from klotho.tonos.utils.interval_normalization import equave_reduce
        return tuple(sorted(equave_reduce(f) for f in self._factors))

    def node_data(self):
        if self._factors is None:
            return {a: {'alias': a} for a in self._aliases}
        from klotho.tonos.utils.interval_normalization import equave_reduce
        result = {}
        for f, a in self._factor_to_alias.items():
            result[a] = {
                'alias': a,
                'factor': f,
                'ratio': equave_reduce(f),
            }
        return result

    def with_factors(self, factors):
        return MasterSet(self._positions, self._edge_pairs,
                         name=self._name, factors=factors)

    def __repr__(self):
        return f"MasterSet('{self._name}', {self._n_factors} nodes, {len(self._edge_pairs)} edges)"

    # ------------------------------------------------------------------
    # Named constructors
    # ------------------------------------------------------------------

    @classmethod
    def tetrad(cls):
        positions = {
            'A': (-1.5, -math.sqrt(3) / 2),
            'B': (1.5, -math.sqrt(3) / 2),
            'C': (0.0, math.sqrt(3)),
            'D': (0.0, 0.0),
        }
        edges = [
            ('D', 'A'), ('D', 'B'), ('D', 'C'),
            ('C', 'A'), ('C', 'B'), ('B', 'A'),
        ]
        return cls(positions, edges, name='tetrad')

    @classmethod
    def asterisk(cls):
        r = 3.0
        angles = {
            'B': math.pi * 3 / 2,
            'C': math.pi * 11 / 10,
            'D': math.pi * 7 / 10,
            'E': math.pi * 3 / 10,
            'F': math.pi * 19 / 10,
        }
        positions = {'A': (0.0, 0.0)}
        for label, ang in angles.items():
            positions[label] = (r * math.cos(ang), r * math.sin(ang))
        edges = [('A', lbl) for lbl in angles]
        return cls(positions, edges, name='asterisk')

    @classmethod
    def centered_pentagon(cls):
        r = 3.0
        gen_angles = {
            ('B', 'F'): math.pi * 6 / 5,
            ('B', 'C'): math.pi * 9 / 5,
            ('F', 'E'): math.pi * 8 / 5,
            ('C', 'D'): math.pi * 7 / 5,
        }
        positions = {'B': (0.0, 0.0)}
        positions['F'] = (r * math.cos(gen_angles[('B', 'F')]),
                          r * math.sin(gen_angles[('B', 'F')]))
        positions['C'] = (r * math.cos(gen_angles[('B', 'C')]),
                          r * math.sin(gen_angles[('B', 'C')]))
        positions['E'] = (positions['F'][0] + r * math.cos(gen_angles[('F', 'E')]),
                          positions['F'][1] + r * math.sin(gen_angles[('F', 'E')]))
        positions['D'] = (positions['C'][0] + r * math.cos(gen_angles[('C', 'D')]),
                          positions['C'][1] + r * math.sin(gen_angles[('C', 'D')]))

        cx = np.mean([v[0] for v in positions.values()])
        cy = np.mean([v[1] for v in positions.values()])
        positions = {k: (v[0] - cx, v[1] - cy) for k, v in positions.items()}

        edges = [('B', 'F'), ('B', 'C'), ('F', 'E'), ('C', 'D'), ('E', 'D')]
        return cls(positions, edges, name='centered_pentagon')

    @classmethod
    def hexagon(cls):
        r = 3.0
        int_angles = [90, 150, 90, 150, 90, 150]
        order = ['C', 'F', 'A', 'E', 'B', 'D']

        heading_deg = 315
        pts = [(0.0, 0.0)]
        heading_rad = math.radians(heading_deg)
        for i in range(5):
            x = pts[-1][0] + r * math.cos(heading_rad)
            y = pts[-1][1] + r * math.sin(heading_rad)
            pts.append((x, y))
            ext = 180 - int_angles[(i + 1) % 6]
            heading_deg -= ext
            heading_rad = math.radians(heading_deg)

        cx = np.mean([p[0] for p in pts])
        cy = np.mean([p[1] for p in pts])
        pts = [(p[0] - cx, p[1] - cy) for p in pts]

        positions = {order[i]: pts[i] for i in range(6)}
        edges = [
            ('C', 'F'), ('F', 'A'), ('A', 'E'),
            ('E', 'B'), ('B', 'D'), ('D', 'C'),
        ]
        return cls(positions, edges, name='hexagon')

    @classmethod
    def irregular_hexagon(cls):
        r = 3.0
        target_short = 2.75

        int_angles = [90, 150, 90, 150, 90, 150]
        order = ['C', 'F', 'A', 'E', 'B', 'D']

        heading_deg = 315
        pts = [(0.0, 0.0)]
        heading_rad = math.radians(heading_deg)
        for i in range(5):
            x = pts[-1][0] + r * math.cos(heading_rad)
            y = pts[-1][1] + r * math.sin(heading_rad)
            pts.append((x, y))
            ext = 180 - int_angles[(i + 1) % 6]
            heading_deg -= ext
            heading_rad = math.radians(heading_deg)

        positions = {order[i]: pts[i] for i in range(6)}

        FA_x = positions['A'][0] - positions['F'][0]
        FA_y = positions['A'][1] - positions['F'][1]
        d = -FA_y - math.sqrt(target_short ** 2 - FA_x ** 2)

        top_nodes = {'C', 'F', 'D'}
        for label in top_nodes:
            x, y = positions[label]
            positions[label] = (x, y - d)

        cx = np.mean([p[0] for p in positions.values()])
        cy = np.mean([p[1] for p in positions.values()])
        positions = {k: (v[0] - cx, v[1] - cy) for k, v in positions.items()}

        edges = [
            ('C', 'F'), ('F', 'A'), ('A', 'E'),
            ('E', 'B'), ('B', 'D'), ('D', 'C'),
        ]
        return cls(positions, edges, name='irregular_hexagon')

    @classmethod
    def ogdoad(cls):
        r = 3.0
        outer = {
            'B': math.pi * 1 / 2,
            'C': math.pi * 3 / 14,
            'D': math.pi * 27 / 14,
            'E': math.pi * 23 / 14,
            'F': math.pi * 19 / 14,
            'G': math.pi * 15 / 14,
            'H': math.pi * 11 / 14,
        }
        positions = {'A': (0.0, 0.0)}
        for label, ang in outer.items():
            positions[label] = (r * math.cos(ang), r * math.sin(ang))
        edges = [('A', lbl) for lbl in outer]
        return cls(positions, edges, name='ogdoad')

    # ------------------------------------------------------------------
    # 3D Named constructors
    # ------------------------------------------------------------------

    @classmethod
    def tetrad_3d(cls):
        base = cls.tetrad()
        apex_height = math.sqrt(6)
        positions = {
            'A': base._positions['A'][:2] + (0.0,),
            'B': base._positions['B'][:2] + (0.0,),
            'C': base._positions['C'][:2] + (0.0,),
            'D': (0.0, 0.0, apex_height),
        }
        edges = [
            ('D', 'A'), ('D', 'B'), ('D', 'C'),
            ('C', 'A'), ('C', 'B'), ('B', 'A'),
        ]
        return cls(positions, edges, name='tetrad_3d')

    @classmethod
    def asterisk_3d(cls, height=None):
        r = 3.0
        if height is None:
            height = r
        base = cls.asterisk()
        positions = {}
        for label, pos in base._positions.items():
            if label == 'A':
                positions[label] = (0.0, 0.0, height)
            else:
                positions[label] = pos[:2] + (0.0,)
        edges = [('A', lbl) for lbl in positions if lbl != 'A']
        return cls(positions, edges, name='asterisk_3d')

    @classmethod
    def ogdoad_3d(cls, height=None):
        r = 3.0
        if height is None:
            height = r
        base = cls.ogdoad()
        positions = {}
        for label, pos in base._positions.items():
            if label == 'A':
                positions[label] = (0.0, 0.0, height)
            else:
                positions[label] = pos[:2] + (0.0,)
        edges = [('A', lbl) for lbl in positions if lbl != 'A']
        return cls(positions, edges, name='ogdoad_3d')


MASTER_SETS = {
    'tetrad': MasterSet.tetrad,
    'asterisk': MasterSet.asterisk,
    'centered_pentagon': MasterSet.centered_pentagon,
    'hexagon': MasterSet.hexagon,
    'irregular_hexagon': MasterSet.irregular_hexagon,
    'ogdoad': MasterSet.ogdoad,
    'tetrad_3d': MasterSet.tetrad_3d,
    'asterisk_3d': MasterSet.asterisk_3d,
    'ogdoad_3d': MasterSet.ogdoad_3d,
}
