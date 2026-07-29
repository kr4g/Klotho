(() => {
  // Version-skew guard: saved notebook outputs from klotho <= 10.14.0
  // install an older bridge under KlothoPlaybackBridge (first-wins) whose
  // config contract differs (an `engine` key defaulting to the removed
  // Tone.js path). Widgets rendered after those stale outputs must get
  // THIS build, so the install guard keys on the versioned name and the
  // public name is overwritten unconditionally. V3 (10.16, adds record())
  // is a strict superset of V2, so it also claims the V2 name — otherwise
  // a stale 10.15 output rendered after a 10.16 widget would see V2 unset
  // and clobber the public name with a build lacking record().
  if (typeof globalThis.__klothoPlaybackBridgeV3 !== "undefined") return;

  function buildBridge(config) {
    var audioPayload = config.audioPayload || null;
    var _payloadObj = (audioPayload && !Array.isArray(audioPayload)) ? audioPayload : {};
    var ringTime = config.ringTime != null ? config.ringTime : 5;
    var neededSynthdefs = config.neededSynthdefs || null;
    // Dict payloads (plot(score)) may carry these inline, since the
    // figure templates only inject one JSON blob; explicit config wins.
    var sampleAssets = config.sampleAssets || _payloadObj.sampleAssets || null;
    var controlData = config.controlData || _payloadObj.controlData || null;
    var meta = config.meta || _payloadObj.meta || null;
    var ssConfig = config.ssConfig || null;
    var manifest = config.manifest || null;

    var _ssScheduler = null;
    var _ssSonic = null;
    var _ssReady = false;
    var _pause = 0.0;

    if (audioPayload && typeof audioPayload === "object" && audioPayload.pause != null) {
      var pauseVal = Number(audioPayload.pause);
      if (!Number.isNaN(pauseVal) && pauseVal > 0) _pause = pauseVal;
    }

    function _rawEvents() {
      if (!audioPayload) return [];
      if (Array.isArray(audioPayload)) return audioPayload;
      return Array.isArray(audioPayload.events) ? audioPayload.events : [];
    }

    function _scEvents() {
      return _rawEvents().filter(function(e) {
        return e && (e.type === "new" || e.type === "set" || e.type === "release");
      });
    }

    async function _ensureSSReady() {
      if (_ssReady) return true;
      try {
        var lifecycle = globalThis.KlothoEngineLifecycle;
        var sonic = null;
        if (lifecycle) {
          sonic = await lifecycle.ensureSonic(ssConfig);
        } else if (typeof globalThis.__ensureSuperSonic === "function") {
          sonic = await globalThis.__ensureSuperSonic();
        }
        if (!sonic) {
          var state = globalThis.__klothoSonic;
          if (state && state.instance) { sonic = state.instance; }
          else if (state && state.promise) { sonic = await state.promise; }
        }
        if (!sonic) return false;
        if (lifecycle) {
          await lifecycle.loadDefs(sonic, neededSynthdefs);
          await lifecycle.loadSamples(sonic, sampleAssets);
        }
        _ssSonic = sonic;
        _ssScheduler = new globalThis.BrowserScheduler({
          sonic: sonic,
          manifest: manifest
            || ((typeof globalThis.__klothoManifest !== "undefined") ? globalThis.__klothoManifest : {}),
          ringTime: ringTime,
        });
        // Pay the control-envelope buffer upload at init, not on
        // press-to-play; replays reuse the same buffer.
        if (controlData && controlData.bufferB64
            && typeof _ssScheduler.preloadControlBuffer === "function") {
          try { _ssScheduler.preloadControlBuffer(controlData); } catch(e) {}
        }
        _ssReady = true;
        return true;
      } catch(e) {
        return false;
      }
    }

    async function ensureReady() {
      return _ensureSSReady();
    }

    function hasPlayableEvents() {
      return _scEvents().length > 0;
    }

    function eventEnd(ev) {
      // Prefer the SuperSonic top-level ``dur`` (new event contract).
      // Falls back to the legacy in-pfields ``dur`` (still used by
      // ``_perc_note`` events) so existing payloads keep working.
      if (!ev) return 0;
      if (typeof ev.dur === "number") return ev.start + ev.dur;
      if (ev.duration != null) return ev.start + ev.duration;
      var pf = ev.pfields || {};
      if (pf.dur != null) return ev.start + pf.dur;
      if (ev.type === "release") return ev.start;
      return ev.start || 0;
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
      for (var j = 0; j < filtered.length; j++) {
        var e = {};
        for (var k in filtered[j]) e[k] = filtered[j][k];
        e.start = filtered[j].start - minStart;
        e._stepIndex = 0;
        result.push(e);
      }
      return result;
    }

    function reorderEventsFrom(allEvents, startGi, total, gap) {
      var gapSec = typeof gap === "number" ? Math.max(0, gap) : _pause;
      var buckets = [];
      for (var g = 0; g < total; g++) buckets.push([]);
      for (var i = 0; i < allEvents.length; i++) {
        var si = allEvents[i]._stepIndex;
        if (si >= 0 && si < total) buckets[si].push(allEvents[i]);
      }
      var groupStarts = [];
      for (var g1 = 0; g1 < total; g1++) {
        var mn = Infinity;
        for (var i1 = 0; i1 < buckets[g1].length; i1++) {
          if (buckets[g1][i1].start < mn) mn = buckets[g1][i1].start;
        }
        groupStarts.push(mn === Infinity ? 0 : mn);
      }
      var groupDurs = [];
      for (var g2 = 0; g2 < total; g2++) {
        var mx = 0;
        for (var i2 = 0; i2 < buckets[g2].length; i2++) {
          var end = eventEnd(buckets[g2][i2]);
          if (end > mx) mx = end;
        }
        groupDurs.push(mx - groupStarts[g2]);
      }
      var result = [];
      var cursor = 0;
      var seqMap = [];
      for (var step = 0; step < total; step++) {
        var gi = (startGi + step) % total;
        seqMap.push(gi);
        var base = groupStarts[gi];
        for (var i3 = 0; i3 < buckets[gi].length; i3++) {
          var e2 = {};
          for (var k2 in buckets[gi][i3]) e2[k2] = buckets[gi][i3][k2];
          e2.start = cursor + (buckets[gi][i3].start - base);
          e2._stepIndex = step;
          result.push(e2);
        }
        cursor += groupDurs[gi] + gapSec;
      }
      return { events: result, seqMap: seqMap };
    }

    function isPlaying() {
      return !!(_ssScheduler && _ssScheduler.isPlaying);
    }

    async function stop() {
      if (_ssScheduler && _ssScheduler.isPlaying) await _ssScheduler.stop();
      // Stopping mid-record cancels the recording (discards the capture).
      if (_recCancel) { var c = _recCancel; _recCancel = null; c(); }
    }

    async function resumeAudio() {
      if (_ssSonic && _ssSonic.audioContext && _ssSonic.audioContext.state === "suspended") {
        await _ssSonic.audioContext.resume();
      }
    }

    async function play(events, options) {
      options = options || {};
      var loopInfinite = false;
      var loopFinite = 0;
      if (options.loop === true) {
        loopInfinite = true;
      } else if (typeof options.loop === "number" && Number.isFinite(options.loop) && options.loop > 1) {
        loopFinite = Math.floor(options.loop);
      }
      var onEvent = options.onEvent || null;
      var onFinish = options.onFinish || null;

      var evts = Array.isArray(events) ? events : _scEvents();
      if (!_ssScheduler || evts.length === 0) {
        if (onFinish) onFinish();
        return;
      }
      _ssScheduler.play(evts, {
        tailPause: _pause,
        meta: meta,
        controlData: controlData,
        loop: loopInfinite ? true : (loopFinite > 0 ? loopFinite : false),
        stemTaps: !!options.stemTaps,
        onEvent: onEvent || function(){},
        onFinish: onFinish || null,
      });
    }

    // ------------------------------------------------------------------
    // Recording: play once (loop forced off) while a capture worklet taps
    // the engine node, then encode downloads after the ring tail.
    // Resolves {files: [{name, blob}]} or null when cancelled/unavailable.
    // Cancel by calling stop() (or the widget's orphan sweep doing so).
    // ------------------------------------------------------------------
    var _recSession = null;
    var _recCancel = null;

    function isRecording() {
      return _recSession != null;
    }

    // How many stem pairs the PAGE's engine can carry: output channels
    // beyond the master pair. The live engine's own system report is
    // authoritative (it reflects whichever output actually booted it —
    // including a 10.16 boot whose output predates the bootConfig
    // stash); the ss_init bootConfig stash is the fallback. An engine
    // booted by a stale pre-10.16 output reports 2 channels, so this
    // returns 0 — the recorder then degrades to mixdown with a reload
    // hint instead of shipping a ZIP of silent or missing stems.
    function stemCapacity() {
      var outs = 0;
      try {
        if (_ssSonic && typeof _ssSonic.getSystemReport === "function") {
          var rep = _ssSonic.getSystemReport();
          if (rep && rep.audio && rep.audio.channelCount) {
            outs = rep.audio.channelCount;
          }
        }
      } catch (e) {}
      if (!outs) {
        var st = globalThis.__klothoSonic;
        var so = st && st.bootConfig && st.bootConfig.scsynthOptions;
        outs = (so && so.numOutputBusChannels) ? so.numOutputBusChannels : 2;
      }
      return Math.max(0, Math.floor((outs - 2) / 2));
    }

    async function record(events, options) {
      options = options || {};
      var recorder = globalThis.KlothoRecorder;
      if (!recorder) {
        console.warn("[Klotho] recorder module not loaded on this page");
        return null;
      }
      var ready = await _ensureSSReady();
      if (!ready || !_ssSonic || !_ssScheduler) return null;
      var evts = Array.isArray(events) ? events : _scEvents();
      if (evts.length === 0) return null;
      if (_recSession) {
        console.warn("[Klotho] this widget is already recording");
        return null;
      }

      // Stems only make sense for Score payloads (track groups in meta),
      // within the page engine's output-pair budget (15 on a 10.16 boot).
      var wantStems = !!options.stems;
      var groups = (meta && Array.isArray(meta.groups)) ? meta.groups : [];
      if (wantStems && groups.length === 0) wantStems = false;
      var capacity = stemCapacity();
      if (wantStems && capacity === 0) {
        console.warn("[Klotho] stems unavailable: this page's audio engine "
          + "was started by an output saved with an older Klotho (2 output "
          + "channels). Reload the notebook page (after re-running the "
          + "cells) and record again; recording the mixdown instead.");
        wantStems = false;
      }
      if (wantStems && typeof _ssScheduler.setupStemTaps !== "function") {
        console.warn("[Klotho] stems unavailable: this page is running an "
          + "older Klotho scheduler. Reload the notebook page and record "
          + "again; recording the mixdown instead.");
        wantStems = false;
      }
      var stemCount = Math.min(groups.length, capacity);
      if (wantStems && groups.length > capacity) {
        console.warn("[Klotho] stems: only the first " + capacity + " of "
          + groups.length + " tracks get separate stems.");
      }
      var channels = wantStems ? 2 + 2 * stemCount : 2;

      var session = await recorder.start(_ssSonic, channels, options.maxSeconds);
      if (!session) return null;
      _recSession = session;

      var ringMs = Math.max(0, ringTime) * 1000 + 250;
      var data = await new Promise(function(resolve) {
        var settled = false;
        function settle(v) {
          if (settled) return;
          settled = true;
          resolve(v);
        }
        _recCancel = function() {
          session.abort();
          settle(null);
        };
        play(evts, {
          loop: false,
          stemTaps: wantStems,
          onEvent: options.onEvent || null,
          onFinish: function() {
            if (options.onFinish) { try { options.onFinish(); } catch (e) {} }
            // Piece (+ tail pause) is done; keep capturing through the
            // ring-out so release tails land in the files.
            setTimeout(function() {
              if (settled) return;
              session.stop().then(settle, function() { settle(null); });
            }, ringMs);
          },
        });
      });
      _recSession = null;
      _recCancel = null;
      if (!data || !data.channels || data.channels.length < 2) return null;

      // Trim the capture so t=0 of every file is the scheduler's play
      // start. startedPerfMs is the main thread's receipt of the capture
      // worklet's "started" message, i.e. at or after the true capture
      // start — so the computed offset can only under-trim. The safety
      // margin biases the same direction: never clip the first attack.
      var trimStart = 0;
      var playStartPerf = _ssScheduler._playStartPerfMs;
      if (playStartPerf && session.startedPerfMs) {
        var SAFETY_S = 0.05;
        var offsetS = (playStartPerf - session.startedPerfMs) / 1000 - SAFETY_S;
        trimStart = Math.max(0, Math.round(offsetS * data.sampleRate));
        if (trimStart >= data.frames) trimStart = 0;
      }
      function ch(i) {
        var arr = data.channels[i];
        return trimStart > 0 ? arr.subarray(trimStart) : arr;
      }

      var base = recorder.defaultBaseName();
      var files = [];
      if (!wantStems) {
        var wav = recorder.encodeWav24([ch(0), ch(1)], data.sampleRate);
        files.push({ name: base + ".wav", blob: new Blob([wav], { type: "audio/wav" }) });
      } else {
        var layout = _ssScheduler._stemLayout || [];
        var entries = [{ name: "main.wav",
                         data: recorder.encodeWav24([ch(0), ch(1)], data.sampleRate) }];
        for (var s = 0; s < layout.length; s++) {
          var c0 = layout[s].ch[0], c1 = layout[s].ch[1];
          if (c1 >= data.channels.length) continue;
          entries.push({ name: layout[s].name + ".wav",
                         data: recorder.encodeWav24([ch(c0), ch(c1)], data.sampleRate) });
        }
        var zip = recorder.zipStore(entries);
        files.push({ name: base + "_stems.zip",
                     blob: new Blob([zip], { type: "application/zip" }) });
      }
      return { files: files };
    }

    function releaseControlPreload() {
      if (_ssScheduler && typeof _ssScheduler.releaseControlPreload === "function") {
        try { _ssScheduler.releaseControlPreload(); } catch(e) {}
      }
    }

    async function preview(params) {
      params = params || {};
      var freq = Number(params.freq);
      if (!Number.isFinite(freq) || freq <= 0) return false;
      var amp = Number(params.amp);
      if (!Number.isFinite(amp) || amp <= 0) amp = 0.3;
      var dur = Number(params.dur);
      if (!Number.isFinite(dur) || dur <= 0) dur = 1.0;
      var defName = (params.defName || "kl_tri") + "";
      var pfields = (params.pfields && typeof params.pfields === "object") ? params.pfields : null;

      var ready = await _ensureSSReady();
      if (!ready || !_ssSonic || typeof _ssSonic.send !== "function") return false;
      // Click-to-play preview: trigger one synth for ``dur`` seconds.
      // We always send ``gate, 1`` on /s_new and ``/n_set gate 0`` after
      // ``dur`` regardless of whether the manifest happens to be loaded
      // on the page. For non-gated synths, scsynth silently ignores the
      // unknown control name; for gated synths this gives the proper
      // release tail. This keeps click-to-play independent of whether
      // a SuperSonic ``play()`` widget has injected ``__klothoManifest``.
      var nodeId = _ssSonic.nextNodeId();
      var args = ["/s_new", defName, nodeId, 0, 0,
                  "freq", freq, "amp", amp, "gate", 1];
      if (pfields) {
        for (var k in pfields) {
          if (!Object.prototype.hasOwnProperty.call(pfields, k)) continue;
          if (k === "freq" || k === "amp" || k === "gate") continue;
          var v = Number(pfields[k]);
          if (!Number.isFinite(v)) continue;
          args.push(k, v);
        }
      }
      _ssSonic.send.apply(_ssSonic, args);
      setTimeout(function() {
        try { _ssSonic.send("/n_set", nodeId, "gate", 0); } catch(_) {}
      }, Math.max(1, Math.round(dur * 1000)));
      return true;
    }

    return {
      ensureReady: ensureReady,
      hasPlayableEvents: hasPlayableEvents,
      isPlaying: isPlaying,
      stop: stop,
      resumeAudio: resumeAudio,
      play: play,
      record: record,
      isRecording: isRecording,
      stemCapacity: stemCapacity,
      hasStemTracks: function() {
        return !!(meta && Array.isArray(meta.groups) && meta.groups.length > 0);
      },
      preview: preview,
      releaseControlPreload: releaseControlPreload,
      getEvents: function() { return _scEvents(); },
      filterEventsForGroup: filterEventsForGroup,
      reorderEventsFrom: reorderEventsFrom,
    };
  }

  globalThis.KlothoPlaybackBridge = buildBridge;
  globalThis.__klothoPlaybackBridgeV2 = buildBridge;
  globalThis.__klothoPlaybackBridgeV3 = buildBridge;
})();
