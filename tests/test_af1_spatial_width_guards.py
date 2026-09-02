"""Three width guards the spatial lane was missing, and the offline fold.

Every failure this file pins is SILENT -- no exception, no red test, just a
speaker that stops making sound -- so each test states the arithmetic that
proves the sound is wrong, not merely that a call returned.

1. **main may not declare an array narrower than the widest track.**  Every
   track sums into main, so main's buses are built at the WIDEST declared
   width.  Main's own ``speakers=`` then describes only the first few lanes
   of that bus, and two things follow that nobody is told about: main's
   inserts were width-checked against main's own (narrow) array and are
   placed on the wide chain, where they read and write only their own lanes
   and leave the rest of main's post-FX bus **unwritten**; and main drops
   out of the decoder tie-break, so the headphone fold quietly uses some
   other track's geometry.  Refused at lowering, with both widths named.

2. **A speaker count outside the precompiled family is refused in Python.**
   ``__busRouterN`` / ``__spatialDecodeN`` are compiled one def per width
   (a SynthDef's channel count is fixed while its graph is built, so a
   ``width`` control is impossible), and only the widths in
   :data:`~klotho.utils.playback.supersonic.spatial_defs.PRECOMPILED_WIDTHS`
   have a blob on disk.  scsynth does not refuse an ``/s_new`` that names a
   def it never received: it creates nothing and says nothing.  So a
   30-speaker rig (a 5x6 grid -- an entirely plausible thing to build) used
   to pass every Python layer and turn into browser silence.

3. **The offline fold exists.**  Five refusal texts sent the composer to an
   offline stereo fold as the way out of a too-wide array or a too-distant
   listener, and one of them named ``fold_to_stereo`` outright.  There was
   no such function anywhere in Klotho.  A refusal whose remedy does not
   exist is worse than a refusal with no remedy, so the function is now
   real and this file pins its arithmetic against a hand-derived case.
"""
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.synthdef import SynthDefFX
from klotho.thetos.spatial import (
    SHADOW_HI_HZ,
    SHADOW_LO_HZ,
    SpeakerArray,
)
from klotho.topos.collections.sequences import Pattern
from klotho.utils.playback.supersonic.converters import (
    convert_score_to_sc_events,
)
from klotho.utils.playback.supersonic.engine import (
    SuperSonicEngine,
    needed_spatial_synthdefs,
    needed_synthdefs,
)
from klotho.utils.playback.supersonic.spatial_defs import PRECOMPILED_WIDTHS

_ROOT = Path(__file__).parent.parent
_SS_DIR = _ROOT / "klotho" / "utils" / "playback" / "supersonic"

requires_node = pytest.mark.skipif(shutil.which("node") is None,
                                   reason="node not available")


def grid(cols, rows, name=None):
    return SpeakerArray.grid(cols=cols, rows=rows, col_spacing=50.0,
                             row_spacing=60.0, name=name)


def voices(n=2, speakers=(1, 2)):
    """A short unit whose leaves name speakers, so lowering has work to do."""
    uc = UC(tempus='4/4', prolatio=(1,) * n, beat='1/4', bpm=120, inst='kl_tri')
    uc.set(uc.leaves, speaker=Pattern(list(speakers)))
    return uc


# ---------------------------------------------------------------------------
# 1. main narrower than the widest track
# ---------------------------------------------------------------------------


