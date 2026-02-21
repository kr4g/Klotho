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
        max_dim = max(len(v) for v in positions.values()) if positions else 2
        max_dim = max(max_dim, 2)
        self._positions = {}
        for k, v in positions.items():
            padded = tuple(float(c) for c in v) + (0.0,) * (max_dim - len(v))
            self._positions[k] = padded
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
            p1 = self._positions[fr]
            p2 = self._positions[to]
            disp = tuple(p2[i] - p1[i] for i in range(len(p1)))
            dx = disp[0] if len(disp) > 0 else 0.0
            dy = disp[1] if len(disp) > 1 else 0.0
            dz = disp[2] if len(disp) > 2 else 0.0
            angle = math.atan2(dy, dx)
            horiz = math.sqrt(dx * dx + dy * dy)
            dist = math.sqrt(sum(d * d for d in disp))
            elev = math.atan2(dz, horiz) if dist > 1e-12 else 0.0
            sym_fwd = _ALPHA[fr] / _ALPHA[to]
            sym_rev = _ALPHA[to] / _ALPHA[fr]
            rd[sym_fwd] = {'angle': angle, 'distance': dist, 'elevation': elev,
                           'displacement': disp}
            rd[sym_rev] = {'angle': angle + math.pi, 'distance': dist, 'elevation': -elev,
                           'displacement': tuple(-d for d in disp)}
        return rd

    @property
    def dimensionality(self):
        if not self._positions:
            return 2
        dim = len(next(iter(self._positions.values())))
        for d in range(dim, 2, -1):
            if any(abs(p[d - 1]) > 1e-12 for p in self._positions.values()):
                return d
        return 2

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
            'B': (0.0, math.sqrt(3)),
            'C': (1.5, -math.sqrt(3) / 2),
            'D': (0.0, 0.0),
        }
        edges = [
            ('D', 'A'), ('D', 'B'), ('D', 'C'),
            ('A', 'B'), ('B', 'C'), ('C', 'A'),
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
        target_short = 2.333

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
    # Additional 2D Named constructors
    # ------------------------------------------------------------------

    @classmethod
    def heptagon(cls):
        r = 3.0
        angles = [2 * math.pi * i / 7 + math.pi / 2 for i in range(7)]
        labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        positions = {labels[i]: (r * math.cos(a), r * math.sin(a)) for i, a in enumerate(angles)}
        edges = [(labels[i], labels[(i + 1) % 7]) for i in range(7)]
        return cls(positions, edges, name='heptagon')

    @classmethod
    def kite(cls):
        r = 3.0
        positions = {
            'A': ( 0,       r * 0.85),
            'B': ( r * 0.6, 0),
            'C': ( 0,      -r * 0.5),
            'D': (-r * 0.6, 0),
        }
        edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'), ('A', 'C')]
        return cls(positions, edges, name='kite')

    @classmethod
    def arrow(cls):
        r = 3.0
        positions = {
            'A': ( 0,        r),
            'B': ( r * 0.8,  0),
            'C': ( r * 0.3,  r * 0.3),
            'D': (-r * 0.3,  r * 0.3),
            'E': (-r * 0.8,  0),
        }
        edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'E'), ('E', 'A')]
        return cls(positions, edges, name='arrow')

    @classmethod
    def k23_bipartite(cls):
        r = 3.0
        positions = {
            'A': (-r * 0.5,  r * 0.6),
            'B': ( r * 0.5,  r * 0.6),
            'C': (-r,       -r * 0.5),
            'D': ( 0,       -r * 0.7),
            'E': ( r,       -r * 0.5),
        }
        edges = [('A', 'C'), ('A', 'D'), ('A', 'E'),
                 ('B', 'C'), ('B', 'D'), ('B', 'E')]
        return cls(positions, edges, name='k23_bipartite')

    @classmethod
    def wheel5(cls):
        r = 3.0
        angles = [2 * math.pi * i / 5 + math.pi / 2 for i in range(5)]
        outer = ['B', 'C', 'D', 'E', 'F']
        positions = {'A': (0.0, 0.0)}
        for i, label in enumerate(outer):
            positions[label] = (r * math.cos(angles[i]), r * math.sin(angles[i]))
        edges = [(outer[i], outer[(i + 1) % 5]) for i in range(5)]
        edges += [('A', lbl) for lbl in outer]
        return cls(positions, edges, name='wheel5')

    @classmethod
    def bowtie(cls):
        r = 3.0
        positions = {
            'A': ( 0,          0),
            'B': ( r * 1.15,   r * 0.7),
            'C': ( r * 1.15,  -r * 0.7),
            'D': (-r * 0.85,   r * 0.5),
            'E': (-r * 0.85,  -r * 0.5),
        }
        edges = [('A', 'B'), ('A', 'C'), ('B', 'C'),
                 ('A', 'D'), ('A', 'E'), ('D', 'E')]
        return cls(positions, edges, name='bowtie')

    @classmethod
    def house(cls):
        sq = 2.0
        positions = {
            'A': ( 0,         sq * 1.2),
            'B': (-sq * 0.8,  0),
            'C': ( sq * 0.8,  0),
            'D': ( sq * 1.1, -2 * sq),
            'E': (-sq * 1.1, -2 * sq),
        }
        edges = [('A', 'B'), ('A', 'C'), ('B', 'C'),
                 ('C', 'D'), ('D', 'E'), ('E', 'B')]
        return cls(positions, edges, name='house')

    @classmethod
    def wheel4(cls):
        sq = 2.0
        positions = {
            'A': ( 0,        0.15),
            'B': ( 0,        sq * 1.3),
            'C': (-sq * 0.9, 0),
            'D': ( 0,       -sq * 0.8),
            'E': ( sq * 0.9, 0),
        }
        edges = [('B', 'C'), ('C', 'D'), ('D', 'E'), ('E', 'B'),
                 ('A', 'B'), ('A', 'C'), ('A', 'D'), ('A', 'E')]
        return cls(positions, edges, name='wheel4')

    @classmethod
    def h_shape(cls):
        r = 3.0
        positions = {
            'A': (-r * 1.1,   r * 0.9),
            'B': (-r * 0.9,  -r * 0.45),
            'C': (-r * 0.15,  r * 0.4),
            'D': ( r * 0.2,  -r * 0.5),
            'E': ( r * 0.85,  r * 0.35),
            'F': ( r * 1.1,  -r * 0.85),
        }
        edges = [('A', 'B'), ('A', 'C'), ('B', 'D'),
                 ('C', 'D'), ('C', 'E'), ('D', 'F'), ('E', 'F')]
        return cls(positions, edges, name='h_shape')

    @classmethod
    def nested_triangles(cls):
        r_out = 3.0
        r_in = 1.0
        sy = 0.1
        ang_out = [2 * math.pi * i / 3 + math.pi / 2 for i in range(3)]
        ang_in = [2 * math.pi * i / 3 + math.pi / 2 + math.pi / 3 for i in range(3)]
        positions = {}
        for i, a in enumerate(ang_out):
            positions[chr(65 + i)] = (r_out * math.cos(a), r_out * math.sin(a))
        for i, a in enumerate(ang_in):
            positions[chr(68 + i)] = (r_in * math.cos(a), r_in * math.sin(a) + sy)
        edges = [
            ('A', 'B'), ('B', 'C'), ('C', 'A'),
            ('D', 'E'), ('E', 'F'), ('F', 'D'),
            ('A', 'D'), ('A', 'F'), ('B', 'D'), ('B', 'E'), ('C', 'E'), ('C', 'F'),
        ]
        return cls(positions, edges, name='nested_triangles')

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
            ('A', 'B'), ('B', 'C'), ('C', 'A'),
        ]
        return cls(positions, edges, name='tetrad_3d')

    @classmethod
    def octahedron(cls):
        s = 3.0
        d = 0.5
        positions = {
            'A': ( s + d,  0,      0),     'B': (-s,     0,      0),
            'C': ( 0,      s + d,  0),     'D': ( 0,    -s,      0),
            'E': ( 0,      0,      s + d), 'F': ( 0,     0,     -s),
        }
        edges = [
            ('A', 'C'), ('A', 'D'), ('A', 'E'), ('A', 'F'),
            ('B', 'C'), ('B', 'D'), ('B', 'E'), ('B', 'F'),
            ('C', 'E'), ('C', 'F'), ('D', 'E'), ('D', 'F'),
        ]
        return cls(positions, edges, name='octahedron')

    @classmethod
    def trigonal_bipyramid(cls):
        r = 3.0
        h = r * math.sqrt(2.0 / 3.0)
        s32 = r * math.sqrt(3) / 2
        positions = {
            'A': ( r,      0,    0),
            'B': (-r / 2,  s32,  0),
            'C': (-r / 2, -s32,  0),
            'D': ( 0,      0,    h),
            'E': ( 0,      0,   -h),
        }
        edges = [
            ('A', 'B'), ('A', 'C'), ('B', 'C'),
            ('A', 'D'), ('B', 'D'), ('C', 'D'),
            ('A', 'E'), ('B', 'E'), ('C', 'E'),
        ]
        return cls(positions, edges, name='trigonal_bipyramid')

    @classmethod
    def triangular_prism(cls):
        r = 3.0
        h = 3.0
        t = 2/3
        s32 = r * math.sqrt(3) / 2
        positions = {
            'A': ( r,          0,        0),
            'B': (-r / 2,      s32,      0),
            'C': (-r / 2,     -s32,      0),
            'D': ( r * t,      0,        h),
            'E': (-r / 2 * t,  s32 * t,  h),
            'F': (-r / 2 * t, -s32 * t,  h),
        }
        edges = [
            ('A', 'B'), ('B', 'C'), ('C', 'A'),
            ('D', 'E'), ('E', 'F'), ('F', 'D'),
            ('A', 'D'), ('B', 'E'), ('C', 'F'),
        ]
        return cls(positions, edges, name='triangular_prism')

    @classmethod
    def pentagonal_bipyramid(cls):
        r = 3.0
        h = r * math.sqrt(2.0 / 3.0)
        angles = [2 * math.pi * i / 5 for i in range(5)]
        positions = {
            'A': (r * math.cos(angles[0]), r * math.sin(angles[0]), 0),
            'B': (r * math.cos(angles[1]), r * math.sin(angles[1]), 0),
            'C': (r * math.cos(angles[2]), r * math.sin(angles[2]), 0),
            'D': (r * math.cos(angles[3]), r * math.sin(angles[3]), 0),
            'E': (r * math.cos(angles[4]), r * math.sin(angles[4]), 0),
            'F': (0, 0,  h),
            'G': (0, 0, -h),
        }
        edges = [
            ('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'E'), ('E', 'A'),
            ('A', 'F'), ('B', 'F'), ('C', 'F'), ('D', 'F'), ('E', 'F'),
            ('A', 'G'), ('B', 'G'), ('C', 'G'), ('D', 'G'), ('E', 'G'),
        ]
        return cls(positions, edges, name='pentagonal_bipyramid')

    @classmethod
    def kite_pyramid(cls):
        r = 3.0
        positions = {
            'A': ( 0,        r * 0.85, 0),
            'B': ( r * 0.7,  0,        0),
            'C': ( 0,       -r * 0.5,  0),
            'D': (-r * 0.7,  0,        0),
            'E': ( 0,        0,        r),
        }
        edges = [
            ('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
            ('A', 'E'), ('B', 'E'), ('C', 'E'), ('D', 'E'),
        ]
        return cls(positions, edges, name='kite_pyramid')

    # ------------------------------------------------------------------
    # N-D Named constructors
    # ------------------------------------------------------------------

    @classmethod
    def asterisk_nd(cls):
        r = 3.0
        outer_labels = ['B', 'C', 'D', 'E', 'F']
        n_dims = len(outer_labels)
        positions = {'A': tuple(0.0 for _ in range(n_dims))}
        for i, label in enumerate(outer_labels):
            pos = [0.0] * n_dims
            pos[i] = r
            positions[label] = tuple(pos)
        edges = [('A', lbl) for lbl in outer_labels]
        return cls(positions, edges, name='asterisk_nd')

    @classmethod
    def ogdoad_nd(cls):
        r = 3.0
        outer_labels = ['B', 'C', 'D', 'E', 'F', 'G', 'H']
        n_dims = len(outer_labels)
        positions = {'A': tuple(0.0 for _ in range(n_dims))}
        for i, label in enumerate(outer_labels):
            pos = [0.0] * n_dims
            pos[i] = r
            positions[label] = tuple(pos)
        edges = [('A', lbl) for lbl in outer_labels]
        return cls(positions, edges, name='ogdoad_nd')


MASTER_SETS = {
    'tetrad': MasterSet.tetrad,
    'asterisk': MasterSet.asterisk,
    'centered_pentagon': MasterSet.centered_pentagon,
    'hexagon': MasterSet.hexagon,
    'irregular_hexagon': MasterSet.irregular_hexagon,
    'ogdoad': MasterSet.ogdoad,
    'heptagon': MasterSet.heptagon,
    'kite': MasterSet.kite,
    'arrow': MasterSet.arrow,
    'k23_bipartite': MasterSet.k23_bipartite,
    'wheel5': MasterSet.wheel5,
    'bowtie': MasterSet.bowtie,
    'house': MasterSet.house,
    'wheel4': MasterSet.wheel4,
    'h_shape': MasterSet.h_shape,
    'nested_triangles': MasterSet.nested_triangles,
    'tetrad_3d': MasterSet.tetrad_3d,
    'octahedron': MasterSet.octahedron,
    'trigonal_bipyramid': MasterSet.trigonal_bipyramid,
    'triangular_prism': MasterSet.triangular_prism,
    'pentagonal_bipyramid': MasterSet.pentagonal_bipyramid,
    'kite_pyramid': MasterSet.kite_pyramid,
    'asterisk_nd': MasterSet.asterisk_nd,
    'ogdoad_nd': MasterSet.ogdoad_nd,
}
