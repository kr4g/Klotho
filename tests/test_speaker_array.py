"""SpeakerArray: labelled speaker geometry and its binaural coefficients.

Three things are pinned here, and each one is pinned because getting it wrong
is silent rather than loud.

**The numbering.**  A 6x4 grid can be labelled eight defensible ways.  The
Sonic Pavilion's rig is labelled column-major from the south-west corner --
speakers 1-4 are the west column running south to north, 21-24 the east
column -- and an off-by-one there puts a sound fifty feet from where it was
written, with nothing in the output to say so.  Every corner is asserted by
its foot coordinates, not by its index.

**The arithmetic.**  Distances and delays are checked against hand arithmetic
written out in the test, and against the three figures the venue is quoted by:
44.4 ms per column step, 53.3 ms per row step, 273.8 ms across the diagonal.

**The binaural model.**  The coefficients feed both the real-time decoder and
the offline fold, so a sign error in one ear is a defect that only shows up as
a preview that sounds subtly wrong.  ``_reference_ear_geometry`` below is an
independent re-derivation from the documented model (ITD from ear path
lengths, ILD from inverse distance, a one-pole cutoff interpolated by how much
further the far ear is), written from the formulas rather than from the
implementation, and every coefficient is compared against it to within one
ULP.  The symmetry a centred source must show is asserted exactly, because
that one is a property of the model rather than of the arithmetic.

Refusals are asserted by message content, not merely by exception type: a
``ValueError`` that says nothing useful is not the behaviour being specified.
"""

import math
from fractions import Fraction

import pytest

from klotho.thetos.spatial import (
    BINAURAL_FIELDS,
    BINAURAL_STRIDE,
    DECODER_MAX_DELAY_S,
    HEAD_HALF,
    HEAD_HALF_FT,
    SHADOW_HI_HZ,
    SHADOW_LO_HZ,
    SPEED_OF_SOUND,
    SpeakerArray,
)


# The venue: 6 columns 50 ft apart, 4 rows 60 ft apart, 250 x 180 ft overall.
PAV_KWARGS = dict(cols=6, rows=4, col_spacing=50.0, row_spacing=60.0,
                  name='PAVILION')


@pytest.fixture
def pav():
    return SpeakerArray.grid(**PAV_KWARGS)


@pytest.fixture
def tri():
    """Three speakers around the origin: one hard left, one dead ahead, one
    hard right.  The geometry a binaural model has to get obviously right."""
    return SpeakerArray.from_positions(
        {'L': (-10.0, 0.0), 'C': (0.0, 10.0), 'R': (10.0, 0.0)}, name='TRI')


def _reference_ear_geometry(positions, listener, half, speed, facing='north'):
    """An independent re-derivation of the binaural model.

    Written from the documented formulas, not from ``spatial.py``: ears at
    ``listener -/+ half`` on the x axis facing north (on the y axis facing
    east, north on the listener's left); delay is path length over the speed
    of sound; gain is the near ear's distance over this ear's; the shadow
    cutoff runs from ``SHADOW_HI_HZ`` at no extra path to ``SHADOW_LO_HZ``
    at one full head width of it.
    """
    lx, ly = listener
    if facing == 'north':
        ear_l, ear_r = (lx - half, ly), (lx + half, ly)
    else:
        ear_l, ear_r = (lx, ly + half), (lx, ly - half)
    rows = []
    for (x, y) in positions:
        d_l = math.sqrt((x - ear_l[0]) ** 2 + (y - ear_l[1]) ** 2)
        d_r = math.sqrt((x - ear_r[0]) ** 2 + (y - ear_r[1]) ** 2)
        near = min(d_l, d_r)
        a_l = min(1.0, max(0.0, (d_l - d_r) / (2.0 * half)))
        a_r = min(1.0, max(0.0, (d_r - d_l) / (2.0 * half)))
        rows.append((d_l / speed, d_r / speed, near / d_l, near / d_r,
                     SHADOW_HI_HZ + (SHADOW_LO_HZ - SHADOW_HI_HZ) * a_l,
                     SHADOW_HI_HZ + (SHADOW_LO_HZ - SHADOW_HI_HZ) * a_r))
    return rows


def _coeff_rows(c):
    """The same six-per-speaker shape ``_reference_ear_geometry`` returns,
    flattened, so the two can be compared in one assertion (``pytest.approx``
    does not descend into nested sequences)."""
    return [v for i in range(len(c))
            for v in (c.delay_l[i], c.delay_r[i], c.gain_l[i], c.gain_r[i],
                      c.shadow_l_hz[i], c.shadow_r_hz[i])]


def _flat(rows):
    return [v for row in rows for v in row]


class TestTheSharedModelConstants:
    """The parameters the live decoder and the offline fold both assume.

    Pinned by **literal value**, not by importing the constant and comparing
    it with itself.  These numbers are the model two separate renderers agree
    on; a test that reads them out of the module under test would pass while
    the head quietly grew an inch and every preview changed.  Found by
    mutation: raising SHADOW_LO_HZ to 1500 Hz left the whole suite green.
    """

    def test_the_head_is_seven_inches_across(self):
        assert HEAD_HALF_FT == 0.29
        assert HEAD_HALF['ft'] == 0.29

    def test_the_metric_head_is_the_same_head_converted(self):
        # 0.29 ft * 0.3048 m/ft = 0.088392 m
        assert HEAD_HALF['m'] == pytest.approx(0.29 * 0.3048, abs=5e-5)

    def test_the_shadow_runs_from_18_kilohertz_down_to_1400(self):
        assert SHADOW_HI_HZ == 18000.0
        assert SHADOW_LO_HZ == 1400.0

    def test_sound_travels_1125_feet_or_343_metres_a_second(self):
        assert SPEED_OF_SOUND['ft'] == 1125.0
        assert SPEED_OF_SOUND['m'] == 343.0

    def test_the_decoder_delay_line_is_half_a_second(self):
        # The venue diagonal is 0.274 s, so half a second leaves room for an
        # off-centre listener.
        assert DECODER_MAX_DELAY_S == 0.5


