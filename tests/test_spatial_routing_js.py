"""Multichannel routing, proved against the OSC the schedulers actually send.

``converters.py`` resolves a ``speaker`` label to a ``speakerLane`` and
``_build_spatial_meta`` publishes the array's geometry; this file is about the
half that turns those numbers into sound -- the bus topology
``scheduler_score.js`` builds and the ``out=`` every voice is given by
``scheduler_core.js``.

The topology, and why it is this one:

* A track carries **one bus channel per speaker**, so a lane is an offset into
  the track's run.  Lane *k* is ``srcBus + k``.
* **main is as wide as the widest spatial track**, because every track sums
  into main and a 24-wide track summing into a 2-wide main would write 22
  channels past the end of main's run -- onto whatever the allocator handed
  out next, which is another track's live audio.
* **A stereo track lands on lanes 0 and 1** of that array -- the first two
  declared speakers.  A stereo signal names no speaker, a room has nowhere
  else to put it, and every lane of main reaches the listener through the
  fold, so the material stays audible instead of being dropped for want of a
  speaker assignment.
* **The headphone fold sits last.**  ``__spatialDecodeN`` reads main's post-FX
  bus at the tail of main's parent group, and main's group is the last child
  of the score group, so every writer of the array has already run.

These are BEHAVIORAL tests: ``tests/fixtures/spatial_routing_probe.mjs`` loads
the real sources into a Node vm sandbox against a fake engine that records
every OSC message, in the style of ``test_spatial_bus_allocation``.

The regression that matters most is :class:`TestNonSpatialUnchanged`: the same
scenario is run against the sources as they stood BEFORE this feature
(extracted from git) and the two transcripts must be identical, message for
message.
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_SS_DIR = _ROOT / "klotho" / "utils" / "playback" / "supersonic"
_PROBE = Path(__file__).parent / "fixtures" / "spatial_routing_probe.mjs"

#: The commit that shipped the spatial SynthDef family and NOTHING that
#: consumes it -- the last state in which a score could not be spatial at all.
#: Used only to fetch two source files for the A/B below; if the object is
#: gone the A/B is skipped and the literal transcript in
#: :data:`NON_SPATIAL_TRANSCRIPT` still holds the line.
PRE_CHANGE_COMMIT = "4f997b0"

requires_node = pytest.mark.skipif(shutil.which("node") is None,
                                   reason="node not available")


def _probe(scenario, src=None):
    argv = ["node", str(_PROBE), scenario]
    if src is not None:
        argv += ["--src", str(src)]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=str(_ROOT))
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _s_new(records, defname=None):
    """The direct (untimestamped) ``/s_new`` messages, optionally by def."""
    out = []
    for m in records:
        if m.get("k") != "send" or m["msg"][0] != "/s_new":
            continue
        if defname is None or m["msg"][1] == defname:
            out.append(m["msg"])
    return out


def _arg(msg, name):
    """A named ``/s_new`` argument's value."""
    ix = msg.index(name)
    return msg[ix + 1]


