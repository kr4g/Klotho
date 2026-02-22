// Shared playback controller for animated Klotho figures.
// Python replaces placeholders: __WID__, __DUR_MS__, __BOUNDARY_OP__
// Caller must define: audioPayload, totalSteps, onStep, onBeforePlay, onReset

var toggleBtn = document.getElementById("__WID___toggle");
var iconEl    = document.getElementById("__WID___icon");
var loopBtn   = document.getElementById("__WID___loop");
var loopSvg   = document.getElementById("__WID___loop_svg");
var looping = false, playing = false;

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

if (audioPayload && typeof Tone !== "undefined") {
    var events = audioPayload.events || [];
    var instruments = globalThis.KLOTHO_BUILD_INSTRUMENTS(audioPayload.instruments || {});
    var player = KlothoPlayer.create();
    toggleBtn.onclick = async function() {
        if (player.isPlaying()) { player.stop(); return; }
        playing = true; setStopIcon(); onBeforePlay();
        await player.play(events, instruments, {
            loop: looping,
            onEvent:  function(stepIdx) { onStep(stepIdx); },
            onStop:   function() { finishPlayback(); },
            onFinish: function() { finishPlayback(); }
        });
    };
} else {
    var durMs = __DUR_MS__;
    var timerId = null;
    function runAnimation(stepIdx) {
        if (!playing) return;
        if (stepIdx __BOUNDARY_OP__ totalSteps) {
            if (looping) {
                onBeforePlay();
                timerId = setTimeout(function(){ runAnimation(0); }, durMs);
            } else { finishPlayback(); }
            return;
        }
        onStep(stepIdx);
        timerId = setTimeout(function(){ runAnimation(stepIdx + 1); }, durMs);
    }
    toggleBtn.onclick = function() {
        if (playing) {
            playing = false;
            if (timerId) { clearTimeout(timerId); timerId = null; }
            finishPlayback();
        } else {
            playing = true; setStopIcon(); onBeforePlay(); runAnimation(0);
        }
    };
}
