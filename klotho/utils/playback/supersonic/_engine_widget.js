// SuperSonic standalone playback widget.
// Python replaces: __WID__, __EVENTS_JSON__, __SYNTHDEF_ASSETS_JSON__,
//                  __NEEDED_JSON__, __SS_CONFIG_JSON__, __META_JSON__,
//                  __CONTROL_DATA_JSON__, __RING_TIME__

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
    var synthdefAssets = __SYNTHDEF_ASSETS_JSON__;
    var neededSynthdefs = __NEEDED_JSON__;
    var ssConfig = __SS_CONFIG_JSON__;
    var meta = __META_JSON__;
    var controlData = __CONTROL_DATA_JSON__;

    var looping = false;
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

    loopBtn.onclick = async function() {
        looping = !looping;
        loopBtn.style.opacity = looping ? "1" : "0.5";
        loopSvg.setAttribute("stroke", looping ? "#4ade80" : "#a0a0a0");
        if (scheduler && scheduler.isPlaying) {
            doPlay();
        }
    };

    function ensureSharedSonic() {
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
        for (var name in synthdefAssets) {
            if (!synthdefAssets.hasOwnProperty(name)) continue;
            if (loaded.has(name)) continue;
            var b64 = synthdefAssets[name];
            var bytes = Uint8Array.from(atob(b64), function(c) { return c.charCodeAt(0); });
            await sonic.loadSynthDef(bytes);
            loaded.add(name);
        }
        for (var i = 0; i < neededSynthdefs.length; i++) {
            var sname = neededSynthdefs[i];
            if (loaded.has(sname)) continue;
            if (synthdefAssets[sname]) continue;
            try {
                await sonic.loadSynthDef(sname);
                loaded.add(sname);
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
            scheduler = new BrowserScheduler({
                sonic: sonic,
                manifest: {},
                ringTime: __RING_TIME__,
            });
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
            loop: looping,
            onFinish: function() {
                setPlayIcon();
            }
        });
    }

    toggleBtn.onclick = async function() {
        if (scheduler && scheduler.isPlaying) {
            await scheduler.stop();
            setPlayIcon();
            return;
        }
        var ok = await ensureReady();
        if (!ok) return;
        var sonic = globalThis.__klothoSonic.instance;
        if (sonic.audioContext && sonic.audioContext.state === "suspended") {
            await sonic.audioContext.resume();
        }
        doPlay();
    };

    var _orphanCheckId = setInterval(function() {
        if (toggleBtn && !toggleBtn.isConnected) {
            if (scheduler) scheduler.stop();
            clearInterval(_orphanCheckId);
        }
    }, 1000);
})();
