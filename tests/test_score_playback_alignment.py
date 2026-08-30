"""``play(score)`` must see the same block alignment every other reader does.

The read-time validation added for BT alignment staleness lives in
``TemporalBlock._ensure_aligned``, and every *public* reader -- ``rows``,
``duration``, ``end``, ``events``, ``principal_row``, ``__iter__``,
``__getitem__`` -- goes through it. ``_iter_ucs``, the walker the SuperSonic
Score converters use, reached past that by iterating ``unit._rows`` /
``unit._seq`` directly, so the audible rendering of a Score depended on
whether some *other* reader had happened to run first.

Only the ``_rows`` half of that was behavioural. ``TemporalUnitSequence``
has no alignment cache and its ``__iter__`` is ``iter(self._seq)``, so the
sequence branch was changed for consistency, not to fix anything; nothing
in this file can tell the two spellings apart, and nothing here claims to.

That is the worst shape a bug can take here: the same Score played twice
sounds different, and the difference is invisible from the notebook because
plotting the block (an aligned read) silently repairs it.

Note on how the staleness is reached: ``Score.add`` **copies** the unit, so
mutating the caller's own block cannot make a Score stale at all. The live
row has to be reached through the item the score handed back
(``score.add(blk).unit``) -- that object is the one ``_iter_ucs`` walks.

These tests pin the two arms -- "convert straight after a live-row edit" and
"convert after any aligned read" -- as identical, for both the audio and the
animation entry points.
"""

import pytest

from klotho.chronos import TemporalUnitSequence, TemporalBlock
from klotho.thetos import CompositionalUnit
from klotho.thetos.composition.score import Score
from klotho.utils.playback.supersonic.converters import (
    convert_score_to_sc_events,
    convert_score_to_sc_animation_events,
)


def _uc(tempus='4/4', prolatio=(1, 1), bpm=60):
    return CompositionalUnit(tempus=tempus, prolatio=prolatio, beat='1/4', bpm=bpm)


def _block_score(axis=1, sort_rows=False):
    """A right-aligned block whose row 0 is a UTS -- i.e. a row that can be
    grown through its own API without any block-level mutator running.

    Returns the block *the score holds*, not the constructed one.
    """
    blk = TemporalBlock([TemporalUnitSequence([_uc()]), _uc()],
                        axis=axis, sort_rows=sort_rows)
    score = Score()
    return score.add(blk).unit, score


def _starts(payload):
    return [ev['start'] for ev in payload['events']]


