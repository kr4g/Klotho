"""semeios lane: SVG wrapper/renderer and ratio-plot defects.

Every assertion here is a *relation* rather than a fixed literal: pixel
heights are compared against the per-lane height the same renderer
produces for a one-lane score, viewBox strings are compared between the
two wrappers rather than against a hand-copied string, and label
positions are compared against each other. A literal would go stale the
first time a default changes, and would then stop testing anything.

Rows covered: AUD-125, AF1-3, AUD-116, AF1-1, AUD-118, AUD-114,
AUD-119, AF1-16, AUD-115, AUD-35.
"""
import math
import re
import xml.etree.ElementTree as ET

import pytest

from klotho.chronos import TemporalUnitSequence as UTS
from klotho.chronos.temporal_units.temporal import TemporalUnit
from klotho.thetos import Score, CompositionalUnit as UC
from klotho.tonos import Chord, Scale, Voicing, fold
from klotho.semeios.visualization._renderers.svg_score import _svg_score_timeline
from klotho.semeios.visualization._shared.svg_utils import (
    svg_wrap, svg_wrap_viewbox,
)


@pytest.fixture(autouse=True)
def _mute_display(monkeypatch):
    import IPython.display
    monkeypatch.setattr(IPython.display, 'display', lambda *a, **k: None)


def _viewbox_numbers(html):
    m = re.search(r'viewBox="([^"]+)"', html)
    assert m, f"no viewBox: {html[:200]}"
    parts = [float(v) for v in m.group(1).split()]
    assert len(parts) == 4, m.group(1)
    return parts


def _viewbox_text(html):
    m = re.search(r'viewBox="([^"]+)"', html)
    assert m, f"no viewBox: {html[:200]}"
    return m.group(1)


def _score_with_n_lanes(n):
    """One single-lane item per track, so the layout's lane count is ``n``."""
    score = Score()
    for i in range(n):
        score.track(f't{i}')
    for i in range(n):
        score.append(UC(tempus='4/4', prolatio=(1, 1), bpm=120),
                     name=f'item{i}', track=f't{i}')
    return score


# ---------------------------------------------------------------- AF1-3 / AUD-125

class TestScoreDefaultFigsize:
    def test_default_height_is_exactly_proportional_to_lane_count(self):
        """The default figsize is ``0.6 * lanes`` inches, so every lane must
        get the *same* pixel height no matter how many lanes there are.

        ``int(0.6 * 3 * 100)`` truncates 179.999... to 179, which loses a
        whole pixel off a three-lane score and makes lane 3 shorter than
        lanes 1 and 2.
        """
        one_lane = _svg_score_timeline(_score_with_n_lanes(1)).height_px
        for n in range(2, 9):
            h = _svg_score_timeline(_score_with_n_lanes(n)).height_px
            assert h == one_lane * n, (
                f"{n} lanes rendered {h}px; {n} x the one-lane height "
                f"({one_lane}px) is {one_lane * n}px"
            )

    def test_lane_count_never_falls_below_band_count(self):
        """AUD-125's premise: every band occupies at least one lane, so the
        ``max(0.6 * lanes, 0.6 * len(bands))`` second arm can never win.

        A band's height is ``max(item lane heights, default=1)`` and
        ``_resolve_lanes`` never returns less than 1, so ``lanes`` is a sum
        of per-band heights each >= 1.
        """
        for n in range(1, 6):
            sd = _svg_score_timeline(_score_with_n_lanes(n))
            lanes = sd.height_px / (_svg_score_timeline(
                _score_with_n_lanes(1)).height_px)
            assert lanes >= len(sd.track_names)


# ---------------------------------------------------------------- AUD-116

class TestTrackLabelEscaping:
    def test_track_name_with_xml_metacharacters_stays_well_formed(self):
        name = 'A & B <bass>'
        score = Score()
        score.track(name)
        score.append(UC(tempus='4/4', prolatio=(1, 1), bpm=120),
                     name='i', track=name)
        svg = _svg_score_timeline(score).svg_str
        doc = svg[svg.index('<svg'):svg.rindex('</svg>') + len('</svg>')]
        ET.fromstring(doc)  # raises ParseError on an unescaped & or <

    def test_escaped_label_still_reads_as_the_track_name(self):
        name = 'A & B <bass>'
        score = Score()
        score.track(name)
        score.append(UC(tempus='4/4', prolatio=(1, 1), bpm=120),
                     name='i', track=name)
        svg = _svg_score_timeline(score).svg_str
        doc = svg[svg.index('<svg'):svg.rindex('</svg>') + len('</svg>')]
        texts = [el.text for el in ET.fromstring(doc).iter()
                 if el.tag.endswith('text')]
        assert name in texts, texts


