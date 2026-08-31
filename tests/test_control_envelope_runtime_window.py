"""A split control envelope must sound as ONE gesture, not two.

Ruling seven (Ryan, 2026-08-31): a split envelope keeps its values. The first
implementation delivered that for the BAKED pfield snapshot -- what
``uc.events`` shows -- and not for the control BUS, which for
``control=True`` is the only thing anyone actually hears.

Measured before this module existed:

    unsplit runtime signal   t=0:0.000  t=1:0.250  t=2:0.501  t=3:0.750  t=4:1.000
    split   runtime signal   t=0:0.000  t=1:0.501  t=2:1.000  t=2:0.000  t=3:0.501  t=4:1.000

At the instrument change the bus snapped from full back to zero and re-ramped:
a crescendo drawn under one phrase played as two crescendos. That is the exact
failure ruling seven forbids, in the path that makes the sound.

The cause was that ``curve_window`` never left ``compositional.py``.
``resolved_control_envelopes`` did not publish it and
``_build_score_control_data`` sampled ``linspace(0, total)`` per descriptor,
so every half rendered the whole curve.

Three more places dropped it, each one restoring the same two-hairpin shape by
a different route: ``_rebake_control_envelope`` (so the first structural edit
after a split undid the split's own values), the zero-width guard (which threw
away the window's POSITION, baking a one-leaf run at the curve's FIRST value
-- a four-instrument crescendo came out entirely silent), and four of the five
copy paths.
"""

import warnings
from fractions import Fraction

import pytest

from klotho.dynatos.envelopes import Envelope
from klotho.thetos import CompositionalUnit as UC


def _unit(instruments):
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
            pfields={'amp': 0.1})
    leaves = list(uc._rt.leaf_nodes)
    for leaf, name in zip(leaves, instruments):
        uc.set_instrument(leaf, name)
    return uc, leaves


def _ramp(uc, leaves, endpoint=True):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp',
                                 node=leaves, control=True, endpoint=endpoint)


def _runtime_signal(uc, block_size=8):
    """The control values the ENGINE would actually play, per descriptor.

    This goes through ``_build_score_control_data`` -- the real sampler --
    rather than re-deriving the samples here. An earlier version of this
    helper re-implemented the windowed sampling itself, and measured, it
    stayed green when the converter was mutated back to sampling the whole
    curve: it was testing that the window is PUBLISHED, not that anything
    reads it. The buffer the engine uploads is the only witness that
    settles ruling seven.
    """
    from klotho.utils.playback.supersonic.converters import (
        _build_score_control_data)
    descriptors = [
        {'envelope': d['envelope'], 'pfields': d['pfields'],
         'start': d['time_span'][0],
         'duration': d['time_span'][1] - d['time_span'][0],
         'targets': [], 'curve_window': d.get('curve_window') or (0.0, 1.0)}
        for d in uc.resolved_control_envelopes()
    ]
    data = _build_score_control_data(descriptors, block_size)
    buffer = data['buffer']
    return [[round(float(v), 4) for v in buffer[i * block_size:(i + 1) * block_size]]
            for i in range(len(descriptors))]


class TestTheBusPlaysOneGesture:

    def test_the_split_signal_is_a_slice_of_the_unsplit_one(self):
        whole, leaves = _unit(['kl_saw'] * 4)
        _ramp(whole, leaves)
        split, leaves = _unit(['kl_saw', 'kl_saw', 'kl_tri', 'kl_tri'])
        _ramp(split, leaves)

        (unsplit_signal,) = _runtime_signal(whole)
        halves = _runtime_signal(split)
        assert len(halves) == 2, 'fixture did not split'

        assert halves[0][0] == pytest.approx(unsplit_signal[0]), (
            f'the first half does not start where the curve starts: {halves}')
        assert halves[-1][-1] == pytest.approx(unsplit_signal[-1]), (
            f'the second half does not end where the curve ends: {halves}')
        assert halves[1][0] > halves[0][0], (
            f'the second half restarts the gesture instead of continuing it: '
            f'{halves}')

    def test_the_window_is_published_to_the_runtime_at_all(self):
        split, leaves = _unit(['kl_saw', 'kl_saw', 'kl_tri', 'kl_tri'])
        _ramp(split, leaves)

        published = split.resolved_control_envelopes()
        assert len(published) == 2
        windows = [d.get('curve_window') for d in published]
        assert all(w is not None for w in windows), (
            f'curve_window never leaves compositional.py: {windows}')
        assert windows == [(0.0, 0.5), (0.5, 1.0)]


class TestARebakeKeepsTheWindow:

    def test_a_structural_edit_after_a_split_does_not_restart_a_half(self):
        split, leaves = _unit(['kl_saw', 'kl_saw', 'kl_tri', 'kl_tri'])
        _ramp(split, leaves)
        before = [round(v, 6) for v in split.events['amp']]

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            split.subdivide(leaves[1], (1, 1))

        after = [round(v, 6) for v in split.events['amp']]
        assert after == sorted(after), (
            f'the ramp is no longer monotonic, so a half restarted: '
            f'{before} -> {after}')


class TestAZeroWidthWindowKeepsItsPosition:

    def test_a_one_leaf_run_reads_its_own_place_in_the_curve(self):
        """With ``endpoint=False`` a run can be one leaf wide, so its window
        has zero width. Falling back to the whole curve threw away the
        POSITION as well as the width, and every such run baked at the
        curve's first value -- a four-instrument crescendo came out silent."""
        uc, leaves = _unit(['kl_saw', 'kl_tri', 'kl_pulse', 'kl_sine'])
        _ramp(uc, leaves, endpoint=False)

        amps = [round(v, 4) for v in uc.events['amp']]
        assert len(set(amps)) > 1, (
            f'every run baked at the same value, so the gesture is gone: '
            f'{amps}')
        assert amps == sorted(amps), f'not a rising ramp: {amps}'


class TestCopyPathsCarryTheWindow:

    @pytest.mark.parametrize('how', ['copy', 'mul'])
    def test_a_copied_split_envelope_keeps_its_windows(self, how):
        split, leaves = _unit(['kl_saw', 'kl_saw', 'kl_tri', 'kl_tri'])
        _ramp(split, leaves)
        originals = [d.get('curve_window')
                     for d in split._control_envelopes.values()]

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            clone = split.copy() if how == 'copy' else split * Fraction(1)

        copied = [d.get('curve_window')
                  for d in clone._control_envelopes.values()]
        assert copied == originals, (
            f'{how} dropped the window: {originals} -> {copied}')
