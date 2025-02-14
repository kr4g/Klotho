import random
from collections import defaultdict
from ..networks import ComboNet
from klotho.tonos.combination_product_sets import CombinationProductSet
from typing import Union

class ComboNetTraversal:
    def __init__(self, combnet: Union[ComboNet, CombinationProductSet]):
        self.combnet = combnet if isinstance(combnet, ComboNet) else ComboNet(combnet)
        self.visited_edges = defaultdict(int)

    def play(self, start_node, num_steps):
        current_node = start_node
        path = [current_node]

        for _ in range(num_steps):
            next_node = self.choose_next_node(current_node)
            if next_node is None:
                print("No more available moves. Game over.")
                break
            
            path.append(next_node)
            self.visited_edges[self.edge_key(current_node, next_node)] += 1
            current_node = next_node

        return path

    def choose_next_node(self, current_node):
        neighbors = self.combnet.graph[current_node]
        if not neighbors:
            return None

        candidates = defaultdict(lambda: defaultdict(list))
        for neighbor, weight in neighbors.items():
            visit_count = self.visited_edges[self.edge_key(current_node, neighbor)]
            candidates[weight][visit_count].append(neighbor)

        sorted_weights = sorted(candidates.keys(), reverse=True)

        for weight in sorted_weights:
            visit_counts = sorted(candidates[weight].keys())
            for visit_count in visit_counts:
                if candidates[weight][visit_count]:
                    return random.choice(candidates[weight][visit_count])

        return None

    def edge_key(self, node1, node2):
        return tuple(sorted([node1, node2]))