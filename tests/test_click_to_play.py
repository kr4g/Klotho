"""Regression: click-to-play is wired only when ``animate=True`` (i.e. ``.play()``)."""
import re

import pytest

from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice
from klotho.tonos.systems.combination_product_sets import (
    CombinationProductSet, MasterSet,
)
from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
from klotho.semeios.visualization._dispatch.plot_cps import (
    _plot_cps, _plot_master_set,
)


def _tooltip_html(fig):
    # For 2D SVG figures the tooltip HTML is appended to svg_str.
    # For animated figures it's inside to_html() (which wraps svg_str).
    if hasattr(fig, 'svg_str'):
        return fig.svg_str
    return fig.to_html()


def _has_click_handler(html):
    # `_playFreq` defined AND invoked from a click listener.
    return '_playFreq' in html and 'var freqs=' in html


def _freqs_value(html):
    m = re.search(r'var freqs=([^;]+);', html)
    return m.group(1).strip() if m else None


class TestStaticNoClickToPlay:
    """When animate=False (default), lattice/CPS/MasterSet plots must NOT attach click-to-play."""

    def test_lattice_plain(self):
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5))
        assert _freqs_value(fig.svg_str) == 'null', (
            "static lattice must not expose freqs"
        )

    def test_lattice_with_path_static(self):
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5), path=[(0, 0), (1, 0), (1, 1)])
        assert _freqs_value(fig.svg_str) == 'null'

    def test_cps_plain(self):
        cps = CombinationProductSet.hexany()
        fig = _plot_cps(cps)
        assert _freqs_value(fig.svg_str) == 'null'

    def test_master_set_plain(self):
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        fig = _plot_master_set(ms)
        assert _freqs_value(fig.svg_str) == 'null'

    def test_3d_lattice_plain(self):
        tl = ToneLattice(3, resolution=1)
        fig = _plot_lattice(tl, figsize=(5, 5), target_dims=3)
        html = fig.to_html()
        assert '"nodeFreqs": null' in html or '"nodeFreqs":null' in html

    def test_3d_master_set_plain(self):
        ms = MasterSet.octahedron().with_factors((1, 3, 5, 7, 9, 11))
        fig = _plot_master_set(ms)
        html = fig.to_html()
        assert '"nodeFreqs": null' in html or '"nodeFreqs":null' in html


class TestAnimateClickToPlay:
    """When animate=True, click-to-play must be wired even without a path/shape."""

    def test_lattice_animate_no_selection(self):
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True)
        html = _tooltip_html(fig)
        freqs = _freqs_value(html)
        assert freqs and freqs != 'null' and freqs != '[]', (
            f"animated lattice without selection must still expose freqs: {freqs!r}"
        )
        assert _has_click_handler(html)

    def test_lattice_animate_with_path(self):
        tl = ToneLattice(2, resolution=3)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True,
                            path=[(0, 0), (1, 0), (1, 1)])
        html = _tooltip_html(fig)
        assert _has_click_handler(html)

    def test_cps_animate_no_selection(self):
        cps = CombinationProductSet.hexany()
        fig = _plot_cps(cps, animate=True)
        html = _tooltip_html(fig)
        assert _has_click_handler(html)

    def test_master_set_animate_no_selection(self):
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        fig = _plot_master_set(ms, animate=True)
        html = _tooltip_html(fig)
        assert _has_click_handler(html)

    def test_master_set_animate_with_shape(self):
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        fig = _plot_master_set(ms, animate=True, shape=['A', 'B', 'C'])
        html = _tooltip_html(fig)
        assert _has_click_handler(html)

    def test_3d_lattice_animate(self):
        tl = ToneLattice(3, resolution=1)
        fig = _plot_lattice(tl, figsize=(5, 5), target_dims=3, animate=True)
        html = fig.to_html()
        assert '"nodeFreqs":' in html
        assert '"nodeFreqs": null' not in html and '"nodeFreqs":null' not in html

    def test_3d_master_set_animate(self):
        ms = MasterSet.octahedron().with_factors((1, 3, 5, 7, 9, 11))
        fig = _plot_master_set(ms, animate=True)
        html = fig.to_html()
        assert '"nodeFreqs":' in html
        assert '"nodeFreqs": null' not in html and '"nodeFreqs":null' not in html


