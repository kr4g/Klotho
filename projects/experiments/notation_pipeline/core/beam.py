"""Beam group assignment from RhythmTree structure.

Follows OpenMusic's approach: each internal node in the RT that contains
sub-groups creates beam boundaries at transitions between its children.
This means nested groups (e.g., quintuplets inside a triplet) get their
own independent beam groups, while leaf-level binary splits within a
beat stay beamed together.
"""

from __future__ import annotations

from ..models import BeamGroup, EngravingLeaf
from .duration import beam_count


def assign_beams(
    rt,
    events: list[EngravingLeaf],
    leaf_node_to_event_indices: dict[int, list[int]],
) -> list[BeamGroup]:
    """Assign beam groups based on RT tree structure."""
    if not events:
        return []

    # Build map: event_index → leaf_node_id
    event_to_leaf = {}
    for leaf_id, indices in leaf_node_to_event_indices.items():
        for idx in indices:
            event_to_leaf[idx] = leaf_id

    # Collect beam boundaries. A boundary exists at the start of each
    # child subtree of an internal node, BUT only for nodes whose children
    # include at least one internal (non-leaf) node. This prevents
    # leaf-level binary splits from fragmenting beams.
    boundary_events = {0}  # first event is always a boundary

    for node in rt.nodes:
        children = list(rt.successors(node))
        if len(children) < 2:
            continue

        # Does this node contain sub-groups (not just bare leaves)?
        has_internal_child = any(rt.out_degree(c) > 0 for c in children)
        if not has_internal_child and node != rt.root:
            # Pure leaf group below root level — don't break beams here
            continue

        # Add boundary at the start of each child (except the first,
        # which inherits boundary from the parent level)
        for child in children[1:]:
            first_leaf = _first_leaf(child, rt)
            if first_leaf is not None and first_leaf in leaf_node_to_event_indices:
                boundary_events.add(leaf_node_to_event_indices[first_leaf][0])

    # Also add boundary at the start of each root child (always)
    for child in rt.successors(rt.root):
        first_leaf = _first_leaf(child, rt)
        if first_leaf is not None and first_leaf in leaf_node_to_event_indices:
            boundary_events.add(leaf_node_to_event_indices[first_leaf][0])

    # Split into segments
    sorted_bounds = sorted(boundary_events)
    segments = []
    for i, start in enumerate(sorted_bounds):
        end = sorted_bounds[i + 1] if i + 1 < len(sorted_bounds) else len(events)
        segments.append((start, end))

    # Within each segment, collect runs of beamable notes, breaking at rests
    beam_groups = []
    for seg_start, seg_end in segments:
        current_run = []
        for idx in range(seg_start, seg_end):
            ev = events[idx]
            if not ev.is_rest and beam_count(ev.note_type) > 0:
                current_run.append(idx)
            else:
                if len(current_run) >= 2:
                    _emit_group(current_run, events, beam_groups)
                current_run = []
        if len(current_run) >= 2:
            _emit_group(current_run, events, beam_groups)

    return beam_groups


def _emit_group(indices: list[int], events: list[EngravingLeaf], out: list[BeamGroup]):
    max_level = max(beam_count(events[i].note_type) for i in indices)
    out.append(BeamGroup(
        event_indices=list(indices),
        max_beam_level=max_level,
        group_node_id=-1,
    ))


def _first_leaf(node_id, rt) -> int | None:
    """Find the first (leftmost) leaf under a node."""
    if rt.out_degree(node_id) == 0:
        return node_id
    children = list(rt.successors(node_id))
    if children:
        return _first_leaf(children[0], rt)
    return None