class TestMainMayNotBeNarrowerThanTheWidestTrack:
    """AUD-3.

    ``score.track('main', speakers=['L', 'R'], inserts=[reverb])`` plus
    ``score.track('wide', speakers=range(1, 25))`` was accepted by every
    Python layer.  In the browser main's buses come out 24 channels wide
    while ``kl_reverb`` -- a 2-in/2-out def -- bridges them, so lanes 2..23
    of main's post-FX bus are never written and speakers 3..24 are silent.
    Measured on the shipped defs: ``kl_reverb`` writes fxBus 120-121 while
    ``__spatialDecode24`` reads 120-143.
    """

    def _narrow_main(self, inserts=None):
        s = Score()
        s.track('main', speakers=['L', 'R'], inserts=inserts)
        s.track('wide', speakers=grid(6, 4, name='PAVILION'))
        s.add(voices(), name='x', track='wide')
        return s

    def test_a_narrower_main_with_inserts_is_refused_at_lowering(self):
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(self._narrow_main(
                inserts=[SynthDefFX('kl_reverb')]))
        msg = str(e.value)
        assert "'main'" in msg
        assert '2' in msg and '24' in msg          # both widths, named
        assert "'wide'" in msg                     # who widened it
        assert 'SILENT' in msg                     # why it must be refused

    def test_a_narrower_main_is_refused_even_with_an_empty_chain(self):
        """No inserts means no muted lanes, but main still loses the fold.

        The decoder tie-break picks main only when main is AS WIDE as the
        widest track (``scheduler_score.js``: ``chosen = widest.indexOf(
        'main') !== -1 ? 'main' : widest[0]``).  A narrower main is not in
        that tie, so the geometry the composer declared on the master chain
        is silently replaced by another track's -- different binaural
        coefficients, no error either way.
        """
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(self._narrow_main())
        assert "'main'" in str(e.value)

    def test_the_refusal_says_both_ways_out_when_both_ways_work(self):
        """With NO inserts on main, both remedies really do work.

        CORRECTED (AF-1b).  This test used to run the ``inserts=[reverb]``
        case and assert that ``speakers=[]`` was offered there too.  It is
        not offered there any more, and must not be: AF-1's verifier ran
        it and found it ACCEPTED the score straight back into the silence
        the refusal exists to prevent (main still widened to 24 by the
        other track, ``kl_reverb`` still bridging lanes 0..1).  With an
        empty chain there are no lanes to leave unwritten, so both ways
        out are honest and both are still named.
        """
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(self._narrow_main())
        msg = str(e.value)
        # Declare main at the full width ...
        assert "score.track('main'" in msg
        # ... or stop declaring speakers on main at all.
        assert 'speakers=[]' in msg

    def test_the_refusal_does_not_offer_speakers_empty_when_it_would_fail(
            self):
        """The remedy that silently failed is gone from the case it fails in.

        ``speakers=[]`` does not narrow main's chain -- nothing does but
        the widest track -- so with a stereo insert on a 24-wide chain it
        removes the array and leaves every muted speaker exactly where it
        was.
        """
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(self._narrow_main(
                inserts=[SynthDefFX('kl_reverb')]))
        assert 'speakers=[]' not in str(e.value)

    def test_main_declaring_no_array_at_all_is_still_accepted(self):
        """The ordinary shape: declare the rig on one track, leave main alone.

        Over-refusing here would break every score written that way --
        which is how the whole corpus is written.  main is left out of
        ``meta.spatial.tracks`` entirely and the score lowers.

        CORRECTED (AF-1b): this used to hang ``inserts=[kl_reverb]`` on
        that main and assert it lowered clean.  It did, and that was the
        flagship defect, not the safe shape -- a 2-in/2-out insert on the
        24-channel chain main is built at.  The insert is what is refused;
        the undeclared main is not.
        """
        s = Score()
        s.track('main')
        s.track('wide', speakers=grid(6, 4, name='PAVILION'))
        s.add(voices(), name='x', track='wide')
        meta = convert_score_to_sc_events(s)['meta']['spatial']
        assert 'main' not in meta['tracks']
        assert meta['tracks']['wide']['width'] == 24

    def test_main_as_wide_as_the_widest_track_is_accepted(self):
        s = Score()
        rig = grid(6, 4, name='PAVILION')
        s.track('main', speakers=rig, inserts=None)
        s.track('wide', speakers=rig)
        s.add(voices(), name='x', track='wide')
        meta = convert_score_to_sc_events(s)['meta']['spatial']
        assert meta['tracks']['main']['width'] == 24

    def test_main_wider_than_every_other_track_is_accepted(self):
        """main is the chain the whole array lives on, so a WIDER main is
        the normal case, not the suspect one: the narrow track simply lands
        on lanes 0..k-1 of it."""
        s = Score()
        s.track('main', speakers=grid(6, 4, name='PAVILION'))
        s.track('quad', speakers=grid(2, 2, name='QUAD'))
        s.add(voices(), name='x', track='quad')
        meta = convert_score_to_sc_events(s)['meta']['spatial']
        assert meta['tracks']['main']['width'] == 24
        assert meta['tracks']['quad']['width'] == 4

    def test_a_lone_one_speaker_main_is_refused_by_the_stereo_floor(self):
        """The widener does not have to be another track.

        ``mainWidth`` starts at ``BUS_CHANNELS`` (2) in the scheduler, so a
        main declaring ONE speaker is built two channels wide with lane 1
        unwritten -- and worse, nothing in the score is as wide as the
        chain, so the decoder tie-break selects no track at all and the
        score silently gets no headphone fold while reporting 'labels but
        no positions'.  Refused on the same rule, with the stereo floor
        named as the widener instead of a track.
        """
        # No items: every bundled instrument is stereo and would trip the
        # lane-overrun refusal on a 1-speaker rig first, which is a
        # different (and already tested) guard.
        s = Score()
        s.track('main', speakers=[1])
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        msg = str(e.value)
        assert "'main'" in msg
        assert 'stereo pair' in msg

    def test_a_two_speaker_main_alone_is_fine(self):
        """The floor is two, so a stereo main is exactly at it."""
        s = Score()
        s.track('main', speakers=['L', 'R'])
        s.add(voices(speakers=('L', 'L')), name='x')
        meta = convert_score_to_sc_events(s)['meta']['spatial']
        assert meta['tracks']['main']['width'] == 2

    def test_a_score_with_no_spatial_track_is_untouched(self):
        s = Score()
        s.track('main', inserts=[SynthDefFX('kl_reverb')])
        s.add(voices(speakers=None) if False else
              UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120,
                 inst='kl_tri'), name='x')
        assert 'spatial' not in convert_score_to_sc_events(s)['meta']


# ---------------------------------------------------------------------------
# 2. off-family speaker counts
# ---------------------------------------------------------------------------