# ---------------------------------------------------------------------------
# The transcript a score with no speaker array must keep producing.
#
# Hand-written, NOT captured: it is the whole point of the file that this can
# be read and checked against the topology the docstring describes. Two
# tracks ("drums" with no inserts, "keys" with one), then main; three groups
# each; a bypass router for every chain without inserts; one summing router
# per track into main's srcBus (56); main's router onto hardware bus 0. Then
# four voices -- one per track, one on "default", one naming a track that does
# not exist -- and a slurred /n_set.
# ---------------------------------------------------------------------------
NON_SPATIAL_TRANSCRIPT = [
    {"k": "send", "msg": ["/g_new", 1000, 1, 900]},
    {"k": "send", "msg": ["/g_new", 1001, 0, 1000]},
    {"k": "send", "msg": ["/g_new", 1002, 3, 1001]},
    {"k": "send", "msg": ["/g_new", 1003, 1, 900]},
    {"k": "send", "msg": ["/g_new", 1004, 0, 1003]},
    {"k": "send", "msg": ["/g_new", 1005, 3, 1004]},
    {"k": "send", "msg": ["/g_new", 1006, 1, 900]},
    {"k": "send", "msg": ["/g_new", 1007, 0, 1006]},
    {"k": "send", "msg": ["/g_new", 1008, 3, 1007]},
    {"k": "send", "msg": ["/s_new", "__busRouter", 1009, 0, 1002,
                          "inBus", 48, "outBus", 50, "gain", 1]},
    {"k": "send", "msg": ["/s_new", "kl_reverb", 1010, 1, 1005,
                          "inBus", 52, "outBus", 54, "mix", 0.3]},
    {"k": "send", "msg": ["/s_new", "__busRouter", 1011, 0, 1008,
                          "inBus", 56, "outBus", 58, "gain", 1]},
    {"k": "send", "msg": ["/s_new", "__busRouter", 1012, 1, 1000,
                          "inBus", 50, "outBus", 56, "gain", 1]},
    {"k": "send", "msg": ["/s_new", "__busRouter", 1013, 1, 1003,
                          "inBus", 54, "outBus", 56, "gain", 1]},
    {"k": "send", "msg": ["/s_new", "__busRouter", 1014, 1, 1006,
                          "inBus", 58, "outBus", 0, "gain", 1]},
    {"k": "bundle", "ntp": 100, "addr": "/s_new",
     "args": ["kl_tri", 1015, 0, 1001, "freq", 221, "amp", 0.3, "out", 48]},
    {"k": "bundle", "ntp": 101, "addr": "/s_new",
     "args": ["kl_tri", 1016, 0, 1004, "freq", 222, "amp", 0.3, "out", 52]},
    {"k": "bundle", "ntp": 102, "addr": "/s_new",
     "args": ["kl_tri", 1017, 0, 1007, "freq", 223, "amp", 0.3, "out", 56]},
    {"k": "bundle", "ntp": 103, "addr": "/s_new",
     "args": ["kl_tri", 1018, 0, 1007, "freq", 224, "amp", 0.3, "out", 56]},
    {"k": "bundle", "ntp": 110, "addr": "/n_set",
     "args": [1015, "freq", 221, "amp", 0.3, "out", 48]},
]


@requires_node
class TestNonSpatialUnchanged:
    """A score with no speaker array must put the SAME bytes on the wire.

    Spatial routing is opt-in from the payload up: ``meta.spatial`` is omitted
    entirely unless a track declares speakers. Nothing else in Klotho may move
    because the feature exists.
    """

    def test_transcript_is_exactly_the_stereo_topology(self):
        r = _probe("nonspatial")
        assert r["log"] == NON_SPATIAL_TRANSCRIPT

    def test_identical_to_the_pre_change_sources(self):
        """The A/B that matters: same scenario, same fake engine, the two
        source trees a `git show` apart."""
        try:
            core = subprocess.run(
                ["git", "show",
                 f"{PRE_CHANGE_COMMIT}:klotho/utils/playback/supersonic/scheduler_core.js"],
                capture_output=True, text=True, cwd=str(_ROOT), check=True).stdout
            score = subprocess.run(
                ["git", "show",
                 f"{PRE_CHANGE_COMMIT}:klotho/utils/playback/supersonic/scheduler_score.js"],
                capture_output=True, text=True, cwd=str(_ROOT), check=True).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip(f"{PRE_CHANGE_COMMIT} not reachable from this checkout")

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "scheduler_core.js").write_text(core)
            (Path(tmp) / "scheduler_score.js").write_text(score)
            before = _probe("nonspatial", src=tmp)
        after = _probe("nonspatial")
        assert after["log"] == before["log"]
        assert after["warnings"] == before["warnings"]

    def test_the_unknown_track_warning_still_fires(self):
        """Non-spatial behaviour includes the warnings, not only the OSC."""
        r = _probe("nonspatial")
        assert any("no track named 'nosuchtrack'" in w for w in r["warnings"])


