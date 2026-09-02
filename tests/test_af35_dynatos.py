"""AF-3.5 span-A lane: dynatos contract tests.

Every test here asserts a RELATION (a docstring claim against the behaviour
it documents, an invariant across two calls, a refusal where a refusal is
owed) rather than a frozen literal, so the oracle stays independent of the
code it checks.

Rows covered: AUD-26, AUD-22, AUD-111, AUD-19, AUD-105, AUD-104, ENV-12,
AUD-112.
"""

import doctest
import warnings
import math

import numpy as np
import pytest

from klotho.dynatos import Envelope, DynamicRange, arch, line, map_curve
from klotho.dynatos.dynamics import Dynamic, ampdb, dbamp, freq_amp_scale
from klotho.dynatos.types import Amplitude, Decibel


# ---------------------------------------------------------------- AUD-26 --
# The docstring example is a CLAIM about the code. Rather than pin the number
# (which would go stale the moment either side moved), run every documented
# example in the dynatos modules and require the module to agree with itself.

_DOCTESTED_MODULES = (
    'klotho.dynatos.envelopes.envelopes',
    'klotho.dynatos.dynamics.dynamics',
    'klotho.dynatos.envelopes.utils.curves',
)


@pytest.mark.parametrize('modname', _DOCTESTED_MODULES)
def test_documented_examples_match_behaviour(modname):
    """AUD-26: a docstring example must produce what it says it produces."""
    module = __import__(modname, fromlist=['__name__'])
    runner = doctest.DocTestRunner(verbose=False)
    finder = doctest.DocTestFinder()
    failures = []
    attempted = 0
    for test in finder.find(module, modname):
        result = runner.run(test, out=lambda s: None, clear_globs=False)
        attempted += result.attempted
        if result.failed:
            failures.append((test.name, result.failed, result.attempted))
    # Without this the parametrization over a module carrying NO doctest
    # examples runs an empty loop and passes unconditionally -- it could never
    # go red, now or after any future edit, while still reporting green. That
    # is the shape this project calls a guard that guards nothing.
    assert attempted, (
        f"{modname} contains no runnable docstring examples, so this "
        f"parametrization asserts nothing. Either add an example, or drop the "
        f"module from _DOCTESTED_MODULES -- do not leave a green check here."
    )
    assert not failures, (
        f"documented examples disagree with the code in {modname}: {failures}"
    )


def test_flagship_envelope_example_is_the_linear_midpoint():
    """AUD-26: independently derive the flagship example's value.

    values [0, 1, 0.5, 0] over times [0.1, 0.8, 0.1] puts t=0.5 exactly
    halfway through the second (linear) segment, so the answer is the
    arithmetic mean of that segment's endpoints. Derived from the envelope's
    own definition, not read off the implementation.
    """
    env = Envelope([0, 1, 0.5, 0], times=[0.1, 0.8, 0.1])
    seg_start, seg_end = env.values[1], env.values[2]
    assert env.at_time(0.5) == pytest.approx((seg_start + seg_end) / 2)


# ---------------------------------------------------------------- ENV-12 --

def test_at_time_returns_float_everywhere_including_endpoints():
    """ENV-12: ``at_time`` documents "float"; the endpoints returned ``int``.

    Relation asserted: the type is the same at every query point, and it is
    the type the docstring names. Nothing is pinned to a literal value.
    """
    env = Envelope([0, 1, 0, 2], times=[1, 1, 1])   # int breakpoints
    probes = [0.0, 0.5, 1.0, 1.5, 3.0]
    kinds = {type(env.at_time(t)) for t in probes}
    assert kinds == {float}, f"at_time returned mixed types across {probes}: {kinds}"


def test_sample_returns_float_everywhere_and_agrees_with_at_time():
    """ENV-12: batch and scalar paths must not differ in type OR value."""
    env = Envelope([0, 1, 0, 2], times=[1, 1, 1])
    probes = [0.0, 0.5, 1.0, 1.5, 3.0]
    batch = env.sample(probes)
    assert {type(v) for v in batch} == {float}, [type(v).__name__ for v in batch]
    assert batch == [env.at_time(t) for t in probes]


def test_curved_segment_does_not_leak_a_numpy_scalar():
    """ENV-12: the curved branch used to hand back ``np.float64``."""
    env = Envelope([0, 1], times=1.0, curve=-3)
    assert type(env.at_time(0.5)) is float