class TestOffFamilyWidthsAreRefusedInPython:
    """AUD-5.

    A 5x6 grid is 30 speakers.  ``SpeakerArray`` accepts it (30 <= 32),
    ``Score.track`` accepts it, lowering serializes 180 coefficients for
    it, and ``needed_spatial_synthdefs`` used to hand back
    ``__busRouter30`` / ``__spatialDecode30`` -- names with no blob on
    disk, which ``_filter_synthdef_assets`` then drops without a word.  The
    first and only complaint came from ``requireDef`` in the browser, where
    it dies as an unhandled promise rejection (a separate finding) and the
    composer sees a stuck icon and silence.
    """

    def _score(self, cols, rows):
        s = Score()
        s.track('rig', speakers=grid(cols, rows, name='RIG'))
        s.add(voices(), name='x', track='rig')
        return s

    def test_thirty_speakers_is_refused(self):
        payload = convert_score_to_sc_events(self._score(5, 6))
        with pytest.raises(ValueError) as e:
            needed_spatial_synthdefs(payload['meta'])
        msg = str(e.value)
        assert '30' in msg
        # AF1-55: this was ``or``, so either half alone satisfied it.
        # A 5x6 rig makes 30 BOTH a declared track width and main's width,
        # so the refusal owes the composer both missing names -- the router
        # that would carry the array and the decoder that would fold it.
        # Measured 2026-09-02 by deleting the one line in
        # ``_refuse_off_family_widths`` that adds ``__spatialDecode30``:
        # the whole file stayed green, 54 passed.
        for name in ('__busRouter30', '__spatialDecode30'):
            assert name in msg, (
                f'the refusal never names {name}, so a composer cannot tell '
                f'which def is missing: {msg}')
        assert 'SILENT' in msg

    def test_the_refusal_lists_the_widths_that_do_work(self):
        payload = convert_score_to_sc_events(self._score(5, 6))
        with pytest.raises(ValueError) as e:
            needed_spatial_synthdefs(payload['meta'])
        msg = str(e.value)
        for w in PRECOMPILED_WIDTHS:
            assert str(w) in msg

    def test_it_refuses_a_labels_only_track_too(self):
        """No geometry, no decoder -- but still no ``__busRouter5``, so the
        track is routed into a def that does not exist."""
        s = Score()
        s.track('rig', speakers=range(1, 6))
        s.add(voices(), name='x', track='rig')
        payload = convert_score_to_sc_events(s)
        with pytest.raises(ValueError) as e:
            needed_spatial_synthdefs(payload['meta'])
        assert '5' in str(e.value)

    def test_play_refuses_before_the_widget_is_built(self):
        """``SuperSonicEngine.__init__`` is what ``play(score)`` calls, and
        it collects the needed defs there -- so the refusal reaches the
        composer as a Python traceback in the notebook rather than as a
        console line in the browser."""
        payload = convert_score_to_sc_events(self._score(5, 6))
        with pytest.raises(ValueError):
            SuperSonicEngine(payload['events'], payload['meta'])

    def test_the_plot_surface_refuses_identically(self):
        """``plot(score)`` reaches the same collector through
        ``_extract_needed_synthdefs``; a page whose play button could only
        be silent is not a page worth building."""
        from klotho.semeios.visualization._animation.animated import (
            _extract_needed_synthdefs,
        )
        payload = convert_score_to_sc_events(self._score(5, 6))
        with pytest.raises(ValueError):
            _extract_needed_synthdefs({
                'events': payload['events'], 'meta': payload['meta'],
                'control': payload.get('control'),
            })

    @pytest.mark.parametrize('cols,rows,width', [
        (1, 1, 1), (2, 1, 2), (2, 2, 4), (3, 2, 6), (4, 2, 8),
        (4, 3, 12), (4, 4, 16), (6, 4, 24), (8, 4, 32),
    ])
    def test_every_precompiled_width_still_passes(self, cols, rows, width):
        """The guard must not cost a single working rig.

        Built through ``_build_spatial_meta`` rather than a whole lowering
        because the two narrowest widths cannot hold a voice at all: every
        bundled instrument is STEREO and occupies two adjacent speakers, so
        a 1-speaker rig has nowhere to put one.  The guard reads meta, and
        meta is what this asserts on.
        """
        from klotho.utils.playback.supersonic.converters import (
            _build_spatial_meta,
        )
        assert width in PRECOMPILED_WIDTHS
        s = Score().track('rig', speakers=grid(cols, rows, name='RIG'))
        names = needed_spatial_synthdefs({'spatial': _build_spatial_meta(s)})
        # main is ``max(widths | {2})`` wide -- a lone 1-speaker rig still
        # sums into a stereo master -- so the decoder is at that width, and
        # every width the guard has to pass is one of the family's.
        assert f'__spatialDecode{max(width, 2)}' in names

    def test_a_stereo_score_is_not_consulted_at_all(self):
        s = Score()
        s.add(UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120,
                 inst='kl_tri'), name='x')
        payload = convert_score_to_sc_events(s)
        assert needed_spatial_synthdefs(payload['meta']) == set()
        assert needed_synthdefs(payload['events'], payload['meta']) == {'kl_tri'}

    def test_the_module_docstring_no_longer_promises_a_runtime_compile(self):
        """It said 'Any other width is compiled here at lowering time and
        sent with /d_recv'.  Nothing in the live pipeline imports the
        builders, so that sentence described a feature that did not exist
        -- and it is exactly why an off-family width felt supported."""
        import klotho.utils.playback.supersonic.spatial_defs as sd
        doc = sd.__doc__
        assert 'compiled here at lowering time and sent with' not in doc
        assert 'd_recv' in doc          # still explained, but as NOT wired
        assert 'not wired' in doc.lower()


# ---------------------------------------------------------------------------
# 3. the offline fold the refusals name
# ---------------------------------------------------------------------------