class TestPavilionNumbering:
    """Column-major from the south-west corner: label = col * rows + row + 1."""

    def test_speaker_1_is_the_south_west_corner(self, pav):
        assert pav.position(1) == (0.0, 0.0)

    def test_speaker_4_is_the_north_west_corner(self, pav):
        # column 0, row 3 -> (0 * 50, 3 * 60)
        assert pav.position(4) == (0.0, 180.0)

    def test_speakers_1_to_4_are_the_west_column_running_south_to_north(self, pav):
        assert [pav.position(s) for s in (1, 2, 3, 4)] == [
            (0.0, 0.0), (0.0, 60.0), (0.0, 120.0), (0.0, 180.0)]

    def test_speaker_5_begins_the_second_column(self, pav):
        assert pav.position(5) == (50.0, 0.0)

    def test_speakers_21_to_24_are_the_east_column(self, pav):
        assert [pav.position(s) for s in (21, 22, 23, 24)] == [
            (250.0, 0.0), (250.0, 60.0), (250.0, 120.0), (250.0, 180.0)]

    def test_the_label_formula_holds_for_every_speaker(self, pav):
        # label = col * 4 + row + 1, position = (col * 50, row * 60)
        for col in range(6):
            for row in range(4):
                assert pav.position(col * 4 + row + 1) == (col * 50.0, row * 60.0)

    def test_the_labels_run_1_to_24_in_lane_order(self, pav):
        assert pav.labels == tuple(range(1, 25))

    def test_lane_is_the_zero_based_offset_of_the_label(self, pav):
        assert pav.lane(1) == 0
        assert pav.lane(17) == 16
        assert pav.lane(24) == 23

    def test_lane_and_label_at_are_inverses(self, pav):
        for label in pav.labels:
            assert pav.label_at(pav.lane(label)) == label

    def test_row_major_numbers_along_rows_instead(self):
        arr = SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0,
                                row_spacing=60.0, numbering='row-major')
        assert arr.position(2) == (50.0, 0.0)     # next speaker is east
        assert arr.position(7) == (0.0, 60.0)     # row 1 starts back west
        assert arr.position(24) == (250.0, 180.0)

    def test_the_serpentine_numbering_reverses_alternate_columns(self):
        arr = SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0,
                                row_spacing=60.0,
                                numbering='column-major-serpentine')
        assert arr.position(4) == (0.0, 180.0)    # first column still runs up
        assert arr.position(5) == (50.0, 180.0)   # second column runs back down

    def test_first_label_zero_gives_a_rig_labelled_from_zero(self):
        arr = SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0,
                                row_spacing=60.0, first_label=0)
        assert arr.labels == tuple(range(24))
        assert arr.position(0) == (0.0, 0.0)
        assert arr.position(23) == (250.0, 180.0)

    def test_explicit_labels_follow_the_numbering_order(self):
        arr = SpeakerArray.grid(cols=2, rows=2, col_spacing=10.0,
                                row_spacing=20.0, labels=['A', 'B', 'C', 'D'])
        assert arr.position('A') == (0.0, 0.0)
        assert arr.position('B') == (0.0, 20.0)
        assert arr.position('C') == (10.0, 0.0)
        assert arr.position('D') == (10.0, 20.0)

    def test_the_origin_moves_the_whole_grid(self):
        arr = SpeakerArray.grid(cols=2, rows=2, col_spacing=10.0,
                                row_spacing=20.0, origin=(100.0, 5.0))
        assert arr.position(1) == (100.0, 5.0)
        assert arr.position(4) == (110.0, 25.0)

    def test_a_three_dimensional_origin_lifts_the_whole_plane(self):
        arr = SpeakerArray.grid(cols=2, rows=2, col_spacing=10.0,
                                row_spacing=20.0, origin=(0.0, 0.0, 14.0))
        assert arr.dimension == 3
        assert arr.position(4) == (10.0, 20.0, 14.0)

    def test_the_grid_shape_and_numbering_are_recorded(self, pav):
        assert pav.grid_shape == (6, 4)
        assert pav.numbering == 'column-major'

    def test_an_array_from_positions_records_no_grid(self, tri):
        assert tri.grid_shape is None and tri.numbering is None


