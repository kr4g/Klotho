import math
import numpy as np
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
    
    # Post-process: sort matches by rotational relationship to target
    return _sort_matches_by_rotation(cps, node_ids, matches)

def _find_complex_matches(cps, node_ids: List[int], ref_distances: List[float], ref_edge_count: int) -> List[Tuple[int, ...]]:
    """Find matches for complex shapes using connectivity + angle verification."""
    matches = []
    all_nodes = list(cps.graph.nodes())
    tolerance = 1e-8
    
    for candidate_nodes in combinations(all_nodes, len(node_ids)):
        if set(candidate_nodes) == set(node_ids):
            continue
            
        cand_distances, cand_edge_count = _get_distances_and_edges(cps, list(candidate_nodes))
        
        if (len(ref_distances) == len(cand_distances) and 
            ref_edge_count == cand_edge_count and
            all(abs(r - c) <= tolerance for r, c in zip(ref_distances, cand_distances)) and
                         _same_connectivity_and_angles(cps, node_ids, list(candidate_nodes))):
                matches.append(candidate_nodes)
    
    # Post-process: sort matches by rotational relationship to target
    return _sort_matches_by_rotation(cps, node_ids, matches)

def _same_connectivity_and_angles(cps, nodes1: List[int], nodes2: List[int]) -> bool:
    """Check if two node groups have same connectivity and angle patterns."""
    # Quick connectivity check using degree sequences
    if not _same_degree_sequence(cps, nodes1, nodes2):
        return False
    
    # If degree sequences match, check graph isomorphism
    if not _graph_isomorphic(cps, nodes1, nodes2):
        return False
    
    # Use angle signatures for complex patterns that need extra discrimination
    # Simple 4-node Hexany patterns work with graph isomorphism alone
    # All other complex patterns (5+ nodes, 6+ nodes, complex 4-node Eikosany) need angle signatures
    if len(nodes1) >= 5 or (len(nodes1) == 4 and len(list(cps.graph.nodes())) > 6):
        if not _angle_signatures_match(cps, nodes1, nodes2):
            return False
        # For complex patterns, use proper geometric matching with reordering
        return _geometric_angle_matching(cps, nodes1, nodes2)
    
    return True

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
    
    tolerance = 1e-12
    return all(abs(a1 - a2) <= tolerance for a1, a2 in zip(sig1, sig2))

def _get_angle_signature(cps, nodes: List[int]) -> List[float]:
    """Generate rotation-invariant angle signature for a node group."""
    angles = []
    for u, v, data in cps.graph.edges(data=True):
        if u in nodes and v in nodes and 'angle' in data:
                angles.append(data['angle'])

    if len(angles) < 2:
        return []

    angles.sort()

    # Use pairwise differences for good discrimination
    relative_angles = []
    for i in range(len(angles)):
        for j in range(i + 1, len(angles)):
            diff = abs(angles[j] - angles[i])
            diff = min(diff, 2 * math.pi - diff)  # Normalize to [0, π]
            relative_angles.append(round(diff, 5))
    
    return sorted(relative_angles)

def _enhanced_external_context_matches(cps, nodes1: List[int], nodes2: List[int]) -> bool:
    """Enhanced external context matching for complex patterns."""
    # Try all permutations to find role-preserving mapping
    for perm in permutations(nodes2):
        if _external_context_matches_permutation(cps, nodes1, list(perm)):
            return True
    return False

def _external_context_matches_permutation(cps, target_nodes: List[int], candidate_nodes: List[int]) -> bool:
    """Check if external context matches for a specific permutation."""
    for target_node, candidate_node in zip(target_nodes, candidate_nodes):
        # Get external neighbors (neighbors not in the pattern)
        target_externals = [n for n in cps.graph.neighbors(target_node) if n not in target_nodes]
        candidate_externals = [n for n in cps.graph.neighbors(candidate_node) if n not in candidate_nodes]
        
        # Must have same number of external connections
        if len(target_externals) != len(candidate_externals):
            return False
        
        # Check how external neighbors connect back to the pattern
        target_pattern_connections = 0
        candidate_pattern_connections = 0
        
        for ext_node in target_externals:
            target_pattern_connections += sum(1 for tn in target_nodes if tn != target_node and cps.graph.has_edge(ext_node, tn))
        
        for ext_node in candidate_externals:
            candidate_pattern_connections += sum(1 for cn in candidate_nodes if cn != candidate_node and cps.graph.has_edge(ext_node, cn))
        
        if target_pattern_connections != candidate_pattern_connections:
            return False
    
    return True