class TestTheOfflineFoldExists:
    """The five sites that sent a composer to an offline fold.

    ``spatial.py`` line ~487 (too many speakers), line ~1074 (listener past
    the delay line), ``spatial_defs.py`` line ~156 (wire-buffer cap) and
    ~230 (delay past the line), and ``scheduler_score.js`` line ~81 (a
    width with no compiled def).  ``spatial.py``'s own module docstring
    opens by naming the offline fold as one of the two consumers of
    :meth:`SpeakerArray.binaural_coefficients`.  It did not exist.
    """

    def test_it_is_importable_under_the_name_the_refusals_use(self):
        from klotho.thetos.spatial import fold_to_stereo
        assert callable(fold_to_stereo)

    def test_every_refusal_that_offers_the_fold_names_it_by_name(self):
        """A meta-test over the five sites, driven where possible.

        The failure this replaces is a composer reading "fold this array
        offline", asking *with what*, and finding nothing.  Four of the
        five are raised here rather than grepped, so a reworded message
        that stops naming the remedy fails this.
        """
        import klotho.thetos.spatial as sp
        import klotho.utils.playback.supersonic.spatial_defs as sd

        assert hasattr(sp, 'fold_to_stereo')
        assert 'fold_to_stereo' in sp.__all__

        # 1. too many speakers for the decoder's wire-buffer budget
        with pytest.raises(ValueError) as e1:
            sp.SpeakerArray.from_positions(
                {i: (float(i), 0.0) for i in range(40)})
        assert 'fold_to_stereo' in str(e1.value)

        # 2. a listener past the live decoder's delay line
        with pytest.raises(ValueError) as e2:
            grid(6, 4, name='PAVILION').binaural_coefficients(
                (10.0, 10.0), max_delay=0.05)
        assert 'fold_to_stereo' in str(e2.value)

        # 3. the same cap, checked before a def is compiled
        with pytest.raises(ValueError) as e3:
            sd.check_width(40)
        assert 'fold_to_stereo' in str(e3.value)

        # 4. a geometry table whose delay overruns the compiled delay line
        bad = [0.0, 0.0, 1.0, 1.0, 18000.0, 18000.0]
        bad[0] = 9.9
        with pytest.raises(ValueError) as e4:
            sd.check_coefficients(bad, 1)
        assert 'fold_to_stereo' in str(e4.value)

        # 5. the browser's own missing-def refusal
        js = (_SS_DIR / 'scheduler_score.js').read_text()
        assert 'fold_to_stereo' in js

    # -- the hand-derived case ------------------------------------------
    #
    # ONE speaker on a 1-D array at x = 10, listener at x = 0, head_half
    # 1.0, speed of sound 1000.0 units/s, sample rate 48000.  Every number
    # below is exact, and none of it comes from running the fold:
    #
    #   ear_l = -1.0, ear_r = +1.0        (facing north: ears on x)
    #   d_l   = 11.0, d_r   =  9.0
    #   gains: ref = min(d) = 9  ->  gain_l = 9/11, gain_r = 9/9 = 1.0
    #   delays: 11/1000 s * 48000 = 528 samples;  9/1000 * 48000 = 432
    #   shadow: a_l = (11 - 9) / (2 * 1.0) = 1.0  -> full shadow, 1400 Hz
    #           a_r = (9 - 11) / 2 = -1 -> clamped to 0 -> 18000 Hz
    #
    # The one-pole is y[n] = (1 - a) x[n] + a y[n-1] with
    # a = exp(-2 pi fc / sr), matching OnePole.ar in the live decoder.  For
    # a unit impulse scaled by g and delayed by D samples that is exactly
    #
    #   y[D + k] = g (1 - a) a**k,      y[n < D] = 0.

    SPEED = 1000.0
    HALF = 1.0
    SR = 48000
    D_L, D_R = 528, 432
    G_L, G_R = 9.0 / 11.0, 1.0

    @staticmethod
    def _one_pole_coef(fc, sr):
        return math.exp(-2.0 * math.pi * fc / sr)

    @pytest.fixture
    def line(self):
        return SpeakerArray({1: (10.0,)}, units='ft',
                            speed_of_sound=self.SPEED)

    def _fold(self, line, block):
        from klotho.thetos.spatial import fold_to_stereo
        return fold_to_stereo(block, line, (0.0,), head_half=self.HALF,
                              sample_rate=self.SR)

    def test_the_coefficients_this_case_rests_on_are_the_hand_derived_ones(
            self, line):
        """Guard the guard: if ``binaural_coefficients`` ever moves, the
        arithmetic below stops being a derivation and starts being a
        coincidence."""
        c = line.binaural_coefficients((0.0,), head_half=self.HALF,
                                       sample_rate=self.SR)
        assert c.delay_l == (self.D_L,) and c.delay_r == (self.D_R,)
        assert c.gain_l[0] == pytest.approx(self.G_L)
        assert c.gain_r[0] == pytest.approx(self.G_R)
        assert c.shadow_l_hz == (SHADOW_LO_HZ,)
        assert c.shadow_r_hz == (SHADOW_HI_HZ,)

    def test_an_impulse_folds_to_the_hand_derived_one_pole(self, line):
        n = 800
        block = [[0.0] for _ in range(n)]
        block[0][0] = 1.0
        out = self._fold(line, block)

        a_l = self._one_pole_coef(SHADOW_LO_HZ, self.SR)
        a_r = self._one_pole_coef(SHADOW_HI_HZ, self.SR)

        # Nothing before the propagation delay.
        assert all(out[i][0] == 0.0 for i in range(self.D_L))
        assert all(out[i][1] == 0.0 for i in range(self.D_R))
        # The impulse response, three taps of each ear.
        for k in range(3):
            assert out[self.D_L + k][0] == pytest.approx(
                self.G_L * (1.0 - a_l) * a_l ** k, rel=1e-12)
            assert out[self.D_R + k][1] == pytest.approx(
                self.G_R * (1.0 - a_r) * a_r ** k, rel=1e-12)

    def test_the_far_ear_is_quieter_and_later_than_the_near_one(self, line):
        """The whole point of the model, stated as sound rather than as
        numbers: the speaker is on the listener's right."""
        n = 800
        block = [[0.0] for _ in range(n)]
        block[0][0] = 1.0
        out = self._fold(line, block)
        peak_l = max(range(len(out)), key=lambda i: abs(out[i][0]))
        peak_r = max(range(len(out)), key=lambda i: abs(out[i][1]))
        assert peak_l > peak_r                    # later
        assert abs(out[peak_l][0]) < abs(out[peak_r][1])   # quieter

    def test_the_output_is_long_enough_to_hold_the_longest_delay(self, line):
        """Truncating to the input length would silently drop the tail --
        the delay pushes real material past the end of the block."""
        out = self._fold(line, [[0.0] for _ in range(100)])
        assert len(out) == 100 + self.D_L
        assert len(out[0]) == 2

    def test_it_matches_a_scalar_reference_over_a_real_array(self):
        """An independent implementation of the documented recurrence, run
        over a 4-speaker grid with a different signal in every lane."""
        from klotho.thetos.spatial import fold_to_stereo
        rig = grid(2, 2, name='QUAD')
        n = 64
        block = [[math.sin(0.05 * (i + 7 * k)) for k in range(4)]
                 for i in range(n)]
        c = rig.binaural_coefficients(sample_rate=self.SR)

        max_d = max(max(c.delay_l), max(c.delay_r))
        ref = [[0.0, 0.0] for _ in range(n + max_d)]
        for lane in range(4):
            for ear, (delays, gains, cutoffs) in enumerate((
                    (c.delay_l, c.gain_l, c.shadow_l_hz),
                    (c.delay_r, c.gain_r, c.shadow_r_hz))):
                a = self._one_pole_coef(cutoffs[lane], self.SR)
                prev = 0.0
                for i in range(n + max_d):
                    j = i - delays[lane]
                    x = block[j][lane] * gains[lane] if 0 <= j < n else 0.0
                    prev = (1.0 - a) * x + a * prev
                    ref[i][ear] += prev

        out = fold_to_stereo(block, rig, sample_rate=self.SR)
        assert len(out) == len(ref)
        for i in range(len(ref)):
            for ear in (0, 1):
                assert out[i][ear] == pytest.approx(ref[i][ear], abs=1e-12)

    # -- refusals --------------------------------------------------------

    def test_a_lane_count_that_is_not_the_array_is_refused(self, line):
        from klotho.thetos.spatial import fold_to_stereo
        rig = grid(2, 2)
        with pytest.raises(ValueError) as e:
            fold_to_stereo([[0.0, 0.0] for _ in range(8)], rig)
        msg = str(e.value)
        assert '2' in msg and '4' in msg           # what was passed, what fits

    def test_a_one_dimensional_block_is_refused_with_the_shape_named(self):
        from klotho.thetos.spatial import fold_to_stereo
        with pytest.raises(ValueError) as e:
            fold_to_stereo([0.0] * 8, grid(2, 2))
        assert 'frames' in str(e.value)

    def test_the_two_over_wide_refusals_admit_what_the_fold_cannot_do(self):
        """A KNOWN GAP, stated in the message rather than papered over.

        Three of the five sites offer a remedy that can actually be
        carried out: the array is 32 speakers or fewer, so it exists as a
        :class:`SpeakerArray` and the fold takes it.  The other two are
        raised precisely BECAUSE the rig is wider than 32 -- and
        ``SpeakerArray`` refuses more than 32 at construction, so there is
        no object to hand the fold.  Both messages now say so, and name
        splitting the rig as the step that has to come first.

        The real fix is a design call above this lane: either let a
        ``SpeakerArray`` carry more than a decoder can, moving the refusal
        onto the decode path, or stop offering the fold at these two sites.
        Two tests outside this file pin the current wording
        (``test_speaker_array.py`` 'fold the array offline',
        ``test_spatial_defs.py`` 'fold_to_stereo'), so it cannot simply be
        dropped here.
        """
        import klotho.thetos.spatial as sp
        import klotho.utils.playback.supersonic.spatial_defs as sd
        with pytest.raises(ValueError) as e1:
            sp.SpeakerArray.from_positions(
                {i: (float(i), 0.0) for i in range(40)})
        with pytest.raises(ValueError) as e2:
            sd.check_width(40)
        for msg in (str(e1.value), str(e2.value)):
            assert 'fold_to_stereo' in msg
            assert 'SpeakerArray' in msg
            assert 'split' in msg
            assert str(sp.MAX_DECODER_SPEAKERS) in msg

    def test_it_has_no_delay_line_limit(self):
        """The claim the refusals make FOR it: a listener the live decoder
        could not reach is fine offline.  0.33 s is the decoder's line; a
        listener 1000 ft away is 0.89 s from the array."""
        from klotho.thetos.spatial import fold_to_stereo
        far = SpeakerArray.from_positions({1: (0.0, 0.0), 2: (10.0, 0.0)})
        out = fold_to_stereo([[0.0, 0.0] for _ in range(16)], far,
                             (0.0, 1000.0), sample_rate=self.SR)
        assert len(out) > 16 + int(0.33 * self.SR)


