"""AF-2 / AUD-6 + AUD-7 -- raw override PLACEMENT must survive a copy.

``_copy_pt_node_data`` used to copy each node's EFFECTIVE (inherited) pfield
and mfield values, so every unit produced by ``from_subtree``, by ``decompose``,
or by ``copy()`` on a ``CompositionalUnit`` SUBCLASS came back with an override
materialized at EVERY node. The inheritance STRUCTURE was destroyed while the
values looked right, so a later rewrite at the copy's root changed nothing below
it: the composer edits the score and hears the old music.

WHERE THE EXPECTED VALUES COME FROM -- none of them was produced by running the
new code, which this project forbids:

* The placement and propagation assertions are HAND-DERIVED FROM THE INHERITANCE
  SPEC: an override written at node N is inherited by N's descendants and by
  nobody else, so a copy that preserves placement must answer a later root write
  exactly as the source does. The base-class ``copy()`` path already behaves this
  way and is used below as a live CONTROL -- it was measured correct BEFORE this
  fix, so it pins the target behaviour independently.
* The ``Bind`` values are hand-computed from the Bind's own arithmetic over a
  known leaf count (index i of n), not read off a run.
* The stochastic assertions test a RELATION (re-rolls versus the source, constant
  across repeated reads, read set equal to the extract's leaf count), never a
  drawn number.

PROVEN RED: every test in this file except the declared controls fails against
pre-AF-2 source. See handoffs/AF-2.md for the recorded run.
"""

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.parameters import Bind


def raw_override_nodes(uc):
    """Nodes carrying a RAW override, using the codebase's own idiom.

    Mirrors ``_extract_parameter_tree`` and ``_mirror_param_state``: filter the
    node payload by the parameter layer's STORAGE keys, which is what keeps
    namespaced mfields visible.
    """
    rt = uc._rt
    keys = rt._param_layer.storage_keys()
    return sorted(
        n for n in rt.nodes
        if isinstance(rt._rx[n], dict) and any(k in keys for k in rt._rx[n])
    )


def flat_uc(**kw):
    return UC(span=1, tempus='4/4', prolatio=(1, 1, 1, 1),
              beat='1/4', bpm=60, **kw)


def branched_uc(**kw):
    """Root 0 -> branch 1 (leaves 2, 3) and branch 4 (leaves 5, 6)."""
    return UC(span=1, tempus='4/4', prolatio=((1, (1, 1)), (1, (1, 1))),
              beat='1/4', bpm=60, **kw)


class Subclassed(UC):
    """A bare subclass: ``copy()`` routes it through ``_copy_rebuild``."""


# ---------------------------------------------------------------- placement

def test_source_places_a_root_write_at_the_root_only():
    """CONTROL -- passes before and after. Pins the premise everything rests on."""
    uc = flat_uc(pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=0.5)
    assert raw_override_nodes(uc) == [0]
    assert list(uc.events['amp']) == [0.5, 0.5, 0.5, 0.5]


def test_base_class_copy_preserves_placement():
    """CONTROL -- the already-correct path, used as the independent oracle."""
    uc = flat_uc(pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=0.5)
    c = uc.copy()
    assert raw_override_nodes(c) == [0]
    c.set_pfields(c._rt.root, amp=0.8)
    assert list(c.events['amp']) == [0.8, 0.8, 0.8, 0.8]


def test_from_subtree_preserves_override_placement():
    uc = flat_uc(pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=0.5)
    sub = uc.from_subtree(uc._rt.root)
    assert raw_override_nodes(sub) == [sub._rt.root], (
        "the root override must stay at the root, not be materialized at every node"
    )


def test_from_subtree_root_rewrite_reaches_the_leaves():
    """The finding itself: the composer edits the copy and must hear the edit."""
    uc = flat_uc(pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=0.5)
    sub = uc.from_subtree(uc._rt.root)
    sub.set_pfields(sub._rt.root, amp=0.9)
    assert list(sub.events['amp']) == [0.9, 0.9, 0.9, 0.9]


