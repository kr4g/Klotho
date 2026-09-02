"""Control-envelope runtime: source contracts over the scheduler JS.

Regression coverage for the silent-envelope bug: ``/b_alloc`` is an
async scsynth command (it completes on the NRT thread after later
messages have already been processed), so the ``/b_setn`` fills sent by
``preloadControlBuffer`` were dropped against the not-yet-allocated
buffer.  Every ``__klEnvCtrl`` then streamed zeros, pinning all mapped
pfields (``freq``, ``amp``) to 0 — any ``apply_envelope(...,
control=True)`` playback was completely silent.  The fix parks the
fills behind a ``/sync`` round-trip and has ``setupControlEnvelopes``
await the fill before any envelope synth can read the buffer.

Static contracts in the style of ``test_recording.TestSourceContract``
(the browser behavior itself was verified live against scsynth-WASM:
buffer readback non-zero after preload, control buses streaming
envelope values during playback).
"""
from pathlib import Path

_SS_DIR = Path(__file__).parent.parent / "klotho" / "utils" / "playback" / "supersonic"

CORE_SRC = (_SS_DIR / "scheduler_core.js").read_text()
SCORE_SRC = (_SS_DIR / "scheduler_score.js").read_text()


class TestControlPreloadContract:
    def test_fills_wait_behind_sync_after_alloc(self):
        """/b_setn must not race the async /b_alloc completion."""
        body = SCORE_SRC[SCORE_SRC.index("preloadControlBuffer = function"):]
        alloc = body.index("'/b_alloc'")
        sync = body.index("await sonic.sync()")
        setn = body.index("'/b_setn'")
        assert alloc < sync < setn

    def test_preload_returns_fill_promise(self):
        body = SCORE_SRC[SCORE_SRC.index("preloadControlBuffer = function"):]
        assert "return this._ctrlPreload.ready;" in body
        assert "return ready;" in body

    def test_setup_awaits_fill_before_envelope_synths(self):
        """setupControlEnvelopes must await the fill; otherwise a first
        play immediately after widget init can still read a zero buffer."""
        setup = SCORE_SRC[SCORE_SRC.index("setupControlEnvelopes"):]
        assert "if (preloadReady) await preloadReady;" in setup

    def test_score_ext_install_guard_is_versioned(self):
        """Pages carrying a stale pre-V2 extension from saved outputs must
        get this build's preload (same lesson as the 10.16 core guard)."""
        assert "__klothoScoreExtV2" in SCORE_SRC
        guard = SCORE_SRC.index("__klothoScoreExtV2) return;")
        marker = SCORE_SRC.index("proto.__klothoScoreExtV2 = true;")
        assert guard < marker


class TestStopFreeVsPurgeContract:
    """The 10.16 stop regression, in two acts. Act 1: /g_freeAll rides the
    OSC out-ring while purge()'s clearSched rides the worklet port — an
    unordered channel that can wipe the ring before the frees drain,
    leaving stopped notes sounding with their scheduled gate-offs
    flushed. Both stop() and play()'s restart path must drain the frees
    through a /sync round-trip BEFORE _unregisterPlayer's purge. Act 2:
    purge() itself is async — its late clearSched ack was wiping the
    NEXT play's freshly scheduled batch (eaten n_maps and __klEnvCtrl
    spawns = frozen control envelopes; eaten releases/frees = stuck
    notes; intermittent because it depends on ack timing). play() must
    await the recorded in-flight purge before scheduling anything, and
    every such await must be bounded so a lost ack degrades instead of
    hanging stop() or play() forever."""

    @staticmethod
    def _method_body(src, header):
        """The method's REAL body, found by matching its braces.

        AF1-35: this used to be ``src[start:start + span]`` with *span* a raw
        character count passed per call site (2600, 4000, 7000, 2200). Both
        directions of that were wrong, and measured on 2026-09-02:

        =============================  =========  ===========
        method                         real size  span used
        =============================  =========  ===========
        ``async stop()``                    1646         2600
        ``async play(events, options)``     7306    4000/7000
        ``_deferUnregister()``              1776         2200
        ``_unregisterPlayer()``             1160         2600
        ``async _awaitBounded()``            245         2600
        =============================  =========  ===========

        An OVERRUN is the dangerous one: ``_awaitBounded`` is 245 characters
        and was searched over 2600, so ``assert "Promise.race" in body`` could
        be satisfied by a ``Promise.race`` belonging to some later method
        entirely -- a green check on a function that no longer does the thing.
        A TRUNCATION is the loud one: ``play()`` is 7306 characters and two
        call sites searched only its first 4000, so a needle that drifted past
        that point turned a correct file red.

        Both failure modes are removed by finding the closing brace instead of
        guessing a length -- and the body then stays correct when anyone adds
        a comment. String literals and comments are skipped so a brace inside
        one cannot unbalance the count.
        """
        start = src.index(header)
        i = src.index('{', start + len(header))
        depth, j, n = 0, i, len(src)
        while j < n:
            c = src[j]
            if c in '"\'`':
                quote, j = c, j + 1
                while j < n and src[j] != quote:
                    j += 2 if src[j] == '\\' else 1
            elif c == '/' and j + 1 < n and src[j + 1] == '/':
                j = src.find('\n', j)
                if j == -1:
                    break
            elif c == '/' and j + 1 < n and src[j + 1] == '*':
                j = src.find('*/', j) + 1
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return src[start:j + 1]
            j += 1
        raise AssertionError(
            f'unbalanced braces after {header!r} -- the body could not be '
            f'delimited, so every check over it would be meaningless')

    def test_stop_syncs_between_frees_and_purge(self):
        body = self._method_body(CORE_SRC, "async stop()")
        free = body.index("self._freeGroup();")
        sync = body.index("await self._fastSync(")
        unreg = body.index("self._unregisterPlayer();")
        assert free < sync < unreg

    def test_play_restart_syncs_between_frees_and_purge(self):
        body = self._method_body(CORE_SRC, "async play(events, options)")
        free = body.index("self._freeGroup();")
        sync = body.index("await self._fastSync(")
        unreg = body.index("self._unregisterPlayer();")
        assert free < sync < unreg

    def test_teardowns_serialize_on_shared_chain(self):
        """Act 3 (V5): every frees->fence->unregister sequence rides the
        shared _engineLock chain. Sequential awaits over the shared state
        are not enough — two presses in the same task can both read "no
        teardown pending" before either records one, and the second
        press's purge then eats the first's frees and in-flight /sync
        (browser-verified failure mode)."""
        assert "_engineLock(work)" in CORE_SRC
        for method in ("async stop()", "async play(events, options)",
                       "_deferUnregister()"):
            body = self._method_body(CORE_SRC, method)
            assert "._engineLock(" in body, f"{method} not serialized"

    def test_play_flush_section_settles_before_scheduling(self):
        """The purge ack must settle inside play()'s serialized section,
        before anything is scheduled: a late clearSched ack would eat a
        random slice of the new batch."""
        body = self._method_body(CORE_SRC, "async play(events, options)")
        lock = body.index("await this._engineLock(")
        purge = body.index("_awaitBounded(_schedLoad().purgePromise")
        plan = body.index("this._buildSendPlan(evts)")
        assert lock < purge < plan

    def test_unregister_records_inflight_purge(self):
        """The purge promise must be observable by the next play()."""
        body = self._method_body(CORE_SRC, "_unregisterPlayer()")
        assert "g.purgePromise = p;" in body

    def test_play_awaits_inflight_purge_before_scheduling(self):
        body = self._method_body(CORE_SRC, "async play(events, options)")
        unreg = body.index("self._unregisterPlayer();")
        purge_await = body.index("_awaitBounded(_schedLoad().purgePromise")
        plan = body.index("this._buildSendPlan(evts)")
        assert unreg < purge_await < plan

    def test_purge_and_sync_awaits_are_bounded(self):
        """A wedged ack must never hang stop()/play(): the helper races
        the promise against a timeout."""
        body = self._method_body(CORE_SRC, "async _awaitBounded(promise, ms)")
        assert "Promise.race" in body


