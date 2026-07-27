// SuperSonic standalone playback widget — a thin consumer of the shared
// KlothoPlaybackBridge (engine lifecycle, scheduler, control-buffer
// preload all live in the bridge; this file only wires the buttons).
// Python replaces: __WID__, __EVENTS_JSON__, __NEEDED_JSON__,
//                  __SS_CONFIG_JSON__, __META_JSON__,
//                  __CONTROL_DATA_JSON__, __SAMPLES_JSON__,
//                  __MANIFEST_JSON__, __RING_TIME__,
//                  __LOOP_MODE__, __LOOP_COUNT__, __LOOP_ENABLED__

(function __klothoSSInit___WID__() {
    var wid = "__WID__";
    var toggleBtn = document.getElementById(wid + "_toggle");
    if (!toggleBtn) {
        setTimeout(__klothoSSInit___WID__, 50);
        return;
    }
    var iconEl = document.getElementById(wid + "_icon");
    var loopBtn = document.getElementById(wid + "_loop");
    var loopSvg = document.getElementById(wid + "_loop_svg");

    var loopCtl = KlothoLoopControl(loopBtn, loopSvg, "__LOOP_MODE__", "__LOOP_COUNT__",
                                    "__LOOP_ENABLED__" === "true");
    var bridge = globalThis.KlothoPlaybackBridge({
        audioPayload: { events: __EVENTS_JSON__ },
        ringTime: __RING_TIME__,
        neededSynthdefs: __NEEDED_JSON__,
        sampleAssets: __SAMPLES_JSON__,
        controlData: __CONTROL_DATA_JSON__,
        meta: __META_JSON__,
        ssConfig: __SS_CONFIG_JSON__,
        manifest: __MANIFEST_JSON__,
    });

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

    function doPlay() {
        if (!bridge.hasPlayableEvents()) return;
        setStopIcon();
        bridge.play(null, {
            loop: loopCtl.schedulerValue(),
            onFinish: function() { setPlayIcon(); },
        });
    }

    loopCtl.onToggle = function() {
        if (bridge.isPlaying()) {
            doPlay();
        }
    };

    // Eager warm-up: boot + defs + samples + control-buffer preload start
    // immediately; the (initially disabled/greyed) play button enables
    // when the engine is ready.
    KlothoGateToggle(toggleBtn, bridge.ensureReady());

    toggleBtn.addEventListener("click", async function() {
        if (bridge.isPlaying()) {
            await bridge.stop();
            setPlayIcon();
            return;
        }
        // A failed session boot leaves a resolved-null promise behind;
        // clearing it lets ensureReady retry the boot from scratch.
        var _ss = globalThis.__klothoSonic;
        if (_ss && !_ss.instance && _ss.promise) { _ss.promise = null; }
        var ok = await bridge.ensureReady();
        if (!ok) return;
        await bridge.resumeAudio();
        doPlay();
    });

    var _orphanCheckId = setInterval(function() {
        if (toggleBtn && !toggleBtn.isConnected) {
            bridge.stop();
            bridge.releaseControlPreload();
            clearInterval(_orphanCheckId);
        }
    }, 1000);
})();