class TestGeometry:
    """Distances and delays, against arithmetic written out here."""

    def test_a_column_step_is_50_feet(self, pav):
        assert pav.distance(1, 5) == 50.0

    def test_a_column_step_is_44_point_4_milliseconds(self, pav):
        # 50 ft / 1125 ft/s = 0.0444444... s
        assert pav.delay(1, 5) == pytest.approx(50.0 / 1125.0)
        assert pav.delay(1, 5) * 1000.0 == pytest.approx(44.44, abs=0.01)

    def test_a_row_step_is_60_feet_and_53_point_3_milliseconds(self, pav):
        assert pav.distance(1, 2) == 60.0
        # 60 / 1125 = 0.0533333... s
        assert pav.delay(1, 2) == pytest.approx(60.0 / 1125.0)
        assert pav.delay(1, 2) * 1000.0 == pytest.approx(53.33, abs=0.01)

    def test_the_diagonal_is_308_feet(self, pav):
        # speaker 1 (0, 0) to speaker 24 (250, 180):
        #   sqrt(250^2 + 180^2) = sqrt(62500 + 32400) = sqrt(94900)
        #                       = 308.05843601498725
        assert pav.distance(1, 24) == pytest.approx(math.sqrt(94900.0), rel=0, abs=0)
        assert pav.distance(1, 24) == pytest.approx(308.058436, abs=1e-6)

    def test_the_diagonal_is_273_point_8_milliseconds(self, pav):
        # 308.05843601498725 / 1125 = 0.27382972090221093 s
        assert pav.delay(1, 24) == pytest.approx(0.273829720902, abs=1e-12)
        assert pav.delay(1, 24) * 1000.0 == pytest.approx(273.8, abs=0.05)

    def test_the_other_diagonal_is_the_same_length(self, pav):
        assert pav.distance(4, 21) == pytest.approx(pav.distance(1, 24))

    def test_distance_is_symmetric(self, pav):
        assert pav.distance(3, 19) == pav.distance(19, 3)

    def test_the_centroid_is_the_middle_of_the_field(self, pav):
        # x: 4 speakers at each of 0, 50, 100, 150, 200, 250 -> 750 * 4 / 24
        # y: 6 speakers at each of 0, 60, 120, 180        -> 360 * 6 / 24
        assert pav.centroid == (125.0, 90.0)
        assert pav.centre == pav.centroid

    def test_a_raw_point_can_stand_in_for_a_speaker(self, pav):
        assert pav.distance(1, (0.0, 90.0)) == 90.0
        assert pav.delay((0.0, 0.0), (0.0, 90.0)) == pytest.approx(90.0 / 1125.0)

    def test_none_means_the_centroid(self, pav):
        assert pav.distance(1, None) == pytest.approx(math.hypot(125.0, 90.0))

    def test_listener_distances_are_one_per_speaker_in_lane_order(self, pav):
        got = pav.distances((0.0, 0.0))
        assert len(got) == 24
        assert got[0] == 0.0                       # lane 0 is speaker 1
        assert got[23] == pytest.approx(math.sqrt(94900.0))

    def test_listener_delays_agree_with_the_pairwise_delay(self, pav):
        got = pav.delays((60.0, 90.0))
        for lane, label in enumerate(pav.labels):
            assert got[lane] == pav.delay(label, (60.0, 90.0))

    def test_listener_delays_default_to_the_centroid(self, pav):
        assert pav.delays() == pav.delays((125.0, 90.0))

    def test_the_speed_of_sound_divides_the_delay(self):
        fast = SpeakerArray.grid(cols=2, rows=1, col_spacing=100.0,
                                 row_spacing=1.0, speed_of_sound=2250.0)
        assert fast.distance(1, 2) == 100.0
        assert fast.delay(1, 2) == pytest.approx(100.0 / 2250.0)

    def test_metres_carry_their_own_default_speed(self):
        arr = SpeakerArray.grid(cols=2, rows=1, col_spacing=10.0,
                                row_spacing=1.0, units='m')
        assert arr.speed_of_sound == SPEED_OF_SOUND['m'] == 343.0
        assert arr.delay(1, 2) == pytest.approx(10.0 / 343.0)

    def test_three_dimensional_distance_uses_every_axis(self):
        arr = SpeakerArray.from_positions({'a': (0.0, 0.0, 0.0),
                                           'b': (3.0, 4.0, 12.0)})
        # 3-4-12 is a Pythagorean quadruple: sqrt(9 + 16 + 144) = 13
        assert arr.distance('a', 'b') == 13.0


