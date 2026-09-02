"""AUD-11: ``play(HarmonicTree)`` must sound the tree's OWN harmonics.

The adapter in ``klotho/utils/playback/_converter_base.py`` used to guard on
a ``partials`` attribute that ``HarmonicTree`` does not have -- the real
attribute is ``harmonics`` -- so the guard never matched, a hardcoded
``[1, 2, 3, 4, 5]`` fallback ran, and EVERY ``HarmonicTree`` auditioned as
the identical C4 overtone stack no matter what it contained. Nothing raised
and nothing warned; the audition simply had no relationship to the object.

Every expected frequency below is derived by hand from the spec, never from
running the converter:

* A leaf's *harmonic* is the product of the ``factor`` values along the path
  from the root (``HarmonicTree.harmonics``, and ``_evaluate`` computes
  ``harmonic = value * inherited_harmonic``).
* The playback adapter's fundamental is the convention root **C4**, which in
  Klotho's 12-TET (A4 = 440 Hz) is **261.6256 Hz** -- the tree is
  pitch-abstract, so the adapter supplies a root and its docstring says so.
* A partial's frequency is therefore ``261.6256 * harmonic``.

So the arithmetic a reader can check with a calculator:

===================================  ==========  ==========================
tree                                 harmonics   frequencies (Hz)
===================================  ==========  ==========================
``HarmonicTree(2, (3, 5, 7))``       6, 10, 14   1569.7536, 2616.256,
                                                 3662.7584
``HarmonicTree(1, (1,))`` (default)  1           261.6256
``HarmonicTree(3, (1,))``            3           784.8768
===================================  ==========  ==========================

None of those are ``[1, 2, 3, 4, 5] * 261.6256``, which is the whole point:
before the fix every one of these lowered to the same five frequencies.
"""

import pytest

from klotho.tonos import Pitch
from klotho.tonos.systems.harmonic_trees import HarmonicTree
from klotho.utils.playback.supersonic.converters import convert_to_sc_events


# 12-TET, A4 = 440 Hz.  C4 is nine semitones below A4 in the same octave
# block: 440 * 2 ** (-9/12) = 261.6255653...,  which Klotho carries as
# 261.6256 Hz.  Hardcoded rather than read off ``Pitch("C4").freq`` so the
# expectation does not move if the pitch table does.
C4_HZ = 261.6256

# The stack the broken adapter always produced, kept here so a regression to
# it is named rather than merely "not equal to the right answer".
OLD_FALLBACK_HZ = [C4_HZ * n for n in (1, 2, 3, 4, 5)]


def _lowered_freqs(obj, **kwargs):
    """Frequencies, in event order, of ``obj`` lowered to SC events."""
    return [e['pfields']['freq'] for e in convert_to_sc_events(obj, **kwargs)]


def test_harmonic_tree_lowers_its_own_harmonics():
    """A tree's leaf harmonics, times C4, are what sounds.

    ``HarmonicTree(root=2, children=(3, 5, 7))`` has leaf harmonics
    2*3 = 6, 2*5 = 10, 2*7 = 14, so the partials are C4 * 6, * 10, * 14.
    """
    ht = HarmonicTree(root=2, children=(3, 5, 7))
    assert ht.harmonics == (6, 10, 14)

    expected = [261.6256 * 6, 261.6256 * 10, 261.6256 * 14]
    assert expected == pytest.approx([1569.7536, 2616.256, 3662.7584])

    freqs = _lowered_freqs(ht)
    assert freqs == pytest.approx(expected)


def test_harmonic_tree_does_not_lower_the_c4_1_to_5_fallback():
    """The broken adapter's hardcoded stack must not come back."""
    ht = HarmonicTree(root=2, children=(3, 5, 7))
    freqs = _lowered_freqs(ht)
    assert freqs != pytest.approx(OLD_FALLBACK_HZ)
    assert len(freqs) != len(OLD_FALLBACK_HZ)


def test_event_count_matches_leaf_count():
    """One partial per leaf -- not always five.

    The default tree ``HarmonicTree()`` is ``root=1, children=(1,)``: a
    single leaf whose harmonic is 1*1 = 1, so it lowers to ONE event at C4.
    The broken adapter lowered five.
    """
    default_tree = HarmonicTree()
    assert default_tree.harmonics == (1,)

    freqs = _lowered_freqs(default_tree)
    assert len(freqs) == 1
    assert freqs[0] == pytest.approx(261.6256)

    wide = HarmonicTree(root=1, children=(3, 5, 7, 9, 11, 13))
    assert len(_lowered_freqs(wide)) == len(wide.harmonics) == 6


