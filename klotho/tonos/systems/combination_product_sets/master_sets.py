import sympy as sp
import math

__all__ = [
    'ALPHA_SYMBOLS',
    'MASTER_SETS',
]

ALPHA_SYMBOLS = {chr(65 + i): sp.Symbol(chr(65 + i)) for i in range(26)}

MASTER_SETS = {
  'tetrad': {
    # Generating
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 7/6, 'distance': math.sqrt(3.0), 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 0/1, 'distance': math.sqrt(3.0), 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 1/2, 'distance': math.sqrt(3.0), 'elevation': None},
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 4/3, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 5/3, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 1/1, 'distance': 3.0, 'elevation': None},

    # Reciprocal
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 1/6, 'distance': math.sqrt(3.0), 'elevation': None},
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 1/1, 'distance': math.sqrt(3.0), 'elevation': None},
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 3/2, 'distance': math.sqrt(3.0), 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 1/3, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 2/3, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 0/1, 'distance': 3.0, 'elevation': None},
  },
  'asterisk': {
    # Generating Hexad (X/A relationships)
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 3/2,   'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 11/10, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 7/10,  'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['E'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 3/10,  'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['F'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 19/10, 'distance': 3.0, 'elevation': None},
    
    # Reciprocal Hexad (A/X relationships)
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 1/2,   'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 1/10,  'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 17/10, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['E']: {'angle': math.pi * 13/10, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['F']: {'angle': math.pi * 9/10,  'distance': 3.0, 'elevation': None},
  },
  'centered_pentagon': {
    # Generating
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['F']: {'angle': math.pi * 6/5, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 9/5, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['F'] / ALPHA_SYMBOLS['E']: {'angle': math.pi * 8/5, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 7/5, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['E'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 0/1, 'distance': 3.0, 'elevation': None},

    # Reciprocal
    ALPHA_SYMBOLS['F'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 1/5, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 4/5, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['E'] / ALPHA_SYMBOLS['F']: {'angle': math.pi * 3/5, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 2/5, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['E']: {'angle': math.pi * 1/1, 'distance': 3.0, 'elevation': None}
  },
  'hexagon': {
    # Generating
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['F']: {'angle': math.pi * 5/4,   'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 7/4,   'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['F'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 17/12, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 19/12, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['E']: {'angle': math.pi * 23/12, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['E']: {'angle': math.pi * 13/12, 'distance': 3.0, 'elevation': None},
    
    # Reciprocal
    ALPHA_SYMBOLS['F'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 1/4,   'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 3/4,   'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['F']: {'angle': math.pi * 5/12,  'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 7/12,  'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['E'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 11/12, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['E'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 1/12,  'distance': 3.0, 'elevation': None},
  },
  'irregular_hexagon': {
    # Generating
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['F']: {'angle': math.pi * 5/4,   'distance': 3.0 + 0.0, 'elevation': None},
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 7/4,   'distance': 3.0 + 0.0, 'elevation': None},
    ALPHA_SYMBOLS['F'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 17/12, 'distance': 3.0 - 0.25, 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 19/12, 'distance': 3.0 - 0.25, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['E']: {'angle': math.pi * 23/12, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['E']: {'angle': math.pi * 13/12, 'distance': 3.0, 'elevation': None},

    # Reciprocal
    ALPHA_SYMBOLS['F'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 1/4,   'distance': 3.0 + 0.0, 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 3/4,   'distance': 3.0 + 0.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['F']: {'angle': math.pi * 5/12,  'distance': 3.0 - 0.25, 'elevation': None},
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 7/12,  'distance': 3.0 - 0.25, 'elevation': None},
    ALPHA_SYMBOLS['E'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 11/12, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['E'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 1/12,  'distance': 3.0, 'elevation': None},
  },
  'ogdoad': {
    # Generating
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['B']: {'angle': math.pi * 1/2,   'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['C']: {'angle': math.pi * 3/14,  'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['D']: {'angle': math.pi * 27/14, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['E']: {'angle': math.pi * 23/14, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['F']: {'angle': math.pi * 19/14, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['G']: {'angle': math.pi * 15/14, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['A'] / ALPHA_SYMBOLS['H']: {'angle': math.pi * 11/14, 'distance': 3.0, 'elevation': None},

    # Reciprocal
    ALPHA_SYMBOLS['B'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 3/2,   'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['C'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 17/14, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['D'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 13/14, 'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['E'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 9/14,  'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['F'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 5/14,  'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['G'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 1/14,  'distance': 3.0, 'elevation': None},
    ALPHA_SYMBOLS['H'] / ALPHA_SYMBOLS['A']: {'angle': math.pi * 25/14, 'distance': 3.0, 'elevation': None},
  }
} 