def _direct_geometric_equivalence(cps, nodes1: List[int], nodes2: List[int]) -> bool:
    """Check if two patterns are geometrically equivalent by comparing distance matrices."""
    # Get distance matrix for target pattern
    target_matrix = _get_distance_matrix(cps, nodes1)
    
    # Try all permutations of candidate to find a matching arrangement
    for perm in permutations(nodes2):
        candidate_matrix = _get_distance_matrix(cps, list(perm))
        if _matrices_match(target_matrix, candidate_matrix):
            return True
    
    return False

def _get_distance_matrix(cps, nodes: List[int]) -> List[List[float]]:
    """Get the full distance matrix for a set of nodes."""
    n = len(nodes)
    matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):
            # Try to get distance from edge data
            if cps.graph.has_edge(nodes[i], nodes[j]):
                try:
                    edge_data = cps.graph[nodes[i]][nodes[j]]
                    if 'distance' in edge_data:
                        distance = edge_data['distance']
                    else:
                        distance = 1.0  # Default distance
                except (KeyError, TypeError):
                    distance = 1.0  # Fallback distance
            else:
                distance = float('inf')  # No direct connection
            
            matrix[i][j] = distance
            matrix[j][i] = distance
    
    return matrix

def _matrices_match(matrix1: List[List[float]], matrix2: List[List[float]], tolerance: float = 1e-10) -> bool:
    """Check if two distance matrices are equivalent within tolerance."""
    if len(matrix1) != len(matrix2):
        return False
    
    n = len(matrix1)
    for i in range(n):
        for j in range(n):
            if abs(matrix1[i][j] - matrix2[i][j]) > tolerance:
                return False
    
    return True

def _filter_by_strict_external_context(cps, target_nodes: List[int], matches: List[Tuple[int, ...]]) -> List[Tuple[int, ...]]:
    """Apply much stricter external context verification using multi-hop neighborhood analysis."""
    if not matches:
        return matches
    
    valid_matches = []
    
    for match in matches:
        candidate_nodes = list(match)
        
        # Try all permutations to find a valid role-preserving mapping
        if _has_strict_role_preserving_mapping(cps, target_nodes, candidate_nodes):
            valid_matches.append(match)
    
    return valid_matches

def _has_strict_role_preserving_mapping(cps, target_nodes: List[int], candidate_nodes: List[int]) -> bool:
    """Check if there exists a permutation that preserves all structural roles and contexts."""
    # First check connectivity pattern matching
    target_pattern = _get_connectivity_pattern_detailed(cps, target_nodes)
    candidate_pattern = _get_connectivity_pattern_detailed(cps, candidate_nodes)
    
    if target_pattern != candidate_pattern:
        return False
    
    # For each valid connectivity-preserving permutation, check external context
    for perm in permutations(candidate_nodes):
        if _external_context_strictly_matches(cps, target_nodes, list(perm)):
            return True
    
    return False

def _get_connectivity_pattern_detailed(cps, nodes: List[int]) -> tuple:
    """Get detailed connectivity pattern including multi-hop information."""
    pattern = []
    for i, node in enumerate(nodes):
        # Internal connections within the pattern
        internal_connections = []
        for j, other_node in enumerate(nodes):
            if i != j and cps.graph.has_edge(node, other_node):
                internal_connections.append(j)
        
        # External connections (neighbors not in pattern)
        external_neighbors = []
        for neighbor in cps.graph.neighbors(node):
            if neighbor not in nodes:
                external_neighbors.append(neighbor)
        
        # Multi-hop context: neighbors of external neighbors
        extended_context = set()
        for ext_neighbor in external_neighbors:
            for second_hop in cps.graph.neighbors(ext_neighbor):
                if second_hop not in nodes and second_hop != node:
                    extended_context.add(second_hop)
        
        pattern.append((
            tuple(sorted(internal_connections)),
            len(external_neighbors),
            len(extended_context)
        ))
    
    return tuple(pattern)