class TestBinauralCoefficients:
    """ITD, ILD and a one-pole head shadow -- the numbers both decoders read."""

    def test_a_speaker_dead_ahead_is_exactly_symmetric(self, tri):
        c = tri.binaural_coefficients((0.0, 0.0))
        i = c.labels.index('C')
        assert c.delay_l[i] == c.delay_r[i]
        assert c.gain_l[i] == c.gain_r[i] == 1.0
        assert c.shadow_l_hz[i] == c.shadow_r_hz[i] == SHADOW_HI_HZ

    def test_a_speaker_hard_left_reaches_the_left_ear_first(self, tri):
        c = tri.binaural_coefficients((0.0, 0.0))
        i = c.labels.index('L')
        assert c.delay_l[i] < c.delay_r[i]
        assert c.gain_l[i] > c.gain_r[i]

    def test_a_speaker_hard_right_reaches_the_right_ear_first(self, tri):
        c = tri.binaural_coefficients((0.0, 0.0))
        i = c.labels.index('R')
        assert c.delay_r[i] < c.delay_l[i]
        assert c.gain_r[i] > c.gain_l[i]

    def test_the_near_ear_gain_is_exactly_one(self, tri):
        c = tri.binaural_coefficients((0.0, 0.0))
        for i, label in enumerate(c.labels):
            assert max(c.gain_l[i], c.gain_r[i]) == 1.0

    def test_the_hard_left_delays_are_the_hand_computed_path_lengths(self, tri):
        # ears at x = -0.29 and +0.29; speaker L at x = -10.
        #   left  ear: 10 - 0.29 =  9.71 ft ->  9.71 / 1125 = 0.00863111... s
        #   right ear: 10 + 0.29 = 10.29 ft -> 10.29 / 1125 = 0.00914666... s
        c = tri.binaural_coefficients((0.0, 0.0))
        i = c.labels.index('L')
        assert c.delay_l[i] == pytest.approx(9.71 / 1125.0, abs=1e-15)
        assert c.delay_r[i] == pytest.approx(10.29 / 1125.0, abs=1e-15)

    def test_the_hard_left_far_ear_gain_is_the_distance_ratio(self, tri):
        # inverse distance, normalized to the near ear: 9.71 / 10.29
        c = tri.binaural_coefficients((0.0, 0.0))
        i = c.labels.index('L')
        assert c.gain_r[i] == pytest.approx(9.71 / 10.29, abs=1e-12)

    def test_the_far_ear_is_fully_shadowed_on_the_interaural_axis(self, tri):
        # A source straight to one side is exactly one head width further
        # from the far ear (2 * 0.29 ft), which is full shadow.
        c = tri.binaural_coefficients((0.0, 0.0))
        i = c.labels.index('L')
        assert c.shadow_l_hz[i] == SHADOW_HI_HZ
        assert c.shadow_r_hz[i] == pytest.approx(SHADOW_LO_HZ, abs=1e-6)

    def test_the_shadow_never_falls_below_the_floor(self, pav):
        c = pav.binaural_coefficients()
        assert min(c.shadow_l_hz) >= SHADOW_LO_HZ - 1e-6
        assert max(c.shadow_r_hz) <= SHADOW_HI_HZ

    def test_every_coefficient_matches_an_independent_derivation(self, pav):
        # rel=1e-12 rather than exact equality: the reference above spells the
        # distance out as sqrt(dx^2 + dy^2) while the implementation calls
        # math.dist, which is more careful about overflow and lands one ULP
        # away. Any sign error, swapped ear or wrong axis is many orders of
        # magnitude larger than that.
        assert _coeff_rows(pav.binaural_coefficients()) == pytest.approx(
            _flat(_reference_ear_geometry(pav.positions, pav.centroid,
                                          HEAD_HALF_FT, pav.speed_of_sound)),
            rel=1e-12)

    def test_the_derivation_also_matches_off_centre(self, pav):
        listener = (60.0, 30.0)
        assert _coeff_rows(pav.binaural_coefficients(listener)) == \
            pytest.approx(_flat(_reference_ear_geometry(
                pav.positions, listener, HEAD_HALF_FT, pav.speed_of_sound)),
                rel=1e-12)

    def test_facing_east_puts_north_on_the_listeners_left(self, pav):
        assert _coeff_rows(pav.binaural_coefficients(facing='east')) == \
            pytest.approx(_flat(_reference_ear_geometry(
                pav.positions, pav.centroid, HEAD_HALF_FT,
                pav.speed_of_sound, facing='east')), rel=1e-12)

    def test_facing_east_hears_a_northern_speaker_on_the_left(self, pav):
        # Speaker 4 is the north-west corner; facing east, north is left.
        c = pav.binaural_coefficients(facing='east')
        i = c.labels.index(4)
        assert c.delay_l[i] < c.delay_r[i]

    def test_facing_north_hears_the_same_speaker_on_the_left_too(self, pav):
        # Speaker 4 is also to the WEST, so facing north it is still left --
        # the two facings must disagree somewhere else to be meaningful.
        c_n = pav.binaural_coefficients(facing='north')
        c_e = pav.binaural_coefficients(facing='east')
        assert c_n.gain_l != c_e.gain_l

    def test_the_listener_defaults_to_the_centroid(self, pav):
        assert pav.binaural_coefficients().listener == (125.0, 90.0)

    def test_a_label_can_name_the_listening_position(self, pav):
        c = pav.binaural_coefficients(13)
        assert c.listener == pav.position(13)

    def test_a_sample_rate_gives_integer_sample_offsets(self, pav):
        seconds = pav.binaural_coefficients()
        samples = pav.binaural_coefficients(sample_rate=48000)
        assert samples.sample_rate == 48000
        for i in range(len(pav)):
            assert samples.delay_l[i] == int(round(seconds.delay_l[i] * 48000))
            assert samples.delay_r[i] == int(round(seconds.delay_r[i] * 48000))
            assert isinstance(samples.delay_l[i], int)

    def test_the_gains_and_cutoffs_ignore_the_sample_rate(self, pav):
        # Both ears of both, not one of each: an earlier version of this test
        # checked gain_l and shadow_r_hz only, and a mutation that scaled
        # shadow_l_hz by the sample rate walked straight through it.
        a = pav.binaural_coefficients()
        b = pav.binaural_coefficients(sample_rate=44100)
        assert a.gain_l == b.gain_l
        assert a.gain_r == b.gain_r
        assert a.shadow_l_hz == b.shadow_l_hz
        assert a.shadow_r_hz == b.shadow_r_hz

    def test_a_wider_head_widens_the_time_difference(self, tri):
        narrow = tri.binaural_coefficients((0.0, 0.0), head_half=0.10)
        wide = tri.binaural_coefficients((0.0, 0.0), head_half=0.50)
        i = narrow.labels.index('L')
        assert (wide.delay_r[i] - wide.delay_l[i]) > \
               (narrow.delay_r[i] - narrow.delay_l[i])

    def test_a_three_dimensional_array_folds_without_complaint(self):
        arr = SpeakerArray.from_positions({'lo': (0.0, 10.0, 0.0),
                                           'hi': (0.0, 10.0, 20.0)})
        c = arr.binaural_coefficients((0.0, 0.0, 0.0))
        # Both are dead ahead in x, so both are symmetric; the higher one is
        # further away and therefore later.
        assert c.delay_l[0] == c.delay_r[0]
        assert c.delay_l[1] > c.delay_l[0]

    def test_max_delay_passes_when_the_array_fits(self, pav):
        assert pav.binaural_coefficients(max_delay=0.5) is not None


