// SuperSonic standalone playback widget.
// Python replaces: __WID__, __EVENTS_JSON__, __NEEDED_JSON__,
//                  __SS_CONFIG_JSON__, __META_JSON__,
//                  __CONTROL_DATA_JSON__, __SAMPLES_JSON__, __RING_TIME__,
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
    var allEvents = __EVENTS_JSON__;
    var neededSynthdefs = __NEEDED_JSON__;
    var ssConfig = __SS_CONFIG_JSON__;
    var meta = __META_JSON__;
    var controlData = __CONTROL_DATA_JSON__;
    var sampleAssets = __SAMPLES_JSON__;

    var loopCtl = KlothoLoopControl(loopBtn, loopSvg, "__LOOP_MODE__", "__LOOP_COUNT__",
                                    "__LOOP_ENABLED__" === "true");
    var scheduler = null;
    var ready = false;
    var _loadPromise = null;

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

    loopCtl.onToggle = function() {
        if (scheduler && scheduler.isPlaying) {
            doPlay();
        }
    };

    function ensureSharedSonic() {
        if (typeof globalThis.__ensureSuperSonic === "function") {
            return globalThis.__ensureSuperSonic();
        }
        var state = globalThis.__klothoSonic;
        if (state && state.instance) return Promise.resolve(state.instance);
        if (state && state.promise) return state.promise;
        state = { instance: null, promise: null, loadedDefs: new Set() };
        globalThis.__klothoSonic = state;
        state.promise = (async function() {
            try {
                var mod = await import(ssConfig.baseURL.replace("/dist/",""));
                globalThis.SuperSonic = mod.SuperSonic;
                var s = new mod.SuperSonic(ssConfig);
                await s.init();
                state.instance = s;
                return s;
            } catch(e) {
                return null;
            }
        })();
        return state.promise;
    }

    async function loadDefs(sonic) {
        var loaded = globalThis.__klothoSonic.loadedDefs;
        var registry = globalThis.__klothoSynthdefAssets || {};
        for (var i = 0; i < neededSynthdefs.length; i++) {
            var name = neededSynthdefs[i];
            if (loaded.has(name)) continue;
            var b64 = registry[name];
            if (b64) {
                var bytes = Uint8Array.from(atob(b64), function(c) { return c.charCodeAt(0); });
                try { await sonic.loadSynthDef(bytes); loaded.add(name); } catch(e) {}
            } else {
                try { await sonic.loadSynthDef(name); loaded.add(name); } catch(e) {}
            }
        }
    }

    // Load referenced samples into scsynth buffers once per session.
    // The name->bufnum map is shared across widgets and never freed;
    // bufnums come from the same shared allocator the control-envelope
    // path uses, so the two can never collide.
    async function loadSamples(sonic) {
        var state = globalThis.__klothoSonic;
        if (!state.sampleMap) state.sampleMap = {};
        if (state._nextBufnum == null) state._nextBufnum = 0;
        for (var name in sampleAssets) {
            if (!sampleAssets.hasOwnProperty(name)) continue;
            if (state.sampleMap[name] != null) continue;
            var b64 = sampleAssets[name].b64;
            var bytes = Uint8Array.from(atob(b64), function(c) { return c.charCodeAt(0); });
            var bufnum = state._nextBufnum++;
            try {
                await sonic.loadSample(bufnum, bytes.buffer);
                state.sampleMap[name] = bufnum;
            } catch(e) {}
        }
    }

    function ensureReady() {
        if (ready) return Promise.resolve(true);
        if (_loadPromise) return _loadPromise;
        _loadPromise = (async function() {
            var sonic = await ensureSharedSonic();
            if (!sonic) {
                _loadPromise = null;
                return false;
            }
            await loadDefs(sonic);
            await loadSamples(sonic);
            scheduler = new BrowserScheduler({
                sonic: sonic,
                manifest: __MANIFEST_JSON__,
                ringTime: __RING_TIME__,
            });
            // Pay the control-envelope buffer upload at init, not on
            // press-to-play; replays reuse the same buffer.
            if (controlData && controlData.bufferB64
                    && typeof scheduler.preloadControlBuffer === "function") {
                try { scheduler.preloadControlBuffer(controlData); } catch(e) {}
            }
            ready = true;
            return true;
        })();
        return _loadPromise;
    }

    ensureReady();

    function doPlay() {
        var evts = allEvents;
        if (evts.length === 0) return;

        setStopIcon();
        scheduler.play(evts, {
            meta: meta,
            controlData: controlData,
            loop: loopCtl.schedulerValue(),
            onFinish: function() {
                setPlayIcon();
            }
        });
    }

    toggleBtn.addEventListener("click", async function() {
        if (scheduler && scheduler.isPlaying) {
            await scheduler.stop();
            setPlayIcon();
            return;
        }
        if (_loadPromise && !ready) {
            _loadPromise = null;
            var sharedState = globalThis.__klothoSonic;
            if (sharedState && !sharedState.instance) {
                sharedState.promise = null;
            }
        }
        var ok = await ensureReady();
        if (!ok) return;
        var sonic = globalThis.__klothoSonic.instance;
        if (sonic.audioContext && sonic.audioContext.state === "suspended") {
            await sonic.audioContext.resume();
        }
        doPlay();
    });

    var _orphanCheckId = setInterval(function() {
        if (toggleBtn && !toggleBtn.isConnected) {
            if (scheduler) {
                scheduler.stop();
                if (typeof scheduler.releaseControlPreload === "function") {
                    scheduler.releaseControlPreload();
                }
            }
            clearInterval(_orphanCheckId);
        }
    }, 1000);
})();
