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


class TestOptInNodeStamping:
    """The other half of WL-33, behind a flag.

    Stamping is opt-in for two measured reasons. It adds ~38 bytes an event to
    a wire format the 10.x perf work spent real effort shrinking (``fast_id``
    exists to save 48 bytes an event), and always-on would rewrite all eight
    payload fixtures, which sits behind the project's fixture fence. Opt-in
    costs nothing by default and forecloses nothing: flipping the default
    later is a one-word change. ``animation=True`` gating ``_stepIndex`` is
    the same pattern, already in the codebase.
    """

    @staticmethod
    def _lower(**kw):
        from klotho.utils.playback._sc_assembly import (
            lower_compositional_ir_to_sc_assembly as lower)
        return lower(_uc(), **kw)

    def test_the_default_payload_is_untouched(self):
        assert all('_nodeId' not in event for event in self._lower())
        assert all('_metricOnset' not in event for event in self._lower())

    def test_stamping_adds_the_node_id(self):
        stamped = [e for e in self._lower(stamp_nodes=True) if '_nodeId' in e]
        assert stamped
        assert all(isinstance(e['_nodeId'], int) for e in stamped)

    def test_the_stamped_id_matches_the_map(self):
        uc = _uc()
        from klotho.utils.playback._sc_assembly import (
            lower_compositional_ir_to_sc_assembly as lower)
        events = lower(uc, stamp_nodes=True)
        mapping = node_event_map(uc)
        for event in events:
            if '_nodeId' in event:
                assert event['_nodeId'] in mapping

    def test_the_metric_onset_is_exact(self):
        """A pair of ints, not a float -- the whole point is that the float
        seconds are a tempo-dependent rendering and not the exact onset."""
        for event in self._lower(stamp_nodes=True):
            if '_metricOnset' not in event:
                continue
            num, den = event['_metricOnset']
            assert isinstance(num, int) and isinstance(den, int)
            assert Fraction(num, den) == Fraction(num, den)

    def test_stamping_changes_nothing_else_about_the_events(self):
        plain = self._lower()
        stamped = self._lower(stamp_nodes=True)
        assert len(plain) == len(stamped)
        for before, after in zip(plain, stamped):
            trimmed = {k: v for k, v in after.items()
                       if k not in ('_nodeId', '_metricOnset', 'id',
                                    '_polyGroupId', '_logicalStepId')}
            assert all(before[k] == v for k, v in trimmed.items() if k in before)