class TestTheFlatBufferLayout:
    """A decoder indexes this by hand, so the stride and field order are API."""

    def test_the_stride_is_six_fields_per_speaker(self):
        assert BINAURAL_STRIDE == 6
        assert BINAURAL_FIELDS == ('delay_l', 'delay_r', 'gain_l', 'gain_r',
                                   'shadow_l_hz', 'shadow_r_hz')

    def test_the_buffer_is_six_floats_per_speaker(self, pav):
        assert len(pav.binaural_coefficients().flat()) == 6 * 24

    def test_lane_times_six_plus_field_addresses_every_coefficient(self, pav):
        c = pav.binaural_coefficients()
        flat = c.flat()
        for lane in range(len(pav)):
            base = lane * BINAURAL_STRIDE
            assert flat[base + 0] == c.delay_l[lane]
            assert flat[base + 1] == c.delay_r[lane]
            assert flat[base + 2] == c.gain_l[lane]
            assert flat[base + 3] == c.gain_r[lane]
            assert flat[base + 4] == c.shadow_l_hz[lane]
            assert flat[base + 5] == c.shadow_r_hz[lane]

    def test_the_layout_is_lane_major_not_field_major(self, pav):
        # Field-major would put speaker 2's delay at index 1; lane-major puts
        # speaker 1's delay_r there. The two only differ by this.
        c = pav.binaural_coefficients()
        assert c.flat()[1] == c.delay_r[0]
        assert c.flat()[BINAURAL_STRIDE] == c.delay_l[1]

    def test_the_flat_values_are_all_floats(self, pav):
        flat = pav.binaural_coefficients(sample_rate=48000).flat()
        assert all(isinstance(v, float) for v in flat)

    def test_the_labels_say_which_lane_is_which_speaker(self, pav):
        c = pav.binaural_coefficients()
        assert c.labels == pav.labels
        assert len(c) == 24

    def test_max_delay_reports_the_worst_ear(self):
        # Asserted against a hand value on a deliberately LOPSIDED array: on
        # the symmetric Pavilion the two ears' maxima are equal, so comparing
        # max_delay() with max(delay_l) would pass even if it only ever
        # looked at one ear. (Found by mutation; that is what it used to do.)
        arr = SpeakerArray.from_positions({'L': (-10.0, 0.0)})
        c = arr.binaural_coefficients((0.0, 0.0))
        assert c.delay_r[0] > c.delay_l[0]        # far ear is the right one
        assert c.max_delay() == c.delay_r[0]
        assert c.max_delay() == pytest.approx(10.29 / 1125.0, abs=1e-15)


class TestOrderings:
    """What a composer reaches for when writing a sweep."""

    def test_the_serpentine_snakes_up_and_down_the_columns(self, pav):
        assert pav.serpentine() == (
            1, 2, 3, 4, 8, 7, 6, 5, 9, 10, 11, 12,
            16, 15, 14, 13, 17, 18, 19, 20, 24, 23, 22, 21)

    def test_the_serpentine_visits_every_speaker_exactly_once(self, pav):
        order = pav.serpentine()
        assert sorted(order) == list(pav.labels)

    def test_no_serpentine_step_jumps_across_the_field(self, pav):
        # The point of a snake: consecutive steps are adjacent, so the
        # longest hop is one diagonal cell (sqrt(50^2 + 60^2) = 78.1 ft).
        order = pav.serpentine()
        hops = [pav.distance(a, b) for a, b in zip(order, order[1:])]
        assert max(hops) <= math.hypot(50.0, 60.0) + 1e-9

    def test_starting_north_east_reverses_both_axes(self, pav):
        assert pav.serpentine(start='ne')[:4] == (24, 23, 22, 21)

    def test_reverse_walks_the_whole_path_backwards(self, pav):
        assert pav.serpentine(reverse=True) == tuple(reversed(pav.serpentine()))

    def test_a_row_serpentine_runs_west_to_east_first(self, pav):
        # Row 0 is the south row: speakers 1, 5, 9, 13, 17, 21.
        assert pav.serpentine(axis='row')[:6] == (1, 5, 9, 13, 17, 21)

    def test_a_row_serpentine_comes_back_east_to_west(self, pav):
        assert pav.serpentine(axis='row')[6:12] == (22, 18, 14, 10, 6, 2)

    def test_axis_order_sweeps_south_to_north(self, pav):
        # y = 0 first (the whole south row), then y = 60, and so on.
        assert pav.axis_order('y')[:6] == (1, 5, 9, 13, 17, 21)
        assert pav.axis_order('y')[-6:] == (4, 8, 12, 16, 20, 24)

    def test_axis_order_sweeps_west_to_east(self, pav):
        assert pav.axis_order('x')[:4] == (1, 2, 3, 4)
        assert pav.axis_order('x')[-4:] == (21, 22, 23, 24)

    def test_reverse_sweeps_the_other_way(self, pav):
        assert pav.axis_order('y', reverse=True) == \
               tuple(reversed(pav.axis_order('y')))

    def test_axis_order_accepts_an_index(self, pav):
        assert pav.axis_order(1) == pav.axis_order('y')

    def test_axis_order_works_without_a_grid(self, tri):
        assert tri.axis_order('x') == ('L', 'C', 'R')