# ---------------------------------------------------------------------------
# 4. the browser-side sibling of guard 1
# ---------------------------------------------------------------------------


_PROBE_JS = r'''
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const SS_DIR = process.argv[2];
const CORE = readFileSync(SS_DIR + '/scheduler_core.js', 'utf8');
const SCORE = readFileSync(SS_DIR + '/scheduler_score.js', 'utf8');

const warnings = [];
const log = [];
const sonic = {
  _id: 1000,
  nextNodeId() { return this._id++; },
  send(...a) { log.push(a); },
  sendOSC() {},
  purge() {},
  async sync() {},
  getMetrics() { return {}; },
};
const sandbox = {
  performance: { timeOrigin: 0, now: () => 0 },
  setTimeout: () => 1,
  clearTimeout: () => {},
  console: { log(){}, debug(){}, error(){}, warn: (...a) => warnings.push(a.join(' ')) },
  atob: (s) => Buffer.from(s, 'base64').toString('binary'),
  DrawScheduler: class { schedule() {} clear() {} },
  SuperSonic: { osc: { encodeSingleBundle: (ntp, addr, args) => ({ ntp, addr, args }) } },
  __klothoSonic: { bootConfig: { scsynthOptions: { numAudioBusChannels: 1024 } }, _nextBufnum: 7 },
  __klothoSynthdefAssets: {
    '__busRouter': 'x', '__busRouterMonitor': 'x', '__chainLimiter': 'x',
    'kl_reverb': 'x',
    '__busRouter2': 'x', '__busRouter8': 'x', '__busRouter24': 'x',
    '__spatialDecode2': 'x', '__spatialDecode8': 'x', '__spatialDecode24': 'x',
  },
};
vm.createContext(sandbox);
vm.runInContext(CORE, sandbox);
vm.runInContext(SCORE, sandbox);

function arrayMeta(name, width) {
  const labels = [];
  for (let i = 0; i < width; i++) labels.push('S' + (i + 1));
  const flat = [];
  for (let lane = 0; lane < width; lane++) {
    flat.push(0.001 * lane, 0.002 * lane, 1 - 0.01 * lane,
              0.9 - 0.01 * lane, 18000 - 100 * lane, 17000 - 100 * lane);
  }
  return {
    name, labels, width,
    positions: labels.map((_, i) => [i, 0]),
    units: 'meters', speedOfSound: 343.0,
    decoder: {
      kind: 'binaural', listener: [0, 0], facing: 0.0, headHalf: 0.09,
      fields: ['delay_l', 'delay_r', 'gain_l', 'gain_r', 'shadow_l_hz', 'shadow_r_hz'],
      stride: 6, maxDelay: 0.33, coefficients: flat,
    },
  };
}

const s = new sandbox.BrowserScheduler({
  sonic, manifest: { kl_tri: { amp: 0.5 } }, ringTime: 0.1,
});
const meta = {
  groups: ['wide'],
  inserts: { main: [{ defName: 'kl_reverb', uid: 'fx1', args: {} }] },
  spatial: {
    arrays: { pair: arrayMeta('pair', 2), hall: arrayMeta('hall', 24) },
    tracks: { main: { array: 'pair', width: 2 }, wide: { array: 'hall', width: 24 } },
  },
};
await s.setupTracks(meta, 900);
process.stdout.write(JSON.stringify({
  warnings,
  mainWidth: s._trackMap.main.width,
}));
'''