@requires_node
class TestLaneRouting:
    """``out = srcBus + speakerLane``, checked at several lanes."""

    def test_each_lane_lands_on_its_own_bus(self):
        r = _probe("lanes")
        base = r["srcBus"]
        # The last event carries no speakerLane at all: lane 0.
        assert r["outs"] == [base + lane for lane in r["lanes"]] + [base]

    def test_different_speakers_are_different_buses(self):
        r = _probe("lanes")
        base = r["srcBus"]
        assert r["outs"][0] != r["outs"][1]          # lane 0 vs lane 1
        assert r["outs"][2] != r["outs"][3]          # lane 3 vs lane 7
        assert r["outs"][3] == base + 7

    def test_the_same_speaker_twice_is_the_same_bus(self):
        """Two voices on one loudspeaker is ordinary music, not a collision."""
        r = _probe("lanes")
        assert r["outs"][2] == r["outs"][4]          # both lane 3
        assert r["outs"][0] == r["outs"][5]          # both lane 0

    def test_every_lane_stays_inside_the_track_run(self):
        r = _probe("lanes")
        base, width = r["srcBus"], r["width"]
        for o in r["outs"]:
            assert base <= o < base + width, (o, base, width)

    def test_a_slurred_note_is_not_re_routed_mid_flight(self):
        """The /n_set that continues a slurred note must carry the SAME out=;
        dropping the lane there would move a sounding note to speaker 1."""
        r = _probe("slur")
        assert r["newOuts"] == [r["srcBus"] + 6]
        assert r["setOuts"] == r["newOuts"]


@requires_node
class TestChainWidth:
    """A spatial track's chain is one bus channel per speaker, end to end."""

    def test_every_bus_in_the_chain_is_width_wide(self):
        r = _probe("chain")
        assert r["widths"] == {"array": 6, "main": 6}
        src = r["trackBuses"]["array"]["srcBus"]
        fx = r["trackBuses"]["array"]["fxBus"]
        mid = _arg(_s_new_from(r["sNews"], "kl_reverb6")[0], "outBus")
        # src -> fx1 -> mid -> fx2 -> fxBus, and no two runs may overlap.
        runs = sorted([src, fx, mid])
        for a, b in zip(runs, runs[1:]):
            assert b - a >= 6, (runs, "a 6-wide run overlaps the next")

    def test_every_bus_in_the_chain_RESERVES_width_channels(self):
        """Landing on a distinct bus is not enough: the run has to be
        RESERVED, or the next allocation hands those channels to somebody
        else and a 6-channel insert writing there sums into another track.
        The allocator's cursor is the only witness to a reservation."""
        r = _probe("chain")
        width = r["widths"]["array"]
        fx1, fx2 = _s_new_from(r["sNews"], "kl_reverb6")
        buses = [
            r["trackBuses"]["array"]["srcBus"], r["trackBuses"]["array"]["fxBus"],
            r["trackBuses"]["main"]["srcBus"], r["trackBuses"]["main"]["fxBus"],
            _arg(fx1, "outBus"),
        ]
        for b in buses:
            assert r["globalCursor"] >= b + width, (b, width, r["globalCursor"])
        for i, a in enumerate(buses):
            for b in buses[i + 1:]:
                assert a + width <= b or b + width <= a, (a, b, buses)

    def test_the_inserts_are_wired_through_the_wide_buses(self):
        r = _probe("chain")
        fx1, fx2 = _s_new_from(r["sNews"], "kl_reverb6")
        src = r["trackBuses"]["array"]["srcBus"]
        fx = r["trackBuses"]["array"]["fxBus"]
        assert _arg(fx1, "inBus") == src
        assert _arg(fx1, "outBus") == _arg(fx2, "inBus")
        assert _arg(fx2, "outBus") == fx

    def test_the_bypass_router_is_the_wide_def(self):
        r = _probe("chain")
        # main has no inserts, so its chain is a bypass -- 6 channels wide.
        bypass = _s_new_from(r["sNews"], "__busRouter6")
        assert any(_arg(m, "inBus") == r["trackBuses"]["main"]["srcBus"]
                   and _arg(m, "outBus") == r["trackBuses"]["main"]["fxBus"]
                   for m in bypass)

    def test_the_summing_router_is_the_wide_def(self):
        r = _probe("chain")
        routers = _s_new_from(r["sNews"], "__busRouter6")
        assert any(_arg(m, "inBus") == r["trackBuses"]["array"]["fxBus"]
                   and _arg(m, "outBus") == r["trackBuses"]["main"]["srcBus"]
                   for m in routers)


