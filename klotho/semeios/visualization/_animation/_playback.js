// Shared playback controller for animated Klotho figures.
// Python replaces placeholders: __WID__, __DUR_MS__, __BOUNDARY_OP__, __LOOP_MODE__, __LOOP_COUNT__, __LOOP_ENABLED__
// Caller must define: audioPayload, totalSteps, onStep, onBeforePlay, onReset

var toggleBtn = document.getElementById("__WID___toggle");
var iconEl    = document.getElementById("__WID___icon");
var loopBtn   = document.getElementById("__WID___loop");
var loopSvg   = document.getElementById("__WID___loop_svg");
var playing = false;
var loopCtl = KlothoLoopControl(loopBtn, loopSvg, "__LOOP_MODE__", "__LOOP_COUNT__",
                                "__LOOP_ENABLED__" === "true");
var bridge = (typeof globalThis.KlothoPlaybackBridge === "function")
    ? globalThis.KlothoPlaybackBridge({
        audioPayload: audioPayload,
        ringTime: __RING_TIME__,
    })
    : null;

// Eager warm-up: start booting the engine now; the play button renders
// disabled/greyed and enables when ready (or on failure, for retry —
// the silent-animation fallback still works without audio).
KlothoGateToggle(toggleBtn, bridge ? bridge.ensureReady() : true);

// Visual reset happens at the piece's end (score-time semantics); the
// transport icon re-arms only at onIdle — finish + ring-out + teardown —
// so "play" never shows while the previous play's tails still ring.
// `ringing` marks that window: a press during it STOPS (cuts the tails
// and re-arms) — a button showing "stop" must never produce more sound.
// Restart is stop then play; both presses are fast. Silent fallback and
// manual stop have no ring-out and use the combined finishPlayback().
var ringing = false;
function resetVisuals() { playing = false; onReset(); }
function finishPlayback() { ringing = false; resetVisuals(); setPlayIcon(); }

function setPlayIcon() {
    iconEl.style.cssText =
        "width:0;height:0;border-top:7px solid transparent;"
        + "border-bottom:7px solid transparent;border-left:12px solid #4ade80;"
        + "border-right:none;margin-left:3px;background:none";
}

function setStopIcon() {
    iconEl.style.cssText =
        "width:12px;height:12px;border:none;border-radius:2px;"
        + "margin-left:0;background:#ef4444";
}

var _timerId = null;
var durMs = __DUR_MS__;

function _runAnimation(stepIdx) {
    if (!playing) return;
    if (stepIdx __BOUNDARY_OP__ totalSteps) {
        if (loopCtl.enabled && (loopCtl.infinite || loopCtl.cyclesRemaining > 1)) {
            if (!loopCtl.infinite) loopCtl.cyclesRemaining -= 1;
            onBeforePlay();
            _timerId = setTimeout(function(){ _runAnimation(0); }, durMs);
        } else { finishPlayback(); }
        return;
    }
    onStep(stepIdx);
    _timerId = setTimeout(function(){ _runAnimation(stepIdx + 1); }, durMs);
}

function _stopAll() {
    if (_timerId) { clearTimeout(_timerId); _timerId = null; }
    if (bridge) bridge.stop();
}

toggleBtn.addEventListener("click", async function() {
    // Cancels a recording too (bridge.stop() discards the capture) —
    // including during the ring-out, when `playing` is already false.
    if (playing || ringing
        || (bridge && bridge.isRecording && bridge.isRecording())) {
        _stopAll();
        finishPlayback();
        return;
    }

    var _ss = globalThis.__klothoSonic;
    if (_ss && !_ss.instance && _ss.promise) { _ss.promise = null; }

    var ok = bridge ? await bridge.ensureReady() : false;
    var hasEvents = ok && bridge && bridge.hasPlayableEvents();

    if (hasEvents) {
        await bridge.resumeAudio();
        playing = true;
        setStopIcon();
        onBeforePlay();
        await bridge.play(null, {
            loop: loopCtl.schedulerValue(),
            onEvent: function(stepIdx) { if (playing) onStep(stepIdx); },
            onFinish: function() { ringing = true; resetVisuals(); },
            onIdle: function() { ringing = false; setPlayIcon(); },
        });
    } else {
        playing = true;
        setStopIcon();
        onBeforePlay();
        loopCtl.rearm();
        _runAnimation(0);
    }
});

// Record button (present only when the figure was built with
// record=True — the controller keys off element presence).
var _recBtn = document.getElementById("__WID___rec");
if (_recBtn && bridge && typeof bridge.record === "function") {
    var _stemsBox = document.getElementById("__WID___stems");
    var _dlEl = document.getElementById("__WID___dl");
    var _recReady = bridge.ensureReady();
    KlothoGateToggle(_recBtn, _recReady);
    // Stale-page engine (pre-10.16 boot): no stem output channels —
    // disable the checkbox with the reload hint.
    if (_stemsBox && typeof bridge.stemCapacity === "function") {
        _recReady.then(function(ok) {
            if (ok && bridge.stemCapacity() === 0) {
                _stemsBox.disabled = true;
                _stemsBox.checked = false;
                var lbl = _stemsBox.parentElement;
                if (lbl) {
                    lbl.style.opacity = "0.4";
                    lbl.title = "Stems need a page reload: this page's "
                        + "audio engine was started by an output saved "
                        + "with an older Klotho.";
                }
            }
        });
    }
    _recBtn.addEventListener("click", async function() {
        if (playing || bridge.isRecording()) return;
        var _ss = globalThis.__klothoSonic;
        if (_ss && !_ss.instance && _ss.promise) { _ss.promise = null; }
        var ok = await bridge.ensureReady();
        if (!ok || !bridge.hasPlayableEvents()) return;
        await bridge.resumeAudio();
        playing = true;
        setStopIcon();
        _recBtn.style.background = "#7f1d1d";
        _recBtn.style.opacity = "1";
        if (loopBtn) { loopBtn.disabled = true; loopBtn.style.opacity = "0.3"; }
        onBeforePlay();
        var result = await bridge.record(null, {
            stems: !!(_stemsBox && _stemsBox.checked),
            onEvent: function(stepIdx) { if (playing) onStep(stepIdx); },
            // Fires at piece end; capture continues through the ring-out,
            // but the animation is done.
            onFinish: function() { finishPlayback(); },
        });
        _recBtn.style.background = "#16213e";
        if (loopBtn) { loopBtn.disabled = false; }
        loopCtl.sync();
        if (playing) finishPlayback(); else setPlayIcon();
        if (result && result.files && globalThis.KlothoRecorder) {
            globalThis.KlothoRecorder.deliver(result.files, _dlEl);
        }
    });
}

var _orphanCheckId = setInterval(function() {
    if (toggleBtn && !toggleBtn.isConnected) {
        _stopAll();
        if (bridge) bridge.releaseControlPreload();
        playing = false;
        clearInterval(_orphanCheckId);
    }
}, 1000);
