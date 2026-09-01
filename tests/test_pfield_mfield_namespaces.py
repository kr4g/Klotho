"""pfields and mfields are two namespaces, not one shared dict.

A ``CompositionalUnit`` carries two kinds of per-node field:

* **pfields** -- synth controls. Open namespace: whatever the SynthDef
  declares, plus whatever the composer invents.
* **mfields** -- engine meta-fields. Closed namespace, named by
  :data:`~klotho.thetos.composition.compositional.ENGINE_MFIELDS`
  (``strum``, ``group``, and the internal ``_slur_*`` markers). ``group``
  is the ROUTING group: which mixer track / physical output the voice
  plays on.

They used to share ONE per-node dict keyed by bare name, so the two
namespaces collided::

    uc.set_pfields(leaf, group=999.0)   # meant: a synth control
    uc.get_mfield(leaf, 'group')        # was: 999.0, not 'default'

That reaches PLAYBACK, not just the inspection surface: lowering routes
each voice by ``event.get_mfield('group')``. A composer who names a synth
control after an engine mfield silently re-routes their own audio -- and
with ``speaker`` about to join ``ENGINE_MFIELDS`` for multichannel
output, the same collision would send a voice to the wrong loudspeaker in
a 24-speaker installation.

``UC.set``'s docstring already promised this could not happen:

    pfields : dict or None, optional
        Explicit parameter fields. Escape hatch: values here always go
        to pfields, even if a name collides with an engine mfield.

The promise held at the API surface and broke in storage. These tests pin
the split: a pfield named ``group`` is an ordinary synth control that
reaches the synth, and the routing group beside it is untouched.
"""

import warnings

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.compositional import ENGINE_MFIELDS
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.thetos.parameters.parameter_tree import ParameterTree
from klotho.utils.playback.supersonic.converters import convert_to_sc_events


def _unit(**kw):
    """Four quarter notes at the default 60 bpm, on a real SynthDef."""
    kw.setdefault('inst', 'kl_saw')
    return UC(span=1, tempus='4/4', prolatio=(1, 1, 1, 1), **kw)


def _leaves(uc):
    return list(uc._rt.leaf_nodes)


# ---------------------------------------------------------------------------
# 1. The defect itself: a pfield must not move the routing group.
# ---------------------------------------------------------------------------

def test_engine_mfields_is_the_list_these_tests_are_about():
    """TRIPWIRE, not proof. If a name joins ENGINE_MFIELDS, it joins this
    contract too.

    ``speaker`` is the next one queued. This test does not demand it
    exists; it pins that everything currently in the set is covered by
    the parametrized tests below, so adding a name without reading this
    file fails here. It cannot fail for any other reason, and it is the
    one test here that no mutation of the implementation reddens.
    """
    assert ENGINE_MFIELDS == frozenset({'strum', 'group'})


@pytest.mark.parametrize('name', sorted(ENGINE_MFIELDS))
def test_a_pfield_does_not_move_the_routing_mfield(name):
    """``set_pfields(leaf, group=...)`` is a synth control, full stop."""
    uc = _unit()
    leaf = _leaves(uc)[0]
    # Seed the mfield explicitly: only ``group`` is registered by the
    # constructor, and an unregistered name would make this pass for the
    # uninteresting reason that there was nothing to overwrite.
    uc.set_mfields(leaf, **{name: 'routing'})
    before = uc.get_mfield(leaf, name)
    assert before == 'routing'

    uc.set_pfields(leaf, **{name: 999.0})

    assert uc.get_mfield(leaf, name) == before, (
        f"a pfield named {name!r} overwrote the engine mfield of the same "
        f"name -- that is the routing group, and it reaches playback"
    )
    assert uc.get_pfield(leaf, name) == 999.0


@pytest.mark.parametrize('name', sorted(ENGINE_MFIELDS))
def test_an_mfield_does_not_move_a_same_named_pfield(name):
    """And the other direction: re-routing must not rewrite a control."""
    uc = _unit()
    leaf = _leaves(uc)[0]
    uc.set_pfields(leaf, **{name: 0.25})

    uc.set_mfields(leaf, **{name: 'solo'})

    assert uc.get_pfield(leaf, name) == 0.25
    assert uc.get_mfield(leaf, name) == 'solo'


