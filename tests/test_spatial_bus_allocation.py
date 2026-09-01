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

    def test_nothing_lands_inside_a_second_widgets_live_run(self):
        """Two widgets ALIVE AT ONCE, which the pairwise checks above cannot
        see: those compare allocations made by ONE scheduler, and every one
        of them passed while this was broken.

        B holds a 24-wide run. A allocates again mid-play after B has moved
        the cursor, then rings out; the ring-out free used to read the SHARED
        cursor as its own range end, so A handed back everything allocated
        since A started -- B's 24 live channels included -- and the next play
        was handed 20 of them.
        """
        r = _probe("two_widgets", 1024)
        b = _spans(r["bAllocations"])[1]        # B's reserved run(s)
        others = [("A", a) for a in r["aAllocations"]] \
            + [("C", a) for a in r["cAllocations"]]
        for who, a in others:
            a0, a1 = a["start"], a["localCursor"]
            for (b0, b1) in b:
                assert a1 <= b0 or b1 <= a0, (
                    f"widget B is still playing on audio buses [{b0},{b1}) "
                    f"and widget {who} was handed [{a0},{a1}) -- overlapping "
                    f"channels {max(a0, b0)}..{min(a1, b1)}, where two "
                    f"unrelated voices sum into each other"
                )
        live_control = set(r["bControlBuses"])
        for who, buses in (("A", r["aControlBuses"]), ("C", r["cControlBuses"])):
            assert not (set(buses) & live_control), (who, buses, live_control)

    def test_an_out_of_order_free_gives_back_only_what_is_on_top(self):
        """The chosen semantics, pinned as a choice, from both sides.

        A monotonic cursor can only rewind over the allocation that is
        currently on TOP of it. A's ring-out gives back its own last run --
        so reclaim is not simply switched off -- and stops dead at B's live
        range rather than rewinding through it. A's earlier channels leak
        until the page reloads: leaked bus NUMBERS cost nothing at runtime
        (scsynth allocated its whole bus array at boot), and the alternative
        is two voices summing with nothing in the output to say so.
        """
        r = _probe("two_widgets", 1024)
        assert r["timersPending"] == 1 and r["timersFired"] == 1, r
        before, after = r["globalBeforeRingOut"], r["globalAfterRingOut"]
        b_end = r["bAudio"][1]
        assert after["audio"] < before["audio"], (
            "the free gave nothing back at all; the topmost run was its own")
        assert after["audio"] >= b_end, (
            f"the cursor rewound to {after['audio']}, inside widget B's live "
            f"run which ends at {b_end}")
        assert after["control"] < before["control"]
        assert after["control"] >= max(r["bControlBuses"]) + 1

    def test_a_widget_alone_still_gets_its_buses_back(self):
        """The other half of the trade. Reclaim is what stops a page running
        out after a few dozen plays, so 'never rewind' is not an acceptable
        way to make overlaps impossible."""
        r = _probe("ring_out_reclaims", 1024)
        assert r["globalBeforeRingOut"]["audio"] > FIRST_PRIVATE_BUS
        assert r["globalAfterRingOut"] == {"audio": FIRST_PRIVATE_BUS,
                                           "control": 0}
        assert [a["start"] for a in r["second"]] == [FIRST_PRIVATE_BUS]
        assert r["secondControl"] == [0]
        # And again, so reclaim is not a one-shot.
        assert r["globalAfterSecondRingOut"] == {"audio": FIRST_PRIVATE_BUS,
                                                 "control": 0}

    def test_the_two_stop_paths_reclaim_the_same_ledger(self):
        """A ring-out is not the only way a range comes back: ``stop()``
        frees the live group immediately and cancels rings that have not
        fired yet. All three read the same per-play ledger, so a mismatch
        there is a stuck transport rather than a quiet overlap -- but it is
        still a way for the bus space to drain away."""
        r = _probe("stop_paths", 1024)
        assert r["beforeAll"] == FIRST_PRIVATE_BUS
        assert r["afterFreeGroup"] == FIRST_PRIVATE_BUS
        assert r["ringsPending"] == 1
        assert r["afterCancel"] == FIRST_PRIVATE_BUS
        assert r["ringsAfterCancel"] == 0
        assert r["timersLeft"] == 0      # the cancelled ring's timer is gone

    def test_freeing_the_same_ledger_twice_cannot_take_it_back_twice(self):
        """Defence in depth, driving ``_reclaimBusRuns`` directly: no path
        frees one play's ledger twice today (every free clears the list it
        took), so this is a guard against a future one rather than a
        reachable defect. It matters because the cursor can legitimately
        return to the same number under new ownership."""
        r = _probe("double_reclaim", 1024)
        assert r["afterFirstReclaim"] == FIRST_PRIVATE_BUS
        assert [a["start"] for a in r["other"]] == [48, 50]
        assert r["afterOther"] == 52
        assert r["afterSecondReclaim"] == 52, (
            "a second free of an already-freed ledger handed back channels "
            "that now belong to another widget")

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

    def test_odd_width_runs_also_stop_at_the_budget(self):
        """Even widths divide the budget cleanly, so the only exhaustion case
        tested was one where rounding never decides anything. An odd run is
        RESERVED one channel wider than it is asked for, and it is the
        reserved width that must be checked against the budget -- checking
        the asked-for width would let the last run reserve past the end."""
        r = _probe("exhaust_odd", 125)
        assert r["runWidth"] == 25 and r["threw"] is True
        assert [(a["start"], a["localCursor"]) for a in r["allocations"]] == [
            (48, 74), (74, 100)]
        for a in r["allocations"]:
            assert a["start"] + a["width"] <= 125, a   # occupied
            assert a["localCursor"] <= 125, a          # reserved
        # A third run would OCCUPY 100..125, which fits, and RESERVE
        # 100..126, which does not. The reserved width is what must decide.
        assert r["localCursorAfterThrow"] == 100
        assert "a 25-channel run at bus 100 would reach 126" in r["message"]

    def test_page_with_no_boot_stash_falls_back_to_supersonics_own_default(self):
        """An engine booted by a pre-10.16 saved output has no bootConfig --
        the same page state the recorder detects for stems. Klotho passed no
        scsynthOptions at all before 10.16, so such an engine booted on
        SuperSonic's OWN default of 128 audio bus channels (checked against
        the pinned dist bundle by the test below). Assuming the 1024 this
        build boots with would hand a stale page buses that do not exist."""
        r = _probe("exhaust")  # no capacity argument => no bootConfig stash
        assert r["reportedCapacity"] == 128
        assert r["threw"] is True
        for a in r["allocations"]:
            assert a["localCursor"] <= 128, a
        # Not merely "some small number": the fallback must be the engine's
        # own default, and 256 (the value that shipped) is past it.
        assert [a["localCursor"] for a in r["allocations"]] == [72, 96, 120]


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