# ---------------------------------------------------------------- AF1-1

class TestViewboxConventionIsShared:
    def test_both_wrappers_write_the_same_box_the_same_way(self):
        """Same logical viewBox, so the same attribute text."""
        a = svg_wrap('<circle r="5"/>', 400, 200)
        b = svg_wrap_viewbox('<circle r="5"/>', 400, 200, 0, 200, flip=False)
        assert _viewbox_text(a) == _viewbox_text(b)

    def test_the_shared_convention_still_describes_the_same_box(self):
        assert _viewbox_numbers(svg_wrap('<circle r="5"/>', 400, 200)) == [
            0.0, 0.0, 400.0, 200.0]


# ---------------------------------------------------------------- AUD-118

def _text_traces(fig):
    return [(tr.text[0], float(tr.x[0]), float(tr.y[0]))
            for tr in fig.data if getattr(tr, 'mode', '') == 'text']


def _degree_ring_labels(fig):
    """Labels on the r = 1.1 degree ring (interval labels sit at 0.925)."""
    return [(t, x, y) for t, x, y in _text_traces(fig)
            if abs(math.hypot(x, y) - 1.1) < 1e-6]


_RATIO_COLLECTIONS = [
    Scale(['1/1', '5/4', '3/2']),
    Chord(['1/1', '5/4', '3/2']),
    Chord(['5/4', '3/2', '15/8']),
    Voicing(['1/1', '5/4', '3/2', '2/1']),
]


#: AF35-19. A Chord's and a Voicing's ``intervals`` span root..top, so the
#: cumulative fraction of the LAST degree is exactly 1 and it is DRAWN at 12
#: o'clock on top of the root. The defect is the POSITION, not the label --
#: skipping the label instead removes a real pitch from the picture in silence.
#: strict=True so that fixing the geometry turns this RED and the row cannot be
#: quietly forgotten.
_OVERPRINTS = pytest.mark.xfail(strict=True, reason=(
    "AF35-19: a root..top collection positions its last degree on top of its "
    "first. Fixing the geometry must flip this to a failure so the row closes."))


class TestRatioCircleDegreeLabels:
    @pytest.mark.parametrize('obj', _RATIO_COLLECTIONS,
                             ids=lambda o: f"{type(o).__name__}-{len(o.degrees)}")
    def test_every_degree_is_labelled(self, obj):
        """No pitch may vanish from the picture.

        This is the invariant that matters, and it is asserted INSTEAD of
        "no two labels overprint" -- which an earlier version of this fix
        satisfied by SKIPPING the wrapped degree's label. That looked like
        tidying up an overprint and was not: ``15/8`` in
        ``Chord(['5/4','3/2','15/8'])`` is a real pitch, not a coincidence
        with the root, and skipping it removed a note from the reader's
        picture in silence. An overprint is ugly and visible; a missing
        pitch is a wrong score that looks right (AF35-19).
        """
        from klotho.semeios.visualization.plots import _plot_scale_chord
        shown = {t for t, _, _ in _degree_ring_labels(_plot_scale_chord(obj))}
        for degree in obj.degrees:
            assert str(degree) in shown, (
                f"degree {degree} of {list(obj.degrees)} has no label on the "
                f"ring -- it is missing from the picture entirely"
            )

    @pytest.mark.parametrize('obj', [
        _RATIO_COLLECTIONS[0],
        pytest.param(_RATIO_COLLECTIONS[1], marks=_OVERPRINTS),
        pytest.param(_RATIO_COLLECTIONS[2], marks=_OVERPRINTS),
        pytest.param(_RATIO_COLLECTIONS[3], marks=_OVERPRINTS),
    ], ids=lambda o: f"{type(o).__name__}-{len(o.degrees)}")
    def test_no_two_degree_labels_share_a_position(self, obj):
        """A Scale genuinely does not overprint; a Chord or Voicing does.

        The distinction is the finding, and it narrows AF35-19: a Scale's
        intervals do not close the circle, so its last degree lands on its
        own point. Only the root..top collections put their last degree on
        top of their first. Marking all four xfail would have hidden that
        the Scale path is already correct.
        """
        from klotho.semeios.visualization.plots import _plot_scale_chord
        labels = _degree_ring_labels(_plot_scale_chord(obj))
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                _, xi, yi = labels[i]
                _, xj, yj = labels[j]
                assert math.hypot(xi - xj, yi - yj) > 1e-6, (
                    f"{labels[i][0]!r} and {labels[j][0]!r} overprint at "
                    f"({xi:.6f}, {yi:.6f}); all labels: {labels}"
                )

    @pytest.mark.parametrize('obj', _RATIO_COLLECTIONS,
                             ids=lambda o: f"{type(o).__name__}-{len(o.degrees)}")
    def test_every_ring_label_names_a_degree_the_collection_has(self, obj):
        """The label at 12 o'clock used to be a hardcoded ``"1/1"``. A Chord
        rooted on 5/4 contains no 1/1, so that label was simply false."""
        from klotho.semeios.visualization.plots import _plot_scale_chord
        allowed = {str(d) for d in obj.degrees}
        for text, _, _ in _degree_ring_labels(_plot_scale_chord(obj)):
            assert text in allowed, (
                f"ring label {text!r} is not a degree of {list(obj.degrees)}"
            )

    @pytest.mark.parametrize('obj', _RATIO_COLLECTIONS,
                             ids=lambda o: f"{type(o).__name__}-{len(o.degrees)}")
    def test_line_layout_first_label_names_the_first_degree(self, obj):
        from klotho.semeios.visualization.plots import _plot_scale_chord
        labels = _text_traces(_plot_scale_chord(obj, layout='line'))
        at_origin = [t for t, x, y in labels if abs(x) < 1e-9 and y > 0]
        assert at_origin == [str(list(obj.degrees)[0])], (
            f"labels at x=0: {at_origin}; first degree is "
            f"{list(obj.degrees)[0]}"
        )