def _s_new_from(messages, defname):
    return [m for m in messages if m[0] == "/s_new" and m[1] == defname]


@requires_node
class TestStereoInASpatialMain:
    """Where a track with no speakers lands, and that it lands SOMEWHERE."""

    def test_main_carries_the_widest_track(self):
        r = _probe("mixed")
        assert r["widths"] == {"array": 8, "stereo": 2, "main": 8}

    def test_a_stereo_track_reaches_main_on_lanes_0_and_1(self):
        r = _probe("mixed")
        main_src = r["buses"]["main"][0]
        stereo_fx = r["buses"]["stereo"][1]
        router = [m for m in _s_new_from(r["sNews"], "__busRouter")
                  if _arg(m, "inBus") == stereo_fx]
        assert len(router) == 1
        # outBus == main's FIRST channel: the stereo pair occupies lanes 0/1.
        assert _arg(router[0], "outBus") == main_src

    def test_the_stereo_track_is_disclosed_not_silently_placed(self):
        r = _probe("mixed")
        assert any("no speakers are declared for: stereo" in w
                   for w in r["warnings"])

    def test_a_stereo_voice_and_a_spatial_voice_land_where_they_should(self):
        r = _probe("mixed")
        stereo_src = r["buses"]["stereo"][0]
        array_src = r["buses"]["array"][0]
        assert r["outs"] == [stereo_src, array_src + 5]

    def test_track_runs_never_overlap(self):
        r = _probe("mixed")
        spans = {
            "array": (r["buses"]["array"][0], 8), "arrayFx": (r["buses"]["array"][1], 8),
            "stereo": (r["buses"]["stereo"][0], 2), "stereoFx": (r["buses"]["stereo"][1], 2),
            "main": (r["buses"]["main"][0], 8), "mainFx": (r["buses"]["main"][1], 8),
        }
        items = list(spans.items())
        for i, (na, (sa, wa)) in enumerate(items):
            for nb, (sb, wb) in items[i + 1:]:
                assert sa + wa <= sb or sb + wb <= sa, (na, nb, spans)