class TestLegacyFallbackMatchesTheEngine:
    """The no-stash fallback is a guess about somebody else's default, so it
    is pinned against the engine version it is a guess about. A SuperSonic
    bump must force a re-read of that bundle rather than silently leaving a
    stale number in a file nobody rereads."""

    def test_the_fallback_is_supersonics_own_default(self):
        from klotho.utils.playback.supersonic.cdn import (
            SUPERSONIC_DEFAULT_NUM_AUDIO_BUSES, SUPERSONIC_VERSION)
        assert SUPERSONIC_VERSION == "0.71.0"
        assert SUPERSONIC_DEFAULT_NUM_AUDIO_BUSES == 128
        assert (f"var LEGACY_AUDIO_BUSES = "
                f"{SUPERSONIC_DEFAULT_NUM_AUDIO_BUSES};") in SCORE_SRC

    def test_the_fallback_is_not_the_budget_this_build_boots_with(self):
        """The two are unrelated numbers and were once confused. A page that
        cannot say what it booted with did NOT boot with our budget."""
        from klotho.utils.playback.supersonic.cdn import (
            SCSYNTH_NUM_AUDIO_BUSES, SUPERSONIC_DEFAULT_NUM_AUDIO_BUSES)
        assert SUPERSONIC_DEFAULT_NUM_AUDIO_BUSES < SCSYNTH_NUM_AUDIO_BUSES

    def test_the_block_size_the_memory_note_is_written_against(self):
        """cdn.py's cost arithmetic multiplies by the block size; SuperSonic
        refuses any bufLength but 128, so 64 was simply wrong."""
        from klotho.utils.playback.supersonic.cdn import (
            SCSYNTH_NUM_AUDIO_BUSES, SUPERSONIC_BLOCK_SIZE)
        assert SUPERSONIC_BLOCK_SIZE == 128
        kib = SCSYNTH_NUM_AUDIO_BUSES * SUPERSONIC_BLOCK_SIZE * 4 / 1024
        assert kib == 512.0
        from klotho.utils.playback.supersonic import cdn
        src = Path(cdn.__file__).read_text()
        assert "1024 x 128 samples x 4 B =" in src
        assert "512 KB" in src


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