def _external_context_strictly_matches(cps, target_nodes: List[int], candidate_nodes: List[int]) -> bool:
    """Very strict external context matching including neighborhood properties."""
    for target_node, candidate_node in zip(target_nodes, candidate_nodes):
        # Get external neighbors
        target_externals = [n for n in cps.graph.neighbors(target_node) if n not in target_nodes]
        candidate_externals = [n for n in cps.graph.neighbors(candidate_node) if n not in candidate_nodes]
        
        if len(target_externals) != len(candidate_externals):
            return False
        
        # Check if external neighborhoods have the same structure
        target_ext_degrees = sorted([len(list(cps.graph.neighbors(n))) for n in target_externals])
        candidate_ext_degrees = sorted([len(list(cps.graph.neighbors(n))) for n in candidate_externals])
        
        if target_ext_degrees != candidate_ext_degrees:
            return False
        
        # Check how many external neighbors connect to other pattern nodes
        target_cross_connections = 0
        for ext_node in target_externals:
            target_cross_connections += sum(1 for tn in target_nodes if tn != target_node and cps.graph.has_edge(ext_node, tn))
        
        candidate_cross_connections = 0
        for ext_node in candidate_externals:
            candidate_cross_connections += sum(1 for cn in candidate_nodes if cn != candidate_node and cps.graph.has_edge(ext_node, cn))
        
        if target_cross_connections != candidate_cross_connections:
            return False
    
    return True

def _geometric_angle_matching(cps, target_nodes: List[int], candidate_nodes: List[int]) -> bool:
    """Check if candidate can match target through proper geometric reordering and angle comparison."""
    # Get the connectivity pattern for target to find valid reorderings
    target_connectivity = _get_connectivity_pattern_simple(cps, target_nodes)
    
    # Try all permutations of candidate that preserve the connectivity pattern
    for perm in permutations(candidate_nodes):
        candidate_connectivity = _get_connectivity_pattern_simple(cps, list(perm))
        
        # Only consider permutations that preserve the structural roles
        if candidate_connectivity == target_connectivity:
            # Now check if the actual edge angles match between target and this permutation
            if _edge_angles_match(cps, target_nodes, list(perm)):
                return True
    
    return False

def _get_connectivity_pattern_simple(cps, nodes: List[int]) -> tuple:
    """Get the connectivity pattern showing which positions connect to which."""
    pattern = []
    for i, node in enumerate(nodes):
        connections = []
        for j, other_node in enumerate(nodes):
            if i != j and cps.graph.has_edge(node, other_node):
                connections.append(j)
        pattern.append(tuple(sorted(connections)))
    return tuple(pattern)

def _edge_angles_match(cps, target_nodes: List[int], candidate_nodes: List[int], tolerance: float = 0.1) -> bool:
    """Check if the actual edge angles match between two node patterns with consistent rotation."""
    # Get all edges and their angles for both patterns
    target_edges = []
    candidate_edges = []
    
    for i in range(len(target_nodes)):
        for j in range(i + 1, len(target_nodes)):
            target_edge = (target_nodes[i], target_nodes[j])
            candidate_edge = (candidate_nodes[i], candidate_nodes[j])
            
            # Check if both edges exist or both don't exist
            target_has_edge = cps.graph.has_edge(*target_edge)
            candidate_has_edge = cps.graph.has_edge(*candidate_edge)
            
            if target_has_edge != candidate_has_edge:
                return False
            
            # If both have edges, collect their angles
            if target_has_edge:
                try:
                    target_data = cps.graph.edges[target_edge[0], target_edge[1]]
                    candidate_data = cps.graph.edges[candidate_edge[0], candidate_edge[1]]
                    
                    target_angle = target_data.get('angle', 0.0)
                    candidate_angle = candidate_data.get('angle', 0.0)
                    
                    target_edges.append(target_angle)
                    candidate_edges.append(candidate_angle)
                except (KeyError, TypeError):
                    return False
    
    # Now check if there's a single rotation that makes ALL angles match
    return _find_consistent_rotation(target_edges, candidate_edges, tolerance)

def _find_consistent_rotation(target_angles: List[float], candidate_angles: List[float], tolerance: float) -> bool:
    """Check if there's a single rotation that makes all angle pairs match."""
    if len(target_angles) != len(candidate_angles):
        return False
    
    if not target_angles:  # No edges to compare
        return True
    
    # Generate rotations based on musical intervals (semitones)
    # Use 12-tone equal temperament divisions plus some finer divisions
    rotations = []
    for i in range(144):  # 144 = 12 * 12, covers all possible musical rotations with fine granularity
        rotation = i * 2 * math.pi / 144  # 2.5-degree increments
        rotations.append(rotation)
    
    # Check each possible rotation
    for rotation in rotations:
        all_match = True
        for target_angle, candidate_angle in zip(target_angles, candidate_angles):
            # Apply rotation to candidate angle
            rotated_candidate = (candidate_angle + rotation) % (2 * math.pi)
            
            # Check if it matches target angle (considering wraparound)
            diff = abs(target_angle - rotated_candidate)
            diff = min(diff, 2 * math.pi - diff)  # Handle wraparound
            
            if diff > tolerance:
                all_match = False
                break
        
        if all_match:
            return True
    
    return False

