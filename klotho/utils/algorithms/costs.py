from typing import List, Callable, TypeVar, Any
import pandas as pd
import numpy as np
import networkx as nx
from networkx.algorithms.approximation import greedy_tsp

T = TypeVar('T')

def normalize_sum(values: List[float]) -> List[float]:
    """
    Normalize a list of positive values so they sum to 1 while maintaining their proportions.
    
    Args:
        values: List of positive numerical values
        
    Returns:
        List of normalized values that sum to 1
    """
    total = sum(values)
    if total <= 0:
        raise ValueError("Sum of values must be positive")
    return [v / total for v in values]

def cost_matrix(items: List[T], cost_function: Callable[[T, T], float], **kwargs: Any) -> pd.DataFrame:
    cost_ufunc = np.frompyfunc(lambda a, b: cost_function(a, b, **kwargs), 2, 1)
    arr = cost_ufunc(np.array(items)[:, None], np.array(items)[None, :]).astype(float)
    df = pd.DataFrame(arr, columns=[str(item) for item in items])
    df.insert(0, "", [str(item) for item in items])
    df = df.set_index("").rename_axis(None)
    return df

def cost_matrix_graph(cost_df: pd.DataFrame) -> nx.Graph:
    """
    Convert a cost matrix DataFrame to an undirected networkx graph.
    Edge weights represent the costs between nodes.
    Self-loops are excluded.
    
    Args:
        cost_df: DataFrame containing the cost matrix
        
    Returns:
        networkx Graph with weighted edges
    """
    G = nx.Graph()
    
    for i, value in enumerate(cost_df.columns):
        G.add_node(i, value=value)
    
    for i in range(len(cost_df.columns)):
        for j in range(i + 1, len(cost_df.columns)):
            cost = cost_df.iloc[i, j]
            if cost > 0:
                G.add_edge(i, j, weight=cost)
    
    return G

def minimum_cost_path(G: nx.Graph, start: int, end: int | None = None) -> List[int]:
    if start not in G.nodes():
        raise ValueError(f"Start node {start} not in graph")
    
    if end is not None:
        if end not in G.nodes():
            raise ValueError(f"End node {end} not in graph")
        
        nodes_to_visit = set(G.nodes()) - {start, end}
        path = [start]
        current = start
        
        while nodes_to_visit:
            next_node = min(nodes_to_visit, key=lambda x: G[current][x]['weight'])
            path.append(next_node)
            nodes_to_visit.remove(next_node)
            current = next_node
            
        path.append(end)
        return path
    
    return greedy_tsp(G, source=start)