def test_sample_refuses_a_scalar_with_a_shaped_error():
    """ENV-12: ``sample(0.0)`` leaked "'float' object is not iterable"."""
    env = Envelope([0, 1], times=1.0)
    with pytest.raises(TypeError) as exc:
        env.sample(0.0)
    message = str(exc.value)
    assert 'sample' in message and 'at_time' in message, message
    assert 'not iterable' not in message, (
        f"still leaking the raw iteration error: {message}"
    )


# ------------------------------------------------------- AUD-22 / AUD-111 --

class TestEnvelopeConstructorValidation:
    """AUD-22 + AUD-111: the constructor accepted shapes it cannot evaluate."""

    def test_too_many_times_is_refused_naming_both_lengths(self):
        values = [0, 1]
        times = [0.5, 0.5, 0.5]
        with pytest.raises(ValueError) as exc:
            Envelope(values, times=times)
        message = str(exc.value)
        # Relation: the message must name the length it got and the length it
        # needs, both derived from the inputs rather than pinned.
        assert str(len(times)) in message, message
        assert str(len(values) - 1) in message, message

    def test_too_few_times_is_refused(self):
        with pytest.raises(ValueError, match='times'):
            Envelope([0, 1, 2, 3], times=[1.0])

    def test_mismatched_curve_list_is_refused_at_construction(self):
        """Before: constructed fine, then IndexError on the third segment."""
        with pytest.raises(ValueError, match='curve'):
            Envelope([0, 1, 2, 3], times=[1, 1, 1], curve=[-3])

    def test_constructed_envelopes_have_consistent_lengths(self):
        """The invariant the refusals exist to protect."""
        for env in (Envelope([0, 1, 0]),
                    Envelope([0, 1, 0], times=[0.2, 0.8], curve=[1, -1]),
                    Envelope.perc(), Envelope.adr(), Envelope.adsr(),
                    Envelope.pairs([(0, 0), (0.1, 1), (1.0, 0)])):
            assert len(env.times) == len(env.values) - 1
            assert len(env.curve) == len(env.values) - 1

    def test_negative_segment_time_is_refused(self):
        """AUD-111: a negative time silently SHORTENED the envelope.

        Relation: total_time must never be less than the largest breakpoint
        time. A negative segment broke exactly that, leaving the cumulative
        boundary list non-monotonic and bisect_left meaningless on it.
        """
        with pytest.raises(ValueError, match='negative'):
            Envelope([0, 1, 0], times=[1.0, -0.5])

    def test_negative_scalar_time_is_refused(self):
        with pytest.raises(ValueError, match='negative'):
            Envelope([0, 1], times=-1.0)

    def test_empty_values_is_refused_at_construction(self):
        """AUD-111: Envelope([]) constructed, then IndexError on first use."""
        with pytest.raises(ValueError, match='values'):
            Envelope([])

    def test_single_value_is_refused_at_construction(self):
        """An envelope with no segment cannot interpolate anything."""
        with pytest.raises(ValueError, match='values'):
            Envelope([0.5])

    def test_exp_refusal_reports_the_values_the_caller_typed(self):
        """AUD-111: the message quoted POST-normalisation numbers only.

        The caller typed [2, 4, 8]; normalize_values rewrote them to
        [0.0, 0.333, 1.0] and the refusal reported only the rewrite, so the
        message named no number the caller had ever seen.
        """
        typed = [2, 4, 8]
        with pytest.raises(ValueError, match='strictly positive') as exc:
            Envelope(typed, normalize_values=True, warp='exp')
        message = str(exc.value)
        assert all(str(v) in message for v in typed), message
        assert 'normaliz' in message.lower() or 'scale' in message.lower(), message

    def test_exp_refusal_still_validates_after_value_scale(self):
        """The refusal must stay AFTER the transforms, not move before them."""
        with pytest.raises(ValueError, match='strictly positive'):
            Envelope([1, 2], warp='exp', value_scale=-1.0)


# ---------------------------------------------------------------- AUD-19 --

