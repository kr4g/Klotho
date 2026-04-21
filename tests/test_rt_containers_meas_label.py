"""Regression: containers layout renders the root with unreduced rt.meas."""
import re

import pytest

from klotho.chronos.rhythm_trees import RhythmTree
from klotho.semeios.visualization._renderers.svg_rt import _svg_rt_containers


class TestContainersRootMeasLabel:
    def test_root_uses_unreduced_meas_span1(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 2, 1))
        svg = _svg_rt_containers(rt).svg_str
        assert '>4/4<' in svg, (
            "root label should render as unreduced meas '4/4', not '1/1'"
        )

    def test_root_uses_meas_span_multi(self):
        rt = RhythmTree(span=3, meas='3/4', subdivisions=(1, 1))
        svg = _svg_rt_containers(rt).svg_str
        assert '>3/4<' in svg

    def test_internal_nodes_use_metric_duration(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 2, 1))
        svg = _svg_rt_containers(rt).svg_str
        # Leaf durations are 1/4, 2/4 (-> 1/2), 1/4 reduced.
        # Ensure some reduced leaf label is still present alongside 4/4.
        assert re.search(r'>1/4<', svg) is not None
