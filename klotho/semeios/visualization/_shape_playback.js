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

function _eventEnd(ev) {
    var pf = ev.pfields || {};
    if (ev.duration != null) return ev.start + ev.duration;
    if (pf.dur != null) return ev.start + pf.dur;
    if (ev.type === "release") return ev.start + 0.5;
    return ev.start + 0.5;
}

function filterEventsForGroup(allEvents, gi) {
    var filtered = [];
    var minStart = Infinity;
    for (var i = 0; i < allEvents.length; i++) {
        if (allEvents[i]._stepIndex === gi) {
            if (allEvents[i].start < minStart) minStart = allEvents[i].start;
            filtered.push(allEvents[i]);
        }
    }
    if (minStart === Infinity) minStart = 0;
    var result = [];
    for (var i = 0; i < filtered.length; i++) {
        var e = {};
        for (var k in filtered[i]) e[k] = filtered[i][k];
        e.start = filtered[i].start - minStart;
        e._stepIndex = 0;
        result.push(e);
    }
    return result;
}

function reorderEventsFrom(allEvents, startGi, total) {
    var buckets = [];
    for (var g = 0; g < total; g++) buckets.push([]);
    for (var i = 0; i < allEvents.length; i++) {
        var si = allEvents[i]._stepIndex;
        if (si >= 0 && si < total) buckets[si].push(allEvents[i]);
    }
    var groupStarts = [];
    for (var g = 0; g < total; g++) {
        var mn = Infinity;
        for (var i = 0; i < buckets[g].length; i++) {
            if (buckets[g][i].start < mn) mn = buckets[g][i].start;
        }
        groupStarts.push(mn === Infinity ? 0 : mn);
    }
    var groupDurs = [];
    for (var g = 0; g < total; g++) {
        var mx = 0;
        for (var i = 0; i < buckets[g].length; i++) {
            var end = _eventEnd(buckets[g][i]);
            if (end > mx) mx = end;
        }
        groupDurs.push(mx - groupStarts[g]);
    }
    var result = [];
    var cursor = 0;
    var seqMap = [];
    for (var step = 0; step < total; step++) {
        var gi = (startGi + step) % total;
        seqMap.push(gi);
        var base = groupStarts[gi];
        for (var i = 0; i < buckets[gi].length; i++) {
            var e = {};
            for (var k in buckets[gi][i]) e[k] = buckets[gi][i][k];
            e.start = cursor + (buckets[gi][i].start - base);
            e._stepIndex = step;
            result.push(e);
        }
        cursor += groupDurs[gi];
    }
    return { events: result, seqMap: seqMap };
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

var _aPlayer = null, _aInstruments = null;
var _ssScheduler = null, _ssSonic = null, _ssReady = false;
var _timerId = null;

function _canToneAudio() {
    if (_aPlayer) return true;
    if (!audioPayload || typeof Tone === "undefined"
        || typeof globalThis.KLOTHO_BUILD_INSTRUMENTS !== "function"
        || typeof globalThis.KlothoPlayer === "undefined") return false;
    _aInstruments = globalThis.KLOTHO_BUILD_INSTRUMENTS(audioPayload.instruments || {});
    _aPlayer = KlothoPlayer.create();
    return true;
}

async function _ensureSSReady() {
    if (_ssReady) return true;
    if (typeof __ensureSuperSonic !== "function") return false;
    try {
        var sonic = await __ensureSuperSonic();
        _ssSonic = sonic;
        _ssScheduler = new BrowserScheduler({
            sonic: sonic,
            manifest: (typeof __klothoManifest !== "undefined") ? __klothoManifest : { synths: {}, inserts: {} },
            ringTime: __RING_TIME__,
        });
        _ssReady = true;
        return true;
    } catch(e) {
        return false;
    }
}

function _getSSEvents() {
    if (!audioPayload) return [];
    var raw = Array.isArray(audioPayload) ? audioPayload : (audioPayload.events || []);
    return raw.filter(function(e) {
        return e.type === "new" || e.type === "set" || e.type === "release";
    });
}

function _stopAll() {
    if (_timerId) { clearTimeout(_timerId); _timerId = null; }
    if (_ssScheduler && _ssScheduler.isPlaying) _ssScheduler.stop();
    if (_aPlayer && _aPlayer.isPlaying()) _aPlayer.stop();
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
    if (engineType === "supersonic") {
        if (playing) {
            _stopAll();
            finishPlayback();
            return;
        }

        var ok = await _ensureSSReady();
        var allEvts = ok ? _getSSEvents() : [];

        if (ok && allEvts.length > 0) {
            if (_ssSonic && _ssSonic.audioContext && _ssSonic.audioContext.state === "suspended") {
                await _ssSonic.audioContext.resume();
            }
            var solo = soloBox && soloBox.checked;
            playbackOrigin = currentView;
            playing = true; setStopIcon();

            if (solo) {
                var soloEvts = filterEventsForGroup(allEvts, currentView);
                revealAndTrack(currentView);
                var _soloFirst = true;
                function ssLoopSolo() {
                    _ssScheduler.play(soloEvts, {
                        _skipStop: !_soloFirst,
                        onEvent: function() {},
                        onFinish: function() {
                            if (looping && playing) ssLoopSolo();
                            else finishPlayback();
                        }
                    });
                    _soloFirst = false;
                }
                ssLoopSolo();
            } else {
                var reordered = reorderEventsFrom(allEvts, currentView, totalGroups);
                dimAllNodes(); hideAllShapeEdges();
                var _seqFirst = true;
                function ssLoopSeq() {
                    _ssScheduler.play(reordered.events, {
                        _skipStop: !_seqFirst,
                        onEvent: function(stepIdx) { if (playing) revealAndTrack(reordered.seqMap[stepIdx]); },
                        onFinish: function() {
                            if (looping && playing) {
                                dimAllNodes(); hideAllShapeEdges();
                                ssLoopSeq();
                            } else {
                                finishPlayback();
                            }
                        }
                    });
                    _seqFirst = false;
                }
                ssLoopSeq();
            }
        } else {
            if (playing) {
                _stopAll();
                finishPlayback();
            } else {
                playbackOrigin = currentView;
                playing = true; setStopIcon(); dimAllNodes(); hideAllShapeEdges();
                _runAnimation(0);
            }
        }
    } else {
        if (_canToneAudio()) {
            if (_aPlayer.isPlaying()) { _aPlayer.stop(); return; }
            var solo = soloBox && soloBox.checked;
            playbackOrigin = currentView;
            playing = true; setStopIcon();
            if (solo) {
                var soloEvents = filterEventsForGroup(audioPayload.events || [], currentView);
                revealAndTrack(currentView);
                await _aPlayer.play(soloEvents, _aInstruments, {
                    loop: looping,
                    onEvent: function() {},
                    onStop: function() { finishPlayback(); },
                    onFinish: function() { finishPlayback(); }
                });
            } else {
                var reordered = reorderEventsFrom(audioPayload.events || [], currentView, totalGroups);
                dimAllNodes(); hideAllShapeEdges();
                await _aPlayer.play(reordered.events, _aInstruments, {
                    loop: looping,
                    onEvent: function(stepIdx) { revealAndTrack(reordered.seqMap[stepIdx]); },
                    onStop: function() { finishPlayback(); },
                    onFinish: function() { finishPlayback(); }
                });
            }
        } else {
            if (playing) {
                _stopAll();
                finishPlayback();
            } else {
                playbackOrigin = currentView;
                playing = true; setStopIcon(); dimAllNodes(); hideAllShapeEdges();
                _runAnimation(0);
            }
        }
    }
};

var _orphanCheckId = setInterval(function() {
    if (toggleBtn && !toggleBtn.isConnected) {
        _stopAll();
        playing = false;
        clearInterval(_orphanCheckId);
    }
}, 1000);
