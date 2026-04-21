"""Tests for the shared projection helper and its use in plot paths."""
import numpy as np
import pytest

from klotho.semeios.visualization._projections import (
    apply_projection,
    VALID_METHODS,
)


@pytest.fixture
def synthetic_5d():
    rng = np.random.default_rng(0)
    return rng.standard_normal((20, 5))


class TestApplyProjectionShape:
    @pytest.mark.parametrize('method', VALID_METHODS)
    def test_output_shape_is_target_dims(self, method, synthetic_5d):
        out = apply_projection(synthetic_5d, method, target_dims=3)
        assert out.shape == (20, 3)

    def test_output_shape_target_dims_2(self, synthetic_5d):
        out = apply_projection(synthetic_5d, 'pca', target_dims=2)
        assert out.shape == (20, 2)


class TestApplyProjectionDeterminism:
    @pytest.mark.parametrize('method', ('mds', 'pca', 'ortho_best', 'ortho_first'))
    def test_repeated_calls_match(self, method, synthetic_5d):
        a = apply_projection(synthetic_5d, method, target_dims=3)
        b = apply_projection(synthetic_5d, method, target_dims=3)
        np.testing.assert_allclose(a, b)


class TestApplyProjectionInvalid:
    def test_unknown_method_raises(self, synthetic_5d):
        with pytest.raises(ValueError):
            apply_projection(synthetic_5d, 'nope')

    def test_spectral_precomputed_without_adjacency_raises(self, synthetic_5d):
        with pytest.raises(ValueError):
            apply_projection(
                synthetic_5d, 'spectral',
                spectral_affinity='precomputed', adjacency=None)


class TestOrthographicSelection:
    def test_ortho_best_picks_highest_variance_axes(self):
        rng = np.random.default_rng(1)
        n = 40
        X = np.zeros((n, 5))
        X[:, 0] = rng.standard_normal(n) * 0.1
        X[:, 1] = rng.standard_normal(n) * 0.2
        X[:, 2] = rng.standard_normal(n) * 5.0
        X[:, 3] = rng.standard_normal(n) * 3.0
        X[:, 4] = rng.standard_normal(n) * 4.0

        out = apply_projection(X, 'ortho_best', target_dims=3)
        expected_variances = sorted([X[:, 2].var(), X[:, 3].var(), X[:, 4].var()])
        out_variances = sorted([out[:, i].var() for i in range(3)])
        np.testing.assert_allclose(out_variances, expected_variances)

    def test_ortho_first_preserves_axis_order(self, synthetic_5d):
        out = apply_projection(synthetic_5d, 'ortho_first', target_dims=3)
        np.testing.assert_allclose(out, synthetic_5d[:, :3])

    def test_ortho_first_pads_when_input_too_small(self):
        X = np.ones((10, 2))
        out = apply_projection(X, 'ortho_first', target_dims=3)
        assert out.shape == (10, 3)
        np.testing.assert_allclose(out[:, :2], X)
        np.testing.assert_allclose(out[:, 2], np.zeros(10))


class TestPCAIsOrthogonalRotation:
    def test_pca_preserves_centered_frobenius_norm(self, synthetic_5d):
        X = synthetic_5d
        out = apply_projection(X, 'pca', target_dims=X.shape[1])
        centered = X - X.mean(axis=0)
        np.testing.assert_allclose(
            np.linalg.norm(out, ord='fro'),
            np.linalg.norm(centered, ord='fro'),
            atol=1e-10,
        )

    def test_pca_output_columns_are_orthogonal(self, synthetic_5d):
        out = apply_projection(synthetic_5d, 'pca', target_dims=3)
        gram = out.T @ out
        off_diag = gram - np.diag(np.diag(gram))
        assert np.max(np.abs(off_diag)) < 1e-8


class TestCPSPlotPaths:
    """End-to-end: plot(cps, dim_reduction=...) works for the five methods."""

    def _cps(self):
        from klotho.tonos.systems.combination_product_sets import CombinationProductSet
        return CombinationProductSet((1, 3, 5, 7, 9, 11), r=3, master_set='asterisk_nd')

    def test_default_is_mds(self):
        from klotho import plot
        result = plot(self._cps())
        assert result is not None

    @pytest.mark.parametrize('method', ('mds', 'pca', 'ortho_best', 'ortho_first'))
    def test_plot_with_each_method(self, method):
        from klotho import plot
        result = plot(self._cps(), dim_reduction=method)
        assert result is not None


class TestReducePositions:
    """_reduce_positions forwards dim_reduction to apply_projection."""

    def test_default_mds(self):
        from klotho.semeios.visualization._dispatch.plot_cps import _reduce_positions
        positions = {i: (float(i), float(i) * 2, float(i) * 3, float(i) * 4, float(i) * 5)
                     for i in range(10)}
        out = _reduce_positions(positions)
        assert len(out) == 10
        assert all(len(v) == 3 for v in out.values())

    @pytest.mark.parametrize('method', ('mds', 'pca', 'ortho_best', 'ortho_first'))
    def test_accepts_all_methods(self, method):
        from klotho.semeios.visualization._dispatch.plot_cps import _reduce_positions
        positions = {i: (float(i), float(i) * 2, float(i) * 3, float(i) * 4, float(i) * 5)
                     for i in range(10)}
        out = _reduce_positions(positions, dim_reduction=method)
        assert len(out) == 10
        assert all(len(v) == 3 for v in out.values())
