import pytest

from klotho.chronos import RhythmTree
from klotho.semeios.visualization.plot_rt import _plot_rt
from klotho.tonos import Spectrum


def _node_snapshot(graph):
    return {node: dict(graph.nodes[node]) for node in graph.nodes}


@pytest.mark.parametrize("layout", ["containers", "tree", "ratios"])
def test_plot_rt_does_not_mutate_source_tree(layout):
    rt = RhythmTree(span=1, meas="4/4", subdivisions=(3, (2, (1, 1)), 5))
    before = _node_snapshot(rt)
    _plot_rt(rt, layout=layout, animate=False)
    after = _node_snapshot(rt)
    assert after == before


def test_spectrum_does_not_write_pitch_into_harmonic_tree_nodes():
    spectrum = Spectrum(440, [1, 2, 3, 5, 7])
    assert "pitch" in spectrum.data.columns
    for node in spectrum.ht.nodes:
        assert "pitch" not in spectrum.ht[node]