class TestMapCurveRangeOrientation:
    """AUD-19: a descending ``in_range`` went straight into ``np.interp``.

    ``np.interp`` documents that ``xp`` must be increasing and does not check
    it, so a reversed input range produced a silently wrong number rather than
    a refusal.
    """

    def test_descending_in_range_hits_both_endpoints(self):
        """From the definition of a range map, in either orientation."""
        hi, lo = 72.0, 60.0
        out = (0.0, 1.0)
        assert map_curve(hi, (hi, lo), out) == pytest.approx(out[0])
        assert map_curve(lo, (hi, lo), out) == pytest.approx(out[1])

    def test_descending_in_range_is_strictly_monotone(self):
        """The bug's signature: every probe past the first collapsed to one value."""
        probes = np.linspace(60.0, 72.0, 9)
        got = [float(map_curve(v, (72.0, 60.0), (0.0, 1.0))) for v in probes]
        # descending input range => output decreases as the value rises
        assert all(b < a for a, b in zip(got, got[1:])), got

    def test_reversing_both_ranges_is_the_identity_for_a_linear_curve(self):
        """map(v, (a,b), (c,d)) == map(v, (b,a), (d,c)) — algebra, not a snapshot."""
        for v in (0.0, 2.5, 5.0, 7.5, 10.0):
            forward = map_curve(v, (0.0, 10.0), (-1.0, 1.0))
            reversed_both = map_curve(v, (10.0, 0.0), (1.0, -1.0))
            assert forward == pytest.approx(reversed_both), v

    def test_descending_in_range_clamps_on_both_sides(self):
        out = (10.0, 20.0)
        assert map_curve(100.0, (72.0, 60.0), out) == pytest.approx(out[0])
        assert map_curve(0.0, (72.0, 60.0), out) == pytest.approx(out[1])

    def test_ascending_in_range_is_unchanged(self):
        """Regression guard: derived from the linear map, not from the code."""
        in_range, out_range = (0.0, 4.0), (10.0, 20.0)
        for v in (0.0, 1.0, 2.0, 3.0, 4.0):
            t = (v - in_range[0]) / (in_range[1] - in_range[0])
            expected = out_range[0] + t * (out_range[1] - out_range[0])
            assert map_curve(v, in_range, out_range) == pytest.approx(expected)

    def test_descending_out_range_is_unchanged(self):
        """The corpus uses this idiom constantly, e.g. (0.75, 0.33)."""
        in_range, out_range = (0.0, 4.0), (0.75, 0.33)
        for v in (0.0, 2.0, 4.0):
            t = (v - in_range[0]) / (in_range[1] - in_range[0])
            expected = out_range[0] + t * (out_range[1] - out_range[0])
            assert map_curve(v, in_range, out_range) == pytest.approx(expected)

    def test_curve_shaping_survives_a_descending_in_range(self):
        """Curved output must still span the whole out_range, monotonically."""
        probes = np.linspace(60.0, 72.0, 7)
        got = [float(map_curve(v, (72.0, 60.0), (0.0, 1.0), curve=-3)) for v in probes]
        assert got[0] == pytest.approx(1.0)
        assert got[-1] == pytest.approx(0.0)
        assert all(b < a for a, b in zip(got, got[1:])), got

    def test_zero_width_in_range_yields_the_start_of_out_range(self):
        """A sweep with nowhere to go sits at its starting value.

        Both lenses agree: a one-note hairpin is played at its starting
        dynamic, and ``(v - a) / (b - a)`` has limit 0 when v == a == b. The
        old np.interp path returned out_range[1] here, which was the arbitrary
        artifact of a right-side clamp.
        """
        assert map_curve(0.0, (0.0, 0.0), (0.75, 0.33)) == pytest.approx(0.75)


# --------------------------------------------------------------- AUD-105 --

