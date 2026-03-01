// Shape playback controller for animated Klotho shape figures.
// Python replaces: __WID__, __DUR_MS__, __ENGINE_TYPE__, __RING_TIME__, __TOTAL_GROUPS__
// Caller must define: groupNodeIndices, groupEdgeIds, shapeColors,
//                     allShapeEdgeIds, allNodeIds, dimmedColor, audioPayload

var toggleBtn = document.getElementById("__WID___toggle");
var iconEl    = document.getElementById("__WID___icon");
var loopBtn   = document.getElementById("__WID___loop");
var loopSvg   = document.getElementById("__WID___loop_svg");
var prevBtn   = document.getElementById("__WID___prev");
var nextBtn   = document.getElementById("__WID___next");
var counterEl = document.getElementById("__WID___counter");
var soloBox   = document.getElementById("__WID___solo");

var looping = false, playing = false;
var currentView = 0;
var playbackOrigin = 0;
var engineType = "__ENGINE_TYPE__";
var totalGroups = __TOTAL_GROUPS__;
var durMs = __DUR_MS__;
var bridge = (typeof globalThis.KlothoPlaybackBridge === "function")
    ? globalThis.KlothoPlaybackBridge({
        engine: engineType,
        audioPayload: audioPayload,
        ringTime: __RING_TIME__,
    })
    : null;

function updateCounter() {
    if (counterEl) counterEl.textContent = (currentView + 1) + " / " + totalGroups;
}

function dimAllNodes() {
    for (var i = 0; i < allNodeIds.length; i++) {
        var el = document.getElementById(allNodeIds[i]);
        if (el) el.setAttribute("fill", dimmedColor);
    }
}
function hideAllShapeEdges() {
    for (var i = 0; i < allShapeEdgeIds.length; i++) {
        var el = document.getElementById(allShapeEdgeIds[i]);
        if (el) el.style.display = "none";
    }
}
function revealGroup(gi) {
    dimAllNodes();
    hideAllShapeEdges();
    if (gi < 0 || gi >= totalGroups) return;
    var col = shapeColors[gi] || "white";
    var nodeIdxs = groupNodeIndices[gi] || [];
    for (var i = 0; i < nodeIdxs.length; i++) {
        var idx = nodeIdxs[i];
        if (idx >= 0 && idx < allNodeIds.length) {
            var el = document.getElementById(allNodeIds[idx]);
            if (el) el.setAttribute("fill", col);
        }
    }
    var edgeIds = groupEdgeIds[gi] || [];
    for (var i = 0; i < edgeIds.length; i++) {
        var el = document.getElementById(edgeIds[i]);
        if (el) el.style.display = "";
    }
}
function revealAndTrack(gi) {
    currentView = gi;
    revealGroup(gi);
    updateCounter();
}
function restoreView() { revealGroup(currentView); updateCounter(); }
function finishPlayback() { playing = false; currentView = playbackOrigin; restoreView(); setPlayIcon(); }

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
    prevBtn.onclick = function() {
        if (playing) return;
        currentView = (currentView - 1 + totalGroups) % totalGroups;
        revealGroup(currentView);
        updateCounter();
    };
}
if (nextBtn) {
    nextBtn.onclick = function() {
        if (playing) return;
        currentView = (currentView + 1) % totalGroups;
        revealGroup(currentView);
        updateCounter();
    };
}

loopBtn.onclick = function() {
    looping = !looping;
    loopBtn.style.opacity = looping ? "1" : "0.5";
    loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0");
};

var _timerId = null;

function _stopAll() {
    if (_timerId) { clearTimeout(_timerId); _timerId = null; }
    if (bridge) bridge.stop();
}

function _runAnimation(step) {
    if (!playing) return;
    if (step >= totalGroups) {
        if (looping) {
            dimAllNodes(); hideAllShapeEdges();
            _timerId = setTimeout(function() { _runAnimation(0); }, durMs);
        } else { finishPlayback(); }
        return;
    }
    var gi = (currentView + step) % totalGroups;
    revealAndTrack(gi);
    _timerId = setTimeout(function() { _runAnimation(step + 1); }, durMs);
}

toggleBtn.onclick = async function() {
    if (playing) {
        _stopAll();
        finishPlayback();
        return;
    }

    var ok = bridge ? await bridge.ensureReady() : false;
    var allEvts = ok && bridge ? bridge.getEvents() : [];

    if (ok && allEvts.length > 0) {
        await bridge.resumeAudio();
        var solo = soloBox && soloBox.checked;
        playbackOrigin = currentView;
        playing = true;
        setStopIcon();

        if (solo) {
            var soloEvts = filterEventsForGroup(allEvts, currentView);
            revealAndTrack(currentView);
            await bridge.play(soloEvts, {
                loop: looping,
                onEvent: function() {},
                onFinish: function() { finishPlayback(); },
            });
        } else {
            var reordered = reorderEventsFrom(allEvts, currentView, totalGroups);
            dimAllNodes();
            hideAllShapeEdges();
            await bridge.play(reordered.events, {
                loop: looping,
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
        dimAllNodes();
        hideAllShapeEdges();
        _runAnimation(0);
    }
};

var _orphanCheckId = setInterval(function() {
    if (toggleBtn && !toggleBtn.isConnected) {
        _stopAll();
        playing = false;
        clearInterval(_orphanCheckId);
    }
}, 1000);