# ---------------------------------------------------------------- AUD-114

class TestKlothoPlotPlayDur:
    """``dur`` must behave like its neighbour ``loop``: a value given at
    play time is the caller's last word and overrides one given at plot
    time. It used to lose, because ``**merged_play`` was unpacked *after*
    the named ``dur`` parameter in the same dict literal.
    """

    @staticmethod
    def _recorder():
        seen = []

        def plot_fn(obj, **kw):
            seen.append(kw)

            class _Fig:  # no to_html: KlothoPlot displays it directly
                pass

            return _Fig()

        return plot_fn, seen

    def test_play_time_dur_wins_over_plot_time_dur(self):
        from klotho.semeios.visualization._dispatch import KlothoPlot
        plot_fn, seen = self._recorder()
        KlothoPlot(plot_fn, object(), {'dur': 3.0}).play(dur=10.0)
        assert seen[-1]['dur'] == 10.0

    def test_dur_and_loop_resolve_the_same_way(self):
        """The relation that matters: whatever precedence ``loop`` has,
        ``dur`` has too. Both are plot-or-play options on one wrapper."""
        from klotho.semeios.visualization._dispatch import KlothoPlot
        plot_fn, seen = self._recorder()
        KlothoPlot(plot_fn, object(),
                   {'dur': 3.0, 'loop': True}).play(dur=10.0, loop=False)
        kw = seen[-1]
        assert (kw['dur'], kw['loop']) == (10.0, False)

    def test_plot_time_dur_still_used_when_play_gives_none(self):
        from klotho.semeios.visualization._dispatch import KlothoPlot
        plot_fn, seen = self._recorder()
        KlothoPlot(plot_fn, object(), {'dur': 3.0}).play()
        assert seen[-1]['dur'] == 3.0

    def test_default_dur_survives_when_neither_side_gives_one(self):
        from klotho.semeios.visualization._dispatch import KlothoPlot
        plot_fn, seen = self._recorder()
        KlothoPlot(plot_fn, object(), {}).play()
        assert seen[-1]['dur'] == 0.5


# ---------------------------------------------------------------- AUD-119

