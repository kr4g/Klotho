"""
Rest-skipping in ``set_instrument`` distribution (include_rests flag).

Patterns and callables passed to ``set_instrument`` must unroll across
sounding nodes only by default, staying aligned with pfield/mfield
distribution in the same ``set`` call. ``include_rests=True`` restores
distribution over every target node.
"""
import pytest
from klotho.thetos import CompositionalUnit as UC
from klotho.topos import Pattern


def make_uc():
    """4 pulses, second one a rest."""
    return UC(tempus='4/4', prolatio=(1, -1, 1, 1), beat='1/4', bpm=60)


def sounding(uc):
    return [l for l in uc.leaves if not l.is_rest]


class TestSetInstrumentSkipsRests:

    def test_pattern_unrolls_over_sounding_nodes_only(self):
        uc = make_uc()
        uc.leaves.set_instrument(Pattern(['kick', 'snare', 'hat']))
        assert [l.get_instrument() for l in sounding(uc)] == ['kick', 'snare', 'hat']

    def test_callable_not_evaluated_on_rests(self):
        uc = make_uc()
        seen = []
        def pick(ctx):
            seen.append(ctx.is_rest)
            return 'kick'
        uc.leaves.set_instrument(pick)
        assert seen == [False, False, False]

    def test_include_rests_true_distributes_over_all_nodes(self):
        uc = make_uc()
        uc.leaves.set_instrument(Pattern(['kick', 'snare', 'hat']), include_rests=True)
        assert [l.get_instrument() for l in uc.leaves] == ['kick', 'snare', 'hat', 'kick']

    def test_static_instrument_still_applies_to_every_target(self):
        uc = make_uc()
        uc.leaves.set_instrument('kick')
        assert [l.get_instrument() for l in uc.leaves] == ['kick'] * 4

    def test_uc_method_with_explicit_node_list(self):
        uc = make_uc()
        ids = [l.id for l in uc.leaves]
        uc.set_instrument(ids, Pattern(['kick', 'snare', 'hat']))
        assert [l.get_instrument() for l in sounding(uc)] == ['kick', 'snare', 'hat']

    def test_handle_on_rest_leaf_does_not_consume_pattern(self):
        uc = make_uc()
        rest = next(l for l in uc.leaves if l.is_rest)
        pat = Pattern(['kick', 'snare'])
        rest.set_instrument(pat)
        assert next(pat) == 'kick'


class TestUnifiedSetAlignment:

    def test_inst_and_pfield_patterns_stay_in_lockstep(self):
        uc = make_uc()
        uc.leaves.set(inst=Pattern(['kick', 'snare', 'hat']),
                      amp=Pattern([0.1, 0.2, 0.3]))
        got = [(l.get_instrument(), l.get_pfield('amp')) for l in sounding(uc)]
        assert got == [('kick', 0.1), ('snare', 0.2), ('hat', 0.3)]

    def test_set_forwards_include_rests_to_instrument(self):
        uc = make_uc()
        uc.leaves.set(inst=Pattern(['kick', 'snare', 'hat']), include_rests=True)
        assert [l.get_instrument() for l in uc.leaves] == ['kick', 'snare', 'hat', 'kick']
