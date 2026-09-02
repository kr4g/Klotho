"""SPAN-A `utils` lane -- regression tests for the docket rows fixed in this pass.

Every test here is named for the docket row it pins and was run RED against the
pre-fix tree before the fix landed.  Where a row's fix is a judgement call
(document-vs-raise), the test pins the judgement that was actually made, so a
later reversal is a red test rather than a silent drift.
"""

import math
import re
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

import klotho.utils.algorithms as algorithms
from klotho.utils.algorithms import graphs as graphs_module
from klotho.utils.algorithms.factors import to_factors
from klotho.utils.algorithms.lists import normalize_sum
from klotho.utils.algorithms.ratios import validate_primes


UTILS_ROOT = Path(__file__).resolve().parents[1] / "klotho" / "utils"
SUPERSONIC = UTILS_ROOT / "playback" / "supersonic"


# --------------------------------------------------------------------------
# AUD-102 -- normalize_sum on a zero total / a negative total
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        [1, -1],
        [3, -2, -1],
        (2, -2),
        [Fraction(1, 2), Fraction(-1, 2)],
    ],
)
def test_aud102_zero_total_with_nonzero_elements_raises(data):
    """A zero total is not normalizable: no scalar makes the sum 1.

    The old code returned all zeros, which is a wrong answer wearing the shape
    of a right one -- the caller's weights vanish and the sum is 0, not 1.
    """
    with pytest.raises(ValueError, match="sum(s|med)? to zero|zero total"):
        normalize_sum(data)


def test_aud102_zero_total_numpy_raises():
    with pytest.raises(ValueError):
        normalize_sum(np.array([1.0, -1.0]))


@pytest.mark.parametrize(
    "data, expected_type",
    [([0, 0, 0], list), ((0, 0), tuple)],
)
def test_aud102_all_zero_input_still_returns_zeros(data, expected_type):
    """All-zero input keeps its documented answer: there is nothing to scale."""
    result = normalize_sum(data)
    assert isinstance(result, expected_type)
    assert list(result) == [0] * len(data)


def test_aud102_all_zero_numpy_still_returns_zeros():
    result = normalize_sum(np.zeros(3))
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.zeros(3))


def test_aud102_negative_total_flips_signs_and_is_documented():
    """The sign flip is KEPT (see docstring) -- so the docstring must say so.

    Scaling by ``1/total`` is the only linear map that makes the sum 1, and it
    genuinely preserves every pairwise proportion.  What it does not preserve
    is sign, and that surprise is what the docstring now names.  This test
    pins BOTH halves: the behaviour, and the documentation of it.
    """
    result = normalize_sum([-1, -2, -3])
    assert all(x > 0 for x in result), "negative total still flips every sign"
    assert math.isclose(sum(result), 1.0)
    # pairwise proportions survive the flip
    assert math.isclose(result[1] / result[0], 2.0)

    doc = normalize_sum.__doc__
    assert doc is not None
    assert "sign" in doc.lower(), "the sign flip must be documented, not silent"


def test_aud102_mixed_sign_with_nonzero_total_is_untouched():
    result = normalize_sum([3, -1])
    assert math.isclose(sum(result), 1.0)
    assert result[0] > 0 and result[1] < 0


def test_aud102_positive_input_unchanged():
    """The ordinary path must not move."""
    assert normalize_sum([1, 2, 3, 4]) == [0.1, 0.2, 0.3, 0.4]
    assert normalize_sum((1, 1)) == (0.5, 0.5)


# --------------------------------------------------------------------------
# AUD-101 -- validate_primes truncated floats BEFORE validating
# --------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [[2.5], [3.7], [2, 3.5], [2.5, 3.7]])
def test_aud101_non_integral_floats_rejected(bad):
    """``[2.5, 3.7]`` used to "validate" as ``[2, 3]``."""
    with pytest.raises(ValueError, match="whole number"):
        validate_primes(bad)


def test_aud101_integral_floats_still_accepted():
    """The documented ``2.0 -> 2`` coercion is preserved."""
    assert validate_primes([2.0, 3.0, 5.0]) == [2, 3, 5]
    assert all(isinstance(p, int) for p in validate_primes([2.0, 3.0]))


def test_aud101_string_primes_still_accepted():
    """Strings worked before the fix and must keep working."""
    assert validate_primes(["3", "5"]) == [3, 5]


def test_aud101_fraction_primes():
    assert validate_primes([Fraction(3, 1)]) == [3]
    with pytest.raises(ValueError, match="whole number"):
        validate_primes([Fraction(3, 2)])