class TestSingleDegreePlots:
    def test_both_interval_modes_agree_that_one_degree_is_plottable(self):
        """The relation: plottability is a property of the collection, not
        of how its intervals happen to be spelled. A one-note sonority is
        drawable in cents mode, so it is drawable in ratios mode."""
        from klotho.semeios.visualization.plots import _plot_scale_chord
        cents = _plot_scale_chord(Chord([100.0], interval_type='cents'))
        ratios = _plot_scale_chord(Chord(['1/1'], interval_type='ratios'))
        assert len(ratios.data) >= 1
        assert (len(ratios.data) > 0) == (len(cents.data) > 0)

    @pytest.mark.parametrize('layout', ['circle', 'line'])
    def test_the_one_degree_is_the_thing_that_gets_drawn(self, layout):
        from klotho.semeios.visualization.plots import _plot_scale_chord
        obj = Chord(['5/4'], interval_type='ratios')
        fig = _plot_scale_chord(obj, layout=layout)
        texts = [t for t, _, _ in _text_traces(fig)]
        assert str(list(obj.degrees)[0]) in texts, texts


# ---------------------------------------------------------------- AF1-16

class TestZeroSpanCollection:
    @staticmethod
    def _all_unison_voicing():
        """``fold`` never merges voices that land on the same pitch, so an
        ordinary octave-collapse leaves a Voicing of N identical degrees."""
        return fold(Voicing(['1/1', '2/1', '4/1'], reference_pitch='C4'),
                    lo='C4', hi='B4')

    def test_fold_really_does_produce_such_a_collection(self):
        v = self._all_unison_voicing()
        assert len(v.degrees) > 1
        assert len(set(v.degrees)) == 1, list(v.degrees)

    @pytest.mark.parametrize('layout', ['circle', 'line'])
    def test_zero_total_span_raises_a_stated_valueerror(self, layout):
        """Not a ZeroDivisionError out of the middle of the label loop."""
        from klotho.semeios.visualization.plots import _plot_scale_chord
        with pytest.raises(ValueError) as exc:
            _plot_scale_chord(self._all_unison_voicing(), layout=layout)
        assert 'ZeroDivision' not in type(exc.value).__name__
        msg = str(exc.value)
        assert 'pitch' in msg.lower() or 'interval' in msg.lower(), msg


# ---------------------------------------------------------------- AUD-115

def _held_rect_widths(svg_str):
    doc = svg_str[svg_str.index('<svg'):
                  svg_str.rindex('</svg>') + len('</svg>')]
    return [float(el.get('width')) for el in ET.fromstring(doc).iter()
            if el.tag.endswith('rect') and el.get('fill-opacity') == '0.35']


class TestHeldOnlyScore:
    @staticmethod
    def _held_only():
        score = Score()
        score.track('a')
        score.new(0.0, None, 'kl_tri', name='held', track='a', freq=440.0)
        return score

    @staticmethod
    def _held_plus_timed():
        score = Score()
        score.track('a')
        score.new(0.0, None, 'kl_tri', name='held', track='a', freq=440.0)
        score.new(0.0, 2.0, 'kl_tri', name='timed', track='a', freq=440.0)
        return score

    def test_a_score_of_only_held_events_renders(self):
        """The renderer already knows how to draw a held event; refusing
        the whole score because held events contribute no span was the
        defect."""
        sd = _svg_score_timeline(self._held_only())
        assert len(sd.step_element_ids) == 1
        assert sd.width_px > 0 and sd.height_px > 0

    def test_the_held_bar_is_drawn_the_same_as_in_a_score_with_a_span(self):
        """Relation, not a literal: whatever width a held bar gets when the
        score has a real span, it gets the same width when the nominal span
        is synthesized -- both run from the left pad to the right pad."""
        alone = _held_rect_widths(_svg_score_timeline(self._held_only()).svg_str)
        with_span = _held_rect_widths(
            _svg_score_timeline(self._held_plus_timed()).svg_str)
        assert len(alone) == 1 and len(with_span) == 1
        assert alone[0] == pytest.approx(with_span[0])

    def test_a_score_of_only_zero_duration_events_renders(self):
        score = Score()
        score.track('a')
        score.new(0.0, 0.0, 'kl_tri', name='blip', track='a', freq=440.0)
        assert len(_svg_score_timeline(score).step_element_ids) == 1

    def test_a_genuinely_empty_score_still_refuses(self):
        with pytest.raises(ValueError):
            _svg_score_timeline(Score())


# ---------------------------------------------------------------- AUD-35

