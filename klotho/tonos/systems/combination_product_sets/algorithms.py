import math
from typing import List, Tuple, Dict, Set
from itertools import combinations, permutations

__all__ = [
    'match_pattern',
]

class _GraphCache:
    """Cache for expensive graph computations to avoid repeated work."""
    
    def __init__(self, cps):
        self.cps = cps
        self._adjacency = None
        self._distances = None
        self._angles = None
        self._relations = None
        self._node_degrees = None
        self._external_connections = None
        
    def _build_caches(self):
        """Build all cache structures in one pass through edges."""
        if self._adjacency is not None:
            return
            
        self._adjacency = {}
        self._distances = {}
        self._angles = {}
        self._relations = {}
        self._node_degrees = {}
        self._external_connections = {}
        
        for node in self.cps.graph.nodes():
            self._adjacency[node] = set()
            self._node_degrees[node] = 0
            self._external_connections[node] = []
        
        for u, v, data in self.cps.graph.edges(data=True):
            self._adjacency[u].add(v)
            self._adjacency[v].add(u)
            self._node_degrees[u] += 1
            self._node_degrees[v] += 1
            
            edge_key = (min(u, v), max(u, v))
            if 'distance' in data:
                self._distances[edge_key] = round(data['distance'], 6)
            if 'angle' in data:
                self._angles[edge_key] = data['angle']
            if 'relation' in data:
                self._relations[edge_key] = str(data['relation'])
    
    def get_distances_and_edges(self, node_ids: List[int]) -> Tuple[List[float], int]:
        """Get sorted distances and edge count for given nodes."""
        self._build_caches()
        distances = []
        edge_count = 0
        node_set = set(node_ids)
        
        for i, u in enumerate(node_ids):
            for v in node_ids[i+1:]:
                if v in self._adjacency[u]:
                    edge_count += 1
                    edge_key = (min(u, v), max(u, v))
                    if edge_key in self._distances:
                        distances.append(self._distances[edge_key])
        
        return (sorted(distances), edge_count)
    
    def is_connected(self, u: int, v: int) -> bool:
        """Check if two nodes are connected."""
        self._build_caches()
        return v in self._adjacency[u]
    
    def get_node_degree(self, node: int, node_set: Set[int]) -> int:
        """Get degree of node within a specific set."""
        self._build_caches()
        return sum(1 for neighbor in self._adjacency[node] if neighbor in node_set)
    
    def get_angle_data(self, nodes: List[int]) -> Tuple[List[float], List[str]]:
        """Get angles and relations for edges within node set."""
        self._build_caches()
        angles = []
        relations = []
        node_set = set(nodes)
        
        for i, u in enumerate(nodes):
            for v in nodes[i+1:]:
                if v in self._adjacency[u]:
                    edge_key = (min(u, v), max(u, v))
                    if edge_key in self._angles:
                        angles.append(self._angles[edge_key])
                    if edge_key in self._relations:
                        relations.append(self._relations[edge_key])
        
        return angles, relations
    
    def get_external_neighbors(self, node: int, node_set: Set[int]) -> List[int]:
        """Get external neighbors of a node."""
        self._build_caches()
        return [neighbor for neighbor in self._adjacency[node] if neighbor not in node_set]
    
    def get_external_angles(self, nodes: List[int]) -> List[float]:
        """Get all external connection angles for a node set."""
        self._build_caches()
        node_set = set(nodes)
        external_angles = []
        
        for node in nodes:
            for neighbor in self._adjacency[node]:
                if neighbor not in node_set:
                    edge_key = (min(node, neighbor), max(node, neighbor))
                    if edge_key in self._angles:
                        external_angles.append(self._angles[edge_key])
        
        return external_angles

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
    
    graph_cache = _GraphCache(cps)
    ref_distances, ref_edge_count = graph_cache.get_distances_and_edges(node_ids)
    if not ref_distances:
        return []
    
    return _find_enhanced_matches(graph_cache, node_ids, ref_distances, ref_edge_count)

def _find_enhanced_matches(cache: _GraphCache, node_ids: List[int], ref_distances: List[float], ref_edge_count: int) -> List[Tuple[int, ...]]:
    """Unified matching using proven layered approach for all pattern sizes."""
    matches = []
    all_nodes = list(cache.cps.graph.nodes())
    tolerance = 1e-8
    
    for candidate_nodes in combinations(all_nodes, len(node_ids)):
        if set(candidate_nodes) == set(node_ids):
            continue
            
        cand_distances, cand_edge_count = cache.get_distances_and_edges(list(candidate_nodes))
        
        if (len(ref_distances) == len(cand_distances) and 
            ref_edge_count == cand_edge_count and
            all(abs(r - c) <= tolerance for r, c in zip(ref_distances, cand_distances)) and
            _enhanced_connectivity_and_angles(cache, node_ids, list(candidate_nodes))):
                matches.append(candidate_nodes)
    
    return matches

def _enhanced_connectivity_and_angles(cache: _GraphCache, nodes1: List[int], nodes2: List[int]) -> bool:
    """Unified layered filtering - works for all pattern sizes and CPS types."""
    if not _same_degree_sequence(cache, nodes1, nodes2):
        return False
    
    if not _graph_isomorphic(cache, nodes1, nodes2):
        return False
    
    if not _angle_signatures_match(cache, nodes1, nodes2):
        return False
    
    return _has_role_preserving_permutation(cache, nodes1, nodes2)