@requires_node
class TestGeometryBuffer:
    """N frames of SIX channels, filled behind a /sync fence.

    An ``N*6 x 1`` buffer holds the same floats and is read as six
    consecutive lanes' worth of numbers by ``BufRd.kr(6, buf, lane)`` -- every
    speaker in the wrong place, with no error. And a fill sent before
    ``/b_alloc`` has completed is DROPPED, leaving a buffer of zeros: a 0 Hz
    shadow cutoff is a one-pole coefficient of 1.0, which mutes the lane.
    """

    def _sends(self, r, addr):
        return [m["msg"] for m in r["log"]
                if m.get("k") == "send" and m["msg"][0] == addr]

    def test_allocated_as_n_frames_of_six_channels(self):
        r = _probe("geometry")
        allocs = self._sends(r, "/b_alloc")
        assert len(allocs) == 1
        _, bufnum, frames, channels = allocs[0]
        assert (frames, channels) == (4, 6), allocs[0]
        assert bufnum == r["bufnum"]

    def test_the_sync_fence_sits_between_alloc_and_fill(self):
        r = _probe("geometry")
        kinds = [m.get("k") if m.get("k") == "sync" else m["msg"][0]
                 for m in r["log"] if m.get("k") in ("send", "sync")]
        alloc = kinds.index("/b_alloc")
        sync = kinds.index("sync")
        setn = kinds.index("/b_setn")
        assert alloc < sync < setn, kinds

    def test_b_setn_carries_flat_in_lane_major_order(self):
        r = _probe("geometry")
        fills = self._sends(r, "/b_setn")
        assert fills, "the geometry table was never uploaded"
        floats = []
        for msg in fills:
            _, bufnum, offset, count = msg[:4]
            assert bufnum == r["bufnum"]
            assert offset == len(floats), (offset, len(floats))
            assert count == len(msg) - 4
            floats.extend(msg[4:])
        assert floats == pytest.approx(r["expectedCoefficients"])
        assert len(floats) == 4 * 6

    def test_one_buffer_per_widget_not_per_play(self):
        r = _probe("replay")
        assert r["allocsAfterFirst"] == 1
        assert r["allocsAfterSecond"] == 1
        assert r["firstBufnum"] == r["secondBufnum"]
        assert r["syncCount"] == 1, "a replay must not pay the fence again"
        assert [d["bufnum"] for d in r["decoderNodes"]] == \
            [r["firstBufnum"], r["firstBufnum"]]

    def test_the_buffer_is_freed_at_widget_teardown(self):
        r = _probe("replay")
        assert ["/b_free", r["firstBufnum"]] in r["frees"]
        assert r["geomAfterRelease"] is None


@requires_node
class TestDecoderPlacement:
    """The fold reads main's post-FX bus, last, and writes hardware 0/1."""

    def test_reads_the_array_and_writes_hardware_zero(self):
        r = _probe("geometry")
        dec = _s_new(r["log"], "__spatialDecode4")
        assert len(dec) == 1
        assert _arg(dec[0], "inBus") == r["mainFxBus"]
        assert _arg(dec[0], "outBus") == 0
        assert _arg(dec[0], "bufnum") == r["bufnum"]

    def test_added_to_the_tail_of_mains_group(self):
        r = _probe("geometry")
        dec = _s_new(r["log"], "__spatialDecode4")[0]
        # /s_new <def> <id> <addAction> <target>; 1 == addToTail.
        assert dec[3] == 1
        assert dec[4] == r["mainParentGroup"]

    def test_created_after_every_writer_of_the_array(self):
        """Node ids are handed out in creation order, so the decoder holding
        the highest one is the machine-checkable form of 'it is last'."""
        r = _probe("geometry")
        dec = _s_new(r["log"], "__spatialDecode4")[0]
        others = [m[2] for m in _s_new(r["log"]) if m[1] != "__spatialDecode4"]
        assert others, "no other nodes to be after"
        assert dec[2] > max(others)

    def test_the_fill_is_sent_before_the_decoder_exists(self):
        r = _probe("geometry")
        seq = [m["msg"][0] if m.get("k") == "send" else "sync"
               for m in r["log"] if m.get("k") in ("send", "sync")]
        assert seq.index("/b_setn") < len(seq) - 1
        assert seq[-1] == "/s_new"      # the decoder, after the fill


@requires_node
class TestNoGeometry:
    """``decoder: null`` -- a labels-only array folds to nothing, and says so."""

    def test_no_decoder_and_no_buffer(self):
        r = _probe("no_decoder")
        assert r["decoderNode"] is None
        assert r["allocs"] == []
        assert not [m for m in r["sNews"]
                    if str(m[1]).startswith("__spatialDecode")]

    def test_the_output_stage_is_the_stereo_router(self):
        """NOT an N-wide router onto hardware bus 0: that would spray lanes
        2..N-1 across the output channels the stem taps live on."""
        r = _probe("no_decoder")
        to_hardware = [m for m in r["sNews"] if _arg(m, "outBus") == 0]
        assert len(to_hardware) == 1
        assert to_hardware[0][1] == "__busRouter"

    def test_the_tracks_are_still_width_wide(self):
        """Routing without a fold is still routing -- the array bus is real,
        it just has no headphone rendering."""
        r = _probe("no_decoder")
        assert r["mainWidth"] == 4
        assert _s_new_from(r["sNews"], "__busRouter4")

    def test_the_missing_fold_is_disclosed(self):
        r = _probe("no_decoder")
        assert any("no positions" in w for w in r["warnings"])