@requires_node
class TestTheBrowserSaysSoToo:
    """Defence in depth for AUD-3.

    Python now refuses this configuration, so a Klotho-built payload can no
    longer reach the scheduler in this state -- but a saved output from an
    older release, or a hand-built meta, still can.  The existing warning
    tested only ``spatial.widths['main'] == null`` (main declares NO array),
    which is the case they thought of; a main with a NARROWER array is its
    unguarded sibling and produced exactly the same silence.
    """

    def _run(self):
        with tempfile.TemporaryDirectory() as d:
            probe = Path(d) / 'narrower_main_probe.mjs'
            probe.write_text(_PROBE_JS)
            r = subprocess.run(['node', str(probe), str(_SS_DIR)],
                               capture_output=True, text=True, cwd=str(_ROOT))
            assert r.returncode == 0, r.stderr
            return json.loads(r.stdout)

    def test_the_narrower_main_array_is_disclosed(self):
        r = self._run()
        assert r['mainWidth'] == 24
        assert any('SILENT' in w for w in r['warnings'])

    def test_the_warning_names_both_widths(self):
        r = self._run()
        hit = [w for w in r['warnings'] if 'SILENT' in w]
        assert hit, r['warnings']
        assert any('2' in w and '24' in w for w in hit)


# ---------------------------------------------------------------------------
# 5. AF-1b: the refusal's own remedies, and whose rule the stereo floor is
# ---------------------------------------------------------------------------


PROBE_DIR = Path(__file__).parent / 'fixtures' / 'synthdefs'


@pytest.fixture
def probe_fx24():
    """Register the only 24-in/24-out effect that exists anywhere.

    It is a TEST fixture on purpose: the tree ships 179 non-infrastructure
    SynthDefs and every one of them is stereo, which is the fact the new
    refusal has to state out loud.  Registration is process-global, so it
    is torn down again.
    """
    from klotho.utils.playback.supersonic import registry
    registry.register_compiled_file(PROBE_DIR / 'spatial_probe_fx24.scsyndef',
                                    kind='fx')
    try:
        yield 'spatial_probe_fx24'
    finally:
        registry.clear_runtime()


