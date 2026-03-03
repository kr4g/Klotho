// Shared playback controller for animated Klotho figures.
// Python replaces placeholders: __WID__, __DUR_MS__, __BOUNDARY_OP__, __ENGINE_TYPE__, __LOOP_MODE__, __LOOP_COUNT__, __LOOP_ENABLED__
// Caller must define: audioPayload, totalSteps, onStep, onBeforePlay, onReset

var toggleBtn = document.getElementById("__WID___toggle");
var iconEl    = document.getElementById("__WID___icon");
var loopBtn   = document.getElementById("__WID___loop");
var loopSvg   = document.getElementById("__WID___loop_svg");
var playing = false;
var loopMode = "__LOOP_MODE__";
var loopCount = Number("__LOOP_COUNT__");
if (!Number.isFinite(loopCount)) loopCount = 0;
var loopEnabled = "__LOOP_ENABLED__" === "true";
var loopInfinite = loopMode === "infinite";
var loopFiniteCount = loopMode === "finite" ? Math.max(2, Math.floor(loopCount)) : 0;
var loopCyclesRemaining = loopFiniteCount;
var engineType = "__ENGINE_TYPE__";
var bridge = (typeof globalThis.KlothoPlaybackBridge === "function")
    ? globalThis.KlothoPlaybackBridge({
        engine: engineType,
        audioPayload: audioPayload,
        ringTime: __RING_TIME__,
    })
    : null;

function finishPlayback() { playing = false; onReset(); setPlayIcon(); }

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

function _setLoopUi() {
    if (loopMode === "off") {
        loopBtn.style.opacity = "0.3";
        loopBtn.style.cursor = "not-allowed";
        loopSvg.setAttribute("stroke", "#666");
        return;
    }
    loopBtn.style.opacity = loopEnabled ? "1" : "0.5";
    loopBtn.style.cursor = "pointer";
    loopSvg.setAttribute("stroke", loopEnabled ? "#4ade80" : "#a0a0a0");
}
_setLoopUi();

loopBtn.addEventListener("click", function() {
    if (loopMode === "off") return;
    loopEnabled = !loopEnabled;
    if (loopEnabled && !loopInfinite) loopCyclesRemaining = loopFiniteCount;
    _setLoopUi();
});

var _timerId = null;
var durMs = __DUR_MS__;

function _runAnimation(stepIdx) {
    if (!playing) return;
    if (stepIdx __BOUNDARY_OP__ totalSteps) {
        if (loopEnabled && (loopInfinite || loopCyclesRemaining > 1)) {
            if (!loopInfinite) loopCyclesRemaining -= 1;
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
    if (playing) {
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
            loop: loopEnabled ? (loopInfinite ? true : loopFiniteCount) : false,
            onEvent: function(stepIdx) { if (playing) onStep(stepIdx); },
            onFinish: function() { finishPlayback(); },
        });
    } else {
        playing = true;
        setStopIcon();
        onBeforePlay();
        if (loopEnabled && !loopInfinite) loopCyclesRemaining = loopFiniteCount;
        _runAnimation(0);
    }
});

var _orphanCheckId = setInterval(function() {
    if (toggleBtn && !toggleBtn.isConnected) {
        _stopAll();
        playing = false;
        clearInterval(_orphanCheckId);
    }
}, 1000);
