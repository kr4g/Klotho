"""Tests for Envelope warp ('lin'/'exp') and curve-honoring control buffers."""

import numpy as np
import pytest

from klotho.dynatos.envelopes import Envelope
from klotho.thetos.composition.compositional import CompositionalUnit


class TestWarpConstruction:
    def test_default_warp_is_lin(self):
        env = Envelope([0, 1, 0])
        assert env.warp == 'lin'

    def test_exp_warp_stored(self):
        env = Envelope([100, 400], warp='exp')
        assert env.warp == 'exp'

    def test_invalid_warp_raises(self):
        with pytest.raises(ValueError, match="warp"):
            Envelope([1, 2], warp='log')

    def test_exp_with_zero_value_raises(self):
        with pytest.raises(ValueError, match="strictly positive"):
            Envelope([0, 1], warp='exp')

    def test_exp_with_negative_value_raises(self):
        with pytest.raises(ValueError, match="strictly positive"):
            Envelope([-1, 1], warp='exp')

    def test_exp_validates_after_value_scale(self):
        with pytest.raises(ValueError, match="strictly positive"):
            Envelope([1, 2], warp='exp', value_scale=-1.0)

    def test_lin_allows_nonpositive_values(self):
        env = Envelope([-1, 0, 1])
        assert env.warp == 'lin'


class TestWarpInterpolation:
    def test_exp_midpoint_is_geometric_mean(self):
        env = Envelope([100, 400], times=1.0, warp='exp')
        assert env.at_time(0.5) == pytest.approx(200.0)

    def test_lin_midpoint_is_arithmetic_mean(self):
        env = Envelope([100, 400], times=1.0)
        assert env.at_time(0.5) == pytest.approx(250.0)

    def test_exp_endpoints_exact(self):
        env = Envelope([100, 400], times=2.0, warp='exp')
        assert env.at_time(0) == 100
        assert env.at_time(2.0) == 400

    def test_exp_flat_segment(self):
        env = Envelope([220, 220], times=1.0, warp='exp')
        assert env.at_time(0.5) == pytest.approx(220.0)

    def test_exp_descending(self):
        env = Envelope([400, 100], times=1.0, warp='exp')
        assert env.at_time(0.5) == pytest.approx(200.0)

    def test_curve_composes_with_exp_warp(self):
        curved = Envelope([100, 400], times=1.0, curve=4, warp='exp')
        plain = Envelope([100, 400], times=1.0, warp='exp')
        p = (np.exp(4 * 0.5) - 1) / (np.exp(4) - 1)
        expected = 100 * (400 / 100) ** p
        assert curved.at_time(0.5) == pytest.approx(expected)
        assert curved.at_time(0.5) != pytest.approx(plain.at_time(0.5))

    def test_multi_segment_exp(self):
        env = Envelope([100, 400, 100], times=[1.0, 1.0], warp='exp')
        assert env.at_time(0.5) == pytest.approx(200.0)
        assert env.at_time(1.0) == pytest.approx(400.0)
        assert env.at_time(1.5) == pytest.approx(200.0)


class TestWarpClassmethods:
    def test_pairs_threads_warp(self):
        env = Envelope.pairs([(0, 100), (1, 400)], warp='exp')
        assert env.warp == 'exp'
        assert env.at_time(0.5) == pytest.approx(200.0)

    def test_perc_default_lin(self):
        assert Envelope.perc().warp == 'lin'

    def test_perc_exp_rejected_for_zero_values(self):
        with pytest.raises(ValueError, match="strictly positive"):
            Envelope.perc(warp='exp')

    def test_adr_adsr_accept_warp_kwarg(self):
        assert Envelope.adr().warp == 'lin'
        assert Envelope.adsr().warp == 'lin'


class TestWarpSurvivesBake:
    def test_bake_preserves_exp_warp(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60)
        env = Envelope([100, 400], warp='exp')
        uc.root.apply_envelope(env, pfields='freq')
        freqs = [uc.get_pfield(n, 'freq') for n in uc._rt.leaf_nodes]
        # 4 events across the span; second event sits 1/4 through the
        # envelope: exp interpolation, not linear.
        assert freqs[0] == pytest.approx(100.0)
        assert freqs[1] == pytest.approx(100 * 4 ** 0.25)
        assert freqs[2] == pytest.approx(200.0)
        assert freqs[3] == pytest.approx(100 * 4 ** 0.75)

    def test_bake_lin_unchanged(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60)
        env = Envelope([0.0, 1.0])
        uc.root.apply_envelope(env, pfields='amp')
        amps = [uc.get_pfield(n, 'amp') for n in uc._rt.leaf_nodes]
        assert amps == pytest.approx([0.0, 0.25, 0.5, 0.75])


class TestControlBufferHonorsCurveAndWarp:
    def _buffer_for(self, env):
        from klotho.utils.playback.supersonic.converters import (
            _build_score_control_data,
        )
        desc = {
            "envelope": env,
            "start": 0.0,
            "duration": env.total_time,
            "pfields": ["amp"],
            "targets": [],
        }
        return _build_score_control_data([desc], block_size=64)["buffer"]

    def test_linear_envelope_buffer_matches_interp(self):
        env = Envelope([0.0, 1.0], times=1.0)
        buf = self._buffer_for(env)
        expected = np.linspace(0.0, 1.0, 64)
        assert np.allclose(buf, expected, atol=1e-6)

    def test_curved_envelope_buffer_differs_from_linear(self):
        env = Envelope([0.0, 1.0], times=1.0, curve=4)
        buf = self._buffer_for(env)
        linear = np.linspace(0.0, 1.0, 64)
        assert not np.allclose(buf, linear, atol=1e-3)

    def test_curved_buffer_matches_at_time_samples(self):
        env = Envelope([0.0, 1.0], times=1.0, curve=4)
        buf = self._buffer_for(env)
        xs = np.linspace(0.0, env.total_time, 64)
        expected = np.array([env.at_time(float(x)) for x in xs])
        assert np.allclose(buf, expected, atol=1e-6)

    def test_exp_warp_buffer(self):
        env = Envelope([100.0, 400.0], times=1.0, warp='exp')
        buf = self._buffer_for(env)
        assert buf[0] == pytest.approx(100.0)
        assert buf[-1] == pytest.approx(400.0)
        assert buf[31] == pytest.approx(100 * 4 ** (31 / 63), rel=1e-4)

    def test_buffer_shape_unchanged(self):
        env = Envelope([0.0, 1.0], times=1.0, curve=-2)
        buf = self._buffer_for(env)
        assert buf.shape == (64,)
        assert buf.dtype == np.float32
