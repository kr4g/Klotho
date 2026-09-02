"""AF2-3: a structural ``replace`` must not destroy a node's parameters.

``CompositionalTree.replace_node`` and ``replace_node_data`` forward to a
``replace=True`` write, which swaps the whole payload dict.  On a plain
``RhythmTree`` that is the contract.  On a ``CompositionalTree`` the payload
also carries the parameter layer's data, so the structural edit silently takes
the note's ``amp``, its ``freq``, its ``group`` routing and any stored
``Bind`` with it -- and the caller cannot prevent that, because
``RhythmLayer.validate_attrs`` REFUSES every key but ``proportion``/``tied``.
There is no payload that carries a pfield through this door.

The wiped leaf then lowers with a substituted amplitude
(``_normalize_sc_pfields`` -> ``single_voice_amplitude``), which is neither the
value the composer stored nor the instrument's own default.  Nothing raises.

The project already ruled this question at the sibling ``replace=True`` door:
``ParameterApiMixin.graft_subtree`` preserves the target's overrides for any
key the donor does not define, because without it "``replace`` wiped them ...
so the three ways of adding structure disagreed about whether a node kept its
voicing."  These tests hold the two outlier doors to that same rule.

TWO FIXTURE TRAPS, both proven, both load-bearing:

1. **Never ramp from 0.0 with ``pfields=['amp']``.**  The inherited default is
   0.0, so a 0->1 ramp bakes leaf 0 at 0.0 as well and destroying leaf 0's
   value is INVISIBLE.  A test on the obvious fixture reads green over a live
   defect.  Hence ``ENV`` starts at 0.2.
2. **A missing value reads as ``None`` from the raw payload but as ``NaN``
   from ``uc.events``** (a float64 column).  ``all(v is not None ...)`` over an
   events column is green over a hole, so every assertion here reads the raw
   payload.
"""

import itertools

import pytest

from klotho.chronos import TemporalUnit as UT
from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.parameters.bind import Bind


def ENV():
    """A ramp that does NOT start at the inherited default (see trap 1)."""
    return Envelope([0.2, 1.0], times=[1.0])


def _unit(prolatio=(1, 1, 1, 1)):
    return UC.from_ut(UT(span=1, tempus='4/4', prolatio=prolatio,
                         beat='1/4', bpm=60))


def _oracle(prolatio, control=False):
    """A unit BUILT at the post-edit shape and enveloped from scratch.

    It never passed through a structural edit, so it is independent of every
    code path under test -- which is the whole point of comparing against it
    rather than against a literal.
    """
    u = _unit(prolatio)
    u.apply_envelope(ENV(), 'amp', node=u._rt.root, control=control)
    return u


def _amps(u):
    """Raw per-leaf ``amp``, so a hole reads as None rather than NaN."""
    return [u._rt[n].get('amp') for n in u._rt.leaf_nodes]


# ----------------------------------------------------------------------
# Premise guards -- these keep the witnesses below from passing vacuously
# ----------------------------------------------------------------------

def test_the_value_under_test_is_actually_present_before_the_edit():
    """T3: without this, T1/T2 could go green by measuring a value that was
    never there, or over a flat ramp whose baked value coincides with the
    inherited default."""
    u = _unit()
    u.apply_envelope(ENV(), 'amp', node=u._rt.root)
    amps = _amps(u)
    assert all(a is not None for a in amps), amps
    assert amps[1] != pytest.approx(amps[0]), (
        "the fixture ramp is flat -- a wipe at leaf 1 would be invisible")


def test_the_edit_really_moved_the_music():
    """T10: none of the witnesses may pass by the edit having been a no-op."""
    before = _unit()
    after = _unit((3, 1, 1, 1))
    assert [float(d) for d in before.durations] != pytest.approx(
        [float(d) for d in after.durations]), (
        "the pre- and post-edit shapes have the same durations, so a test "
        "asserting the edit changed something proves nothing")


# ----------------------------------------------------------------------
# The defect witnesses -- RED before the fix
# ----------------------------------------------------------------------

def test_replace_node_keeps_the_note_its_own_dynamic():
    """T1: reweighting a note must not take the dynamic it was carrying."""
    u = _unit()
    u.apply_envelope(ENV(), 'amp', node=u._rt.root)
    leaf = u._rt.leaf_nodes[1]          # MID-SPAN, deliberately not the anchor
    before = u._rt[leaf]['amp']
    u._rt.replace_node(leaf, proportion=3)
    assert u._rt[leaf].get('amp') == pytest.approx(before), (
        "a note that was reweighted lost the dynamic it was carrying")


