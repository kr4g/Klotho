"""EVENTS-1: ``uc.events`` memoizes on a key that does not read slur state.

The key was ``(_structure_version, _bpm, _beat, _offset,
_instruments_version)``. ``apply_slur`` moves none of them, so a DataFrame
read once BEFORE a slur was drawn was served forever afterwards and the
``_slur_id``/``_slur_start``/``_slur_end`` columns never appeared.

Playback was never affected -- the sibling snapshot in
``_build_effective_parameter_tree`` did key on the slur numbers -- so the
symptom was the INSPECTION surface lying to a composer checking their work.
That is the worse way round: the reader who consults ``uc.events`` is the one
with no other way to see what the object thinks it holds.

The fix keys both memos on a DERIVED digest of slur membership rather than on
counters, because the counters were already going quiet: SLUR-1's identity
rule (an unsplit arc keeps its id) stopped ``_next_slur_id`` moving on the
commonest reshape, which NEW-42 filed as a caution.
"""

import warnings

from klotho.thetos import CompositionalUnit as UC


def _slur_flags(uc):
    """``(heads, tails)`` counted off the lowering surface."""
    events = uc.events
    heads = sum(1 for _, row in events.iterrows()
                if row.get('_slur_start') == 1.0)
    tails = sum(1 for _, row in events.iterrows()
                if row.get('_slur_end') == 1.0)
    return heads, tails


class TestEventsSeesTheSlurItWasToldAbout:
    """EVENTS-1. ``uc.events`` memoizes on
    ``(_structure_version, _bpm, _beat, _offset, _instruments_version)``.
    ``apply_slur`` moves none of them, so a DataFrame read once before the
    slur is served forever after.

    Playback is unaffected -- the sibling snapshot in
    ``_build_effective_parameter_tree`` keys on the slur numbers -- so this
    is the inspection surface lying to a composer who checked their work,
    which is the reader least able to tell.
    """

    def test_a_slur_drawn_after_a_read_is_visible_on_the_next_read(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)

        uc.events                                   # prime the memo
        uc.apply_slur([leaves[1], leaves[2]])

        columns = [c for c in uc.events.columns if 'slur' in c]
        assert columns, 'the slur is invisible on the inspection surface'

    def test_the_flags_land_on_the_right_notes_after_a_primed_read(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)

        uc.events
        uc.apply_slur([leaves[1], leaves[2]])

        events = uc.events.set_index('node_id')
        assert events.loc[leaves[1], '_slur_start'] == 1.0
        assert events.loc[leaves[2], '_slur_end'] == 1.0

    def test_a_dissolved_slur_stops_being_visible(self):
        """The other direction. A memo that only ever gains columns is a
        memo that lies the moment an arc dies."""
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur([leaves[1], leaves[2]])

        uc.events                                   # prime WITH the slur
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc.make_rest(leaves[2])

        heads, tails = _slur_flags(uc)
        assert (heads, tails) == (0, 0)