def test_the_two_registries_stay_separate_lists():
    uc = _unit()
    leaf = _leaves(uc)[0]
    uc.set_pfields(leaf, group=999.0)
    assert 'group' in uc.pfields
    assert 'group' in uc.mfields
    # ...but the VALUES are not shared, which is the whole point.
    assert uc.get_pfield(leaf, 'group') == 999.0
    assert uc.get_mfield(leaf, 'group') == 'default'


def test_routing_survives_a_same_named_pfield_all_the_way_to_the_engine():
    """The end-to-end claim: audio still goes where the composer said."""
    uc = _unit()
    uc.set_mfields(_leaves(uc), group='strings')
    uc.set_pfields(_leaves(uc), group=999.0)

    new_events = [e for e in convert_to_sc_events(uc) if e['type'] == 'new']
    assert new_events
    for event in new_events:
        assert event['group'] == 'strings', (
            "the lowered voice was routed by the synth control instead of "
            "the routing mfield"
        )
        assert event['pfields'].get('group') == 999.0, (
            "the synth control named 'group' did not reach the synth"
        )


# ---------------------------------------------------------------------------
# 2. The documented escape hatch on ``UC.set``.
# ---------------------------------------------------------------------------

def test_set_escape_hatch_sends_a_colliding_name_to_pfields():
    """``uc.set(node, pfields={'group': ...})``, exactly as documented."""
    uc = _unit()
    leaf = _leaves(uc)[0]

    uc.set(leaf, pfields={'group': 3.5})

    assert uc.get_pfield(leaf, 'group') == 3.5
    assert uc.get_mfield(leaf, 'group') == 'default'


def test_set_escape_hatch_sends_a_colliding_name_to_mfields():
    """The mirror hatch: ``mfields=`` wins over a SynthDef control name."""
    uc = _unit()
    leaf = _leaves(uc)[0]
    uc.set_pfields(leaf, freq=440.0)

    uc.set(leaf, mfields={'freq': 'not-a-control'})

    assert uc.get_pfield(leaf, 'freq') == 440.0
    assert uc.get_mfield(leaf, 'freq') == 'not-a-control'


def test_set_routes_both_hatches_in_one_call():
    uc = _unit()
    leaf = _leaves(uc)[0]

    uc.set(leaf, pfields={'group': 7.0}, mfields={'group': 'perc'})

    assert uc.get_pfield(leaf, 'group') == 7.0
    assert uc.get_mfield(leaf, 'group') == 'perc'


def test_bare_kwarg_still_auto_routes_to_the_mfield():
    """The default routing is unchanged: a bare ``group=`` is routing."""
    uc = _unit()
    leaf = _leaves(uc)[0]

    uc.set(leaf, group='choir')

    assert uc.get_mfield(leaf, 'group') == 'choir'
    assert uc.get_pfield(leaf, 'group') is None


# ---------------------------------------------------------------------------
# 3. Inheritance works for both kinds, independently.
# ---------------------------------------------------------------------------

def test_both_namespaces_inherit_down_the_tree():
    uc = _unit()
    root = uc._rt.root
    uc.set_pfields(root, group=1.5)
    uc.set_mfields(root, group='pads')
    for leaf in _leaves(uc):
        assert uc.get_pfield(leaf, 'group') == 1.5
        assert uc.get_mfield(leaf, 'group') == 'pads'


def test_a_leaf_override_shadows_only_its_own_namespace():
    uc = _unit()
    root = uc._rt.root
    leaves = _leaves(uc)
    uc.set_pfields(root, group=1.5)
    uc.set_mfields(root, group='pads')

    uc.set_pfields(leaves[0], group=9.0)

    assert uc.get_pfield(leaves[0], 'group') == 9.0
    assert uc.get_mfield(leaves[0], 'group') == 'pads'
    assert uc.get_pfield(leaves[1], 'group') == 1.5
    assert uc.get_mfield(leaves[1], 'group') == 'pads'


def test_a_write_after_a_read_patches_the_cache_in_the_right_namespace():
    """The incremental effective-cache patch, not the full rebuild.

    ``set_mfields`` restores the cache it just invalidated and repatches
    only the written subtree -- a separate code path from the cold build,
    with its own copy of the "which keys does this layer own" question.
    Reading first is what makes the cache exist and puts the write on
    that path.
    """
    uc = _unit()
    leaf = _leaves(uc)[0]
    assert uc.get_mfield(leaf, 'group') == 'default'   # builds the cache

    # The RAW tree door, deliberately: ``uc.set_mfields`` batches its
    # writes, and the batch's exit invalidation hides a wrong patch behind
    # a cold rebuild. Unbatched, the patched cache is what the next read
    # serves.
    uc._rt.set_mfields(uc._rt.root, group='warm')
    assert uc._rt.get_mfield(leaf, 'group') == 'warm'

    uc._rt.get_pfield(leaf, 'amp')
    uc._rt.set_pfields(uc._rt.root, group=1.25)
    assert uc._rt.get_pfield(leaf, 'group') == 1.25
    assert uc._rt.get_mfield(leaf, 'group') == 'warm'


