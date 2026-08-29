"""RT-1 -- the dead ``type`` classification is gone from RhythmTree.

``_set_type`` was dead twice over: it had zero call sites in the repo, and
it never assigned ``self._meta['type']`` either -- it returned a string
nobody caught. The field it was supposed to fill was written ``None`` at
construction and read in exactly one place, the ``.info`` property, so
every ``rt.info`` printed a meaningless ``type: None``.

Deleting it rather than fixing it is a deliberate call. A correct
simple/complex classifier is still possible, but it is blocked on evidence
we do not have: Haddad's rule ("the sum of the proportions is a
multiplicative factor of the numerator") is satisfied in his ``5/9 (4 3 3)``
figure -- sum 10, numerator 5 -- which he calls SIMPLE while this code
called it ``'complex'``; one figure cannot settle whether the sum must be a
multiple of the numerator or a divisor of it. ``measure_complexity`` also
carries its own ``# XXX - only works for binary meters!!!`` limitation,
which is a second and independent correction. Both must land before a
classifier can be trusted.
"""

import pytest

from klotho.chronos.rhythm_trees import RhythmTree


class TestNoDeadTypeField:

    def test_info_does_not_advertise_a_type(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        assert 'type:' not in rt.info

    def test_meta_has_no_type_key(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        assert 'type' not in rt._meta

    def test_set_type_is_gone(self):
        assert not hasattr(RhythmTree, '_set_type')

    def test_info_still_carries_the_real_metadata(self):
        rt = RhythmTree(span=2, meas='7/8', subdivisions=(1, (2, (1, 1)), 1))
        info = rt.info
        for field in ('span:', 'meas:', 'depth:', 'k:'):
            assert field in info

    def test_info_reports_the_actual_values(self):
        rt = RhythmTree(span=2, meas='7/8', subdivisions=(1, (2, (1, 1)), 1))
        info = rt.info
        assert 'span: 2' in info
        assert 'meas: 7/8' in info
        assert f'depth: {rt.depth}' in info
        assert f'k: {rt.k}' in info

    def test_a_cloned_tree_has_no_type_either(self):
        """``_post_structure_clone`` wrote the dead field a second time."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, (2, (1, 1)), 1))
        sub = rt.subtree(rt.leaf_nodes[1])
        assert 'type' not in sub._meta

    def test_info_still_renders_durations_and_onsets(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        info = rt.info
        assert 'Durations:' in info
        assert 'Onsets:' in info
        assert 'Subdivs:' in info