def _sort_matches_by_rotation(cps, target_nodes: List[int], matches: List[Tuple[int, ...]]) -> List[Tuple[int, ...]]:
    """Sort matches by their rotational relationship to the target pattern."""
    if not matches:
        return matches
    
    # Calculate rotation offset for each match
    match_rotations = []
    for match in matches:
        rotation_offset = _calculate_rotation_offset(cps, target_nodes, list(match))
        match_rotations.append((match, rotation_offset))
    
    # Sort by rotation offset (consistent rotational progression)
    match_rotations.sort(key=lambda x: x[1])
    
    # Return just the matches in rotational order
    return [match[0] for match in match_rotations]

def _calculate_rotation_offset(cps, target_nodes: List[int], candidate_nodes: List[int]) -> float:
    """Calculate the rotational offset of candidate relative to target."""
    target_connectivity = _get_connectivity_pattern_simple(cps, target_nodes)
    
    # Try all valid permutations and find the one with the most meaningful rotation
    best_rotation = 0.0
    best_quality = -1
    
    for perm in permutations(candidate_nodes):
        candidate_connectivity = _get_connectivity_pattern_simple(cps, list(perm))
        if candidate_connectivity == target_connectivity:
            # This permutation preserves connectivity, now check rotation quality
            rotation, quality = _calculate_permutation_rotation_quality(cps, target_nodes, list(perm))
            
            if quality > best_quality:
                best_quality = quality
                best_rotation = rotation
    
    return best_rotation

def _calculate_permutation_rotation_quality(cps, target_nodes: List[int], candidate_perm: List[int]) -> tuple:
    """Calculate rotation and quality score for a specific permutation."""
    target_edges = []
    candidate_edges = []
    
    # Collect edge angles from this specific permutation
    for i in range(len(target_nodes)):
        for j in range(i + 1, len(target_nodes)):
            target_has_edge = cps.graph.has_edge(target_nodes[i], target_nodes[j])
            candidate_has_edge = cps.graph.has_edge(candidate_perm[i], candidate_perm[j])
            
            if target_has_edge and candidate_has_edge:
                try:
                    target_data = cps.graph.edges[target_nodes[i], target_nodes[j]]
                    candidate_data = cps.graph.edges[candidate_perm[i], candidate_perm[j]]
                    
                    target_angle = target_data.get('angle', 0.0)
                    candidate_angle = candidate_data.get('angle', 0.0)
                    
                    target_edges.append(target_angle)
                    candidate_edges.append(candidate_angle)
                except (KeyError, TypeError):
                    continue
    
    if not target_edges:
        return 0.0, 0  # No edges to compare
    
    # Check if this can be aligned by rotation only (not reflection)
    if not _can_align_by_rotation_only(cps, target_nodes, candidate_perm):
        return 0.0, -1  # Mark as invalid (reflection required)
    
    # Find the rotation and calculate quality
    rotation_offset, match_count, total_error = _find_rotation_offset_with_quality(target_edges, candidate_edges)
    
    # Quality is based on how many edges match and how small the total error is
    quality = match_count * 1000 - total_error  # Higher match count beats lower error
    
    return rotation_offset, quality

def _can_align_by_rotation_only(cps, target_nodes: List[int], candidate_perm: List[int]) -> bool:
    """Check if candidate can be aligned with target by rotation alone (no reflection)."""
    # Get the "orientation" or "handedness" of both patterns
    target_orientation = _get_pattern_orientation(cps, target_nodes)
    candidate_orientation = _get_pattern_orientation(cps, candidate_perm)
    
    # If orientations have same sign, can align by rotation only
    # If orientations have opposite sign, would need reflection
    return (target_orientation > 0) == (candidate_orientation > 0)

