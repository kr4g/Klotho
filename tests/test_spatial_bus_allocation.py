"""Private audio-bus allocation: the shared cursor, and the budget it draws on.

Multichannel output gives a track one bus channel per speaker, so allocations
stop being uniformly two channels wide. The property that has to survive that
is the one this file exists to pin: ``_allocAudioBus()`` and
``_allocAudioBusN(width)`` step ONE page-global cursor
(``globalThis.__klothoBusAlloc``), so a stereo track and a 24-wide spatial
track can never be handed overlapping ranges. An overlap is not a crash --
it is two unrelated voices silently summing into each other.

These are BEHAVIORAL tests: ``tests/fixtures/spatial_bus_alloc_probe.mjs``
loads the real ``scheduler_core.js`` / ``scheduler_score.js`` into a Node vm
sandbox and drives the allocator, in the style of
``test_recording.test_stems_taps_survive_page_state``. Disjointness is proved
by comparing every pair of ranges, never by reading a sequence.
"""
import json
import shutil
import subprocess
from itertools import combinations
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_SS_DIR = _ROOT / "klotho" / "utils" / "playback" / "supersonic"
_PROBE = Path(__file__).parent / "fixtures" / "spatial_bus_alloc_probe.mjs"

SCORE_SRC = (_SS_DIR / "scheduler_score.js").read_text()

FIRST_PRIVATE_BUS = 48

requires_node = pytest.mark.skipif(shutil.which("node") is None,
                                   reason="node not available")