@requires_node
class TestNarrowMasterInsert:
    """A stereo master insert on a main that a spatial track widened.

    ``Score.track()`` checks an insert's channel count against the track's
    speaker count -- but only for a track that DECLARES speakers. A master
    chain declared without ``speakers=`` is validated as stereo and then
    placed on the wide chain, where it reads and writes two lanes and leaves
    the rest of main's post-FX bus unwritten: those speakers go silent, with
    nothing downstream to say so.

    KNOWN GAP, not a fix: the routing still happens, and the warning is what
    makes the silence findable. Whether Klotho should REFUSE this instead is
    a design call, not an implementation detail.
    """

    def test_the_narrowed_master_is_disclosed(self):
        r = _probe("narrow_master")
        assert r["mainWidth"] == 8
        assert any("only ever checked as STEREO" in w for w in r["warnings"])
        assert any("SILENT" in w for w in r["warnings"])

    def test_a_spatial_score_with_no_master_inserts_is_quiet_about_it(self):
        r = _probe("mixed")
        assert not any("STEREO" in w for w in r["warnings"])


@requires_node
class TestSpatialMainOnly:
    """An array declared on "main" produces meta with no ``groups`` at all."""

    def test_the_track_map_is_still_built(self):
        r = _probe("main_only")
        assert r["hasTrackMap"] is True
        assert r["mainWidth"] == 4
        assert r["defaultIsMain"] is True

    def test_voices_are_routed_by_lane(self):
        r = _probe("main_only")
        assert r["outs"] == [r["srcBus"] + 2]

    def test_the_decoder_is_instantiated(self):
        r = _probe("main_only")
        assert _s_new_from(r["sNews"], "__spatialDecode4")

    def test_play_takes_the_score_path_for_a_spatial_only_meta(self):
        """play()'s gate has to count `spatial` as score metadata. Reading
        only `groups`/`inserts` sends this score down the bare single-group
        path: no track map, every voice on out=0, declaration dropped."""
        r = _probe("play_gate")
        assert r["hasTrackMap"] is True
        assert r["mainWidth"] == 4
        assert r["decoders"] == ["__spatialDecode4"]
        assert r["outs"] and r["outs"][0] != 0


@requires_node
class TestRefusals:
    """Loud refusal, and nothing sent -- because the alternative is silence.

    scsynth does not report a SynthDef it could not load or was never given:
    it skips it, the ``/s_new`` creates nothing, and the piece plays with no
    message anywhere.
    """

    def test_wider_than_the_cap_is_refused(self):
        r = _probe("too_wide")
        assert r["threw"] is True
        assert "40 speakers" in r["message"]
        assert "stops at 32" in r["message"]
        assert "SILENTLY" in r["message"]

    def test_a_refused_payload_sends_nothing_at_all(self):
        r = _probe("too_wide")
        assert r["sends"] == 0
        assert r["trackMap"] is None

    @pytest.mark.parametrize("case", ["zero", "fractional", "string",
                                      "nan", "null", "negative"])
    def test_a_width_that_is_not_a_speaker_count_is_refused(self, case):
        cases = {c["name"]: c for c in _probe("bad_width")["cases"]}
        assert cases[case]["threw"] is True
        assert "whole number of at least 1" in cases[case]["message"]

    def test_an_off_family_width_is_refused_before_anything_is_sent(self):
        """Width 5 has no precompiled blob, so the page was never sent one.
        Defence in depth: engine.py names the def in `needed`, and the loader
        swallows the failure -- this is the guard that makes it audible."""
        r = _probe("missing_def")
        assert r["threw"] is True
        assert "__spatialDecode5" in r["message"]
        assert r["sends"] == 0


