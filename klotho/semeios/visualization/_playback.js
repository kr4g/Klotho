// Shared playback controller for animated Klotho figures.
// Python replaces placeholders: __WID__, __DUR_MS__, __BOUNDARY_OP__, __ENGINE_TYPE__
// Caller must define: audioPayload, totalSteps, onStep, onBeforePlay, onReset

var toggleBtn = document.getElementById("__WID___toggle");
var iconEl    = document.getElementById("__WID___icon");
var loopBtn   = document.getElementById("__WID___loop");
var loopSvg   = document.getElementById("__WID___loop_svg");
var looping = false, playing = false;
var engineType = "__ENGINE_TYPE__";

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

loopBtn.onclick = function() {
    looping = !looping;
    loopBtn.style.opacity = looping ? "1" : "0.5";
    loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0");
};

var _aPlayer = null, _aInstruments = null;
var _ssScheduler = null, _ssSonic = null, _ssReady = false;
var _timerId = null;
var durMs = __DUR_MS__;

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
    var raw = audioPayload.events || audioPayload;
    if (!Array.isArray(raw)) return [];
    return raw.filter(function(e) {
        return e.type === "new" || e.type === "set" || e.type === "release";
    });
}

function _runAnimation(stepIdx) {
    if (!playing) return;
    if (stepIdx __BOUNDARY_OP__ totalSteps) {
        if (looping) {
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
    if (_ssScheduler && _ssScheduler.isPlaying) _ssScheduler.stop();
    if (_aPlayer && _aPlayer.isPlaying()) _aPlayer.stop();
}

toggleBtn.onclick = async function() {
    if (engineType === "supersonic") {
        if (playing) {
            _stopAll();
            finishPlayback();
            return;
        }

        var ok = await _ensureSSReady();
        var evts = ok ? _getSSEvents() : [];

        if (ok && evts.length > 0) {
            if (_ssSonic.audioContext && _ssSonic.audioContext.state === "suspended") {
                await _ssSonic.audioContext.resume();
            }
            playing = true; setStopIcon(); onBeforePlay();
            var _ssFirstPlay = true;
            function ssLoopPlay() {
                _ssScheduler.play(evts, {
                    _skipStop: !_ssFirstPlay,
                    onEvent: function(stepIdx) { if (playing) onStep(stepIdx); },
                    onFinish: function() {
                        if (looping && playing) {
                            onBeforePlay();
                            ssLoopPlay();
                        } else {
                            finishPlayback();
                        }
                    }
                });
                _ssFirstPlay = false;
            }
            ssLoopPlay();
        } else {
            if (playing) {
                _stopAll();
                finishPlayback();
            } else {
                playing = true; setStopIcon(); onBeforePlay(); _runAnimation(0);
            }
        }
    } else {
        if (_canToneAudio()) {
            if (_aPlayer.isPlaying()) { _aPlayer.stop(); return; }
            playing = true; setStopIcon(); onBeforePlay();
            await _aPlayer.play(audioPayload.events || [], _aInstruments, {
                loop: looping,
                onEvent:  function(stepIdx) { onStep(stepIdx); },
                onStop:   function() { finishPlayback(); },
                onFinish: function() { finishPlayback(); }
            });
        } else {
            if (playing) {
                playing = false;
                if (_timerId) { clearTimeout(_timerId); _timerId = null; }
                finishPlayback();
            } else {
                playing = true; setStopIcon(); onBeforePlay(); _runAnimation(0);
            }
        }
    }
};