def test_subclass_copy_preserves_override_placement():
    uc = Subclassed(span=1, tempus='4/4', prolatio=(1, 1, 1, 1),
                    beat='1/4', bpm=60, pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=0.5)
    c = uc.copy()
    assert raw_override_nodes(c) == [c._rt.root]
    c.set_pfields(c._rt.root, amp=0.8)
    assert list(c.events['amp']) == [0.8, 0.8, 0.8, 0.8]


def test_decompose_fragments_preserve_override_placement():
    from klotho.chronos.temporal_units.algorithms import decompose
    uc = UC(span=1, tempus='4/4', prolatio=(1, (1, (1, 1)), 1, 1),
            beat='1/4', bpm=60, pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=0.5)
    for frag in decompose(uc, depth=1):
        if not hasattr(frag, 'set_pfields'):
            continue
        assert raw_override_nodes(frag) == [frag._rt.root]
        frag.set_pfields(frag._rt.root, amp=0.8)
        assert list(frag.events['amp']) == [0.8] * len(list(frag.events['amp']))


def test_interior_override_is_not_flattened_onto_its_descendants():
    """An override on a BRANCH must stay on that branch, not spread to its leaves."""
    uc = branched_uc(pfields={'amp': 0.0})
    uc.set_pfields(1, amp=0.5)
    # The constructor's ``pfields={'amp': 0.0}`` itself writes at the root, so
    # the source legitimately carries TWO overrides: the root default and the
    # branch write. The invariant is not a count -- it is that the copy places
    # them exactly where the source did.
    assert raw_override_nodes(uc) == [0, 1]
    sub = uc.from_subtree(uc._rt.root)
    assert raw_override_nodes(sub) == raw_override_nodes(uc), (
        "the branch override must stay on the branch, not spread to its leaves"
    )
    # And the branch override must still shadow a root rewrite, as it does on
    # the source: leaves 2 and 3 keep 0.5 while 5 and 6 follow the root to 0.9.
    sub.set_pfields(sub._rt.root, amp=0.9)
    assert list(sub.events['amp']) == [0.5, 0.5, 0.9, 0.9]


def test_inheritance_from_outside_the_extract_survives_at_the_new_root():
    """Extracting a BRANCH must not lose what that branch inherited from above."""
    uc = branched_uc(pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=0.5)
    ex = uc.from_subtree(1)
    assert list(ex.events['amp']) == [0.5, 0.5], (
        "the value inherited from the ancestor that did not come along is lost"
    )
    assert raw_override_nodes(ex) == [ex._rt.root], (
        "it must be re-homed at the extract's root, not stamped on every leaf"
    )


def test_mfields_survive_the_copy_with_their_placement():
    """mfields are namespaced in the payload; a name-based filter drops them."""
    uc = flat_uc(pfields={'amp': 0.0}, mfields={'group': ''})
    uc.set_mfields(uc._rt.root, group='solo')
    sub = uc.from_subtree(uc._rt.root)
    assert raw_override_nodes(sub) == [sub._rt.root]
    assert list(sub.events['group']) == ['solo'] * 4


# -------------------------------------------------------------------- Binds

def test_bind_index_survives_from_subtree_without_raising():
    """AUD-7 LOUD half. Bind.index over 4 leaves is i/(n-1) for i in 0..3:
    0/3, 1/3, 2/3, 3/3 -> 0.0, 0.333, 0.667, 1.0 (rounded to 3 places by the
    map itself). Hand-computed, not read off a run."""
    uc = flat_uc(pfields={'pan': 0.0})
    uc.set_pfields(uc._rt.root,
                   pan=Bind.index(map=lambda i, n: round(i / max(n - 1, 1), 3)))
    assert list(uc.events['pan']) == [0.0, 0.333, 0.667, 1.0]
    sub = uc.from_subtree(uc._rt.root)
    assert list(sub.events['pan']) == [0.0, 0.333, 0.667, 1.0]


