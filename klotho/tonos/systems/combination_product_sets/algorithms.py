import math
import numpy as np
from typing import List, Tuple
from itertools import combinations, permutations

__all__ = [
    'match_pattern',
    'sub_cps',
    'classify',
    'faces',
]


def match_pattern(cps, node_ids: List[int], sort_by: str = 'position',
                  include_target: bool = False) -> List[Tuple[int, ...]]:
    """
    Find all groups of nodes forming the same geometric shape as the input nodes.

    The match is purely geometric: two node sets match if they occupy congruent
    positions (same shape, allowing rotation and reflection). Each returned match
    is ordered so that ``match[i]`` occupies the same structural position as
    ``node_ids[i]``.

    Parameters
    ----------
    cps : CombinationProductSet
        The CPS instance to search.
    node_ids : list of int
        Node IDs defining the reference shape.
    sort_by : str, optional
        How to order results:

        - ``'position'`` (default) -- clockwise spatial sweep based on
          centroid angular position relative to the target.
        - ``'rotation'`` -- clockwise Procrustes rotation angle.
    include_target : bool, optional
        If True, prepend the target itself as the first result.
        Default is False.

    Returns
    -------
    list of tuple of int
        Matching node-ID tuples, ordered to correspond positionally
        with *node_ids*.
    """
    if len(node_ids) < 3:
        return [tuple(node_ids)] if include_target else []

    positions = cps.positions
    all_nodes = sorted(cps.graph.nodes())
    k = len(node_ids)
    N = len(all_nodes)
    node_to_idx = {node: i for i, node in enumerate(all_nodes)}

    pos_array = np.array([positions[node] for node in all_nodes])
    diff = pos_array[:, np.newaxis, :] - pos_array[np.newaxis, :, :]
    full_dist = np.round(np.sqrt((diff ** 2).sum(axis=-1)), 8)

    ref_idx = np.array([node_to_idx[n] for n in node_ids])
    ref_set = frozenset(ref_idx.tolist())
    triu_i, triu_j = np.triu_indices(k, k=1)

    ref_pair_dists = full_dist[ref_idx[triu_i], ref_idx[triu_j]]
    ref_fingerprint = np.sort(ref_pair_dists)
    ref_sub = full_dist[np.ix_(ref_idx, ref_idx)]

    ref_pos_rounded = np.round(pos_array[ref_idx], 8)
    ref_pos_key = frozenset(map(tuple, ref_pos_rounded))
    seen_positions = {ref_pos_key}

    all_cand = np.array(list(combinations(range(N), k)))
    row_idx = all_cand[:, triu_i]
    col_idx = all_cand[:, triu_j]
    all_pair_dists = full_dist[row_idx, col_idx]
    all_sorted = np.sort(all_pair_dists, axis=1)

    fp_match = np.all(np.abs(all_sorted - ref_fingerprint) < 1e-7, axis=1)
    hit_indices = np.where(fp_match)[0]

    matches = []
    for ci in hit_indices:
        cand_idx = all_cand[ci]
        if frozenset(cand_idx.tolist()) == ref_set:
            continue

        cand_pos_rounded = np.round(pos_array[cand_idx], 8)
        pk = frozenset(map(tuple, cand_pos_rounded))
        if pk in seen_positions:
            continue
        seen_positions.add(pk)

        cand_sub = full_dist[np.ix_(cand_idx, cand_idx)]
        cand_nodes = [all_nodes[i] for i in cand_idx]
        ordered = _find_correspondence(ref_sub, cand_sub, cand_nodes)
        matches.append(tuple(ordered))

    ref_pts = pos_array[ref_idx]
    if sort_by == 'rotation':
        sort_fn = _cw_rotation_angle
    else:
        sort_fn = _cw_position_angle

    sort_keys = []
    for match in matches:
        match_idx = np.array([node_to_idx[n] for n in match])
        match_pts = pos_array[match_idx]
        angle = sort_fn(ref_pts, match_pts)
        centroid_dist = float(np.linalg.norm(
            ref_pts.mean(axis=0) - match_pts.mean(axis=0)
        ))
        sort_keys.append((angle, centroid_dist))

    matches = [m for _, m in sorted(zip(sort_keys, matches))]

    if include_target:
        matches.insert(0, tuple(node_ids))

    return matches