# ---------------------------------------------------------------------------
# End to end: a real Score, lowered by converters.py, consumed by the real
# schedulers. Nothing between the two halves is invented by this file.
# ---------------------------------------------------------------------------


def _ring_score(width=8, geometry=True, extra_stereo_track=False):
    import math
    from klotho.thetos.spatial import SpeakerArray
    from klotho.thetos.composition.score import Score
    from klotho.thetos import CompositionalUnit

    labels = list(range(1, width + 1))
    if geometry:
        speakers = SpeakerArray(
            {i + 1: (4 * math.cos(2 * math.pi * i / width),
                     4 * math.sin(2 * math.pi * i / width))
             for i in range(width)},
            name="ring",
        )
    else:
        speakers = labels

    score = Score()
    score.track("array", speakers=speakers)
    if extra_stereo_track:
        score.track("pad")

    uc = CompositionalUnit(span=1, tempus="4/4", prolatio=(1, 1, 1, 1))
    # The default instrument writes TWO channels, so a voice occupies the
    # speaker it names and the one above it; converters.py refuses a label
    # with no room above it. Hence width - 1, not width.
    for leaf, label in zip(uc.leaves, [1, 3, 3, width - 1]):
        uc.set(leaf, speaker=label)
    score.add(uc, track="array")

    if extra_stereo_track:
        pad = CompositionalUnit(span=1, tempus="4/4", prolatio=(1, 1))
        score.add(pad, track="pad")
    return score


def _lower(score):
    from klotho.utils.playback.supersonic.converters import (
        convert_score_to_sc_events,
    )
    return convert_score_to_sc_events(score)