class TestValueSemantics:
    """Immutable, iterable, len()-able, equal by value."""

    def test_len_is_the_speaker_count(self, pav):
        assert len(pav) == 24

    def test_iteration_yields_labels(self, pav):
        assert list(pav) == list(range(1, 25))

    def test_containment_tests_labels(self, pav):
        assert 17 in pav
        assert 25 not in pav
        assert 'FL' not in pav

    def test_a_subscript_is_a_label_not_a_lane(self, pav):
        assert pav[1] == (0.0, 0.0)          # speaker 1, which is lane 0
        with pytest.raises(ValueError):
            pav[0]                            # there is no speaker 0

    def test_items_pairs_labels_with_positions(self, pav):
        assert list(pav.items())[:2] == [(1, (0.0, 0.0)), (2, (0.0, 60.0))]

    def test_two_identically_built_arrays_are_equal(self):
        assert SpeakerArray.grid(**PAV_KWARGS) == SpeakerArray.grid(**PAV_KWARGS)

    def test_a_different_name_is_a_different_value(self):
        a = SpeakerArray.grid(cols=2, rows=1, col_spacing=1.0, row_spacing=1.0)
        b = SpeakerArray.grid(cols=2, rows=1, col_spacing=1.0, row_spacing=1.0,
                              name='B')
        assert a != b

    def test_a_different_spacing_is_a_different_value(self):
        a = SpeakerArray.grid(cols=2, rows=1, col_spacing=1.0, row_spacing=1.0)
        b = SpeakerArray.grid(cols=2, rows=1, col_spacing=2.0, row_spacing=1.0)
        assert a != b

    def test_a_grid_is_not_equal_to_the_same_points_without_the_grid(self):
        # Equality has to include the grid provenance, because a grid array
        # answers serpentine() and one built from positions refuses it. Two
        # values that compare equal but behave differently is exactly the
        # surprise the programmer's lens forbids.
        grid = SpeakerArray.grid(cols=2, rows=2, col_spacing=1.0,
                                 row_spacing=1.0)
        loose = SpeakerArray.from_positions(list(grid.items()))
        assert grid.positions == loose.positions and grid.labels == loose.labels
        assert grid != loose
        assert grid.serpentine() is not None
        with pytest.raises(ValueError, match='needs a grid'):
            loose.serpentine()

    def test_two_grids_numbered_differently_are_different_values(self):
        a = SpeakerArray.grid(cols=2, rows=2, col_spacing=1.0, row_spacing=1.0)
        b = SpeakerArray.grid(cols=2, rows=2, col_spacing=1.0, row_spacing=1.0,
                              numbering='column-major-serpentine')
        assert a != b

    def test_arrays_are_hashable_and_usable_as_keys(self):
        a = SpeakerArray.grid(**PAV_KWARGS)
        b = SpeakerArray.grid(**PAV_KWARGS)
        assert hash(a) == hash(b)
        assert {a: 'pavilion'}[b] == 'pavilion'

    def test_comparison_with_a_non_array_is_false_not_an_error(self, pav):
        assert (pav == 24) is False

    def test_positions_are_floats_even_when_given_as_ints(self):
        arr = SpeakerArray.from_positions({1: (0, 0), 2: (3, 4)})
        assert arr.positions == ((0.0, 0.0), (3.0, 4.0))
        assert all(isinstance(v, float) for p in arr.positions for v in p)

    def test_a_fraction_position_is_converted_once_at_construction(self):
        # The module docstring promises this: exact input is welcome, but it
        # becomes float immediately, because the first distance() would make
        # it irrational anyway.
        arr = SpeakerArray.from_positions({1: (Fraction(1, 2), Fraction(0))})
        assert arr.position(1) == (0.5, 0.0)
        assert all(isinstance(v, float) for v in arr.position(1))

    def test_an_array_cannot_be_mutated(self, pav):
        with pytest.raises(AttributeError, match='immutable'):
            pav._speed = 1.0

    def test_an_attribute_cannot_be_deleted(self, pav):
        with pytest.raises(AttributeError, match='immutable'):
            del pav._labels

    def test_the_repr_names_the_array_its_size_and_its_grid(self, pav):
        text = repr(pav)
        assert "name='PAVILION'" in text
        assert 'speakers=24' in text
        assert '6x4 column-major' in text
        assert "units='ft'" in text
        assert '1125.0' in text

    def test_the_repr_of_an_unnamed_array_omits_the_name(self, tri):
        assert 'name=' not in repr(SpeakerArray.from_positions({1: (0.0, 0.0)}))

    def test_a_mapping_and_a_pair_list_build_the_same_array(self):
        a = SpeakerArray.from_positions({1: (0.0, 0.0), 2: (1.0, 0.0)})
        b = SpeakerArray.from_positions([(1, (0.0, 0.0)), (2, (1.0, 0.0))])
        assert a == b

    def test_string_labels_work_for_arrays_that_are_not_grids(self, tri):
        assert tri.labels == ('L', 'C', 'R')
        assert tri.lane('C') == 1


