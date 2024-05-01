import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from allopy.chronos import rhythm_trees as r_trees
from allopy.chronos.rhythm_trees.rt_algorithms import *

# _G = {
#     (4, (7,)): [7, 4],
#     (3, (8,)): [4, 3],
#     (8, (7,)): [7, 8],
#     (4, (3,)): [3, 4],
#     (4, (6,)): [6, 4],
#     (2, (3,)): [3, 2],
#     (4, (5,)): [5, 4],
#     (3, (5,)): [5, 3],
#     (3, (7,)): [7, 6],
#     (7, (6,)): [6, 7],
#     (2, (5,)): [5, 4],
#     (7, (5,)): [10, 7],
#     (5, (7,)): [7, 5],
# }
# for k, v in _G.items():
#     r = get_group_subdivision(k)
#     print(f'G: {k}, out: {r}\n')#, expected: {v}\n')

rts = [
    r_trees.RT(time_signature='4/4', subdivisions=(3,(1,(2,1)),2,1,(1,(1,1,1)))),
    r_trees.RT(time_signature='15/16', subdivisions=(3,2,1,3,1,2,3)),
    r_trees.RT(time_signature='4/3', subdivisions=((4,(3,(8,(3,4)))),-3)),
    r_trees.RT(time_signature='7/5', subdivisions=((4,(1,1,1)),(3,(1,)*8),-5)),
    r_trees.RT(time_signature='21/12', subdivisions=(11,7,5,3)),
]

for rt in rts:
    # print(notate(rt), end='\n\n')
    print(rt, end='\n\n')