@requires_node
class TestRealScoreEndToEnd:
    """The contract as ``converters.py`` emits it, consumed as it ships."""

    def _run(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.json"
            path.write_text(json.dumps(payload))
            argv = ["node", str(_PROBE), "payload", "--payload", str(path)]
            r = subprocess.run(argv, capture_output=True, text=True,
                               cwd=str(_ROOT))
            assert r.returncode == 0, r.stderr
            return json.loads(r.stdout)

    def test_every_declared_speaker_reaches_its_own_bus(self):
        payload = _lower(_ring_score(width=8))
        r = self._run(payload)
        base = r["trackMap"]["array"]["srcBus"]
        assert r["trackMap"]["array"]["width"] == 8
        for e in r["events"]:
            assert e["speakerLane"] is not None, e
            assert e["out"] == base + e["speakerLane"], e
        # Speakers 1, 3, 3, 7: three distinct buses, the top one at lane 6.
        assert len({e["out"] for e in r["events"]}) == 3
        assert max(e["out"] for e in r["events"]) == base + 6

    def test_the_geometry_python_computed_is_what_gets_uploaded(self):
        payload = _lower(_ring_score(width=8))
        table = (payload["meta"]["spatial"]["arrays"]["ring"]
                 ["decoder"]["coefficients"])
        r = self._run(payload)
        assert r["allocs"] == [["/b_alloc", r["allocs"][0][1], 8, 6]]
        assert r["setnFloats"] == pytest.approx(table)
        assert len(table) == 8 * 6

    def test_the_fold_is_instantiated_for_the_real_array(self):
        payload = _lower(_ring_score(width=8))
        r = self._run(payload)
        dec = _s_new_from(r["sNews"], "__spatialDecode8")
        assert len(dec) == 1
        assert _arg(dec[0], "inBus") == r["trackMap"]["main"]["fxBus"]
        assert _arg(dec[0], "outBus") == 0

    def test_a_labels_only_array_routes_without_folding(self):
        payload = _lower(_ring_score(width=8, geometry=False))
        assert (payload["meta"]["spatial"]["arrays"]["array"]["decoder"]
                is None)
        r = self._run(payload)
        base = r["trackMap"]["array"]["srcBus"]
        for e in r["events"]:
            assert e["out"] == base + e["speakerLane"]
        assert r["allocs"] == []
        assert not [m for m in r["sNews"]
                    if str(m[1]).startswith("__spatialDecode")]

    def test_a_stereo_track_alongside_still_plays(self):
        payload = _lower(_ring_score(width=8, extra_stereo_track=True))
        r = self._run(payload)
        assert r["trackMap"]["pad"]["width"] == 2
        assert r["trackMap"]["main"]["width"] == 8
        pad_events = [e for e in r["events"] if e["group"] == "pad"]
        assert pad_events, "the stereo track lowered no events"
        for e in pad_events:
            assert e["speakerLane"] is None
            assert e["out"] == r["trackMap"]["pad"]["srcBus"]
        # And it reaches main on lanes 0/1 rather than nowhere.
        router = [m for m in _s_new_from(r["sNews"], "__busRouter")
                  if _arg(m, "inBus") == r["trackMap"]["pad"]["fxBus"]]
        assert len(router) == 1
        assert _arg(router[0], "outBus") == r["trackMap"]["main"]["srcBus"]


class TestEngineShipsTheSpatialDefs:
    """A def the page was never sent is a def scsynth silently skips.

    The wide routers and the decoder are named by ``meta.spatial``, never by
    an event's ``defName``, so the ordinary scan cannot see them.
    """

    def _engine(self, meta, group="array"):
        from klotho.utils.playback.supersonic.engine import SuperSonicEngine
        events = [{
            "id": "e1", "type": "new", "defName": "kl_tri",
            "start": 0.0, "dur": 1.0, "group": group,
            "pfields": {"freq": 440.0},
        }]
        return SuperSonicEngine(events, meta=meta)

    def _spatial_meta(self, width, groups=("array",), track="array"):
        meta = {"spatial": {
            "arrays": {"a": {"name": "a", "labels": list(range(width)),
                             "width": width, "positions": None, "units": None,
                             "speedOfSound": None, "decoder": None}},
            "tracks": {track: {"array": "a", "width": width}},
        }}
        if groups:
            meta["groups"] = list(groups)
        return meta

    def test_the_wide_router_and_the_decoder_are_included(self):
        e = self._engine(self._spatial_meta(8))
        assert "__busRouter8" in e._needed
        assert "__spatialDecode8" in e._needed
        assert "__busRouter8" in e.synthdef_assets
        assert "__spatialDecode8" in e.synthdef_assets

    def test_a_non_spatial_score_gains_nothing(self):
        e = self._engine({"groups": ["a"]}, group="a")
        assert not [n for n in e._needed
                    if n.startswith("__spatialDecode")]
        assert not [n for n in e._needed
                    if n.startswith("__busRouter") and n[-1].isdigit()]

    def test_main_is_sized_from_the_widest_track(self):
        meta = self._spatial_meta(4)
        meta["groups"] = ["array", "wide"]
        meta["spatial"]["tracks"]["wide"] = {"array": "a", "width": 24}
        e = self._engine(meta)
        assert "__busRouter4" in e._needed
        assert "__busRouter24" in e._needed
        # The fold reads main's bus, so its width is main's width.
        assert "__spatialDecode24" in e._needed
        assert "__spatialDecode4" not in e._needed

    def test_a_stereo_track_needs_no_extra_router(self):
        """Width 2 keeps the undecorated ``__busRouter`` so a non-spatial
        score's OSC does not move; nothing needs ``__busRouter2``."""
        e = self._engine(self._spatial_meta(2))
        assert "__busRouter2" not in e._needed
        assert "__busRouter" in e._needed

    def test_spatial_alone_makes_it_a_score(self):
        """An array declared on "main" produces no ``groups``. Without this,
        scheduler_score.js is never even shipped and setupTracks does not
        exist -- the declaration would be dropped in silence."""
        meta = self._spatial_meta(4, groups=(), track="main")
        e = self._engine(meta, group="main")
        assert e._is_score is True
        html = e._generate_html()
        assert "setupTracks" in html