def test_replace_node_data_keeps_the_note_its_own_dynamic():
    """T2: the same, through the other door.  Both are separate overrides."""
    u = _unit()
    u.apply_envelope(ENV(), 'amp', node=u._rt.root)
    leaf = u._rt.leaf_nodes[1]
    before = u._rt[leaf]['amp']
    u._rt.replace_node_data(leaf, {'proportion': 3})
    assert u._rt[leaf].get('amp') == pytest.approx(before), (
        "a note that was reweighted lost the dynamic it was carrying")


def test_replace_node_data_at_the_root_keeps_the_units_routing():
    """T4: ``group`` is track/loudspeaker routing and the constructor sets it
    on every unit's root, so this fires on ANY unit from ANY root replace."""
    u = _unit()
    before = list(u.events['group'])
    u._rt.replace_node_data(u._rt.root, {'proportion': 1})
    assert list(u.events['group']) == before, (
        "a root replace stripped the group mfield from the whole unit")


def test_replace_node_keeps_a_stored_bind_callable():
    """T5: R33 -- a duplicated or edited node keeps the ``Bind`` ITSELF, never
    a drawn value.  Destroying it is the harshest possible violation."""
    draws = itertools.count()
    u = _unit()
    u._rt.set_pfields(u._rt.root, amp=Bind(lambda ctx: next(draws) / 10.0))
    before = list(u.events['amp'])
    u._rt.replace_node(u._rt.root, proportion=1)   # a NO-OP proportion write
    assert list(u.events['amp']) == before, (
        "a stored Bind was destroyed by a replace that changed nothing")


def test_replace_node_fires_the_wipe_even_when_nothing_changes():
    """T6: writing the value that is already there must change nothing."""
    u = _unit()
    u.apply_envelope(ENV(), 'amp', node=u._rt.root)
    leaf = u._rt.leaf_nodes[1]
    before = dict(u._rt[leaf])
    u._rt.replace_node(leaf, proportion=before['proportion'])
    assert u._rt[leaf].get('amp') == pytest.approx(before['amp']), (
        "a replace that wrote the value already there still destroyed the "
        "payload")


# ----------------------------------------------------------------------
# Fences -- GREEN today AND after the fix.  They exist to go RED under the
# two wrong fix shapes, BOTH of which score 9264 green on the whole suite.
# ----------------------------------------------------------------------

def test_replace_node_leaves_the_bar_its_full_length():
    """T7, the DERIVED-KEY fence.

    Preserving "the keys this write path would refuse" -- a rule that reads
    reasonable and that two independent analyses recommended -- also preserves
    ``metric_duration``/``metric_onset``, which the rhythm layer RECOMPUTES
    inside ``super()``.  Restoring them overwrites the fresh values with stale
    pre-edit ones that nothing recomputes again: durations come back summing
    to 3.0 in a 4.0-second bar, so the note the composer just lengthened plays
    half its written length and a one-second hole opens mid-bar -- while the
    amp preservation works, so the change looks successful.  The full suite is
    green and the oracles are byte-identical under that variant.

    Assert onsets AND durations: the broken shape leaves onsets correct.
    Assert IMMEDIATELY, with no intervening edit: the stale value heals on the
    next unrelated node-data write, which would make this vacuous.
    """
    u = _unit()
    u.apply_envelope(ENV(), 'amp', node=u._rt.root)
    u._rt.replace_node(u._rt.leaf_nodes[0], proportion=3)
    o = _oracle((3, 1, 1, 1))
    assert [float(d) for d in u.durations] == pytest.approx(
        [float(d) for d in o.durations])
    assert [float(x) for x in u.onsets] == pytest.approx(
        [float(x) for x in o.onsets])
    assert sum(float(d) for d in u.durations) == pytest.approx(
        float(u.duration)), "the bar's notes no longer fill its span"


