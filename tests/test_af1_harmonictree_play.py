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


# ---------------------------------------------------------------------------
# AF-1b: the three holes the AF-1 verifier found still open.
#
#   1. Nothing guarded the TOP end once the real harmonics started sounding.
#   2. The core decision -- ``harmonics``, not ``ratios`` -- was unpinned:
#      mutating it passed all nine tests above.
#   3. Leaf ORDER did not survive to the payload, and nothing said whether
#      that was the contract or a bug.
#
# As above, every expected number is derived by hand from the spec.
# ---------------------------------------------------------------------------


def test_harmonics_not_ratios_are_what_sound():
    """AF-1b/M1. The adapter sounds ``harmonics``; ``ratios`` is a different set.

    This is the entire content of the AF-1 fix, and until now nothing stated
    it: every tree in the tests above was built WITHOUT an ``equave``, and
    ``_evaluate`` sets ``ratio = harmonic`` when ``equave is None``.  So the
    two attributes were numerically identical in every case and swapping them
    changed nothing.  A tree WITH an equave separates them.

    ``HarmonicTree(root=2, children=(3, 5, 7), equave=2)``:

    * harmonics -- product along each path -- are 2*3 = 6, 2*5 = 10, 2*7 = 14.
    * ratios are those reduced into one equave of 2, i.e. into ``[1, 2)``:
      6/4 = 3/2, 10/8 = 5/4, 14/8 = 7/4.

    Sounding the harmonics on C4 = 261.6256 Hz gives

        6  ->  261.6256 * 6  = 1569.7536 Hz
        10 ->  261.6256 * 10 = 2616.256  Hz
        14 ->  261.6256 * 14 = 3662.7584 Hz

    Sounding the ratios instead would give 261.6256 * 5/4 = 327.032,
    * 3/2 = 392.4384, * 7/4 = 457.8448 Hz -- an octave-collapsed chord in a
    completely different register.  Both are plausible-sounding audio; only
    one is the tree's harmonics.  (Which of the two an audition *should*
    sound is a live design question -- see the adapter's docstring -- so this
    test pins the answer the adapter actually gives, not a preference.)
    """
    ht = HarmonicTree(root=2, children=(3, 5, 7), equave=2)

    assert ht.harmonics == (6, 10, 14)
    assert [float(r) for r in ht.ratios] == [1.5, 1.25, 1.75]
    # Guard against this test quietly going vacuous if reduction changes.
    assert tuple(float(r) for r in ht.ratios) != tuple(float(h) for h in ht.harmonics)

    freqs = _lowered_freqs(ht)
    assert freqs == pytest.approx([1569.7536, 2616.256, 3662.7584])

    ratio_freqs = [C4_HZ * 1.25, C4_HZ * 1.5, C4_HZ * 1.75]
    assert ratio_freqs == pytest.approx([327.032, 392.4384, 457.8448])
    assert freqs != pytest.approx(ratio_freqs)
    # Every sounded partial is above the whole reduced chord: the registers
    # do not overlap, so no rounding tolerance can confuse the two.
    assert min(freqs) > max(ratio_freqs)


def test_duplicate_harmonics_each_sound():
    """AF-1b/M5. Repeated leaf harmonics are NOT collapsed to a set.

    Two leaves that arrive at the same harmonic are two partials at the same
    frequency, and two coincident partials are louder than one: the chord
    builder divides the target amplitude across the voices it is given, so
    dropping a duplicate changes the spectral weight, not just the event
    count.  The pinned contract one test up -- one event per leaf -- says the
    same thing from the other side.

    ``HarmonicTree(root=1, children=(2, 2, 3))`` has leaf harmonics 2, 2, 3,
    hence THREE partials: 261.6256 * 2 = 523.2512 Hz (twice) and
    261.6256 * 3 = 784.8768 Hz.  De-duplicating would give two.
    """
    ht = HarmonicTree(root=1, children=(2, 2, 3))
    assert ht.harmonics == (2, 2, 3)

    freqs = _lowered_freqs(ht)
    assert len(freqs) == 3
    assert len(set(ht.harmonics)) == 2, "the tree really does repeat a harmonic"
    assert freqs == pytest.approx([523.2512, 523.2512, 784.8768])


