"""AF2-16 -- "a set is a set": a write at an ancestor overwrites descendants.

Ruled by Ryan, 2026-09-01, in his own words:

    "we can always overwrite anything. I may have authored values to the leaf
     nodes by iterating over them, but then I may want to overwrite them by
     setting something at the root and cascading down. Maybe we have some sort
     'lock' feature that we can apply at nodes to prevent the cascade from
     flowing past it. But otherwise, a set is a set."

Before this, ``uc.leaves.set_pfields(amp=0.5)`` -- which authors an override on
EVERY leaf, and is an ordinary idiom in the MAT 111MC corpus -- left the unit
permanently deaf to a later root write. The values stayed at 0.5 with no error
and no warning: the composer edits the score and hears the old music, on the
original unit, with no copy and no extraction involved.

WHERE THE EXPECTED VALUES COME FROM: the rule itself, stated above, applied to a
hand-built four-leaf unit. Not from running the new code.

PROVEN RED against cf5c448 (the commit immediately before the fix), in an
isolated tree with ``klotho.__file__`` asserted -- see handoffs/AF-2.md.

The per-node LOCK named in the ruling is deliberately NOT implemented here; it is
filed as its own design item so it gets designed rather than bolted on.
"""

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.parameters import Bind


def unit(**kw):
    return UC(span=1, tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60, **kw)


def test_a_root_write_overwrites_values_authored_on_every_leaf():
    """The reported case, exactly."""
    uc = unit(pfields={'amp': 0.0})
    uc.leaves.set_pfields(amp=0.5)
    assert list(uc.events['amp']) == [0.5, 0.5, 0.5, 0.5], "precondition"
    uc.set_pfields(uc._rt.root, amp=0.9)
    assert list(uc.events['amp']) == [0.9, 0.9, 0.9, 0.9]


def test_the_handle_spelling_behaves_identically():
    """``uc.root.set_pfields`` is the spelling the corpus actually uses."""
    uc = unit(pfields={'amp': 0.0})
    uc.leaves.set_pfields(amp=0.5)
    uc.root.set_pfields(amp=0.9)
    assert list(uc.events['amp']) == [0.9, 0.9, 0.9, 0.9]


def test_an_interior_write_overwrites_only_its_own_subtree():
    """Cascade is scoped: a branch write must not reach its siblings."""
    uc = UC(span=1, tempus='4/4', prolatio=((1, (1, 1)), (1, (1, 1))),
            beat='1/4', bpm=60, pfields={'amp': 0.0})
    uc.leaves.set_pfields(amp=0.5)
    uc.set_pfields(1, amp=0.7)          # branch 1 owns leaves 2 and 3
    assert list(uc.events['amp']) == [0.7, 0.7, 0.5, 0.5]


def test_a_later_write_below_still_wins_because_it_is_later():
    """Order expresses intent; proximity does not. The escape hatch for
    'these are the exceptions' is to write the exceptions AFTER the ancestor."""
    uc = unit(pfields={'amp': 0.0})
    uc.set_pfields(uc._rt.root, amp=0.9)
    uc.leaves[0].set_pfields(amp=0.1)
    assert list(uc.events['amp']) == [0.1, 0.9, 0.9, 0.9]


def test_it_applies_to_mfields_too():
    """mfields are namespaced in the payload; a name-keyed sweep would miss them."""
    uc = unit(pfields={'amp': 0.0}, mfields={'group': ''})
    uc.leaves.set_mfields(group='solo')
    assert list(uc.events['group']) == ['solo'] * 4, "precondition"
    uc.set_mfields(uc._rt.root, group='tutti')
    assert list(uc.events['group']) == ['tutti'] * 4


def test_it_applies_to_a_stored_bind():
    """A Bind is a value like any other: you set it, so it is set."""
    uc = unit(pfields={'amp': 0.0})
    uc.leaves.set_pfields(amp=Bind(lambda c: 0.25))
    assert list(uc.events['amp']) == [0.25] * 4, "precondition"
    uc.set_pfields(uc._rt.root, amp=Bind(lambda c: 0.75))
    assert list(uc.events['amp']) == [0.75] * 4


def test_an_unrelated_field_is_untouched():
    """The sweep clears only the keys actually written."""
    uc = unit(pfields={'amp': 0.0, 'pan': 0.0})
    uc.leaves.set_pfields(amp=0.5, pan=0.3)
    uc.set_pfields(uc._rt.root, amp=0.9)
    assert list(uc.events['amp']) == [0.9] * 4
    assert list(uc.events['pan']) == [0.3] * 4, "pan was never written at the root"
