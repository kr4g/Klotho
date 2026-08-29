"""Joining rendered events back to the nodes that produced them (WL-33, part).

The map has always been built during lowering, behind ``return_node_map=True``
on a private function -- so anyone wanting it had to reach into an underscore
module and re-derive the call. This is the public verb over the existing map.

What is deliberately NOT here: stamping the node id onto the events themselves.
That changes every lowered payload and therefore every payload fixture, which
sits behind the project's fixture fence (diff before regenerating; regens are
their own commit). Left for Ryan's call -- see the API-3 handoff.
"""

from fractions import Fraction

import pytest

from klotho.chronos import TemporalUnit
from klotho.thetos import CompositionalUnit
from klotho.utils.playback import node_event_map


def _uc(prolatio=(1, -1, 1, 1)):
    return CompositionalUnit(tempus='4/4', prolatio=prolatio, bpm=120)


class TestNodeEventMap:
    def test_every_sounding_leaf_maps_to_an_event(self):
        uc = _uc()
        mapping = node_event_map(uc)
        assert [leaf.id for leaf in uc.leaves.sounding] == sorted(mapping)

    def test_a_rest_maps_to_nothing(self):
        uc = _uc()
        rest = [leaf.id for leaf in uc.leaves if leaf.is_rest]
        assert rest and all(node not in node_event_map(uc) for node in rest)

    def test_each_entry_carries_id_seconds_and_metric_onset(self):
        for entries in node_event_map(_uc()).values():
            for event_id, start, metric_onset in entries:
                assert isinstance(event_id, str) and event_id
                assert isinstance(start, float)
                assert isinstance(metric_onset, Fraction)

    def test_the_metric_onset_matches_the_node(self):
        uc = _uc()
        mapping = node_event_map(uc)
        for node, entries in mapping.items():
            for _, _, metric_onset in entries:
                assert metric_onset == uc._rt[node].get('metric_onset')

    def test_seconds_follow_the_metric_onset_at_this_tempo(self):
        """4/4 at 120bpm is two seconds a bar, so a whole note is 2.0s."""
        for entries in node_event_map(_uc()).values():
            for _, start, metric_onset in entries:
                assert start == pytest.approx(float(metric_onset) * 2.0)

    def test_a_chord_node_maps_to_one_event_per_voice(self):
        uc = _uc(prolatio=(1, 1))
        uc.set_pfields(list(uc.leaves)[0].id, freq=(261.6, 329.6, 392.0))
        mapping = node_event_map(uc)
        assert len(mapping[list(uc.leaves)[0].id]) == 3

    def test_event_ids_are_unique_within_one_call(self):
        ids = [entry[0] for entries in node_event_map(_uc()).values()
               for entry in entries]
        assert len(ids) == len(set(ids))

    def test_node_ids_are_the_stable_half_of_the_join(self):
        """Event ids come from a process-local counter, so they differ between
        lowerings; the node ids do not. That is what the docstring says and
        what makes the node id the thing to join on."""
        uc = _uc()
        first, second = node_event_map(uc), node_event_map(uc)
        assert sorted(first) == sorted(second)
        assert [e[0] for v in first.values() for e in v] != \
               [e[0] for v in second.values() for e in v]

    def test_seconds_are_stable_between_lowerings(self):
        uc = _uc()
        first, second = node_event_map(uc), node_event_map(uc)
        assert [e[1] for v in first.values() for e in v] == \
               [e[1] for v in second.values() for e in v]

    def test_it_works_on_a_plain_temporal_unit(self):
        mapping = node_event_map(
            CompositionalUnit.from_ut(TemporalUnit(tempus='4/4', prolatio=(1, 1))))
        assert len(mapping) == 2

    def test_it_is_exported_from_the_playback_package(self):
        import klotho.utils.playback as pb
        assert pb.node_event_map is node_event_map