def test_aud101_existing_errors_unchanged():
    with pytest.raises(ValueError, match="unique"):
        validate_primes([2, 3, 3])
    with pytest.raises(ValueError, match="must be prime"):
        validate_primes([2, 3, 4])


def test_aud101_ints_unchanged():
    assert validate_primes([2, 3, 5, 7]) == [2, 3, 5, 7]


# --------------------------------------------------------------------------
# AUD-103 -- to_factors handed back pseudo-prime keys for 0 and negatives
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [0, -1, -6, Fraction(-3, 2), "-5/4", Fraction(0, 1), "0"],
)
def test_aud103_non_positive_input_raises(value):
    """``to_factors(0)`` was ``{0: 1}`` and ``to_factors(-6)`` was ``{-1: 1, ...}``.

    Neither ``0`` nor ``-1`` is a prime, so every lattice consumer downstream
    rejected the dict with an error about the *lattice*, not about the input.
    """
    with pytest.raises(ValueError, match="positive"):
        to_factors(value)


def test_aud103_error_names_the_offending_value():
    with pytest.raises(ValueError) as excinfo:
        to_factors(-6)
    assert "-6" in str(excinfo.value)


@pytest.mark.parametrize(
    "value, expected",
    [
        (12, {2: 2, 3: 1}),
        (1, {}),
        (Fraction(3, 2), {3: 1, 2: -1}),
        ("5/4", {5: 1, 2: -2}),
    ],
)
def test_aud103_positive_input_unchanged(value, expected):
    assert to_factors(value) == expected


def test_aud103_type_error_still_type_error():
    with pytest.raises(TypeError):
        to_factors([1, 2])


# --------------------------------------------------------------------------
# AUD-108 -- the package __all__ dropped the eight graph traversals
# --------------------------------------------------------------------------


def test_aud108_package_all_covers_every_graph_export():
    missing = [n for n in graphs_module.__all__ if n not in algorithms.__all__]
    assert missing == [], f"graphs.__all__ names not re-exported: {missing}"


def test_aud108_star_import_agrees_between_package_and_module():
    package_ns: dict = {}
    exec("from klotho.utils.algorithms import *", package_ns)
    module_ns: dict = {}
    exec("from klotho.utils.algorithms.graphs import *", module_ns)

    assert module_ns, "guard: the module star-import must actually bind something"
    for name in graphs_module.__all__:
        assert name in module_ns, f"{name} vanished from the module star-import"
        assert name in package_ns, f"{name} missing from the package star-import"


def test_aud108_every_all_entry_actually_resolves():
    """A name in ``__all__`` that does not resolve breaks ``import *`` outright."""
    assert algorithms.__all__, "guard: __all__ must be non-empty"
    for name in algorithms.__all__:
        assert hasattr(algorithms, name), f"__all__ names {name}, which does not exist"


# --------------------------------------------------------------------------
# AUD-69 -- a gated Kit voice inside a loose Score Event never got released
# --------------------------------------------------------------------------


def _kit_release_payload(members, default, order):
    """Lower one Score Event whose Kit voices straddle the gated/ungated line."""
    from klotho.thetos.composition.score import Score
    from klotho.thetos.instruments.synthdef import SynthDefKit
    from klotho.utils.playback.supersonic.converters import convert_score_to_sc_events

    kit = SynthDefKit.from_manifest(members, default=default)
    score = Score()
    event = score.new(start=0.0, dur=1.0, inst=kit, voice=order)
    event.add_release(1.0)
    payload = convert_score_to_sc_events(score)

    by_id = {
        e["id"]: e["defName"]
        for e in payload["events"]
        if e.get("type") == "new"
    }
    released = [by_id[e["id"]] for e in payload["events"] if e.get("type") == "release"]
    return by_id, released


# 'kl_saw' is gated; 'kl_kicktone' is not.  Both are real manifest entries.
GATED_DEF = "kl_saw"
UNGATED_DEF = "kl_kicktone"


def test_aud69_gated_voice_under_ungated_default_is_released():
    """The silent half: the gated voice sustained until the widget stopped.

    Before the fix this produced ZERO release events -- the whole decision
    was taken from the *default* member's ``has_gate``, which
    ``SynthDefKit`` itself documents as "a display/fallback hint".
    """
    by_id, released = _kit_release_payload(
        {"thump": UNGATED_DEF, "saw": GATED_DEF}, default="thump",
        order=("thump", "saw"),
    )
    assert set(by_id.values()) == {UNGATED_DEF, GATED_DEF}, "guard: both voices lowered"
    assert released == [GATED_DEF]