class TestMainsInsertsAreCheckedAgainstTheWidthMainIsBuiltAt:
    """AUD-3b.  The refusal added for AUD-3 offered two ways out.

    Ran against the flagship repro -- ``kl_reverb`` on ``main`` beside a
    24-speaker track -- neither of them produced a working master chain:

    * *"Declare main at the full array"* moves the failure to
      ``Score.track``, which refuses a 2-channel insert on a 24-channel
      track.  Loud, but there is nowhere to go from there: no bundled
      effect reads and writes 24 channels.
    * *"take the array off main with ``speakers=[]``"* was **accepted**,
      and rebuilt the exact silence the refusal exists to prevent -- main
      is still widened to 24 by the other track, ``kl_reverb`` still
      bridges lanes 0..1, and lanes 2..23 of main's post-FX bus are still
      never written.  The only diagnostic left is a browser
      ``console.warn`` nobody reads at a concert.

    The rule underneath both is one sentence, and it was only ever half
    enforced: **an insert on main must read and write as many channels as
    main's chain is BUILT at**, which is ``max(every declared width, 2)``
    -- not as many as main's own ``speakers=`` happens to name, and not
    two just because main named none.  Declaring an array on main was
    never what made the insert width matter; the other track's width is.
    """

    def _wide_rig_with_main_insert(self, def_name='kl_reverb', declare=None):
        s = Score()
        if declare is None:
            s.track('main', inserts=[SynthDefFX(def_name)])
        else:
            s.track('main', speakers=declare, inserts=[SynthDefFX(def_name)])
        s.track('wide', speakers=grid(6, 4, name='PAVILION'))
        s.add(voices(), name='x', track='wide')
        return s

    def test_a_stereo_insert_on_an_undeclared_main_is_refused(self):
        """The flagship silence, reachable with entirely bundled pieces.

        Hand-derived: a 6x4 grid is 24 speakers, so ``mainWidth`` is
        ``max(24, 2) == 24`` and main's post-FX bus is a run of 24
        channels.  ``kl_reverb`` is 2-in/2-out (``assets/io.json``), so the
        chain writes 2 of those 24 lanes and leaves 22 unwritten: 22 of the
        24 speakers play silently.
        """
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(self._wide_rig_with_main_insert())
        msg = str(e.value)
        assert "'main'" in msg
        assert '24' in msg and '2' in msg
        assert '22' in msg                      # the unwritten lanes, counted
        assert 'SILENT' in msg

    def test_the_speakers_empty_remedy_no_longer_leads_back_into_it(self):
        """``speakers=[]`` was the second way out the AUD-3 text offered.

        It is the same configuration as the test above once the array is
        gone, so it must reach the same refusal.  Before this change it
        lowered clean.
        """
        s = self._wide_rig_with_main_insert(declare=['L', 'R'])
        s.track('main', speakers=[])
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        assert 'SILENT' in str(e.value)

    def test_the_refusal_admits_that_no_bundled_effect_fits(self):
        """A missing capability, named as one.

        The remedy text may not send a composer looking for a wide reverb
        in the bundle; there is not one, and this pins the message against
        the bundle rather than against itself.
        """
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(self._wide_rig_with_main_insert())
        msg = str(e.value)
        assert 'register_synthdef' in msg
        assert "kind='fx'" in msg
        # ... and the claim is true of the shipped assets, counted from
        # them rather than from the code that writes the message.
        io = json.loads((_SS_DIR / 'assets' / 'io.json').read_text())
        kinds = json.loads((_SS_DIR / 'assets' / 'kinds.json').read_text())
        fx = [n for n, k in kinds.items() if k == 'fx']
        fits = [n for n in fx
                if io.get(n, {}).get('ins') == 24
                and io.get(n, {}).get('outs') == 24]
        stereo = [n for n in fx
                  if io.get(n, {}).get('ins') == 2
                  and io.get(n, {}).get('outs') == 2]
        assert fits == []
        assert len(stereo) == len(fx)          # ALL of them, not most
        assert f"{len(fx)} effects" in msg     # and the message says so

    def test_the_refusal_offers_the_route_that_needs_no_new_synthdef(self):
        """Moving the effect off main works today and must be offered."""
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(self._wide_rig_with_main_insert())
        msg = str(e.value)
        assert "inserts=[]" in msg

    def test_a_matching_width_insert_on_main_is_accepted(self, probe_fx24):
        """The configuration the message sends the composer to must work."""
        rig = grid(6, 4, name='PAVILION')
        s = Score()
        s.track('main', speakers=rig, inserts=[SynthDefFX(probe_fx24)])
        s.track('wide', speakers=rig)
        s.add(voices(), name='x', track='wide')
        meta = convert_score_to_sc_events(s)['meta']
        assert meta['spatial']['tracks']['main']['width'] == 24
        assert [i['defName'] for i in meta['inserts']['main']] == [probe_fx24]

    def test_a_matching_insert_is_accepted_even_with_main_undeclared(
            self, probe_fx24):
        """main's own ``speakers=`` was never what made the width matter.

        Refusing this too would be over-refusing: the chain is 24 wide, the
        insert is 24 wide, every lane is written.
        """
        s = self._wide_rig_with_main_insert(def_name=probe_fx24)
        meta = convert_score_to_sc_events(s)['meta']
        assert meta['spatial']['tracks']['wide']['width'] == 24
        assert 'main' not in meta['spatial']['tracks']

    def test_an_insert_wider_than_mains_chain_reads_past_it(self, probe_fx24):
        """The other direction, and the more dangerous one.

        A quad rig makes ``mainWidth`` 4.  A 24-channel insert on it reads
        24 channels from a 4-channel bus run -- 20 of them belong to
        whatever the allocator handed out next, which is another track's
        live audio.
        """
        s = Score()
        s.track('main', inserts=[SynthDefFX(probe_fx24)])
        s.track('quad', speakers=grid(2, 2, name='QUAD'))
        s.add(voices(), name='x', track='quad')
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        assert 'PAST' in str(e.value)

    def test_a_stereo_insert_on_a_stereo_spatial_score_is_untouched(self):
        """``built`` is 2, the insert is 2, nothing is wrong.

        This is the shape the whole corpus is written in and the refusal
        must not reach it.
        """
        s = Score()
        s.track('main', inserts=[SynthDefFX('kl_reverb')])
        s.track('pair', speakers=['L', 'R'])
        # Both notes at 'L': ``kl_tri`` is a 2-out def, so it occupies the
        # speaker it names and the one above it, and naming 'R' on a
        # 2-speaker array trips the (separate) lane-overrun refusal.
        s.add(voices(speakers=('L', 'L')), name='x', track='pair')
        meta = convert_score_to_sc_events(s)['meta']
        assert meta['spatial']['tracks']['pair']['width'] == 2

    def test_an_insert_with_no_recorded_width_is_refused_not_guessed(self):
        """Same policy ``_check_insert_width`` already applies on a track.

        An unrecorded width is not a width of two.  Guessing two here is
        exactly the assumption that produced the flagship silence, so the
        unknown is refused and the composer is told where widths are
        recorded.
        """
        s = Score()
        s.track('main', inserts=[SynthDefFX('no_such_def_anywhere')])
        s.track('wide', speakers=grid(6, 4, name='PAVILION'))
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        assert 'no recorded channel count' in str(e.value)

    def test_the_plot_surface_refuses_it_too(self):
        """``plot(score)`` lowers through the same ``_build_score_meta``.

        A refusal reachable only from ``play()`` would let a composer
        build, animate and export a score that cannot sound, and find out
        at the concert.
        """
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events,
        )
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_animation_events(
                self._wide_rig_with_main_insert())
        assert 'SILENT' in str(e.value)

    def test_main_with_no_inserts_at_all_stays_accepted_at_any_width(self):
        """A chain with no inserts is bypassed at the FULL width.

        ``scheduler_score.js`` sends ``routerDefName(chainWidth)`` when a
        track has no inserts, so an empty main writes all 24 lanes.  Only
        an insert can narrow the bridge, so only an insert is refused.
        """
        s = Score()
        s.track('main')
        s.track('wide', speakers=grid(6, 4, name='PAVILION'))
        s.add(voices(), name='x', track='wide')
        meta = convert_score_to_sc_events(s)['meta']
        assert meta['spatial']['tracks']['wide']['width'] == 24


