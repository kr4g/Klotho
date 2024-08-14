import random
from collections import defaultdict
from allopy.topos.graphs import CombNet

class CombNetTraversal:
    def __init__(self, combnet: CombNet):
        self.combnet = combnet
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

        # Group neighbors by weight and visit count
        candidates = defaultdict(lambda: defaultdict(list))
        for neighbor, weight in neighbors.items():
            visit_count = self.visited_edges[self.edge_key(current_node, neighbor)]
            candidates[weight][visit_count].append(neighbor)

        # Sort weights in descending order
        sorted_weights = sorted(candidates.keys(), reverse=True)

        for weight in sorted_weights:
            visit_counts = sorted(candidates[weight].keys())
            for visit_count in visit_counts:
                if candidates[weight][visit_count]:
                    return random.choice(candidates[weight][visit_count])

        return None

    def edge_key(self, node1, node2):
        return tuple(sorted([node1, node2]))