def test_a_distribution_callable_sees_both_namespaces_mid_batch():
    """``ctx.mfields`` inside a distribution reads the patched cache.

    Distribution runs inside ``batch_writes``, where the incremental
    patch is the ONLY thing keeping earlier writes visible to later
    targets -- the cold rebuild does not run until the batch exits.
    """
    uc = _unit()
    leaves = _leaves(uc)
    uc.set_mfields(leaves, section='A')
    uc.set_pfields(leaves, section=0.5)

    seen = []
    uc.set_pfields(leaves,
                   probe=lambda c: seen.append((c.pfields.get('section'),
                                                c.mfields.get('section'))) or 1.0)
    assert seen == [(0.5, 'A')] * len(leaves)


def test_items_is_one_flat_dict_and_the_mfield_owns_a_shared_name():
    """``pt[node].items()`` cannot show two values under one key.

    Pinned rather than left to dict ordering: it is the same answer the
    ``uc.events`` column gives, so the two inspection surfaces agree.
    """
    uc = _seeded()
    leaf = _leaves(uc)[0]
    merged = uc.pt.items(leaf)
    assert merged['group'] == 'brass'
    assert merged['amp'] == 0.3
    assert uc.pt.pfield_items(leaf)['group'] == 4.25
    assert uc.pt.mfield_items(leaf)['group'] == 'brass'


def test_bare_parameter_tree_keeps_the_namespaces_apart_too():
    """The split lives in ``ParameterLayer``, so a bare PT has it as well."""
    pt = ParameterTree(1, (1, 1))
    leaf = pt.leaf_nodes[0]
    pt.set_pfields(leaf, group=2.0)
    pt.set_mfields(leaf, group='bass')
    assert pt.get_pfield(leaf, 'group') == 2.0
    assert pt.get_mfield(leaf, 'group') == 'bass'


# ---------------------------------------------------------------------------
# 4. All four copy paths carry both namespaces.
# ---------------------------------------------------------------------------

def _seeded():
    uc = _unit()
    uc.set_pfields(uc._rt.root, group=4.25, amp=0.3)
    uc.set_mfields(uc._rt.root, group='brass')
    return uc


def _assert_split_intact(unit, label):
    for leaf in list(unit._rt.leaf_nodes):
        assert unit.get_pfield(leaf, 'group') == 4.25, f"{label}: pfield lost"
        assert unit.get_mfield(leaf, 'group') == 'brass', f"{label}: mfield lost"


def test_copy_carries_both_namespaces():
    _assert_split_intact(_seeded().copy(), 'copy')


def test_deepcopy_carries_both_namespaces():
    import copy as _copy
    _assert_split_intact(_copy.deepcopy(_seeded()), 'deepcopy')


def test_copy_rebuild_carries_both_namespaces():
    _assert_split_intact(_seeded()._copy_rebuild(), '_copy_rebuild')


def test_scaling_carries_both_namespaces():
    from fractions import Fraction
    _assert_split_intact(_seeded() * Fraction(2, 1), 'scale')


def test_from_subtree_carries_both_namespaces():
    uc = _seeded()
    sub = uc.from_subtree(uc._rt.root)
    _assert_split_intact(sub, 'from_subtree')


def test_rt_subtree_carries_both_namespaces():
    """The raw ``_rt.subtree`` door, which has its own carry-over hook."""
    uc = _seeded()
    sub = uc._rt.subtree(uc._rt.root)
    for leaf in list(sub.leaf_nodes):
        assert sub.get_pfield(leaf, 'group') == 4.25
        assert sub.get_mfield(leaf, 'group') == 'brass'


def test_graft_carries_both_namespaces():
    donor = _unit()
    donor.set_pfields(donor._rt.root, group=4.25)
    donor.set_mfields(donor._rt.root, group='brass')

    host = _unit()
    target = _leaves(host)[0]
    host._rt.graft_subtree(target, donor._rt, mode='replace')

    grafted = [n for n in host._rt.leaf_nodes
               if target in host._rt.branch(n)] or [target]
    for leaf in grafted:
        assert host._rt.get_pfield(leaf, 'group') == 4.25
        assert host._rt.get_mfield(leaf, 'group') == 'brass'