class TestRefusals:
    """Ruling Nine: refuse rather than guess, and say what to do instead."""

    def test_a_bare_speaker_count_is_ambiguous(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray(24)
        assert 'ambiguous' in str(e.value)
        assert '0..n-1 or 1..n' in str(e.value)
        assert 'SpeakerArray.grid' in str(e.value)

    def test_an_empty_array_is_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray({})
        assert 'at least one speaker' in str(e.value)
        assert 'from_positions' in str(e.value)

    def test_a_duplicate_label_is_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray([(1, (0.0, 0.0)), (1, (5.0, 0.0))])
        assert 'appears twice' in str(e.value)
        assert '1' in str(e.value)

    def test_mixed_dimensions_are_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray({1: (0.0, 0.0), 2: (0.0, 0.0, 3.0)})
        assert '3 coordinates' in str(e.value) and '2' in str(e.value)
        assert 'z=0.0' in str(e.value)

    def test_a_four_dimensional_position_is_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray({1: (0.0, 0.0, 0.0, 0.0)})
        assert '1-D, 2-D or 3-D' in str(e.value)

    def test_a_zero_speed_of_sound_is_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray({1: (0.0, 0.0)}, speed_of_sound=0.0)
        assert 'must be positive' in str(e.value)
        assert '1125.0 ft/s' in str(e.value)

    def test_a_negative_speed_of_sound_is_refused(self):
        with pytest.raises(ValueError, match='must be positive'):
            SpeakerArray({1: (0.0, 0.0)}, speed_of_sound=-1125.0)

    def test_an_unknown_unit_needs_an_explicit_speed(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray({1: (0.0, 0.0)}, units='cubits')
        assert 'no default speed of sound' in str(e.value)
        assert 'cubits per second' in str(e.value)

    def test_an_unknown_unit_with_a_speed_is_accepted(self):
        arr = SpeakerArray({1: (0.0, 0.0), 2: (2.0, 0.0)},
                           units='cubits', speed_of_sound=750.0)
        assert arr.delay(1, 2) == pytest.approx(2.0 / 750.0)

    def test_a_float_label_is_refused(self):
        with pytest.raises(TypeError) as e:
            SpeakerArray({1.5: (0.0, 0.0)})
        assert 'must be an int or a str' in str(e.value)

    def test_a_boolean_label_is_refused(self):
        # True is an int in Python and would silently collide with speaker 1.
        with pytest.raises(TypeError, match='must be an int or a str'):
            SpeakerArray({True: (0.0, 0.0)})

    def test_a_scalar_position_is_refused(self):
        with pytest.raises(TypeError) as e:
            SpeakerArray({1: 5.0})
        assert 'sequence of coordinates' in str(e.value)

    def test_an_unknown_label_names_the_valid_labels(self, tri):
        with pytest.raises(ValueError) as e:
            tri.position('X')
        assert "no speaker labelled 'X'" in str(e.value)
        assert "array 'TRI'" in str(e.value)
        assert "'L', 'C', 'R'" in str(e.value)
        assert 'not by a 0-based index' in str(e.value)

    def test_a_long_label_list_is_truncated_in_the_message(self, pav):
        with pytest.raises(ValueError) as e:
            pav.position(25)
        text = str(e.value)
        assert 'no speaker labelled 25' in text
        assert "array 'PAVILION'" in text
        assert '24 in all' in text
        assert '13' not in text            # the middle is elided, not listed

    def test_an_unhashable_label_is_refused_not_crashed_on(self, pav):
        with pytest.raises(ValueError, match='no speaker labelled'):
            pav.position(['not', 'a', 'label'])

    def test_a_lane_outside_the_array_is_refused(self, pav):
        with pytest.raises(IndexError) as e:
            pav.label_at(24)
        assert 'outside 0..23' in str(e.value)

    def test_a_negative_lane_is_refused_not_wrapped(self, pav):
        with pytest.raises(IndexError, match='outside 0..23'):
            pav.label_at(-1)

    def test_a_listener_of_the_wrong_dimension_is_refused(self, pav):
        with pytest.raises(ValueError) as e:
            pav.binaural_coefficients((1.0, 2.0, 3.0))
        assert '3 coordinates' in str(e.value)
        assert '2-D' in str(e.value)

    def test_a_two_dimensional_point_in_a_three_dimensional_array_is_refused(self):
        arr = SpeakerArray.from_positions({1: (0.0, 0.0, 0.0)})
        with pytest.raises(ValueError) as e:
            arr.distances((1.0, 2.0))
        assert '2 coordinates' in str(e.value) and '3-D' in str(e.value)

    def test_an_ear_landing_on_a_speaker_is_refused(self, pav):
        # Speaker 1 is at (0, 0) and the left ear sits at x - 0.29, so a
        # listener at x = 0.29 puts that ear exactly on the cone.
        with pytest.raises(ValueError) as e:
            pav.binaural_coefficients((HEAD_HALF_FT, 0.0))
        assert 'lands exactly on speaker 1' in str(e.value)
        assert 'undefined at zero distance' in str(e.value)
        assert 'head_half' in str(e.value)

    def test_a_listener_at_a_speaker_is_fine_the_ears_are_offset(self, pav):
        # Standing AT a speaker is odd but well defined: the ears are still
        # 0.29 ft away on either side. Refusing it would be over-reach.
        c = pav.binaural_coefficients((0.0, 0.0))
        assert c.gain_l[0] == 1.0 and c.gain_r[0] == 1.0

    def test_an_unknown_numbering_lists_the_conventions(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray.grid(cols=2, rows=2, col_spacing=1.0, row_spacing=1.0,
                              numbering='boustrophedon')
        assert 'unknown numbering' in str(e.value)
        assert "'column-major'" in str(e.value)
        assert "'row-major-serpentine'" in str(e.value)

    def test_a_grid_with_no_columns_is_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray.grid(cols=0, rows=4, col_spacing=1.0, row_spacing=1.0)
        assert 'at least one column and one row' in str(e.value)

    def test_a_zero_spacing_is_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray.grid(cols=2, rows=2, col_spacing=0.0, row_spacing=1.0)
        assert 'must both be positive' in str(e.value)
        assert 'on top of each other' in str(e.value)

    def test_a_negative_spacing_is_refused_with_the_remedy(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray.grid(cols=2, rows=2, col_spacing=-50.0, row_spacing=1.0)
        assert 'origin=' in str(e.value) and 'numbering=' in str(e.value)

    def test_labels_and_first_label_together_are_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray.grid(cols=2, rows=1, col_spacing=1.0, row_spacing=1.0,
                              labels=['A', 'B'], first_label=0)
        assert 'not both' in str(e.value)

    def test_the_wrong_number_of_labels_is_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray.grid(cols=6, rows=4, col_spacing=1.0, row_spacing=1.0,
                              labels=['A', 'B'])
        assert '2 entries' in str(e.value) and '24 speakers' in str(e.value)

    def test_a_one_dimensional_origin_is_refused(self):
        with pytest.raises(ValueError) as e:
            SpeakerArray.grid(cols=2, rows=2, col_spacing=1.0, row_spacing=1.0,
                              origin=(0.0,))
        assert 'a grid is a plane' in str(e.value)

    def test_an_unknown_facing_lists_the_facings(self, pav):
        with pytest.raises(ValueError) as e:
            pav.binaural_coefficients(facing='up')
        assert "facing='up'" in str(e.value)
        assert "'north'" in str(e.value) and "'east'" in str(e.value)

    def test_a_zero_head_is_refused(self, pav):
        with pytest.raises(ValueError) as e:
            pav.binaural_coefficients(head_half=0.0)
        assert 'must be positive' in str(e.value)
        assert 'no binaural image' in str(e.value)

    def test_an_exotic_unit_needs_an_explicit_head_size(self):
        arr = SpeakerArray({1: (0.0, 10.0)}, units='cubits',
                           speed_of_sound=750.0)
        with pytest.raises(ValueError) as e:
            arr.binaural_coefficients((0.0, 0.0))
        assert 'no default head size' in str(e.value)
        assert 'head_half=' in str(e.value)

    def test_facing_east_needs_a_second_axis(self):
        line = SpeakerArray.from_positions({1: (0.0,), 2: (10.0,)})
        with pytest.raises(ValueError) as e:
            line.binaural_coefficients((5.0,), facing='east')
        assert 'needs a y axis' in str(e.value)
        assert '1-D' in str(e.value)

    def test_a_delay_past_the_decoder_line_is_refused(self, pav):
        # From (0, 0) the far corner is 308 ft away: 0.27 s, well inside the
        # real 0.5 s line -- so squeeze the limit to pin the message.
        with pytest.raises(ValueError) as e:
            pav.binaural_coefficients((10.0, 10.0), max_delay=0.05)
        assert 'furthest speaker' in str(e.value)
        assert "array 'PAVILION'" in str(e.value)
        assert '0.05 s delay line' in str(e.value)
        assert 'fold this one offline' in str(e.value)

    def test_the_refusal_names_the_offending_speaker(self, pav):
        with pytest.raises(ValueError) as e:
            pav.binaural_coefficients((0.0, 0.0), max_delay=0.05)
        assert '(24)' in str(e.value)      # the far corner from (0, 0)

    def test_serpentine_needs_a_grid(self, tri):
        with pytest.raises(ValueError) as e:
            tri.serpentine()
        assert 'needs a grid' in str(e.value)
        assert "array 'TRI'" in str(e.value)
        assert "axis_order('x')" in str(e.value)

    def test_an_unknown_serpentine_axis_is_refused(self, pav):
        with pytest.raises(ValueError) as e:
            pav.serpentine(axis='diagonal')
        assert "'column'" in str(e.value) and "'row'" in str(e.value)

    def test_an_unknown_start_corner_lists_the_corners(self, pav):
        with pytest.raises(ValueError) as e:
            pav.serpentine(start='ws')
        assert "'sw'" in str(e.value) and "'ne'" in str(e.value)

    def test_an_unknown_axis_name_is_refused(self, pav):
        with pytest.raises(ValueError) as e:
            pav.axis_order('w')
        assert "'x', 'y', 'z'" in str(e.value)

    def test_an_axis_the_array_does_not_have_is_refused(self, pav):
        with pytest.raises(ValueError) as e:
            pav.axis_order('z')
        assert '2-D' in str(e.value)
        assert 'x, y' in str(e.value)
