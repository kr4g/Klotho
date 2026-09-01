"""S1 -- a pfield may not be named after a node key another layer owns.

``ParameterLayer.set_pfields``/``set_mfields`` write through
``tree._write_node_data``, which bypasses ``normalize_attrs``/``validate_attrs``
entirely. So on a ``CompositionalTree`` -- one tree carrying both a
``RhythmLayer`` and a ``ParameterLayer`` -- naming a field ``proportion`` was
accepted in silence, overwrote the rhythm layer's own data, and registered the
name as an inheritable pfield so it appeared as an events/playback column on
every node. The poisoned value took effect only at the NEXT structural edit:
measured, ``uc.set_pfields(leaf0, proportion=5)`` left durations correct and
then an UNRELATED ``subdivide`` elsewhere rewrote them to
``5/8, 1/8, 1/8, 1/16, 1/16``.

The mirror door was already shut -- ``uc._rt.set_node_data(leaf, amp=0.5)``
raises ``Illegal RhythmTree node attribute update: ['amp']`` -- so this closes
the other half of a door the codebase had already decided about.
"""

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.parameters.parameter_tree import ParameterTree

RESERVED = ('proportion', 'tied', 'metric_duration', 'metric_onset')


def _uc():
    return UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)


class TestTheReservedNamesAreRefused:
    @pytest.mark.parametrize('name', RESERVED)
    def test_unit_set_pfields(self, name):
        uc = _uc()
        with pytest.raises(ValueError, match='Illegal pfield name'):
            uc.set_pfields(uc._rt.leaf_nodes[0], **{name: 5})

    @pytest.mark.parametrize('name', RESERVED)
    def test_unit_set_mfields(self, name):
        uc = _uc()
        with pytest.raises(ValueError, match='Illegal mfield name'):
            uc.set_mfields(uc._rt.leaf_nodes[0], **{name: 5})

    @pytest.mark.parametrize('name', RESERVED)
    def test_raw_tree_door(self, name):
        uc = _uc()
        with pytest.raises(ValueError, match='Illegal pfield name'):
            uc._rt.set_pfields(uc._rt.leaf_nodes[0], **{name: 5})

    @pytest.mark.parametrize('name', RESERVED)
    def test_node_proxy_door(self, name):
        uc = _uc()
        with pytest.raises(ValueError, match='Illegal pfield name'):
            uc.root.set_pfields(**{name: 5})

    @pytest.mark.parametrize('name', RESERVED)
    def test_register_pfields_without_a_value(self, name):
        """Registration writes nothing, but it makes the rhythm layer's own
        raw data read back as an inherited field on every node."""
        uc = _uc()
        with pytest.raises(ValueError, match='Illegal pfield name'):
            uc._rt.register_pfields([name])
        assert name not in uc._rt.pfields
        assert name not in list(uc.events.columns)

    @pytest.mark.parametrize('name', RESERVED)
    def test_register_mfields_without_a_value(self, name):
        uc = _uc()
        with pytest.raises(ValueError, match='Illegal mfield name'):
            uc._rt.register_mfields([name])
        assert name not in uc._rt.mfields

    def test_register_still_accepts_an_ordinary_generator(self):
        """The guard consumes *keys*; a one-shot iterable must still land."""
        uc = _uc()
        uc._rt.register_pfields(k for k in ('cutoff', 'res'))
        assert 'cutoff' in uc._rt.pfields and 'res' in uc._rt.pfields

    def test_constructing_with_a_reserved_pfield_name_is_refused(self):
        with pytest.raises(ValueError, match='Illegal pfield name'):
            UC(tempus='4/4', prolatio=(1, 1), pfields=['proportion'])
        with pytest.raises(ValueError, match='Illegal pfield name'):
            UC(tempus='4/4', prolatio=(1, 1), pfields={'metric_onset': 0.0})

    def test_the_refusal_names_the_offending_key_and_what_to_do(self):
        uc = _uc()
        with pytest.raises(ValueError) as exc:
            uc.set_pfields(uc._rt.leaf_nodes[0], proportion=5)
        text = str(exc.value)
        assert "'proportion'" in text
        assert 'metric_duration' in text and 'metric_onset' in text
        assert 'Choose a different field name' in text

    def test_a_reserved_name_alongside_a_legal_one_refuses_the_whole_write(self):
        uc = _uc()
        leaf = uc._rt.leaf_nodes[0]
        with pytest.raises(ValueError, match='Illegal pfield name'):
            uc.set_pfields(leaf, amp=0.5, proportion=5)
        assert 'proportion' not in uc._rt.pfields
        assert uc.get_pfield(leaf, 'amp') is None


class TestNothingChangesForLegalNames:
    def test_ordinary_pfields_still_write_and_inherit(self):
        uc = _uc()
        uc.set_pfields(uc._rt.root, amp=0.4, freq=220.0)
        for n in uc._rt.leaf_nodes:
            assert uc.get_pfield(n, 'amp') == 0.4
            assert uc.get_pfield(n, 'freq') == 220.0
        assert uc._rt.durations == uc.copy()._rt.durations

    def test_ordinary_mfields_still_write(self):
        uc = _uc()
        uc.set_mfields(uc._rt.root, group='bass')
        assert uc.get_mfield(uc._rt.leaf_nodes[0], 'group') == 'bass'

    def test_a_near_miss_name_is_fine(self):
        uc = _uc()
        uc.set_pfields(uc._rt.root, proportions=5, metric_dur=2)
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'proportions') == 5

    def test_a_plain_parameter_tree_has_no_reserved_names(self):
        """A bare ``ParameterTree`` carries no structural layer, so none of
        these keys is owned by anything and there is nothing to poison."""
        pt = ParameterTree(1, (1, 1))
        leaf = pt.leaf_nodes[0]
        pt.set_pfields(leaf, proportion=5)
        assert pt.get_pfield(leaf, 'proportion') == 5


class TestTheRhythmStaysIntact:
    def test_a_later_unrelated_subdivide_does_not_rewrite_durations(self):
        """The symptom that made this silent: the poisoned value only bit at
        the next structural edit, far from the write that caused it."""
        uc = _uc()
        before = uc._rt.durations
        with pytest.raises(ValueError):
            uc.set_pfields(uc._rt.leaf_nodes[0], proportion=5)
        uc.subdivide(uc._rt.leaf_nodes[-1], (1, 1))
        assert sum(uc._rt.durations) == sum(before)
        assert uc._rt.durations[0] == before[0]
