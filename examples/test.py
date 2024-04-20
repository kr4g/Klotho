import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from utils.algorithms.tree_algorithms import *

_G = {
    (4, (3,)): [3, 4],
    (4, (6,)): [6, 4],
    (2, (3,)): [3, 2],
    (4, (5,)): [5, 4],
    (3, (5,)): [5, 3],
    (3, (7,)): [7, 6],
    (7, (6,)): [6, 7],
    (2, (5,)): [5, 4],
    (7, (5,)): [10, 7],
    (5, (7,)): [7, 5],
    (3, (8,)): [4, 3],
}
for k, v in _G.items():
    r = get_group_subdivision(k)
    print(f'G: {k}, out: {r}, expected: {v}')