def _cw_position_angle(ref_pts, match_pts):
    ref_centroid = ref_pts[:, :2].mean(axis=0)
    match_centroid = match_pts[:, :2].mean(axis=0)
    ref_angle = math.atan2(ref_centroid[1], ref_centroid[0])
    match_angle = math.atan2(match_centroid[1], match_centroid[0])
    cw = (ref_angle - match_angle) % (2 * math.pi)
    if (2 * math.pi - cw) < 1e-10:
        cw = 0.0
    return cw


def _cw_rotation_angle(ref_pts, match_pts):
    ref_c = ref_pts[:, :2] - ref_pts[:, :2].mean(axis=0)
    tgt_c = match_pts[:, :2] - match_pts[:, :2].mean(axis=0)

    H = ref_c.T @ tgt_c
    U, _, Vt = np.linalg.svd(H)
    d = np.linalg.det(Vt.T @ U.T)
    S = np.diag([1.0, np.sign(d)])
    R = Vt.T @ S @ U.T

    ccw_angle = math.atan2(R[1, 0], R[0, 0])
    cw = (-ccw_angle) % (2 * math.pi)
    if (2 * math.pi - cw) < 1e-10:
        cw = 0.0
    return cw


def _find_correspondence(ref_sub, cand_sub, candidate_nodes):
    n = len(candidate_nodes)
    ref_profiles = [tuple(np.sort(ref_sub[i]).tolist()) for i in range(n)]
    cand_profiles = [tuple(np.sort(cand_sub[j]).tolist()) for j in range(n)]

    profile_to_ref = {}
    for i, p in enumerate(ref_profiles):
        profile_to_ref.setdefault(p, []).append(i)

    profile_to_cand = {}
    for j, p in enumerate(cand_profiles):
        profile_to_cand.setdefault(p, []).append(j)

    ordered = [None] * n
    ambiguous_groups = []

    for profile, ref_positions in profile_to_ref.items():
        cand_positions = profile_to_cand.get(profile, [])
        if len(ref_positions) == 1 and len(cand_positions) == 1:
            ordered[ref_positions[0]] = candidate_nodes[cand_positions[0]]
        else:
            ambiguous_groups.append((ref_positions, cand_positions))

    if not ambiguous_groups:
        return ordered

    fixed_map = {}
    for i in range(n):
        if ordered[i] is not None:
            fixed_map[i] = candidate_nodes.index(ordered[i])

    free_ref = []
    free_cand_pool = []
    for ref_positions, cand_positions in ambiguous_groups:
        free_ref.extend(ref_positions)
        free_cand_pool.extend(cand_positions)

    for perm in permutations(free_cand_pool):
        trial = list(range(n))
        for ri, ci in fixed_map.items():
            trial[ri] = ci
        for idx, ri in enumerate(free_ref):
            trial[ri] = perm[idx]

        permuted = cand_sub[np.ix_(trial, trial)]
        if np.allclose(permuted, ref_sub, atol=1e-6):
            return [candidate_nodes[trial[i]] for i in range(n)]

    return list(candidate_nodes)