def _probe(scenario, capacity=None):
    argv = ["node", str(_PROBE), scenario]
    if capacity is not None:
        argv.append(str(capacity))
    proc = subprocess.run(argv, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _spans(allocs):
    """(occupied, reserved) ranges for each allocation.

    ``occupied`` is what the SynthDef actually writes -- ``Out.ar(bus, sig)``
    covers ``sig.numChannels`` consecutive channels from ``bus``. ``reserved``
    is what the cursor consumed (occupied, rounded up to even). Both are
    checked: an allocator that advanced by LESS than it handed out would keep
    the occupied ranges disjoint on paper while overlapping in the engine.
    """
    occupied = [(a["start"], a["start"] + a["width"]) for a in allocs]
    reserved = [(a["start"], a["localCursor"]) for a in allocs]
    return occupied, reserved


def _assert_pairwise_disjoint(ranges, allocs, label):
    for (i, j) in combinations(range(len(ranges)), 2):
        (a0, a1), (b0, b1) = ranges[i], ranges[j]
        assert a1 <= b0 or b1 <= a0, (
            f"{label}: allocation {i} {allocs[i]} occupies [{a0},{a1}) and "
            f"allocation {j} {allocs[j]} occupies [{b0},{b1}) -- they overlap, "
            f"so two unrelated voices would sum into the same bus channels"
        )


@requires_node
class TestSharedCursor:
    """The one property that must never break."""

    def test_mixed_widths_never_overlap(self):
        r = _probe("mixed", 1024)
        allocs = r["allocations"]
        assert len(allocs) == 11
        assert {a["via"] for a in allocs} == {"stereo", "wide"}
        occupied, reserved = _spans(allocs)
        _assert_pairwise_disjoint(occupied, allocs, "occupied")
        _assert_pairwise_disjoint(reserved, allocs, "reserved")

    def test_reserved_spans_cover_every_occupied_channel(self):
        """Rounding may reserve more than was asked for; never less."""
        r = _probe("mixed", 1024)
        for a in r["allocations"]:
            reserved = a["localCursor"] - a["start"]
            assert reserved >= a["width"], a

    def test_local_and_global_cursors_stay_in_step(self):
        r = _probe("mixed", 1024)
        for a in r["allocations"]:
            assert a["globalCursor"] == a["localCursor"], a

    def test_cursor_survives_a_second_script_inclusion(self):
        """Two widgets on one page include the sources twice. The install
        guards no-op, and the NEXT scheduler must continue the page-global
        cursor -- a restart would re-hand out buses already carrying audio."""
        r = _probe("two_includes", 1024)
        assert r["reinstalled"] is True
        first, second = r["first"], r["second"]
        assert min(a["start"] for a in second) >= max(a["localCursor"] for a in first), (
            "the second scheduler restarted the cursor instead of continuing it"
        )
        allocs = first + second
        occupied, reserved = _spans(allocs)
        _assert_pairwise_disjoint(occupied, allocs, "occupied across inclusions")
        _assert_pairwise_disjoint(reserved, allocs, "reserved across inclusions")

    def test_nothing_is_allocated_below_the_private_floor(self):
        """A stale pre-10.16 page leaves the shared cursor at 16, inside the
        hardware span. The floor guard lifts it before anything is handed
        out, for wide allocations as well as stereo ones."""
        r = _probe("stale_floor", 1024)
        assert r["staleCursorBefore"] < FIRST_PRIVATE_BUS
        for a in r["allocations"]:
            assert a["start"] >= FIRST_PRIVATE_BUS, a


@requires_node
class TestAlignment:
    """Rounding up to even is a DELIBERATE choice, not an accident: scsynth
    imposes no alignment rule, but the shared cursor has been even since the
    floor was set to 48 and one odd-width run would de-align every stereo
    pair allocated after it on that page."""

    def test_odd_width_leaves_the_cursor_even(self):
        r = _probe("mixed", 1024)
        odd = [a for a in r["allocations"] if a["width"] % 2 == 1]
        assert odd, "the mixed scenario must exercise at least one odd width"
        for a in odd:
            assert a["localCursor"] % 2 == 0, a

    def test_every_allocation_starts_on_an_even_bus(self):
        for scenario in ("mixed", "stale_floor"):
            r = _probe(scenario, 1024)
            for a in r["allocations"]:
                assert a["start"] % 2 == 0, (scenario, a)

    def test_odd_width_reserves_exactly_one_spare_channel(self):
        r = _probe("mixed", 1024)
        for a in r["allocations"]:
            spare = (a["localCursor"] - a["start"]) - a["width"]
            assert spare == (a["width"] % 2), a


@requires_node
class TestStereoUnchanged:
    """``_allocAudioBus()`` is now ``_allocAudioBusN(2)``. It must hand out
    exactly what it did before -- verified against HEAD by an A/B run of both
    source trees whose JSON (stereo sequence, track bus map, and every
    setupTracks OSC send) was byte-identical."""

    def test_stereo_sequence_is_pairs_from_the_floor(self):
        r = _probe("stereo_only", 1024)
        starts = [a["start"] for a in r["allocations"]]
        assert starts == [48, 50, 52, 54, 56, 58, 60, 62]

    def test_setup_tracks_bus_map_unchanged(self):
        r = _probe("setup_tracks", 1024)
        assert r["trackBuses"] == {
            "drums": {"srcBus": 48, "fxBus": 50},
            "keys": {"srcBus": 52, "fxBus": 54},
            "main": {"srcBus": 56, "fxBus": 58},
        }
        assert r["globalCursor"] == 60

    def test_setup_tracks_routing_unchanged(self):
        """drums bypass 48->50; main bypass 56->58; both tracks sum into
        main's srcBus 56; main's router lands on hardware out 0."""
        r = _probe("setup_tracks", 1024)
        assert r["routerSends"] == [
            {"inBus": 48, "outBus": 50},
            {"inBus": 56, "outBus": 58},
            {"inBus": 50, "outBus": 56},
            {"inBus": 54, "outBus": 56},
            {"inBus": 58, "outBus": 0},
        ]


@requires_node
class TestExhaustion:
    """Running past the engine's budget used to allocate buses scsynth does
    not have -- silently, since nothing checked."""

    def test_refuses_instead_of_allocating_past_the_budget(self):
        r = _probe("exhaust", 128)
        assert r["threw"] is True
        assert r["reportedCapacity"] == 128
        for a in r["allocations"]:
            assert a["localCursor"] <= 128, a

    def test_refusal_names_the_budget_and_the_remedy(self):
        r = _probe("exhaust", 128)
        msg = r["message"]
        assert msg.startswith("[Klotho] out of private audio buses:")
        assert "128 audio bus channels" in msg          # the budget
        assert "80 above the private floor of 48" in msg  # the arithmetic
        assert "smaller speaker array" in msg           # what to do
        assert "reload the notebook page" in msg        # the stale-engine case

    def test_a_refused_allocation_does_not_move_the_cursor(self):
        r = _probe("exhaust", 128)
        last_good = r["allocations"][-1]["localCursor"]
        assert r["localCursorAfterThrow"] == last_good
        assert r["globalCursorAfterThrow"] == last_good

    def test_page_with_no_boot_stash_falls_back_to_the_old_budget(self):
        """An engine booted by a pre-10.16 saved output has no bootConfig --
        the same page state the recorder detects for stems. Assume the OLD
        256, not the new 1024: guessing high on a page that cannot say what
        it booted hands out buses that do not exist."""
        r = _probe("exhaust")  # no capacity argument => no bootConfig stash
        assert r["reportedCapacity"] == 256
        assert r["threw"] is True
        for a in r["allocations"]:
            assert a["localCursor"] <= 256, a


@requires_node
class TestWidthRefusals:
    def test_every_bad_width_is_refused(self):
        r = _probe("bad_width", 1024)
        names = {c["name"] for c in r["cases"]}
        assert names == {"zero", "negative", "fractional", "string", "nan",
                         "infinity", "absurd", "null", "undefined"}
        for c in r["cases"]:
            assert c["threw"] is True, c
            assert c["returned"] is None, c
            assert "whole number from 1 to 256" in c["message"], c

    def test_a_refused_width_does_not_move_the_cursor(self):
        r = _probe("bad_width", 1024)
        assert r["cursorAfter"] == r["cursorBefore"] == FIRST_PRIVATE_BUS
        assert r["globalCursorAfter"] == FIRST_PRIVATE_BUS


class TestOneImplementation:
    """Defence-in-depth (static): the behavioral tests above prove the two
    entry points share a cursor TODAY, but they cannot prove there is only
    one implementation -- a second copy that happened to agree would pass
    them. This is the guard against that copy being introduced."""

    def test_stereo_alloc_delegates_to_the_width_aware_one(self):
        assert "return this._allocAudioBusN(BUS_CHANNELS);" in SCORE_SRC
        # no second cursor
        assert SCORE_SRC.count("this._nextAudioBus =") == 1


class TestBusBudget:
    """The Python side of the budget the allocator checks against."""

    def test_audio_buses_raised_for_multichannel(self):
        from klotho.utils.playback.supersonic.cdn import SCSYNTH_NUM_AUDIO_BUSES
        assert SCSYNTH_NUM_AUDIO_BUSES == 1024

    def test_boot_config_carries_the_budget(self):
        from klotho.utils.playback.supersonic.cdn import supersonic_config
        assert supersonic_config()["scsynthOptions"]["numAudioBusChannels"] == 1024

    def test_output_channels_did_not_move(self):
        """The speaker array lives on PRIVATE buses: hardware channels above
        0/1 are inaudible in the browser, 2..31 are stem-tap pairs, and
        raising numOutputBusChannels would push the hardware span toward
        FIRST_PRIVATE_BUS. 32 already covers the widest hardware mirror the
        design asks for (channels 2..31 = 30 speakers)."""
        from klotho.utils.playback.supersonic.cdn import (
            SCSYNTH_NUM_OUTPUT_CHANNELS, supersonic_config)
        assert SCSYNTH_NUM_OUTPUT_CHANNELS == 32
        opts = supersonic_config()["scsynthOptions"]
        num_in = opts.get("numInputBusChannels", 2)  # SuperSonic default
        assert SCSYNTH_NUM_OUTPUT_CHANNELS + num_in <= FIRST_PRIVATE_BUS

    def test_budget_fits_a_real_spatial_score(self):
        """A 24-speaker track costs 24 channels per bus: srcBus + fxBus + one
        per intermediate insert. 256 left room for exactly one such track;
        1024 must leave room for several."""
        from klotho.utils.playback.supersonic.cdn import SCSYNTH_NUM_AUDIO_BUSES
        private = SCSYNTH_NUM_AUDIO_BUSES - FIRST_PRIVATE_BUS
        assert private == 976
        per_spatial_track = 24 * 4  # srcBus, fxBus, two insert stages
        assert private // per_spatial_track >= 10

    def test_budget_raise_does_not_touch_the_engine_pin(self):
        """numAudioBusChannels was already a scsynthOptions key; only its
        VALUE moved, so the pinned SuperSonic build is unchanged."""
        from klotho.utils.playback.supersonic.cdn import (
            SUPERSONIC_VERSION, supersonic_config)
        assert SUPERSONIC_VERSION == "0.71.0"
        assert set(supersonic_config()["scsynthOptions"]) == {
            "numOutputBusChannels", "numAudioBusChannels"}
