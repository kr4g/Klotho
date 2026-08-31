"""``make_rest`` healed the same edit twice, and the public handle lost.

``UC.make_rest`` ran ``_split_slurs_for_rests`` BEFORE writing the rests, and
then -- since TIE-3/TIE-4 wired the verb to the seam -- the seam heal ran
again DURING the write. Two mechanisms, two moments, one edit.

They disagree, and the pre-heal is the one that is wrong, because it reasons
about a tie that the write is about to destroy. ``make_rest`` clears ``tied``
on every leaf it silences (a tied rest is illegal, charter §1), so a leaf
that was a continuation of a rested note is a NOTE by the time the dust
settles -- but the pre-heal, running first, still sees a continuation and
drops it out of the arc.

Measured over 2430 cases across four tree shapes: 46 disagreements between
``uc.make_rest`` and ``uc._rt.make_rest``, and in every one the seam-only
answer keeps music the pre-heal discards. Removing the pre-heal takes the
count to zero and changes no other test in the suite -- it bought nothing
that anything could see, and cost a note.

R12 lens 2 is the rule it breaks: one musical question must not get two
answers depending on which handle the caller held. That was the whole SLUR-1
finding, and here the PUBLIC handle was the wrong one.
"""

import itertools
import warnings

import pytest

from klotho.thetos import CompositionalUnit as UC


SHAPES = [
    (1,) * 6,
    ((2, (1, 1)), 1, 1, 1),
    ((3, (1, 1, 1)), (2, (1, 1))),
    (1, (2, (1, 1)), 1, 1),
]


def _build(shape, tie_at):
    uc = UC(tempus='6/4', prolatio=shape, beat='1/4', bpm=60,
            pfields={'freq': 440})
    leaves = list(uc._rt.leaf_nodes)
    if tie_at is not None and tie_at < len(leaves):
        uc._rt.set_node_data(leaves[tie_at], tied=True)
    return uc, leaves


def _arcs(uc):
    return sorted(tuple(spec['leaf_nodes'])
                  for spec in uc._slur_specs.values())


class TestTheHandlesAgreeAboutResting:
    """The property, swept rather than sampled: a single example would have
    missed this, because the divergence needs a tie whose HEAD is among the
    rested leaves."""

    def test_no_shape_makes_the_two_handles_disagree(self):
        divergences = []
        for shape in SHAPES:
            for tie_at in (None, 1, 2, 3):
                size = len(_build(shape, None)[1])
                for start in range(size - 1):
                    for span in (2, 3, 4):
                        if start + span > size:
                            continue
                        rest_sets = (list(itertools.combinations(range(size), 1))
                                     + list(itertools.combinations(range(size), 2)))
                        for rests in rest_sets:
                            with warnings.catch_warnings():
                                warnings.simplefilter('ignore')
                                via_uc, a = _build(shape, tie_at)
                                via_raw, b = _build(shape, tie_at)
                                try:
                                    via_uc.apply_slur(a[start:start + span])
                                    via_raw.apply_slur(b[start:start + span])
                                except ValueError:
                                    continue
                                via_uc.make_rest([a[i] for i in rests])
                                for i in rests:
                                    via_raw._rt.make_rest(b[i])
                            if _arcs(via_uc) != _arcs(via_raw):
                                divergences.append(
                                    (shape, tie_at, (start, span), rests,
                                     _arcs(via_uc), _arcs(via_raw)))
        assert not divergences, (
            f'{len(divergences)} handle disagreements, first three: '
            f'{divergences[:3]}')


class TestTheNoteThePreHealDiscarded:
    """The headline case, spelled out, so the reason survives the sweep.

    Six beats; beat 3 is tied to beat 2; the arc covers beats 3-6. Resting
    beats 1 and 2 silences the tie's HEAD -- so beat 3 stops being anyone's
    continuation and becomes an ordinary note, and it is the note the phrase
    now begins on.
    """

    def test_the_arc_keeps_the_note_the_rest_un_tied(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc, leaves = _build((1,) * 6, 2)
            uc.apply_slur(leaves[2:6])
            uc.make_rest([leaves[0], leaves[1]])

        assert _arcs(uc) == [tuple(leaves[2:6])], (
            f'the arc lost the note that the rest turned back into a note: '
            f'{_arcs(uc)}')
