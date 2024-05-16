import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from allopy.chronos import rhythm_trees as r_trees
from allopy.chronos.rhythm_trees.rt_algorithms import *
from utils.data_structures.graphs import Graph

rts = [
    # r_trees.RT(time_signature='4/4', subdivisions=(3,(1,(2,1)),2,1,(1,(1,1,1)))),
    # r_trees.RT(time_signature='15/16', subdivisions=(3,2,1,3,1,2,3)),
    r_trees.RT(time_signature='4/3', subdivisions=((4,(3,(8,(3,4)))),-3)),
    # r_trees.RT(time_signature='7/5', subdivisions=((4,(1,1,1)),(3,(1,)*8),-5)),
    # r_trees.RT(time_signature='21/12', subdivisions=(11,7,5,3)),
]

g = Graph(rts[0].time_signature, rts[0].subdivisions)
g.sum_children(list(g.G.in_degree())[0][0])