class TestTheStereoFloorBelongsToMainAlone:
    """AUD-3c.  Is the rule about the NAME ``main`` or about the role?

    It is about the role, and in Klotho the role is addressed by that
    literal name everywhere -- ``Score.track`` exempts only ``"main"`` from
    the already-registered refusal, ``add()`` exempts only ``"main"`` from
    the must-exist check, and ``scheduler_score.js`` builds
    ``trackMap["main"]`` by hand at ``mainWidth`` after every other track.

    The floor follows from that and from nothing else: ``mainWidth``
    starts at ``BUS_CHANNELS`` and is raised by every other track, so
    main's chain can be wider than main's own declaration.  Every OTHER
    track's chain is built at ``widthOf(name)`` -- exactly its declared
    width, with no floor and no widening -- and its inserts are checked
    against that number at declaration time.  So there is no narrower-than-
    my-own-chain case to catch on a track that is not main, and refusing
    one would be inventing a rule.
    """

    def test_a_one_speaker_track_that_is_not_main_is_accepted(self):
        """Hand-derived: ``widthOf('mono')`` is 1, ``__busRouter1`` is in
        ``PRECOMPILED_WIDTHS``, and the router sums main's lane 0.  Nothing
        is unwritten anywhere, so nothing is refused."""
        s = Score()
        s.track('wide', speakers=grid(6, 4, name='PAVILION'))
        s.track('mono', speakers=[1])
        s.add(voices(), name='x', track='wide')
        meta = convert_score_to_sc_events(s)['meta']['spatial']
        assert meta['tracks']['mono']['width'] == 1
        assert meta['tracks']['wide']['width'] == 24
        assert 1 in PRECOMPILED_WIDTHS

    def test_the_same_one_speaker_declaration_on_main_is_refused(self):
        """The contrast that shows the rule is main's, not the width's."""
        s = Score()
        s.track('main', speakers=[1])
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        assert 'stereo pair' in str(e.value)

    def test_a_narrow_non_main_tracks_inserts_are_checked_at_its_own_width(
            self):
        """And they are checked at declaration, before lowering is reached."""
        s = Score()
        s.track('wide', speakers=grid(6, 4, name='PAVILION'))
        with pytest.raises(ValueError) as e:
            s.track('mono', speakers=[1], inserts=[SynthDefFX('kl_reverb')])
        assert '1 channels wide' in str(e.value)

    def test_the_refusal_says_which_track_the_floor_belongs_to(self):
        """A composer reading it must not conclude every track has a floor."""
        s = Score()
        s.track('main', speakers=[1])
        with pytest.raises(ValueError) as e:
            convert_score_to_sc_events(s)
        msg = str(e.value)
        assert 'master' in msg
        assert 'main' in msg