def test_graft_replace_keeps_the_targets_own_overrides_in_both_namespaces():
    """``mode='replace'`` preserves what the donor root does not define.

    The preserved keys are read from the target's RAW payload, so this is
    the one carry-over that has to know the storage encoding rather than
    the field names.
    """
    donor = _unit()
    host = _unit()
    target = _leaves(host)[0]
    host.set_pfields(target, wobble=0.75)
    host.set_mfields(target, section='B')

    host._rt.graft_subtree(target, donor._rt, mode='replace')

    assert host._rt.get_pfield(target, 'wobble') == 0.75
    assert host._rt.get_mfield(target, 'section') == 'B', (
        "the target's own mfield override was dropped by the graft"
    )


def test_pt_snapshot_carries_both_namespaces():
    uc = _seeded()
    pt = uc.pt
    for leaf in list(pt.leaf_nodes):
        assert pt.get_pfield(leaf, 'group') == 4.25
        assert pt.get_mfield(leaf, 'group') == 'brass'


# ---------------------------------------------------------------------------
# 5. Inspection surfaces.
# ---------------------------------------------------------------------------

def test_events_reports_the_routing_group_and_warns_about_the_shadowed_pfield():
    """One table, one column name: the engine mfield owns it.

    Same shape of answer as the structural-column rule (d4dd5dd): the
    narrower namespace wins the column, ONE warning names what it hid,
    and the hidden field stays readable on the unit.
    """
    uc = _seeded()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        df = uc.events
    assert list(df['group']) == ['brass'] * 4
    assert any('group' in str(w.message) for w in caught), (
        "the shadowed pfield column was dropped silently"
    )
    assert uc.get_pfield(_leaves(uc)[0], 'group') == 4.25


def test_events_has_no_warning_when_nothing_collides():
    uc = _unit()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        uc.events
    assert not [w for w in caught if issubclass(w.category, UserWarning)]


def test_event_pfields_and_mfields_disagree_on_purpose():
    uc = _seeded()
    event = list(uc)[0]
    assert event.pfields['group'] == 4.25
    assert event.mfields['group'] == 'brass'
    assert event.get_pfield('group') == 4.25
    assert event.get_mfield('group') == 'brass'


# ---------------------------------------------------------------------------
# 5b. Late-bound values resolve against their own namespace.
# ---------------------------------------------------------------------------

def test_a_bind_resolves_against_the_namespace_it_was_stored_in():
    """A ``Bind``'s read set is the subtree of the node HOLDING it.

    With one name in both namespaces there are two holders, and the raw
    scan that finds them has to look in the right slot: an mfield Bind
    stored on a branch must not be resolved against a same-named pfield
    Bind stored on the root, which would hand it the whole tree's
    ``ctx.total`` instead of the branch's.
    """
    from klotho.thetos.parameters.bind import Bind

    uc = UC(span=1, tempus='4/4', prolatio=((1, (1, 1)), (1, (1, 1))),
            inst='kl_saw')
    branch = list(uc._rt.successors(uc._rt.root))[0]
    leaf = uc._rt.subtree_leaves(branch)[0]

    # both Binds resolve to their own ctx.total
    uc.set_pfields(uc._rt.root, x=Bind.index(map=lambda i, n: n))
    uc.set_mfields(branch, x=Bind.index(map=lambda i, n: n))

    assert uc.get_pfield(leaf, 'x') == 4, "the root pfield Bind saw 4 leaves"
    assert uc.get_mfield(leaf, 'x') == 2, (
        "the branch mfield Bind was resolved against the root's pfield Bind"
    )


def test_an_mfield_bind_reaches_the_event_and_the_snapshot_resolved():
    """The Bind INDEX is built by scanning raw payloads, so it has to
    decode storage keys back to names; the readers it gates -- event
    ``mfields`` and the effective-PT snapshot that feeds lowering -- are
    keyed by name and would otherwise serve the raw ``Bind`` object."""
    from klotho.thetos.parameters.bind import Bind

    uc = _unit()
    uc.set_mfields(uc._rt.root, group=Bind(lambda: 'lead'))
    leaf = _leaves(uc)[0]

    assert list(uc)[0].mfields['group'] == 'lead'
    assert uc.pt.get_mfield(leaf, 'group') == 'lead'
    assert not isinstance(uc.pt.get_mfield(leaf, 'group'), Bind)


