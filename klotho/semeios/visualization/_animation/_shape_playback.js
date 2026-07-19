// Shape playback controller for animated Klotho shape figures.
// Python replaces: __WID__, __DUR_MS__, __ENGINE_TYPE__, __RING_TIME__, __TOTAL_GROUPS__, __LOOP_MODE__, __LOOP_COUNT__, __LOOP_ENABLED__
// Caller must define: audioPayload, shapeColors, and the visual hooks
//   dimAllNodes(), hideAllShapeEdges(), revealGroupVisual(gi, color)
// (SVG figures implement the hooks on DOM elements; 3D figures on
// THREE.js meshes/tubes.)
// Optional hook: renderTrail(history) — when defined, the controller keeps
// an onion-skin history of already-shown groups and calls this hook after
// dimming so past shapes can be painted as translucent shadows.

var toggleBtn = document.getElementById("__WID___toggle");
var iconEl    = document.getElementById("__WID___icon");
var loopBtn   = document.getElementById("__WID___loop");
var loopSvg   = document.getElementById("__WID___loop_svg");
var prevBtn   = document.getElementById("__WID___prev");
var nextBtn   = document.getElementById("__WID___next");
var counterEl = document.getElementById("__WID___counter");
var soloBox   = document.getElementById("__WID___solo");

var playing = false;
var loopCtl = KlothoLoopControl(loopBtn, loopSvg, "__LOOP_MODE__", "__LOOP_COUNT__",
                                "__LOOP_ENABLED__" === "true");
var currentView = 0;
var playbackOrigin = 0;
var engineType = "__ENGINE_TYPE__";
var totalGroups = __TOTAL_GROUPS__;
var durMs = __DUR_MS__;
var pauseMs = 0;
if (audioPayload && typeof audioPayload === "object" && audioPayload.pause != null) {
    var p = Number(audioPayload.pause);
    if (!Number.isNaN(p) && p > 0) pauseMs = p * 1000;
}
var stepMs = durMs + pauseMs;
var bridge = (typeof globalThis.KlothoPlaybackBridge === "function")
    ? globalThis.KlothoPlaybackBridge({
        engine: engineType,
        audioPayload: audioPayload,
        ringTime: __RING_TIME__,
    })
    : null;

var trailOn = (typeof renderTrail === "function");
var trailHistory = [];

function _browseTrail(gi) {
    var h = [];
    for (var k = 0; k < gi; k++) h.push(k);
    return h;
}

function updateCounter() {
    if (counterEl) counterEl.textContent = (currentView + 1) + " / " + totalGroups;
}

function revealGroup(gi) {
    dimAllNodes();
    hideAllShapeEdges();
    if (trailOn) renderTrail(trailHistory);
    if (gi < 0 || gi >= totalGroups) return;
    revealGroupVisual(gi, shapeColors[gi] || "white");
}
function revealAndTrack(gi) {
    currentView = gi;
    if (trailOn) {
        // onEvent can fire once per voice of a chord: repeats of the current
        // group must not reset the history — only a wrap to an earlier group.
        var lastShown = trailHistory[trailHistory.length - 1];
        if (gi !== lastShown && trailHistory.indexOf(gi) !== -1) trailHistory = [];
    }
    revealGroup(gi);
    if (trailOn && trailHistory[trailHistory.length - 1] !== gi) trailHistory.push(gi);
    updateCounter();
}
function restoreView() { revealGroup(currentView); updateCounter(); }
function finishPlayback() {
    playing = false;
    currentView = playbackOrigin;
    if (trailOn) trailHistory = _browseTrail(currentView);
    restoreView();
    setPlayIcon();
}

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

function filterEventsForGroup(allEvents, gi) {
    if (!bridge || typeof bridge.filterEventsForGroup !== "function") return [];
    return bridge.filterEventsForGroup(allEvents, gi);
}

function reorderEventsFrom(allEvents, startGi, total) {
    if (!bridge || typeof bridge.reorderEventsFrom !== "function") {
        return { events: [], seqMap: [] };
    }
    return bridge.reorderEventsFrom(allEvents, startGi, total);
}

if (totalGroups > 0) {
    revealGroup(0);
    updateCounter();
}

if (prevBtn) {
    prevBtn.addEventListener("click", function() {
        if (playing) return;
        currentView = (currentView - 1 + totalGroups) % totalGroups;
        if (trailOn) trailHistory = _browseTrail(currentView);
        revealGroup(currentView);
        updateCounter();
    });
}
if (nextBtn) {
    nextBtn.addEventListener("click", function() {
        if (playing) return;
        currentView = (currentView + 1) % totalGroups;
        if (trailOn) trailHistory = _browseTrail(currentView);
        revealGroup(currentView);
        updateCounter();
    });
}


var _timerId = null;

function _stopAll() {
    if (_timerId) { clearTimeout(_timerId); _timerId = null; }
    if (bridge) bridge.stop();
}

function _runAnimation(step) {
    if (!playing) return;
    if (step >= totalGroups) {
        if (loopCtl.enabled && (loopCtl.infinite || loopCtl.cyclesRemaining > 1)) {
            if (!loopCtl.infinite) loopCtl.cyclesRemaining -= 1;
            if (trailOn) trailHistory = [];
            dimAllNodes(); hideAllShapeEdges();
            _timerId = setTimeout(function() { _runAnimation(0); }, stepMs);
        } else {
            _timerId = setTimeout(function() { finishPlayback(); }, pauseMs);
        }
        return;
    }
    var gi = (currentView + step) % totalGroups;
    revealAndTrack(gi);
    _timerId = setTimeout(function() { _runAnimation(step + 1); }, stepMs);
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
    var allEvts = ok && bridge ? bridge.getEvents() : [];

    if (ok && allEvts.length > 0) {
        await bridge.resumeAudio();
        var solo = soloBox && soloBox.checked;
        playbackOrigin = currentView;
        playing = true;
        setStopIcon();
        if (trailOn) trailHistory = [];

        if (solo) {
            var soloEvts = filterEventsForGroup(allEvts, currentView);
            revealAndTrack(currentView);
            await bridge.play(soloEvts, {
                loop: loopCtl.schedulerValue(),
                onEvent: function() {},
                onFinish: function() { finishPlayback(); },
            });
        } else {
            var reordered = reorderEventsFrom(allEvts, currentView, totalGroups);
            dimAllNodes();
            hideAllShapeEdges();
            await bridge.play(reordered.events, {
                loop: loopCtl.schedulerValue(),
                onEvent: function(stepIdx) {
                    if (playing) revealAndTrack(reordered.seqMap[stepIdx]);
                },
                onFinish: function() { finishPlayback(); },
            });
        }
    } else {
        playbackOrigin = currentView;
        playing = true;
        setStopIcon();
        if (trailOn) trailHistory = [];
        dimAllNodes();
        hideAllShapeEdges();
        loopCtl.rearm();
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
