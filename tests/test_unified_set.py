"""Tests for the unified CompositionalUnit.set() kwarg routing."""

import pytest

from klotho.thetos.composition.compositional import (
    ENGINE_MFIELDS,
    CompositionalUnit,
)
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.tonos import Pitch
from klotho.topos.collections.sequences import Pattern


def _uc(prolatio=(1, 1, 1, 1)):
    return CompositionalUnit(tempus='4/4', prolatio=prolatio, bpm=60)


class TestRouting:
    def test_engine_mfields_constant(self):
        assert ENGINE_MFIELDS == {'strum', 'group'}

    def test_single_call_equivalent_to_three(self):
        a = _uc()
        a.set(a._rt.root, inst='kl_tri', freq=440.0, amp=0.2, strum=0.5)

        b = _uc()
        b.set_instrument(b._rt.root, 'kl_tri')
        b.set_pfields(b._rt.root, freq=440.0, amp=0.2)
        b.set_mfields(b._rt.root, strum=0.5)

        for n in a._rt.leaf_nodes:
            assert a.get_pfield(n, 'freq') == b.get_pfield(n, 'freq')
            assert a.get_pfield(n, 'amp') == b.get_pfield(n, 'amp')
            assert a.get_mfield(n, 'strum') == b.get_mfield(n, 'strum')
        assert a.get_instrument(a._rt.root) == b.get_instrument(b._rt.root)

    def test_strum_and_group_land_in_mfields(self):
        uc = _uc()
        uc.set(uc._rt.root, strum=0.3, group='bass', amp=0.5)
        n = uc._rt.leaf_nodes[0]
        assert uc.get_mfield(n, 'strum') == 0.3
        assert uc.get_mfield(n, 'group') == 'bass'
        assert uc.get_pfield(n, 'amp') == 0.5
        assert uc.get_pfield(n, 'strum') is None

    def test_freq_coercion_applies(self):
        uc = _uc()
        uc.set(uc._rt.root, freq='F#3')
        assert isinstance(uc.get_pfield(uc._rt.leaf_nodes[0], 'freq'), Pitch)

    def test_inst_guard_applies(self):
        uc = _uc()
        with pytest.raises(TypeError, match="effect SynthDef"):
            uc.set(uc._rt.root, inst='kl_reverb')

    def test_escape_hatch_dicts_override_routing(self):
        uc = _uc()
        uc.set(uc._rt.root, pfields={'strum': 99.0}, mfields={'amp': 'meta'})
        n = uc._rt.leaf_nodes[0]
        assert uc.get_pfield(n, 'strum') == 99.0
        assert uc.get_mfield(n, 'amp') == 'meta'

    def test_patterns_distribute(self):
        uc = _uc()
        uc.set(uc.leaves, freq=Pattern([100.0, 200.0]))
        vals = [uc.get_pfield(n, 'freq') for n in uc._rt.leaf_nodes]
        assert vals == [100.0, 200.0, 100.0, 200.0]

    def test_callables_distribute(self):
        uc = _uc()
        uc.set(uc.leaves, amp=lambda c: 0.1 * (c.index + 1))
        vals = [uc.get_pfield(n, 'amp') for n in uc._rt.leaf_nodes]
        assert vals == pytest.approx([0.1, 0.2, 0.3, 0.4])


class TestSelectorHandleParity:
    def test_selector_set(self):
        uc = _uc()
        uc.leaves.set(inst=SynthDefInstrument.tri(), freq=330.0, strum=0.2)
        n = uc._rt.leaf_nodes[0]
        assert uc.get_pfield(n, 'freq') == 330.0
        assert uc.get_mfield(n, 'strum') == 0.2
        assert uc.get_instrument(n).defName == 'kl_tri'

    def test_handle_set(self):
        uc = _uc()
        uc.leaves.first.set(freq=550.0, group='lead')
        n = uc._rt.leaf_nodes[0]
        assert uc.get_pfield(n, 'freq') == 550.0
        assert uc.get_mfield(n, 'group') == 'lead'
        other = uc._rt.leaf_nodes[1]
        assert uc.get_pfield(other, 'freq') is None

    def test_selector_owner_parity(self):
        a = _uc()
        a.leaves.set(freq=220.0, amp=0.4)
        b = _uc()
        b.set(b.leaves, freq=220.0, amp=0.4)
        for na, nb in zip(a._rt.leaf_nodes, b._rt.leaf_nodes):
            assert a.get_pfield(na, 'freq') == b.get_pfield(nb, 'freq')
            assert a.get_pfield(na, 'amp') == b.get_pfield(nb, 'amp')