class TestEnvCtrlSteppedWrites:
    """The frozen-freq bug: kl_*/fd_* instruments glide ``freq`` through
    ``VarLag(warp: \\exp)`` / the FoxDot idiom, which expand to a
    ``Changed()``-retriggered EnvGen chase.  Against a control bus that
    moves EVERY block (the old linear-phase ``__klEnvCtrl``), the
    trigger never re-arms, so mapped freqs froze at their onset value —
    freq envelopes played as a static cluster while chase-free params
    (amp) followed theirs.  The def now sample-and-holds the bus in
    ~30ms steps (floor-quantized read phase) so the chase retriggers
    per step and the synth's own portamento smooths the glide.
    Verified live in JupyterLab via spectrum analysis of a recorded
    performance (cluster partials collapse, target partials appear)."""

    def _graph(self):
        import importlib.util
        parser_path = (_SS_DIR / "_vendor" / "synthdef_parser" / "parser.py")
        spec = importlib.util.spec_from_file_location("sdparser", parser_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        d = mod.parse_synthdef_file(
            str(_SS_DIR / "assets" / "synthdefs" / "infra" / "__klEnvCtrl.scsyndef"))
        return d["synths"]["__klEnvCtrl"]

    def test_params_unchanged(self):
        sd = self._graph()
        assert list(sd["named_parameters"].keys()) == [
            "bufnum", "bus", "dur", "startFrame", "numFrames"]

    def test_phase_is_floor_quantized(self):
        """UnaryOpUGen special_index 9 is ``floor`` — the step quantizer."""
        sd = self._graph()
        assert any(u["name"] == "UnaryOpUGen" and u["special_index"] == 9
                   for u in sd["ugens"]), \
            "__klEnvCtrl no longer floor-quantizes its BufRd phase; " \
            "continuously-written buses freeze VarLag/FoxDot glide chases"

    def test_scd_source_matches(self):
        scd = (_SS_DIR / "assets" / "klotho_synthdefs.scd").read_text()
        block = scd[scd.index("SynthDef(\\__klEnvCtrl"):]
        block = block[:block.index("writeDefFile")]
        assert ".floor" in block and "stepFrames" in block


class TestSynthdefRegistryMerge:
    """Stale saved outputs run their registry merge first on page load; a
    first-wins merge pinned their synthdef bytes for the page's lifetime,
    so freshly rendered widgets kept d_recv'ing old builds (this masked
    the stepped ``__klEnvCtrl``: pages kept the linear-phase def and freq
    envelopes stayed frozen).  The merge must be last-wins on changed
    bytes and must invalidate the loaded-defs registry so loadDefs
    re-sends the replacement."""

    def _merge_src(self):
        from klotho.utils.playback.supersonic._js_fragments import (
            synthdef_registry_merge_js,
        )
        return synthdef_registry_merge_js("{}")

    def test_merge_is_not_first_wins(self):
        src = self._merge_src()
        assert "!_r[k]" not in src
        assert "_r[k] !== _new[k]" in src

    def test_merge_invalidates_loaded_defs_on_change(self):
        src = self._merge_src()
        assert "loadedDefs.delete(k)" in src
