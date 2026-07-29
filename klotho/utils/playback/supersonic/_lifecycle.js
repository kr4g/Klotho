// Shared SuperSonic engine lifecycle: boot, SynthDef loading, sample loading.
// Installed once per page; every playback surface (standalone widget,
// animated-figure bridge) goes through these instead of carrying its own
// copies. Session state (loadedDefs, sampleMap, bufnum allocator) lives on
// globalThis.__klothoSonic and is shared across widgets.
(() => {
    if (typeof globalThis.KlothoEngineLifecycle !== "undefined") return;

    function ensureSonic(ssConfig) {
        if (typeof globalThis.__ensureSuperSonic === "function") {
            return globalThis.__ensureSuperSonic();
        }
        var state = globalThis.__klothoSonic;
        if (state && state.instance) return Promise.resolve(state.instance);
        if (state && state.promise) return state.promise;
        if (!ssConfig) return Promise.resolve(null);
        state = { instance: null, promise: null, loadedDefs: new Set() };
        globalThis.__klothoSonic = state;
        state.promise = (async function() {
            try {
                var mod = await import(ssConfig.baseURL.replace("/dist/", ""));
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

    async function loadDefs(sonic, neededSynthdefs) {
        if (!neededSynthdefs || !neededSynthdefs.length) return;
        var state = globalThis.__klothoSonic;
        if (!state.loadedDefs) state.loadedDefs = new Set();
        var loaded = state.loadedDefs;
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
    async function loadSamples(sonic, sampleAssets) {
        if (!sampleAssets) return;
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
            } catch(e) {
                // Leave the name unmapped (the scheduler warns per event
                // batch), but say why here — a corrupt/undecodable wav
                // otherwise plays as pure silence with zero feedback.
                console.warn('[Klotho] sample load failed: ' + name, e);
            }
        }
    }

    globalThis.KlothoEngineLifecycle = {
        ensureSonic: ensureSonic,
        loadDefs: loadDefs,
        loadSamples: loadSamples,
    };
})();