def test_aud69_ungated_voice_under_gated_default_gets_no_release():
    """The mirror image: a release aimed at a synth with no gate control."""
    by_id, released = _kit_release_payload(
        {"saw": GATED_DEF, "thump": UNGATED_DEF}, default="saw",
        order=("saw", "thump"),
    )
    assert set(by_id.values()) == {UNGATED_DEF, GATED_DEF}, "guard: both voices lowered"
    assert released == [GATED_DEF]


def test_aud69_all_gated_kit_releases_every_voice():
    _, released = _kit_release_payload(
        {"saw": GATED_DEF, "sine": "kl_sine"}, default="saw",
        order=("saw", "sine"),
    )
    assert sorted(released) == sorted([GATED_DEF, "kl_sine"])


def test_aud69_all_ungated_kit_releases_nothing():
    _, released = _kit_release_payload(
        {"thump": UNGATED_DEF, "arpy": "fd_arpy"}, default="thump",
        order=("thump", "arpy"),
    )
    assert released == []


@pytest.mark.parametrize(
    "inst, expected_releases",
    [(GATED_DEF, 1), (UNGATED_DEF, 0)],
)
def test_aud69_non_kit_path_is_unchanged(inst, expected_releases):
    """The plain-instrument path never had the defect and must not move."""
    from klotho.thetos.composition.score import Score
    from klotho.utils.playback.supersonic.converters import convert_score_to_sc_events

    score = Score()
    event = score.new(start=0.0, dur=1.0, inst=inst)
    event.add_release(1.0)
    payload = convert_score_to_sc_events(score)
    releases = [e for e in payload["events"] if e.get("type") == "release"]
    assert len(releases) == expected_releases


def test_aud69_fyi_names_the_actually_ungated_def():
    """The old FYI named the *default* synth, pointing at the wrong voice."""
    import klotho.utils.playback.supersonic.converters as conv

    seen = []
    original = conv._event_fyi
    conv._event_fyi = lambda key, message: seen.append(message)
    try:
        _kit_release_payload(
            {"saw": GATED_DEF, "thump": UNGATED_DEF}, default="saw",
            order=("saw", "thump"),
        )
    finally:
        conv._event_fyi = original

    ungated_notes = [m for m in seen if "ungated" in m]
    assert ungated_notes, "guard: an ungated-voice FYI must be emitted at all"
    assert UNGATED_DEF in ungated_notes[0]
    assert GATED_DEF not in ungated_notes[0]


# --------------------------------------------------------------------------
# AF1-13 -- dead imports in supersonic/converters.py
# --------------------------------------------------------------------------


def test_af1_13_no_dead_harmonic_tree_import():
    source = (SUPERSONIC / "converters.py").read_text()
    for name in ("HarmonicTree", "Spectrum"):
        assert name not in source, f"{name} is imported but never used"


# --------------------------------------------------------------------------
# AUD-172 -- freq_to_midi answered 69.0 (A440) for junk input
# --------------------------------------------------------------------------


def test_aud172_valid_frequencies_unchanged():
    from klotho.utils.playback._converter_base import freq_to_midi

    assert freq_to_midi(440.0) == pytest.approx(69.0)
    assert freq_to_midi(880.0) == pytest.approx(81.0)
    assert freq_to_midi(220) == pytest.approx(57.0)


@pytest.mark.parametrize("bad", [0, 0.0, -0.0, -440, -1e-9])
def test_aud172_non_positive_frequency_raises(bad):
    """``freq_to_midi(0)`` used to return 69.0 -- exactly A440's answer.

    A bad frequency became a plausible note number in the payload, so the
    mistake showed up as a wrong pitch rather than as an error.
    """
    from klotho.utils.playback._converter_base import freq_to_midi

    with pytest.raises(ValueError, match="positive"):
        freq_to_midi(bad)


@pytest.mark.parametrize("bad", ["x", None, [], {}, "440"])
def test_aud172_non_numeric_frequency_raises(bad):
    from klotho.utils.playback._converter_base import freq_to_midi

    with pytest.raises(TypeError):
        freq_to_midi(bad)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_aud172_non_finite_frequency_raises(bad):
    """NaN used to pass straight through into the JSON payload.

    ``nan`` is not valid JSON, so this one does not merely mislead -- it can
    produce a payload the browser cannot parse.
    """
    from klotho.utils.playback._converter_base import freq_to_midi

    with pytest.raises(ValueError):
        freq_to_midi(bad)


def test_aud172_answer_for_bad_input_is_no_longer_confusable_with_a440():
    """A relation, not an identity: junk must not share A440's answer."""
    from klotho.utils.playback._converter_base import freq_to_midi

    good = freq_to_midi(440.0)
    for bad in (0, -440, "x", None):
        with pytest.raises((ValueError, TypeError)):
            freq_to_midi(bad)
    assert good == pytest.approx(69.0)