def test_root_factor_reaches_the_payload():
    """Changing only the root transposes the audition by that factor.

    ``root=1, children=(1,)`` -> harmonic 1 -> 261.6256 Hz.
    ``root=3, children=(1,)`` -> harmonic 3 -> 784.8768 Hz.
    The ratio of the two is exactly 3.  Under the bug both lowered to the
    same five frequencies and the ratio was 1.
    """
    low = _lowered_freqs(HarmonicTree(root=1, children=(1,)))
    high = _lowered_freqs(HarmonicTree(root=3, children=(1,)))

    assert low == pytest.approx([261.6256])
    assert high == pytest.approx([784.8768])
    assert high[0] / low[0] == pytest.approx(3.0)


def test_child_factors_reach_the_payload():
    """Two trees sharing a root but differing in children sound different.

    ``HarmonicTree(1, (3, 5))`` -> harmonics 3, 5 -> 784.8768, 1308.128 Hz.
    ``HarmonicTree(1, (7, 11))`` -> harmonics 7, 11 -> 1831.3792, 2877.8816 Hz.
    """
    a = _lowered_freqs(HarmonicTree(root=1, children=(3, 5)))
    b = _lowered_freqs(HarmonicTree(root=1, children=(7, 11)))

    assert a == pytest.approx([261.6256 * 3, 261.6256 * 5])
    assert b == pytest.approx([261.6256 * 7, 261.6256 * 11])
    assert a != pytest.approx(b)


def test_nested_harmonics_multiply_along_the_path():
    """A grafted branch's harmonic is the product of the whole path.

    Root 2 with a child 3 that itself has children (5, 7) gives leaf
    harmonics 2*3*5 = 30 and 2*3*7 = 42, i.e. 7848.768 and 10988.2752 Hz.
    """
    ht = HarmonicTree(root=2, children=(3,))
    branch = ht.leaf_nodes[0]
    ht.add_child(branch, factor=5)
    ht.add_child(branch, factor=7)

    assert set(ht.harmonics) == {30, 42}

    freqs = sorted(_lowered_freqs(ht))
    assert freqs == pytest.approx([261.6256 * 30, 261.6256 * 42])


def test_fundamental_is_the_documented_c4_convention():
    """The adapter's convention root is C4, and it is documented as such.

    ``HarmonicTree`` carries no pitch, so the adapter must supply a
    fundamental. Silently choosing one is what produced this bug's twin, so
    the choice is pinned here and the docstring is required to name it.
    """
    from klotho.utils.playback import _converter_base

    freqs = _lowered_freqs(HarmonicTree(root=1, children=(1,)))
    assert freqs[0] == pytest.approx(Pitch("C4").freq)
    assert freqs[0] == pytest.approx(261.6256)

    registry = _converter_base._build_convert_registry()
    adapter = registry.lookup(HarmonicTree(root=1, children=(1,)))
    assert adapter.__doc__ is not None
    assert "C4" in adapter.__doc__


def test_undertone_harmonics_are_refused_with_a_legible_message():
    """A negative leaf harmonic raises a message that names the problem.

    A negative ``factor`` yields a negative harmonic, hence a negative
    frequency, and the pitch machinery then dies inside ``log2`` with a bare
    ``math domain error``. Playback has no settled convention for undertones
    (whether -2 means the subharmonic 1/2 is an open question), so the
    adapter refuses rather than inventing one -- but it must say so.
    """
    ht = HarmonicTree(root=1, children=(2, -2))
    assert ht.harmonics == (2, -2)

    with pytest.raises(ValueError) as excinfo:
        convert_to_sc_events(ht)

    message = str(excinfo.value)
    assert "HarmonicTree" in message
    assert "undertone" in message.lower()
    assert message != "math domain error"


def test_kwargs_still_reach_the_spectrum_handler():
    """The adapter forwards playback kwargs, so a tree is a normal playable.

    ``arp=True`` splits the audition into successive partials, so the events
    no longer all start at 0; the harmonics must be unchanged by it.
    """
    ht = HarmonicTree(root=2, children=(3, 5, 7))

    chord = convert_to_sc_events(ht)
    assert {e['start'] for e in chord} == {0}

    arped = convert_to_sc_events(ht, arp=True, dur=3.0)
    starts = sorted(e['start'] for e in arped)
    assert starts == pytest.approx([0.0, 1.0, 2.0])
    assert sorted(e['pfields']['freq'] for e in arped) == pytest.approx(
        [261.6256 * 6, 261.6256 * 10, 261.6256 * 14])