def test_the_restore_does_not_clobber_a_control_envelopes_respell():
    """T8, the PLACEMENT fence.

    The restore must sit between ``super()`` and
    ``_announce_if_surface_write``.  Placed after the announce -- which is what
    the obvious implementation does, wrapping the public verb as
    capture-call-restore -- the edited node keeps its pre-edit value while
    every neighbour respells, putting a kink in a curve nobody drew.  Suite
    green under that variant too.  The correctness window is one line wide.
    """
    u = _unit()
    u.apply_envelope(ENV(), 'amp', node=u._rt.root, control=True)
    u._rt.replace_node(u._rt.leaf_nodes[1], proportion=3)
    o = _oracle((1, 3, 1, 1), control=True)
    got = [u._rt[n].get('amp') for n in u._rt.leaf_nodes]
    exp = [o._rt[n].get('amp') for n in o._rt.leaf_nodes]
    assert got == pytest.approx(exp), (
        "the edited node kept its pre-edit value while its neighbours "
        "respelled -- a kink in a curve nobody drew")


@pytest.mark.parametrize("door", ['set_node_data', 'update_node_data',
                                  'set_node_attributes'])
def test_the_other_three_doors_still_preserve(door):
    """T9: the sanctioned twin.  Nine doors already preserve; the fix makes
    the two outliers agree with them rather than inventing a new rule."""
    u = _unit()
    u.apply_envelope(ENV(), 'amp', node=u._rt.root)
    leaf = u._rt.leaf_nodes[1]
    before = u._rt[leaf]['amp']
    if door == 'set_node_data':
        u._rt.set_node_data(leaf, proportion=3)
    elif door == 'update_node_data':
        u._rt.update_node_data(leaf, {'proportion': 3})
    else:
        u._rt.set_node_attributes(leaf, {'proportion': 3})
    assert u._rt[leaf].get('amp') == pytest.approx(before), (
        f"{door} destroyed a parameter value it has always preserved")


def test_a_rest_leaf_and_a_tie_survive_the_preserve():
    """T11: the fix must not resurrect values on rests, nor disturb the
    rest/tie surface."""
    u = _unit()
    leaves = list(u._rt.leaf_nodes)
    u._rt.set_pfields(leaves[1], amp=0.9)
    u._rt.make_rest(leaves[2])
    u._rt.replace_node(leaves[1], proportion=2)
    amps = _amps(u)
    assert amps[1] == pytest.approx(0.9), (
        "the authored value on the edited leaf did not survive")
    assert amps[2] is None, "the fix resurrected a value on a rest"
    props = [u._rt[n].get('proportion') for n in u._rt.leaf_nodes]
    assert props[2] < 0, "the rest stopped being a rest"
    assert props[1] == 2, "the structural edit did not take"


def test_a_derived_key_smuggled_in_as_a_pfield_cannot_corrupt_the_rhythm():
    """The preserve set must exclude keys another LAYER owns or derives.

    ``ParameterLayer.storage_keys()`` does not guarantee that on its own.
    ``ParameterLayer.set_instrument`` is the one pfield-registration door with
    no reserved-name check (``LAYER-22``), so an instrument whose ``pfields``
    are named ``metric_duration``/``metric_onset`` registers them as ordinary
    pfields.  The preserve step would then restore the PRE-EDIT rhythm over the
    values ``super()`` had just recomputed -- silently, and the bar stops
    summing to its own span.

    Measured before the ``reserved_keys`` subtraction: a 4/4 bar came back with
    durations summing to 5/8.  This is the fence for that, and it is a RELATION
    (the bar fills its own span) rather than a literal, so it cannot go stale.
    """
    from fractions import Fraction

    from klotho.thetos.composition.compositional import CompositionalUnit
    from klotho.thetos.instruments.base import Instrument

    uc = CompositionalUnit(span=1, tempus='4/4', prolatio=(1, 1, 1, 1))
    rt = uc._rt
    rt.set_instrument(
        rt.leaf_nodes[0],
        Instrument(name='kl_saw', pfields={'metric_duration': 99.0}),
    )
    # Premise guard: without this the test would pass by the key never
    # reaching the registry at all.
    assert 'metric_duration' in rt._param_layer.storage_keys(), (
        "set_instrument no longer registers an arbitrary pfield name, so this "
        "test is guarding nothing -- check LAYER-22 before deleting it")

    rt.replace_node(rt.leaf_nodes[0], proportion=5)

    total = sum(Fraction(str(d)) for d in rt.durations)
    assert total == Fraction(1), (
        f"the bar's notes sum to {total}, not to its own span -- a derived "
        f"key was preserved over the value super() recomputed")
