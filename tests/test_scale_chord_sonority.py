from fractions import Fraction

import pytest

from klotho.tonos.scales.scale import Scale
from klotho.tonos.chords.chord import Chord, Voicing
from klotho.tonos.pitch.pitch import Pitch


def test_scale_cyclic_indexing_ratios():
    scale = Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])
    assert scale[0] == Fraction(1, 1)
    assert scale[7] == Fraction(2, 1)
    assert scale[-1] == Fraction(15, 16)


def test_chord_cyclic_indexing_ratios():
    chord = Chord(["1/1", "5/4", "3/2"])
    assert chord[0] == Fraction(1, 1)
    assert chord[3] == Fraction(2, 1)
    assert chord[-1] == Fraction(3, 4)


def test_sonority_non_cyclic_indexing():
    voicing = Voicing(["1/2", "1/1", "3/2"])
    assert voicing[0] == Fraction(1, 2)
    with pytest.raises(IndexError):
        _ = voicing[3]


def test_scale_intervals_include_equave():
    scale = Scale(["1/1", "9/8", "5/4"])
    assert scale.intervals == [Fraction(9, 8), Fraction(10, 9), Fraction(8, 5)]


def test_chord_intervals_exclude_equave():
    chord = Chord(["1/1", "5/4", "3/2"])
    assert chord.intervals == [Fraction(5, 4), Fraction(6, 5)]


def test_sonority_intervals_exclude_equave():
    voicing = Voicing(["1/2", "1/1", "3/2"])
    assert voicing.intervals == [Fraction(2, 1), Fraction(3, 2)]


def test_scale_root_instancing_returns_pitches():
    scale = Scale(["1/1", "9/8", "5/4"])
    instanced = scale.root("C4")
    assert isinstance(instanced[0], Pitch)
    assert isinstance(instanced.degrees[0], Pitch)


def test_chord_root_instancing_returns_pitches():
    chord = Chord(["1/1", "5/4", "3/2"])
    instanced = chord.root("C4")
    assert isinstance(instanced[0], Pitch)
    assert isinstance(instanced.degrees[0], Pitch)