class TestNonToneLatticeNoFreqs:
    """Non-tone lattices shouldn't have click-to-play even with animate=True."""

    def test_plain_non_tone_lattice(self):
        from klotho.topos.graphs.lattices import Lattice
        lat = Lattice(2, resolution=2)
        fig = _plot_lattice(lat, figsize=(5, 5), animate=True)
        html = _tooltip_html(fig)
        # For non-tone lattices preview_config is None even when animate=True.
        assert _freqs_value(html) in (None, 'null', '[]')


def _has_synthdef_loader(html, def_name='kl_tri'):
    """The page must merge synthdef assets and load the preview synth.

    This is the assertion that would have caught the original bug: the
    preview sends ``/s_new <defName>`` which silently fails unless the
    SynthDef bytes are loaded on the page.
    """
    return '__klothoSynthdefAssets' in html and f'"{def_name}"' in html


class TestPreviewSynthdefLoading:
    """animate=True figures without path/shape must ship synthdef loaders."""

    def test_lattice_bare(self):
        from klotho.semeios.visualization._animation import ClickPreviewFigure
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True)
        assert isinstance(fig, ClickPreviewFigure)
        assert _has_synthdef_loader(fig.to_html())

    def test_lattice_nodes_only(self):
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True,
                            nodes=[(0, 0), (1, 0)])
        assert _has_synthdef_loader(fig.to_html())

    def test_3d_lattice_bare(self):
        tl = ToneLattice(3, resolution=1)
        fig = _plot_lattice(tl, figsize=(5, 5), target_dims=3, animate=True)
        assert _has_synthdef_loader(fig.to_html())

    def test_cps_bare(self):
        cps = CombinationProductSet.hexany()
        fig = _plot_cps(cps, animate=True)
        assert _has_synthdef_loader(fig.to_html())

    def test_master_set_bare(self):
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        fig = _plot_master_set(ms, animate=True)
        assert _has_synthdef_loader(fig.to_html())

    def test_static_has_no_loader(self):
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5))
        assert '__klothoSynthdefAssets' not in fig.svg_str


class TestPreviewPfields:
    """.play() kwargs like attackTime must reach the preview config."""

    def test_pfields_in_preview_config(self):
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True,
                            attackTime=0.5, releaseTime=2.0)
        html = fig.to_html()
        assert '"attackTime": 0.5' in html
        assert '"releaseTime": 2.0' in html

    def test_control_keys_not_in_pfields(self):
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True,
                            loop=True, ring_time=3)
        html = fig.to_html()
        import re
        m = re.search(r'var previewCfg=(\{.*?\});', html)
        assert m is not None
        import json
        cfg = json.loads(m.group(1))
        pfields = cfg.get('pfields') or {}
        assert 'loop' not in pfields and 'ring_time' not in pfields

    def test_bridge_preview_forwards_pfields(self):
        # The bridge JS must accept and forward params.pfields.
        from pathlib import Path
        import klotho.utils.playback as pb
        bridge_js = (Path(pb.__file__).parent / '_animation_bridge.js').read_text()
        assert 'params.pfields' in bridge_js

    def test_path_animation_preview_has_pfields(self):
        tl = ToneLattice(2, resolution=3)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True,
                            path=[(0, 0), (1, 0)], attackTime=0.25)
        html = _tooltip_html(fig)
        assert '"attackTime": 0.25' in html


class TestClickHighlight:
    """Clicking a node highlights it for dur and dims everything else."""

    def test_2d_tooltip_has_highlight_machinery(self):
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True)
        html = fig.to_html()
        assert 'activeTimers' in html
        assert '_applyPreviewState' in html
        assert 'dimmedColor' in html

    def test_3d_has_highlight_machinery(self):
        tl = ToneLattice(3, resolution=1)
        fig = _plot_lattice(tl, figsize=(5, 5), target_dims=3, animate=True)
        html = fig.to_html()
        assert 'activeTimers' in html
        assert '_klDimmables' in html

    def test_static_2d_has_no_click_state(self):
        tl = ToneLattice(2, resolution=2)
        fig = _plot_lattice(tl, figsize=(5, 5))
        # The machinery is present in the script but only armed when
        # freqs is non-null; freqs must be null for static plots.
        assert _freqs_value(fig.svg_str) == 'null'