def _output_file_dispatchers():
    """(function, sample object) for every ``_dispatch`` entry point that
    declares an ``output_file`` parameter.

    Built by introspection rather than by hand so the list cannot fall out
    of date: a new dispatcher that declares the parameter joins these tests
    automatically, and one that stops declaring it drops out.
    """
    import inspect
    from klotho.chronos.rhythm_trees import RhythmTree
    from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice
    from klotho.tonos.systems.combination_product_sets import (
        CombinationProductSet, MasterSet,
    )
    from klotho.semeios.visualization import _dispatch

    samples = {
        '_plot_rt': lambda: RhythmTree(span=1, meas='4/4',
                                       subdivisions=(1, 2, 1)),
        '_plot_lattice': lambda: ToneLattice(2, resolution=2),
        '_plot_cps': CombinationProductSet.hexany,
        '_plot_master_set': lambda: MasterSet.hexagon().with_factors(
            (1, 3, 5, 7, 9, 11)),
    }
    out = []
    for name in _dispatch.__all__:
        fn = getattr(_dispatch, name)
        if not inspect.isfunction(fn):
            continue
        if 'output_file' not in inspect.signature(fn).parameters:
            continue
        assert name in samples, (
            f"{name} declares output_file but this test has no sample "
            f"object for it -- add one rather than letting it go untested"
        )
        out.append((name, fn, samples[name]))
    return out


_OUTPUT_FILE_DISPATCHERS = _output_file_dispatchers()


class TestDispatcherOutputFile:
    def test_the_introspection_found_the_dispatchers(self):
        assert {n for n, _, _ in _OUTPUT_FILE_DISPATCHERS} == {
            '_plot_rt', '_plot_lattice', '_plot_cps', '_plot_master_set'}

    @pytest.mark.parametrize('name,fn,make', _OUTPUT_FILE_DISPATCHERS,
                             ids=[n for n, _, _ in _OUTPUT_FILE_DISPATCHERS])
    def test_html_output_file_is_written(self, name, fn, make, tmp_path):
        out = tmp_path / f'{name}.html'
        fn(make(), output_file=str(out))
        assert out.exists(), f"{name} ignored output_file"
        assert out.stat().st_size > 0

    @pytest.mark.parametrize('name,fn,make', _OUTPUT_FILE_DISPATCHERS,
                             ids=[n for n, _, _ in _OUTPUT_FILE_DISPATCHERS])
    def test_written_html_holds_what_the_figure_renders(self, name, fn, make,
                                                        tmp_path):
        """Relation: the file is the figure, not some other rendering."""
        out = tmp_path / f'{name}.html'
        fig = fn(make(), output_file=str(out))
        assert out.read_text(encoding='utf-8') == fig.to_html()

    @pytest.mark.parametrize('name,fn,make', _OUTPUT_FILE_DISPATCHERS,
                             ids=[n for n, _, _ in _OUTPUT_FILE_DISPATCHERS])
    def test_unsupported_extension_is_refused_not_ignored(self, name, fn, make,
                                                          tmp_path):
        out = tmp_path / f'{name}.pdf'
        with pytest.raises(ValueError) as exc:
            fn(make(), output_file=str(out))
        assert '.html' in str(exc.value)
        assert not out.exists()

    def test_svg_output_file_is_a_parsable_svg_document(self, tmp_path):
        from klotho.semeios.visualization._dispatch import _plot_rt
        from klotho.chronos.rhythm_trees import RhythmTree
        out = tmp_path / 'rt.svg'
        _plot_rt(RhythmTree(span=1, meas='4/4', subdivisions=(1, 2, 1)),
                 output_file=str(out))
        ET.fromstring(out.read_text(encoding='utf-8'))

    def test_output_file_also_honoured_positionally(self, tmp_path):
        """``output_file`` is a positional parameter of these functions, so
        a caller may pass it that way; it must not be ignored then either."""
        from klotho.semeios.visualization._dispatch import _plot_rt
        from klotho.chronos.rhythm_trees import RhythmTree
        out = tmp_path / 'pos.html'
        _plot_rt(RhythmTree(span=1, meas='4/4', subdivisions=(1, 2, 1)),
                 'containers', (11, 2), True, str(out))
        assert out.exists()

    def test_output_file_given_twice_raises_like_python_would(self, tmp_path):
        from klotho.semeios.visualization._dispatch import _plot_rt
        from klotho.chronos.rhythm_trees import RhythmTree
        with pytest.raises(TypeError, match='output_file'):
            _plot_rt(RhythmTree(span=1, meas='4/4', subdivisions=(1, 2, 1)),
                     'containers', (11, 2), True, str(tmp_path / 'a.html'),
                     output_file=str(tmp_path / 'b.html'))
