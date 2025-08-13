import math
from typing import List, Tuple
from itertools import combinations, permutations

__all__ = [
    'match_pattern',
]

def match_pattern(cps, node_ids: List[int]) -> List[Tuple[int, ...]]:
    """
    Find all groups of nodes that form the same geometric shape as the input nodes.
    
    Args:
        cps: CombinationProductSet instance
        node_ids: List of node IDs that define the reference shape
        
    Returns:
        List of tuples containing node IDs for matching shapes
    """
    if len(node_ids) < 3:
        return []
    
    # Get reference pattern data
    ref_distances, ref_edge_count = _get_distances_and_edges(cps, node_ids)
    if not ref_distances:
        return []
    
    # For simple shapes (triangles), use optimized distance-only matching
    if len(node_ids) <= 3:
        return _find_simple_matches(cps, node_ids, ref_distances, ref_edge_count)
    
    # For complex shapes, use full structural matching
    return _find_complex_matches(cps, node_ids, ref_distances, ref_edge_count)

def _get_distances_and_edges(cps, node_ids: List[int]) -> Tuple[List[float], int]:
    """Get sorted distances and edge count for given nodes."""
    distances = []
    edge_count = 0
    
    for u, v, data in cps.graph.edges(data=True):
        if u in node_ids and v in node_ids:
            edge_count += 1
            if 'distance' in data:
                distances.append(round(data['distance'], 6))
    
    return (sorted(distances) if distances else [], edge_count)

def _find_simple_matches(cps, node_ids: List[int], ref_distances: List[float], ref_edge_count: int) -> List[Tuple[int, ...]]:
    """Optimized matching for simple shapes using distance-only comparison."""
    matches = []
    all_nodes = list(cps.graph.nodes())
    tolerance = 1e-6
    
    for candidate_nodes in combinations(all_nodes, len(node_ids)):
        if set(candidate_nodes) == set(node_ids):
            continue
            
        cand_distances, cand_edge_count = _get_distances_and_edges(cps, list(candidate_nodes))
        
        if (len(ref_distances) == len(cand_distances) and 
            ref_edge_count == cand_edge_count and
            all(abs(d1 - d2) <= tolerance for d1, d2 in zip(ref_distances, cand_distances))):
            matches.append(candidate_nodes)
    
    return matches

def _find_complex_matches(cps, node_ids: List[int], ref_distances: List[float], ref_edge_count: int) -> List[Tuple[int, ...]]:
    """Find matches for complex shapes using connectivity + angle verification."""
    matches = []
    all_nodes = list(cps.graph.nodes())
    
    for candidate_nodes in combinations(all_nodes, len(node_ids)):
        if set(candidate_nodes) == set(node_ids):
            continue
            
        cand_distances, cand_edge_count = _get_distances_and_edges(cps, list(candidate_nodes))
        
        if (len(ref_distances) == len(cand_distances) and 
            ref_edge_count == cand_edge_count and
            _same_connectivity_and_angles(cps, node_ids, list(candidate_nodes))):
            matches.append(candidate_nodes)
    
    return matches

def _same_connectivity_and_angles(cps, nodes1: List[int], nodes2: List[int]) -> bool:
    """Check if two node groups have same connectivity and angle patterns."""
    # Quick connectivity check using degree sequences
    if not _same_degree_sequence(cps, nodes1, nodes2):
        return False
    
    # If degree sequences match, check graph isomorphism
    if not _graph_isomorphic(cps, nodes1, nodes2):
        return False
    
    # Finally verify angle signatures match
    return _angle_signatures_match(cps, nodes1, nodes2)

def _same_degree_sequence(cps, nodes1: List[int], nodes2: List[int]) -> bool:
    """Quick check if two node groups have the same degree sequence."""
    degrees1 = []
    degrees2 = []
    
    # Count degrees for nodes1
    for node in nodes1:
        degree = sum(1 for u, v, data in cps.graph.edges(data=True) 
                    if (u == node and v in nodes1 and 'distance' in data) or 
                       (v == node and u in nodes1 and 'distance' in data))
        degrees1.append(degree)
    
    # Count degrees for nodes2
    for node in nodes2:
        degree = sum(1 for u, v, data in cps.graph.edges(data=True) 
                    if (u == node and v in nodes2 and 'distance' in data) or 
                       (v == node and u in nodes2 and 'distance' in data))
        degrees2.append(degree)
    
    return sorted(degrees1) == sorted(degrees2)

def _graph_isomorphic(cps, nodes1: List[int], nodes2: List[int]) -> bool:
    """Check if two subgraphs are isomorphic using adjacency comparison."""
    # Build adjacency sets
    adj1 = {node: set() for node in nodes1}
    adj2 = {node: set() for node in nodes2}
    
    for u, v, data in cps.graph.edges(data=True):
        if u in nodes1 and v in nodes1 and 'distance' in data:
            adj1[u].add(v)
            adj1[v].add(u)
        if u in nodes2 and v in nodes2 and 'distance' in data:
            adj2[u].add(v)
            adj2[v].add(u)
    
    # Try to find an isomorphic mapping
    for perm in permutations(nodes2):
        mapping = dict(zip(nodes1, perm))
        
        # Check if this mapping preserves adjacency
        if all({mapping[n] for n in adj1[node]} == adj2[mapping[node]] for node in nodes1):
            return True
    
    return False

def _angle_signatures_match(cps, nodes1: List[int], nodes2: List[int]) -> bool:
    """Check if angle signatures match between two node groups."""
    sig1 = _get_angle_signature(cps, nodes1)
    sig2 = _get_angle_signature(cps, nodes2)
    
    if len(sig1) != len(sig2):
        return False
    
    tolerance = 1e-4
    return all(abs(a1 - a2) <= tolerance for a1, a2 in zip(sig1, sig2))

def _get_angle_signature(cps, nodes: List[int]) -> List[float]:
    """Generate rotation-invariant angle signature for a node group."""
    # Extract angles from edges within the group
    angles = []
    for u, v, data in cps.graph.edges(data=True):
        if u in nodes and v in nodes and 'angle' in data:
            angles.append(data['angle'])
    
    if len(angles) < 2:
        return []
    
    angles.sort()
    
    # Calculate pairwise angle differences (rotation-invariant)
    relative_angles = []
    for i in range(len(angles)):
        for j in range(i + 1, len(angles)):
            diff = abs(angles[j] - angles[i])
            # Normalize to [0, π] range
            diff = min(diff, 2 * math.pi - diff)
            relative_angles.append(round(diff, 5))
    
    return sorted(relative_angles)