class TestScoreConversionSeesTheAlignedBlock:

    def test_audio_conversion_is_the_same_with_or_without_a_prior_read(self):
        blk_a, score_a = _block_score()
        blk_a.rows[0].append(_uc())
        straight = _starts(convert_score_to_sc_events(score_a))

        blk_b, score_b = _block_score()
        blk_b.rows[0].append(_uc())
        blk_b.events                      # any aligned read repairs the block
        after_read = _starts(convert_score_to_sc_events(score_b))

        assert straight == pytest.approx(after_read)

    def test_audio_conversion_renders_the_aligned_onsets(self):
        # Spelled out rather than compared to ``blk.end``, because reading the
        # block at all repairs it and would make the assertion vacuous. At
        # axis=1 the grown row 0 (8s) sets the block end and the plain row 1
        # (4s) shifts to 4.0; each UC contributes two 2s chronons.
        blk, score = _block_score()
        blk.rows[0].append(_uc())
        assert _starts(convert_score_to_sc_events(score)) == pytest.approx(
            [0.0, 2.0, 4.0, 4.0, 6.0, 6.0])

    def test_animation_conversion_is_the_same_with_or_without_a_prior_read(self):
        blk_a, score_a = _block_score()
        blk_a.rows[0].append(_uc())
        straight = _starts(convert_score_to_sc_animation_events(score_a))

        blk_b, score_b = _block_score()
        blk_b.rows[0].append(_uc())
        blk_b.events
        after_read = _starts(convert_score_to_sc_animation_events(score_b))

        assert straight == pytest.approx(after_read)

    @pytest.mark.parametrize('axis', [-1.0, -0.5, 0.0, 0.5, 1.0])
    def test_every_axis_renders_the_same_either_way(self, axis):
        blk_a, score_a = _block_score(axis=axis)
        blk_a.rows[0].append(_uc())
        straight = _starts(convert_score_to_sc_events(score_a))

        blk_b, score_b = _block_score(axis=axis)
        blk_b.rows[0].append(_uc())
        blk_b.events
        after_read = _starts(convert_score_to_sc_events(score_b))

        assert straight == pytest.approx(after_read), axis

    def test_a_shrinking_row_renders_the_same_either_way(self):
        # The other direction: the untouched row is the one left hanging past
        # the block's new end when alignment goes stale.
        def build():
            blk = TemporalBlock([TemporalUnitSequence([_uc(), _uc()]), _uc()],
                                axis=1, sort_rows=False)
            score = Score()
            return score.add(blk).unit, score

        blk_a, score_a = build()
        blk_a.rows[0].remove(1)
        straight = _starts(convert_score_to_sc_events(score_a))

        blk_b, score_b = build()
        blk_b.rows[0].remove(1)
        blk_b.events
        after_read = _starts(convert_score_to_sc_events(score_b))

        assert straight == pytest.approx(after_read)

    def test_a_nested_block_renders_the_same_either_way(self):
        def build():
            inner = TemporalBlock([TemporalUnitSequence([_uc()]), _uc()],
                                  axis=0, sort_rows=False)
            blk = TemporalBlock([inner, _uc()], axis=1, sort_rows=False)
            score = Score()
            return score.add(blk).unit, score

        blk_a, score_a = build()
        blk_a.rows[0].rows[0].append(_uc())
        straight = _starts(convert_score_to_sc_events(score_a))

        blk_b, score_b = build()
        blk_b.rows[0].rows[0].append(_uc())
        blk_b.events
        after_read = _starts(convert_score_to_sc_events(score_b))

        assert straight == pytest.approx(after_read)

    def test_a_block_nested_in_a_sequence_renders_the_same_either_way(self):
        # A stale block one level down inside a sequence.
        #
        # This does NOT pin the UTS half of ``_iter_ucs``. That branch was
        # changed from ``unit._seq`` to ``unit`` for consistency with its
        # sibling, and the change is behaviour-neutral today:
        # ``TemporalUnitSequence.__iter__`` is ``iter(self._seq)`` and there
        # is no alignment cache on a sequence to go stale. Reverting that one
        # line leaves the whole suite green (measured). The block below still
        # reaches its stale inner block through the TemporalBlock branch,
        # which is the half that is load-bearing -- reverting *that* line
        # fails ten tests in this file, this one included.
        #
        # Kept as written because a block nested inside a sequence is a real
        # shape worth covering; only the claim about which branch it exercises
        # was wrong.
        def build():
            inner = TemporalBlock([TemporalUnitSequence([_uc()]), _uc()],
                                  axis=1, sort_rows=False)
            seq = TemporalUnitSequence([_uc(), inner])
            score = Score()
            return score.add(seq).unit, score

        seq_a, score_a = build()
        seq_a[1].rows[0].append(_uc())
        straight = _starts(convert_score_to_sc_events(score_a))

        seq_b, score_b = build()
        seq_b[1].rows[0].append(_uc())
        seq_b[1].events
        after_read = _starts(convert_score_to_sc_events(score_b))

        assert straight == pytest.approx(after_read)

    def test_playback_agrees_with_the_block_events_surface(self):
        # ``blk.events`` is the surface the fix wave already trusted; the
        # played rendering must land on the same onsets.
        #
        # Two things here are load-bearing, and both were wrong once:
        #
        # 1. The conversion must run BEFORE ``blk.events`` is touched.
        #    Reading ``events`` is an aligned read and repairs the block, so
        #    reading it first would make the comparison vacuous.
        # 2. The two sides are compared as ordered MULTISETS, not as sets.
        #    Multiplicity is the whole signal: on this fixture the stale
        #    rendering is [0, 0, 2, 2, 4, 6] and the aligned one is
        #    [0, 2, 4, 4, 6, 6]. Those are different renderings but the same
        #    four distinct values, so collapsing either side to a set --
        #    which this test used to do -- destroys exactly the difference
        #    it exists to detect, and the test cannot go red at all.
        blk, score = _block_score()
        blk.rows[0].append(_uc())
        played = sorted(round(s, 9) for s in _starts(convert_score_to_sc_events(score)))
        surfaced = sorted(round(float(s), 9) for s in blk.events['start'])
        assert played == pytest.approx(surfaced)


class TestUnmutatedScoresAreUnchanged:
    """The fix must be invisible to a Score nobody mutated through a live row."""

    def test_block_score_renders_as_it_always_did(self):
        _, score = _block_score()
        assert _starts(convert_score_to_sc_events(score)) == pytest.approx(
            [0.0, 0.0, 2.0, 2.0])

    def test_sequence_score_renders_as_it_always_did(self):
        score = Score()
        score.add(TemporalUnitSequence([_uc(), _uc()]))
        assert _starts(convert_score_to_sc_events(score)) == pytest.approx(
            [0.0, 2.0, 4.0, 6.0])

    def test_repeated_conversion_is_idempotent(self):
        blk, score = _block_score()
        blk.rows[0].append(_uc())
        first = _starts(convert_score_to_sc_events(score))
        for _ in range(3):
            assert _starts(convert_score_to_sc_events(score)) == pytest.approx(first)