def sub_cps(cps, k: int, s: int) -> List[dict]:
    """
    Enumerate all sub-CPS structures within a CPS.

    A sub-CPS is formed by fixing an *anchor* subset of factors and varying
    the remaining *k* factors taken *s* at a time.

    Parameters
    ----------
    cps : CombinationProductSet
        The parent CPS.
    k : int
        Number of varying factors in each sub-CPS.
    s : int
        Combination rank within the sub-CPS.

    Returns
    -------
    list of dict
        Each dict contains ``'nodes'``, ``'anchor'``, ``'varying'``,
        and ``'combos'`` keys.
    """
    factors = list(cps.factors)
    n = len(factors)
    r = cps.rank

    if r is None:
        raise ValueError("sub_cps requires a standard CPS with a rank (r). Use on CPS created via __init__, not from_rules.")

    anchor_size = r - s
    if anchor_size < 0 or k + anchor_size > n:
        return []

    combo_to_node = {}
    for node, attrs in cps.graph.nodes(data=True):
        if 'combo' in attrs:
            combo_to_node[attrs['combo']] = node

    results = []
    for anchor in combinations(factors, anchor_size):
        remaining = [f for f in factors if f not in anchor]
        for varying in combinations(remaining, k):
            nodes = []
            combos = []
            for sub_combo in combinations(varying, s):
                full_combo = tuple(sorted(list(anchor) + list(sub_combo)))
                if full_combo in combo_to_node:
                    nodes.append(combo_to_node[full_combo])
                    combos.append(full_combo)

            if len(nodes) == math.comb(k, s):
                results.append({
                    'nodes': tuple(sorted(nodes)),
                    'anchor': anchor,
                    'varying': varying,
                    'combos': combos,
                })

    seen = set()
    unique = []
    for entry in results:
        key = entry['nodes']
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    return unique


def classify(cps, node_ids: List[int]) -> dict:
    """
    Classify a subset of CPS nodes as harmonic, subharmonic, or mixed.

    Harmonic subsets share common anchor factors; subharmonic subsets
    exclude factors entirely; mixed subsets do neither.

    Parameters
    ----------
    cps : CombinationProductSet
        The CPS instance.
    node_ids : list of int
        Node IDs to classify.

    Returns
    -------
    dict
        Classification result with keys ``'type'``, ``'nodes'``,
        ``'shared'``, ``'excluded'``, and ``'factors_present'``.
    """
    factors = set(cps.factors)
    G = cps.graph

    combos = []
    for n in node_ids:
        attrs = G.nodes[n]
        if 'combo' in attrs:
            combo = attrs['combo']
            if isinstance(combo, tuple) and isinstance(combo[0], tuple):
                return {'type': 'unknown', 'reason': 'ratio-based nodes'}
            combos.append(set(combo))

    if not combos:
        return {'type': 'unknown', 'reason': 'no combo data'}

    shared = combos[0].copy()
    for c in combos[1:]:
        shared &= c

    all_present = set()
    for c in combos:
        all_present |= c

    excluded = factors - all_present

    result = {
        'nodes': list(node_ids),
        'shared': sorted(shared),
        'excluded': sorted(excluded),
        'factors_present': sorted(all_present),
    }

    if shared:
        diff = sorted(all_present - shared)
        result['type'] = 'harmonic'
        result['anchor'] = sorted(shared)
        result['varying'] = diff
    elif excluded:
        result['type'] = 'subharmonic'
    else:
        result['type'] = 'mixed'

    return result


def faces(cps, size: int) -> List[Tuple[int, ...]]:
    """
    Find all fully-connected cliques of a given size in the CPS graph.

    A *face* is a subset of nodes where every pair is connected by an
    edge (a complete subgraph).

    Parameters
    ----------
    cps : CombinationProductSet
        The CPS instance.
    size : int
        Number of nodes per face.

    Returns
    -------
    list of tuple of int
        Each tuple contains the node IDs forming a complete subgraph.
    """
    G = cps.graph
    all_nodes = list(G.nodes())
    result = []

    for subset in combinations(all_nodes, size):
        edge_count = 0
        for u, v, data in G.edges(data=True):
            if u in subset and v in subset and 'distance' in data:
                edge_count += 1
        undirected_edges = edge_count // 2
        max_possible = size * (size - 1) // 2
        if undirected_edges == max_possible:
            result.append(subset)

    return result