def test_audition_is_ordered_by_partial_not_by_leaf_order():
    """AF-1b/M4. The audition sounds ascending by partial. THIS IS THE CONTRACT.

    ``HarmonicTree(root=1, children=(7, 3, 5))`` has ``harmonics == (7, 3, 5)``
    in leaf order, and lowers to 3, 5, 7 ascending:

        3 -> 261.6256 * 3 = 784.8768 Hz
        5 -> 261.6256 * 5 = 1308.128  Hz
        7 -> 261.6256 * 7 = 1831.3792 Hz

    ``Spectrum._init_data`` sorts by partial, so the adapter's output is
    *invariant* under any permutation of the tree's leaves.  That is the
    contract, on both lenses of R12:

    * **The score.** An audition of a spectrum is a chord -- a stack of
      noteheads, which a stack is written low-to-high by construction.  There
      is no notation for "these noteheads, but in tree order".  ``arp=True``
      is the arpeggio squiggle, which rolls bottom-to-top; the top-to-bottom
      roll is the separate, explicit ``direction='d'``.  A score cannot mean
      "tree order", so a player cannot play it.
    * **The caller.** ``Spectrum`` -- the type this adapter builds, and the
      type any other route to spectrum playback goes through -- is already
      pitch-ordered and documented as such: ``Spectrum(Pitch('C4'),
      [7, 3, 5]).partials == (3, 5, 7)``.  A ``HarmonicTree`` that sounded in
      a different order from the ``Spectrum`` it auditions as would be the
      surprise.  And the ordering knob already exists and is explicit:
      ``direction``.

    The two lenses agree, so this is pinned rather than escalated.  The
    decisive reason is in the next test: leaf order is not authorial order.
    """
    ht = HarmonicTree(root=1, children=(7, 3, 5))
    assert ht.harmonics == (7, 3, 5), "leaf order is descending-ish, not sorted"

    assert _lowered_freqs(ht) == pytest.approx([784.8768, 1308.128, 1831.3792])

    # Same set of leaves in a different order -> byte-identical frequencies.
    permuted = HarmonicTree(root=1, children=(3, 7, 5))
    assert permuted.harmonics == (3, 7, 5)
    assert _lowered_freqs(permuted) == pytest.approx(_lowered_freqs(ht))

    # And with arp=True the ORDER IN TIME is ascending, not leaf order:
    # dur 3.0 over three partials puts them at 0, 1, 2 seconds.
    arped = convert_to_sc_events(ht, arp=True, dur=3.0)
    in_time = [(e['start'], e['pfields']['freq'])
               for e in sorted(arped, key=lambda e: e['start'])]
    assert [t for t, _ in in_time] == pytest.approx([0.0, 1.0, 2.0])
    assert [f for _, f in in_time] == pytest.approx(
        [784.8768, 1308.128, 1831.3792])

    # ``direction='d'`` is how a caller asks for the other order.
    down = convert_to_sc_events(ht, arp=True, dur=3.0, dir='d')
    assert [e['pfields']['freq']
            for e in sorted(down, key=lambda e: e['start'])] == pytest.approx(
        [1831.3792, 1308.128, 784.8768])


def test_leaf_order_is_not_authorial_order():
    """Why sorting is right: leaf order records id recycling, not intent.

    ``Tree.leaf_nodes`` walks the tree and ``successors`` yields children in
    *sorted node-id* order, while rustworkx recycles the ids of deleted nodes
    (the trap named in the project brief).  So a leaf APPENDED to a tree can
    land in the MIDDLE of ``harmonics``:

    * ``HarmonicTree(root=1, children=(3, 5, 7))`` -> harmonics ``(3, 5, 7)``
      on leaf nodes ``(1, 2, 3)``.
    * prune the middle leaf (node 2) -> harmonics ``(3, 7)``, leaves ``(1, 3)``.
    * ``add_child(root, factor=11)`` re-uses the freed id 2, so the NEW leaf
      sorts between the two survivors -> harmonics ``(3, 11, 7)``.

    Nothing the composer did was ordered "3, 11, 7".  Ordering an audition by
    that sequence would make what you hear depend on the tree's edit history,
    which is exactly the class of silent, plausible-sounding wrongness this
    file exists to close.  Ascending by partial is the only order available
    that means something.
    """
    ht = HarmonicTree(root=1, children=(3, 5, 7))
    assert ht.harmonics == (3, 5, 7)

    ht.prune(ht.leaf_nodes[1])
    assert ht.harmonics == (3, 7)

    ht.add_child(ht.root, factor=11)
    # The appended leaf is in the middle -- this is the whole point.
    assert ht.harmonics == (3, 11, 7)

    # The audition is unbothered: 3, 7, 11 ascending.
    #   3  -> 261.6256 * 3  = 784.8768  Hz
    #   7  -> 261.6256 * 7  = 1831.3792 Hz
    #   11 -> 261.6256 * 11 = 2877.8816 Hz
    assert _lowered_freqs(ht) == pytest.approx(
        [784.8768, 1831.3792, 2877.8816])


