"""Shared dimensionality-reduction helpers for Klotho's plotting pipeline.

All plot paths that need to project high-dimensional node positions to 3-D
(or any lower dim) go through :func:`apply_projection`. Centralizing the
menu keeps the lattice, CPS, and master-set renderers consistent and
makes it a single-file change to add a new method.
"""
from __future__ import annotations

from typing import Any

import numpy as np


VALID_METHODS = ('mds', 'spectral', 'pca', 'ortho_best', 'ortho_first')


def apply_projection(
    points: np.ndarray,
    method: str,
    *,
    target_dims: int = 3,
    random_state: int = 42,
    mds_metric: bool = True,
    mds_max_iter: int = 300,
    spectral_affinity: str = 'rbf',
    spectral_gamma: float | None = None,
    adjacency: np.ndarray | None = None,
) -> np.ndarray:
    """Project ``points`` into ``target_dims`` dimensions via ``method``.

    Parameters
    ----------
    points : numpy.ndarray
        Shape ``(n_samples, n_features)``. When ``method='spectral'`` and
        ``spectral_affinity='precomputed'``, ``points`` is ignored and
        ``adjacency`` is used instead.
    method : str
        One of ``'mds'``, ``'spectral'``, ``'pca'``, ``'ortho_best'``, or
        ``'ortho_first'``.
    target_dims : int, optional
        Number of output dimensions. Default 3.
    random_state : int, optional
        Random seed used by MDS and spectral embedding.
    mds_metric : bool, optional
        Forwarded to ``sklearn.manifold.MDS`` as ``metric_mds``. Default True.
    mds_max_iter : int, optional
        Forwarded to ``sklearn.manifold.MDS``. Default 300.
    spectral_affinity : str, optional
        Forwarded to ``sklearn.manifold.SpectralEmbedding``. Default 'rbf'.
    spectral_gamma : float or None, optional
        Forwarded to ``sklearn.manifold.SpectralEmbedding``.
    adjacency : numpy.ndarray or None, optional
        Precomputed adjacency matrix used only when
        ``method='spectral'`` and ``spectral_affinity='precomputed'``.

    Returns
    -------
    numpy.ndarray
        Projected points of shape ``(n_samples, target_dims)``.

    Raises
    ------
    ValueError
        If ``method`` is not a known projection method.
    """
    if method == 'mds':
        return _mds(points, target_dims, random_state,
                    mds_metric, mds_max_iter)
    if method == 'spectral':
        return _spectral(points, target_dims, random_state,
                         spectral_affinity, spectral_gamma, adjacency)
    if method == 'pca':
        return _pca(points, target_dims)
    if method == 'ortho_best':
        return _ortho_best(points, target_dims)
    if method == 'ortho_first':
        return _ortho_first(points, target_dims)
    raise ValueError(
        f"Unknown projection method {method!r}. "
        f"Valid methods: {VALID_METHODS}"
    )


def _mds(points: np.ndarray, target_dims: int, random_state: int,
         metric: bool, max_iter: int) -> np.ndarray:
    from sklearn.manifold import MDS
    reducer = MDS(
        n_components=target_dims,
        metric_mds=metric,
        max_iter=max_iter,
        init='random',
        n_init=4,
        random_state=random_state,
        normalized_stress='auto',
    )
    return reducer.fit_transform(points)


def _spectral(points: np.ndarray, target_dims: int, random_state: int,
              affinity: str, gamma: float | None,
              adjacency: np.ndarray | None) -> np.ndarray:
    from sklearn.manifold import SpectralEmbedding
    if affinity == 'precomputed':
        if adjacency is None:
            raise ValueError(
                "spectral_affinity='precomputed' requires an adjacency matrix"
            )
        reducer = SpectralEmbedding(
            n_components=target_dims,
            affinity='precomputed',
            random_state=random_state,
        )
        return reducer.fit_transform(adjacency)
    reducer = SpectralEmbedding(
        n_components=target_dims,
        affinity=affinity,
        gamma=gamma,
        random_state=random_state,
    )
    return reducer.fit_transform(points)


def _pca(points: np.ndarray, target_dims: int) -> np.ndarray:
    arr = np.asarray(points, dtype=float)
    centered = arr - arr.mean(axis=0)
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    return centered @ vh[:target_dims].T


def _ortho_best(points: np.ndarray, target_dims: int) -> np.ndarray:
    arr = np.asarray(points, dtype=float)
    variances = arr.var(axis=0)
    chosen = np.argsort(variances)[::-1][:target_dims]
    return arr[:, chosen]


def _ortho_first(points: np.ndarray, target_dims: int) -> np.ndarray:
    arr = np.asarray(points, dtype=float)
    n_features = arr.shape[1]
    if n_features < target_dims:
        pad = np.zeros((arr.shape[0], target_dims - n_features))
        return np.hstack([arr, pad])
    return arr[:, :target_dims]