# ---------------------------------------------------------------------------
# 6. Deletion, clearing, and the id-reuse hazard.
# ---------------------------------------------------------------------------

def test_clear_parameters_clears_both_namespaces():
    uc = _seeded()
    uc.clear_parameters()
    for leaf in _leaves(uc):
        assert uc.get_pfield(leaf, 'group') is None
        assert uc.get_mfield(leaf, 'group') is None


def test_remove_fields_removes_the_override_in_both_namespaces():
    uc = _seeded()
    leaf = _leaves(uc)[0]
    uc.set_pfields(leaf, group=9.0)
    uc.set_mfields(leaf, group='solo')

    uc._rt.remove_fields(leaf, ['group'])

    # the leaf's own overrides are gone; the root's values are inherited again
    assert uc.get_pfield(leaf, 'group') == 4.25
    assert uc.get_mfield(leaf, 'group') == 'brass'


def test_a_dead_node_leaves_neither_namespace_behind_on_a_reused_id():
    """rustworkx reuses freed ids; neither kind may re-attach to the reuse."""
    uc = _unit()
    victim = _leaves(uc)[-1]
    uc.set_pfields(victim, group=9.0)
    uc.set_mfields(victim, group='doomed')

    uc._rt.remove_subtree(victim)
    uc._rt.add_child(uc._rt.root, proportion=1)

    reused = [n for n in uc._rt.leaf_nodes if n == victim]
    assert reused, "the freed id was not reused; test no longer exercises it"
    # The recycled slot inherits from the root and carries nothing of the
    # node that died in it.
    assert uc._rt.get_pfield(victim, 'group') is None
    assert uc._rt.get_mfield(victim, 'group') == 'default'


# ---------------------------------------------------------------------------
# 7. The reserved-name lock is unchanged.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('setter', ['set_pfields', 'set_mfields'])
@pytest.mark.parametrize('name', ['proportion', 'metric_duration'])
def test_rhythm_layer_keys_are_still_refused_in_both_namespaces(setter, name):
    uc = _unit()
    with pytest.raises(ValueError, match='owned by another layer'):
        getattr(uc._rt, setter)(_leaves(uc)[0], **{name: 1})


def test_a_storage_sentinel_cannot_be_smuggled_in_as_a_field_name():
    """The split encodes mfields under a private key prefix; a field name
    carrying that prefix would land in the same slot and re-open the
    collision from the other side."""
    from klotho.thetos.parameters.parameter_tree import mfield_storage_key
    smuggled = mfield_storage_key('group')
    uc = _unit()
    with pytest.raises(ValueError):
        uc._rt.set_pfields(_leaves(uc)[0], **{smuggled: 1.0})
    with pytest.raises(ValueError):
        uc._rt.register_pfields([smuggled])


# ---------------------------------------------------------------------------
# 8. Lowering reads the mfield, never the pfield.
# ---------------------------------------------------------------------------

def test_a_pfield_named_group_is_an_ordinary_control_at_lowering():
    uc = _unit(inst=SynthDefInstrument(name='w', defName='kl_saw',
                                       pfields={'freq': 220.0, 'amp': 0.2}))
    uc.set_pfields(_leaves(uc), group=12.0)
    new_events = [e for e in convert_to_sc_events(uc) if e['type'] == 'new']
    assert new_events
    for event in new_events:
        assert event['pfields']['group'] == 12.0
        assert event['group'] == 'default'


def test_slur_markers_are_mfields_and_are_untouched_by_a_pfield():
    """The internal ``_slur_*`` markers are mfields like any other.

    The snapshot writes them LAST, so before the split a colliding pfield
    was the side that lost: the marker overwrote it. Both directions are
    checked here, so the test fails whichever way the collision goes.
    """
    uc = _unit()
    leaves = _leaves(uc)
    uc.apply_slur(node=leaves[:2])
    uc.set_pfields(leaves, _slur_id=99.0)
    pt = uc.pt
    assert pt.get_mfield(leaves[0], '_slur_start') == 1
    assert pt.get_mfield(leaves[0], '_slur_id') != 99.0
    assert pt.get_pfield(leaves[0], '_slur_id') == 99.0
    assert uc.get_pfield(leaves[0], '_slur_id') == 99.0