def test_ultrasonic_partials_warn_and_still_sound():
    """AF-1b/1. A partial above the audible ceiling is named, not silently sent.

    A ``HarmonicTree`` multiplies along the path, so its magnitudes are
    EMERGENT: nobody types 2310.  Chaining 2 -> 3 -> 5 -> 7 -> 11 gives a
    single leaf whose harmonic is 2*3*5*7*11 = 2310, i.e.

        261.6256 * 2310 = 604355.136 Hz

    which is not a sound.  Below the engine's Nyquist it would merely be
    inaudible; above it, it ALIASES -- an oscillator asked for 604 kHz at
    48 kHz sample rate folds back into the audible band as an unrelated
    pitch, which is a wrong note that sounds entirely plausible.  So the
    adapter warns and names the offending partials.  It does NOT refuse and
    does NOT clamp: this is a spectral tool and the frequency the composer
    asked for is still what gets sent.
    """
    ht = HarmonicTree(root=2, children=(3,))
    for factor in (5, 7, 11):
        ht.add_child(ht.leaf_nodes[0], factor=factor)
    assert ht.harmonics == (2310,)

    with pytest.warns(UserWarning) as record:
        freqs = _lowered_freqs(ht)

    message = str(record[0].message)
    assert "2310" in message, "the warning must name the offending partial"
    assert "604355" in message, "and the frequency it lands on"
    assert "HarmonicTree" in message

    # Still sounds, unclamped.
    assert freqs == pytest.approx([604355.136], rel=1e-6)


def test_audible_tree_does_not_warn():
    """The guard must not nag about a spectrum anyone can hear.

    ``HarmonicTree(root=2, children=(3, 5, 7))`` tops out at partial 14,
    i.e. 261.6256 * 14 = 3662.7584 Hz -- a fifth of the ceiling.
    """
    import warnings as _warnings

    ht = HarmonicTree(root=2, children=(3, 5, 7))
    with _warnings.catch_warnings():
        _warnings.simplefilter("error")
        freqs = _lowered_freqs(ht)
    assert max(freqs) == pytest.approx(3662.7584)


def test_ultrasonic_ceiling_is_20_khz_and_the_boundary_is_pinned():
    """The ceiling is 20 kHz, and which side of it a partial falls on matters.

    20 kHz is the nominal top of human hearing AND sits below the Nyquist
    frequency of every sample rate the engine can run at (22.05 kHz at
    44.1 k, 24 kHz at 48 k), so one threshold covers both failure modes:
    above it a partial is at best inaudible, and at worst folded.  The
    runtime sample rate is a property of the browser's AudioContext and is
    not known at lowering time, which is why the guard cannot key on Nyquist
    itself.

    On C4 the boundary falls between two integer partials:

        20000 / 261.6256 = 76.445...
        partial 76 -> 261.6256 * 76 = 19883.5456 Hz   (under -- silent guard)
        partial 77 -> 261.6256 * 77 = 20145.1712 Hz   (over  -- warns)
    """
    import warnings as _warnings

    from klotho.utils.playback import _converter_base

    # Behaviour first, so moving the constant fails on the SOUND rather than
    # on a restatement of the constant.
    under = HarmonicTree(root=1, children=(76,))
    assert under.harmonics == (76,)
    with _warnings.catch_warnings():
        _warnings.simplefilter("error")
        assert _lowered_freqs(under) == pytest.approx([19883.5456], rel=1e-6)

    over = HarmonicTree(root=1, children=(77,))
    assert over.harmonics == (77,)
    with pytest.warns(UserWarning, match="77"):
        assert _lowered_freqs(over) == pytest.approx([20145.1712], rel=1e-6)

    # ...and the constant that puts the boundary there.
    assert _converter_base.AUDIBLE_CEILING_HZ == 20000.0