def _same_degree_sequence(cache: _GraphCache, nodes1: List[int], nodes2: List[int]) -> bool:
    """Quick check if two node groups have the same degree sequence."""
    nodes1_set = set(nodes1)
    nodes2_set = set(nodes2)
    
    degrees1 = [cache.get_node_degree(node, nodes1_set) for node in nodes1]
    degrees2 = [cache.get_node_degree(node, nodes2_set) for node in nodes2]
    
    return sorted(degrees1) == sorted(degrees2)

def _graph_isomorphic(cache: _GraphCache, nodes1: List[int], nodes2: List[int]) -> bool:
    """Check if two subgraphs are isomorphic using adjacency comparison."""
    adj1 = {node: set() for node in nodes1}
    adj2 = {node: set() for node in nodes2}
    
    for i, u in enumerate(nodes1):
        for v in nodes1[i+1:]:
            if cache.is_connected(u, v):
                adj1[u].add(v)
                adj1[v].add(u)
    
    for i, u in enumerate(nodes2):
        for v in nodes2[i+1:]:
            if cache.is_connected(u, v):
                adj2[u].add(v)
                adj2[v].add(u)
    
    degree_sequence1 = sorted([len(adj1[node]) for node in nodes1])
    degree_sequence2 = sorted([len(adj2[node]) for node in nodes2])
    
    if degree_sequence1 != degree_sequence2:
        return False
    
    for perm in permutations(nodes2):
        mapping = dict(zip(nodes1, perm))
        
        if all({mapping[n] for n in adj1[node]} == adj2[mapping[node]] for node in nodes1):
            return True
    
    return False

def _angle_signatures_match(cache: _GraphCache, nodes1: List[int], nodes2: List[int]) -> bool:
    """Check if signatures match between two node groups (angles + external context)."""
    sig1 = _get_angle_signature(cache, nodes1)
    sig2 = _get_angle_signature(cache, nodes2)
    
    angles1, relations1, context1 = sig1
    angles2, relations2, context2 = sig2
    
    if len(angles1) != len(angles2):
        return False
    
    tolerance = 1e-8
    angles_match = all(abs(a1 - a2) <= tolerance for a1, a2 in zip(angles1, angles2))
    
    context_match = context1 == context2
    
    return angles_match and context_match

def _get_angle_signature(cache: _GraphCache, nodes: List[int]) -> tuple:
    """Generate signature including internal angles and external context."""
    angles, relations = cache.get_angle_data(nodes)

    if len(angles) < 2:
        return ([], [], [])

    angles.sort()
    relations.sort()

    relative_angles = []
    for i in range(len(angles)):
        for j in range(i + 1, len(angles)):
            diff = abs(angles[j] - angles[i])
            diff = min(diff, 2 * math.pi - diff)
            relative_angles.append(round(diff, 8))

    nodes_set = set(nodes)
    external_context = []
    
    for node in sorted(nodes):
        external_neighbors = cache.get_external_neighbors(node, nodes_set)
        external_neighbor_degrees = []
        
        for neighbor in external_neighbors:
            neighbor_degree = cache._node_degrees[neighbor]
            external_neighbor_degrees.append(neighbor_degree)
        
        external_neighbor_degrees.sort()
        external_context.append(tuple(external_neighbor_degrees))

    return (sorted(relative_angles), relations, sorted(external_context))

def _has_role_preserving_permutation(cache: _GraphCache, target: List[int], candidate: List[int]) -> bool:
    """Check if candidate has a permutation that preserves the role structure of target."""
    target_connectivity = _get_connectivity_pattern(cache, target)
    
    matching_perms = []
    for perm in permutations(candidate):
        if _get_connectivity_pattern(cache, list(perm)) == target_connectivity:
            matching_perms.append(list(perm))
    
    for perm in matching_perms:
        if _external_context_matches(cache, target, perm):
            return True
    
    return False

def _get_connectivity_pattern(cache: _GraphCache, nodes: List[int]) -> tuple:
    """Get the connectivity pattern showing which positions connect to which."""
    pattern = []
    
    for i, node in enumerate(nodes):
        connections = []
        for j, other in enumerate(nodes):
            if i != j and cache.is_connected(node, other):
                connections.append(j)
        pattern.append(tuple(connections))
    
    return tuple(pattern)

def _external_context_matches(cache: _GraphCache, target: List[int], candidate: List[int]) -> bool:
    """Check if the relative angular patterns of external connections match."""
    if len(target) != len(candidate):
        return False
    
    target_ext_angles = cache.get_external_angles(target)
    candidate_ext_angles = cache.get_external_angles(candidate)
    
    if len(target_ext_angles) != len(candidate_ext_angles):
        return False
    
    target_ext_angles.sort()
    candidate_ext_angles.sort()
    
    target_rel_diffs = []
    for i in range(len(target_ext_angles)):
        next_i = (i + 1) % len(target_ext_angles)
        diff = target_ext_angles[next_i] - target_ext_angles[i]
        if diff < 0:
            diff += 2 * 3.14159265359
        target_rel_diffs.append(diff)
    
    candidate_rel_diffs = []
    for i in range(len(candidate_ext_angles)):
        next_i = (i + 1) % len(candidate_ext_angles)
        diff = candidate_ext_angles[next_i] - candidate_ext_angles[i]
        if diff < 0:
            diff += 2 * 3.14159265359
        candidate_rel_diffs.append(diff)
    
    target_rel_diffs.sort()
    candidate_rel_diffs.sort()
    
    tolerance = 1e-8
    if len(target_rel_diffs) != len(candidate_rel_diffs):
        return False
    
    for t_diff, c_diff in zip(target_rel_diffs, candidate_rel_diffs):
        if abs(t_diff - c_diff) > tolerance:
            return False
    
    return True