def _get_pattern_orientation(cps, nodes: List[int]) -> float:
    """Calculate the orientation (handedness) of the pattern using edge angle sequences."""
    if len(nodes) < 3:
        return 1.0  # Default for patterns too small to have orientation
    
    # Calculate orientation using the sequence of edge angles around the pattern
    # This detects whether the pattern has clockwise or counterclockwise "handedness"
    
    # Get all edge angles in the pattern
    edge_angles = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if cps.graph.has_edge(nodes[i], nodes[j]):
                try:
                    edge_data = cps.graph.edges[nodes[i], nodes[j]]
                    angle = edge_data.get('angle', 0.0)
                    edge_angles.append(angle)
                except:
                    continue
    
    if len(edge_angles) < 2:
        return 1.0  # Not enough edges to determine orientation
    
    # Sort angles and look at the "spiral" direction
    edge_angles.sort()
    
    # Calculate the "twist" or accumulated angular change
    # This captures the handedness of the pattern
    total_twist = 0.0
    for i in range(len(edge_angles)):
        next_i = (i + 1) % len(edge_angles)
        angle_diff = edge_angles[next_i] - edge_angles[i]
        
        # Normalize to [-π, π]
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
            
        total_twist += angle_diff
    
    return total_twist  # Positive = one handedness, negative = opposite

def _find_rotation_offset_with_quality(target_angles: List[float], candidate_angles: List[float]) -> tuple:
    """Find the rotation offset that best aligns candidate with target, returning rotation, match_count, and total_error."""
    if not target_angles or not candidate_angles:
        return 0.0, 0, 0.0
    
    # For fine-grained rotation detection, try small increments
    best_rotation = 0.0
    best_match_count = 0
    best_total_error = float('inf')
    tolerance = 0.1  # radians
    
    # Generate fine-grained rotations (every 2.5 degrees)
    rotation_set = set()
    for i in range(144):  # 144 * 2.5° = 360°
        rotation_angle = i * math.pi / 72  # π/72 rad = 2.5°
        rotation_set.add(rotation_angle)
    
    # Also include common musical intervals for robustness
    for semitones in range(12):
        rotation_angle = semitones * math.pi / 6  # π/6 rad = 30° per semitone  
        rotation_set.add(rotation_angle)
        
    for rotation in rotation_set:
        match_count = 0
        total_error = 0.0
        
        for target_angle, candidate_angle in zip(target_angles, candidate_angles):
            # Check if candidate_angle + rotation ≈ target_angle (mod 2π)
            rotated_candidate = (candidate_angle + rotation) % (2 * math.pi)
            diff = abs(target_angle - rotated_candidate)
            diff = min(diff, 2 * math.pi - diff)  # Handle wraparound
            
            if diff <= tolerance:
                match_count += 1
                total_error += diff
        
        # Prefer rotations with more matches, and among ties, prefer lower total error
        if (match_count > best_match_count or 
            (match_count == best_match_count and match_count > 0 and total_error < best_total_error)):
            best_match_count = match_count
            best_rotation = rotation
            best_total_error = total_error if match_count > 0 else float('inf')
    
    return best_rotation, best_match_count, best_total_error

def _find_rotation_offset(target_angles: List[float], candidate_angles: List[float]) -> float:
    """Find the rotation offset that best aligns candidate with target."""
    rotation, _, _ = _find_rotation_offset_with_quality(target_angles, candidate_angles)
    return rotation

def _angles_match_with_rotation(cps, target_angle: float, candidate_angle: float, tolerance: float) -> bool:
    """Check if two angles match after applying any of the discrete rotations found in the graph."""
    # Get all unique angles in the graph to use as potential rotation amounts
    rotation_angles = _get_discrete_rotation_angles(cps)
    
    # Check if angles match directly (no rotation)
    if abs(target_angle - candidate_angle) <= tolerance:
        return True
    
    # Try each discrete rotation
    for rotation in rotation_angles:
        rotated_candidate = candidate_angle + rotation
        # Normalize to [0, 2π]
        rotated_candidate = rotated_candidate % (2 * math.pi)
        
        if abs(target_angle - rotated_candidate) <= tolerance:
            return True
    
    return False

def _get_discrete_rotation_angles(cps) -> List[float]:
    """Get all unique angles in the graph to use as discrete rotation amounts."""
    angles = set()
    for u, v, data in cps.graph.edges(data=True):
        if 'angle' in data:
            angles.add(data['angle'])
    
    # Add common musical rotations (octave equivalents)
    rotation_set = set(angles)
    for angle in angles:
        # Add multiples up to 2π
        for mult in range(1, 8):  # Up to 8 times for good coverage
            rotated = (angle * mult) % (2 * math.pi)
            rotation_set.add(rotated)
    
    return list(rotation_set) 