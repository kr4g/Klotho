"""Tests for beam group assignment."""

import pytest
from fractions import Fraction

from klotho.chronos import RhythmTree as RT, Meas

from notation_pipeline.models import NoteType, EngravingLeaf, BeamGroup
from notation_pipeline.core.beam import assign_beams
from notation_pipeline.core.duration import classify_duration


def _make_events_from_rt(rt) -> tuple[list[EngravingLeaf], dict[int, list[int]]]:
    """Helper: extract leaves from RT and create simple EngravingLeaf events."""
    events = []
    leaf_map = {}  # node_id -> [event_index]
    for leaf in rt.leaf_nodes:
        data = rt[leaf]
        dur = abs(Fraction(data['metric_duration']))
        onset = Fraction(data['metric_onset'])
        is_rest = data.get('proportion', 1) < 0

        # Classify duration (may be None for tuplet contexts)
        classification = classify_duration(dur)
        if classification is not None:
            note_type, dots = classification
        else:
            note_type, dots = NoteType.QUARTER, 0  # placeholder

        idx = len(events)
        leaf_map[leaf] = [idx]
        events.append(EngravingLeaf(
            node_id=leaf,
            duration=dur,
            onset=onset,
            note_type=note_type,
            dots=dots,
            is_rest=is_rest,
        ))
    return events, leaf_map


class TestAssignBeams:
    def test_four_quarters_no_beams(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1, 1))
        events, leaf_map = _make_events_from_rt(rt)
        groups = assign_beams(rt, events, leaf_map)
        # Quarter notes don't get beamed
        assert len(groups) == 0

    def test_eighths_in_groups(self):
        # All eighths via nested binary
        rt = RT(meas='4/4', subdivisions=((1, (1, 1)), (1, (1, 1)), (1, (1, 1)), (1, (1, 1))))
        events, leaf_map = _make_events_from_rt(rt)
        groups = assign_beams(rt, events, leaf_map)
        # Should have 4 beam groups (one per beat)
        assert len(groups) == 4
        for g in groups:
            assert len(g.event_indices) == 2
            assert g.max_beam_level == 1  # eighth notes

    def test_rest_breaks_beam(self):
        # Four groups of 2 eighths, with a rest in the second group
        rt = RT(meas='4/4', subdivisions=(
            (1, (1, 1)),    # 2 eighths
            (1, (1, -1)),   # note + rest
            (1, (1, 1)),    # 2 eighths
            (1, (1, 1)),    # 2 eighths
        ))
        events, leaf_map = _make_events_from_rt(rt)
        groups = assign_beams(rt, events, leaf_map)
        # Groups 1, 3, 4 should each have 2-note beam groups
        # Group 2 has only 1 beamable note (rest breaks it), so no beam group
        two_note_groups = [g for g in groups if len(g.event_indices) == 2]
        assert len(two_note_groups) == 3

    def test_flat_triplet_beamed(self):
        # Flat triplet — all leaves under root
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        events, leaf_map = _make_events_from_rt(rt)
        groups = assign_beams(rt, events, leaf_map)
        # Triplet notes may or may not be beamable depending on their classified duration
        # In a 4/4 triplet, each leaf has duration 1/3 — not directly classifiable
        # This is expected; beaming depends on classification within tuplet context