def test_bind_reading_ctx_keeps_the_whole_read_set():
    """AUD-7 SILENT half -- the dangerous one. A ctx-reading Bind that is not
    ``reads_selection`` raises nothing; it just flattens. Four leaves under one
    Bind must see total == 4 and index 0..3."""
    uc = flat_uc(pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=Bind(lambda c: (c.index, c.total)))
    assert list(uc.events['amp']) == [(0, 4), (1, 4), (2, 4), (3, 4)]
    sub = uc.from_subtree(uc._rt.root)
    assert list(sub.events['amp']) == [(0, 4), (1, 4), (2, 4), (3, 4)], (
        "each leaf became its own one-leaf read set -- a pan spread flattens silently"
    )


def test_bind_inherited_from_outside_reads_the_extracts_leaves():
    """D1, ruled by R33: the Bind is KEPT (it travels and stays live), landing at
    the extract's root. A 2-leaf extract must therefore see total == 2."""
    uc = branched_uc(pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=Bind(lambda c: (c.index, c.total)))
    assert list(uc.events['amp']) == [(0, 4), (1, 4), (2, 4), (3, 4)]
    ex = uc.from_subtree(1)
    assert list(ex.events['amp']) == [(0, 2), (1, 2)], (
        "the inherited Bind must sit at the extract's root over its own 2 leaves"
    )


def test_stochastic_bind_rerolls_but_is_stable_within_the_extract():
    """R33 is a UNIVERSAL rule -- ``from_subtree`` duplicates, so it copies the
    Bind, not the drawn value, and draws again. Asserts a RELATION only: never a
    drawn number."""
    import random
    uc = branched_uc(pfields={'amp': 0.0})
    rng = random.Random(1234)
    uc.set_pfields(uc._rt.root, amp=Bind(lambda c: rng.random()))
    src = list(uc.events['amp'])
    assert src == list(uc.events['amp']), "source draws must be stable across reads"
    ex = uc.from_subtree(1)
    first = list(ex.events['amp'])
    assert first == list(ex.events['amp']), "extract draws must be stable across reads"
    assert len(first) == 2
    assert first != src[:2], "R33: a duplicating verb copies the Bind, so it re-rolls"


# ------------------- the authored-vs-inherited distinction, both directions

def test_an_authored_leaf_value_still_wins_over_a_root_write_on_a_fragment():
    """CONTROL — passes before and after, and it is here because an adversarial
    verifier read this behaviour as a surviving AUD-6 defect. It is not.

    Measured on the SOURCE: a leaf carrying its OWN ``amp`` is NOT changed by a
    later root write — ``[0.5, 0.5, 0.5, 0.5]`` stays — while a leaf with no
    override of its own follows the root to 0.9. So a single-leaf fragment that
    keeps answering 0.5 after ``frag.root.set_pfields(amp=0.9)`` is REPRODUCING
    its source faithfully. Expecting 0.9 there means expecting a root write to
    erase an authored value, which is not what inheritance means here and not
    what the source does.

    Pinned so the next reader does not 'fix' it into a real defect."""
    uc = flat_uc(pfields={'amp': 0.5})
    uc.leaves.set_pfields(amp=0.5)
    uc.set_pfields(uc._rt.root, amp=0.9)
    assert list(uc.events['amp']) == [0.5, 0.5, 0.5, 0.5], (
        "source premise: an authored leaf value survives a root write"
    )

    from klotho.chronos.temporal_units.algorithms import decompose
    src = flat_uc(pfields={'amp': 0.5})
    src.leaves.set_pfields(amp=0.5)
    frag = list(decompose(src))[0]
    frag.set_pfields(frag._rt.root, amp=0.9)
    assert list(frag.events['amp']) == [0.5], (
        "the fragment must answer as its source does, not cascade over an "
        "authored value"
    )


def test_a_fragment_root_write_DOES_reach_a_leaf_that_authored_nothing():
    """The other direction, and this one WAS red before `bb0164e`: the fragment's
    root must carry what the leaf inherited from outside, so a root write on the
    fragment cascades exactly as it would on the source."""
    from klotho.chronos.temporal_units.algorithms import decompose
    src = flat_uc(pfields={'amp': 0.0})
    src.set_pfields(src._rt.root, amp=0.5)
    frag = list(decompose(src))[0]
    assert list(frag.events['amp']) == [0.5], "inherited context must survive the extract"
    frag.set_pfields(frag._rt.root, amp=0.9)
    assert list(frag.events['amp']) == [0.9]