class TestAmplitudeDecibelContract:
    """AUD-105. The stated contract:

    * ``ampdb`` accepts amplitudes in ``[0, inf)``. ``ampdb(0)`` is ``-inf``
      exactly -- silence has a real, round-tripping representation in dB, and
      it emits no RuntimeWarning, because it is a defined case and not a
      numerical accident.
    * A negative amplitude is a phase inversion, not a level; ``ampdb``
      refuses it rather than returning NaN.
    * NaN is refused on the way in by both converters, so it can never leave
      one. ``dbamp(-inf) == 0.0`` stays, because playback relies on it.
    """

    def test_zero_amplitude_is_negative_infinity_and_round_trips(self):
        assert ampdb(0) == -math.inf
        assert dbamp(ampdb(0)) == 0.0

    def test_zero_amplitude_emits_no_runtime_warning(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            assert ampdb(0.0) == -math.inf

    def test_negative_amplitude_is_refused_naming_the_value(self):
        with pytest.raises(ValueError) as exc:
            ampdb(-0.5)
        assert '-0.5' in str(exc.value), str(exc.value)

    def test_nan_amplitude_is_refused(self):
        with pytest.raises(ValueError):
            ampdb(float('nan'))

    def test_nan_decibels_is_refused(self):
        with pytest.raises(ValueError):
            dbamp(float('nan'))

    def test_nan_never_survives_either_converter(self):
        """The whole point of the contract, stated as one relation.

        AF-3.5: this used to probe ``[0.0, 1e-9, 0.5, 1.0, 4.0]`` -- five
        ordinary finite amplitudes and not one NaN. A guard named for NaN
        whose probe set contains no NaN cannot fail for the reason it is
        named, whatever else it happens to check. The probes now include
        every edge the docstring above names: NaN itself, both infinities
        and a negative amplitude.

        The relation, for BOTH converters and in both directions: every
        input either comes back a non-NaN number or is REFUSED by name.
        NaN leaving a converter is the one outcome forbidden outright.
        """
        probes = [float('nan'), float('inf'), float('-inf'), -0.5,
                  0.0, 1e-9, 0.5, 1.0, 4.0]
        refused = {'ampdb': [], 'dbamp': []}
        for fn, key in ((ampdb, 'ampdb'), (dbamp, 'dbamp')):
            for p in probes:
                try:
                    out = fn(p)
                except ValueError:
                    refused[key].append(p)
                    continue
                assert not math.isnan(out), (
                    f'{key}({p!r}) returned NaN instead of refusing it')

        # A refusal is only an answer if it actually happens: NaN must be
        # among the values each converter turned away, or "refused by name"
        # is a claim nothing here checks.
        for key, turned_away in refused.items():
            assert any(math.isnan(p) for p in turned_away), (
                f'{key} accepted NaN rather than refusing it; it refused '
                f'{turned_away}')

        # ...and the round trip cannot manufacture one either.
        for a in (0.0, 1e-9, 0.5, 1.0, 4.0):
            assert not math.isnan(dbamp(ampdb(a))), a

    def test_round_trip_is_the_identity_on_the_defined_domain(self):
        for db in (-90.0, -60.0, -12.0, -3.0, 0.0, 6.0):
            assert ampdb(dbamp(db)) == pytest.approx(db)

    def test_amplitude_type_wrapper_inherits_the_refusal(self):
        """AUD-105: Amplitude(-1).decibel used to be a NaN Decibel."""
        with pytest.raises(ValueError):
            Amplitude(-1).decibel

    def test_amplitude_type_wrapper_keeps_silence_representable(self):
        silent = Amplitude(0).decibel
        assert float(silent) == -math.inf
        assert float(Decibel(float(silent)).amplitude) == 0.0

    def test_dynamic_amp_inherits_the_refusal_for_nan(self):
        with pytest.raises(ValueError):
            Dynamic('nonsense', float('nan')).amp

    def test_dynamic_at_negative_infinity_is_silent_not_broken(self):
        assert Dynamic('silence', -math.inf).amp == 0.0


# --------------------------------------------------------------- AUD-104 --

class TestDegenerateDynamicsInputs:
    """AUD-104: degenerate inputs surfaced as raw ZeroDivisionError."""

    def test_single_dynamic_is_refused_naming_the_parameter(self):
        with pytest.raises(ValueError, match='dynamics') as exc:
            DynamicRange(dynamics=('f',))
        assert 'ZeroDivision' not in type(exc.value).__name__

    def test_empty_dynamics_is_refused(self):
        """Before: constructed fine, then IndexError from .min_dynamic."""
        with pytest.raises(ValueError, match='dynamics'):
            DynamicRange(dynamics=())

    def test_two_dynamics_is_the_smallest_working_range(self):
        """Boundary check on the refusal: two is enough to span a range."""
        dr = DynamicRange(dynamics=('p', 'f'), min_dynamic=-40, max_dynamic=-4)
        assert dr.min_dynamic.marking == 'p'
        assert dr.max_dynamic.marking == 'f'
        assert dr.min_dynamic.db < dr.max_dynamic.db


class TestFreqAmpScaleGuards:
    """AUD-104: ``min_db`` at or above 0 dB."""

    def test_zero_min_db_is_refused_not_a_zero_division(self):
        with pytest.raises(ValueError, match='min_db') as exc:
            freq_amp_scale(440, -12, min_db=0)
        assert 'ZeroDivision' not in type(exc.value).__name__

    def test_positive_min_db_is_refused(self):
        """The silent half: min_db=5 returned a plausible number.

        ``min_db`` is the FLOOR of the dynamic range, so a value at or above
        unity gain inverts the range's direction and the phon estimate built
        from it, with no error anywhere.
        """
        with pytest.raises(ValueError, match='min_db'):
            freq_amp_scale(440, -12, min_db=5)

    def test_negative_min_db_still_scales_monotonically(self):
        """Regression guard, stated as a relation over the working domain."""
        louder = freq_amp_scale(440, -6, min_db=-60)
        quieter = freq_amp_scale(440, -30, min_db=-60)
        assert louder > quieter > 0


class TestDynamicRangeRangesIsReadOnly:
    """AUD-104: ``.ranges`` handed out the instance's own mutable dict."""

    def test_ranges_refuses_assignment(self):
        dr = DynamicRange()
        with pytest.raises(TypeError):
            dr.ranges['f'] = 'clobbered'

    def test_ranges_refuses_deletion(self):
        dr = DynamicRange()
        with pytest.raises(TypeError):
            del dr.ranges['ppp']

    def test_ranges_agrees_with_item_access_for_every_marking(self):
        """Relation: the view and the accessor are two doors on one table."""
        dr = DynamicRange()
        for marking, dynamic in dr.ranges.items():
            assert dr[marking] is dynamic

    def test_a_hostile_caller_cannot_break_min_dynamic(self):
        """Deleting a key through the old leak made .min_dynamic raise forever."""
        dr = DynamicRange()
        with pytest.raises(TypeError):
            del dr.ranges[dr.ranges and next(iter(dr.ranges))]
        assert dr.min_dynamic.marking == 'ppp'


# --------------------------------------------------------------- AUD-112 --
# NOTE: the `axis` damping half of AUD-112 is deliberately NOT touched or
# pinned here. Whether the 0.4 factor that keeps the apex off the edge is a
# musical choice or a defect is the client's call, so every test below uses
# the default axis and asserts nothing about how the apex moves.

class TestArchDegenerateInputs:

    def test_a_single_step_shows_the_base_not_the_peak(self):
        """AUD-112: arch(steps=1) returned [peak].

        Stated as agreement with ``line``, which already answers with its
        START for one step. An arch begins at its base, so one sample of it
        is the base -- the peak is the one point it is definitely not at
        when it begins.
        """
        base, peak = 0.25, 0.9
        assert arch(base, peak, steps=1)[0] == pytest.approx(base)
        assert arch(base, peak, steps=1)[0] == pytest.approx(line(base, peak, 1)[0])

    def test_every_arch_begins_at_its_base(self):
        """The invariant the single-step case broke, across a range of steps."""
        base, peak = 0.25, 0.9
        for steps in (1, 2, 3, 5, 16, 101):
            assert arch(base, peak, steps=steps)[0] == pytest.approx(base), steps

    def test_zero_steps_is_still_empty(self):
        assert len(arch(0.0, 1.0, steps=0)) == 0

    def test_curve_list_of_three_is_refused_naming_the_expected_length(self):
        """Before: an opaque numpy broadcast error, or silent garbage."""
        with pytest.raises(ValueError) as exc:
            arch(0.0, 1.0, steps=100, curve=[1, 2, 3])
        message = str(exc.value)
        assert 'curve' in message and '2' in message, message
        assert 'broadcast' not in message, message

    def test_curve_list_of_one_is_refused(self):
        """This size did NOT raise: it broadcast per-sample and returned garbage."""
        with pytest.raises(ValueError, match='curve'):
            arch(0.0, 1.0, steps=5, curve=[1])

    def test_curve_list_that_happens_to_match_the_sample_count_is_refused(self):
        """The silent case: len(curve)==3 with 3 rising samples used to 'work'."""
        with pytest.raises(ValueError, match='curve'):
            arch(0.0, 1.0, steps=5, curve=[1, 2, 3])

    def test_a_scalar_curve_is_the_same_as_repeating_it_for_both_sides(self):
        """Regression guard: the documented meaning of a scalar curve."""
        assert np.allclose(arch(0.0, 1.0, steps=9, curve=3),
                           arch(0.0, 1.0, steps=9, curve=[3, 3]))

    def test_a_two_element_curve_shapes_the_sides_independently(self):
        """Independence, as a relation: [a, b] is neither `a` nor `b` alone."""
        asymmetric = arch(0.0, 1.0, steps=9, curve=[3, -3])
        assert not np.allclose(asymmetric, arch(0.0, 1.0, steps=9, curve=3))
        assert not np.allclose(asymmetric, arch(0.0, 1.0, steps=9, curve=-3))

    def test_the_arch_still_reaches_its_peak(self):
        for curve in (0.0, 3, [3, -3]):
            assert np.max(arch(0.0, 1.0, steps=9, curve=curve)) == pytest.approx(1.0)
