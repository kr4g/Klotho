(() => {
  if (typeof globalThis.KlothoPlaybackBridge !== "undefined") return;

  function buildBridge(config) {
    var engine = config.engine || "tone";
    var audioPayload = config.audioPayload || null;
    var ringTime = config.ringTime != null ? config.ringTime : 5;

    var _aPlayer = null;
    var _aInstruments = null;
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

    function _toneEvents() {
      return _rawEvents();
    }

    function _scEvents() {
      return _rawEvents().filter(function(e) {
        return e && (e.type === "new" || e.type === "set" || e.type === "release");
      });
    }

    function _hasToneAudio() {
      if (_aPlayer) return true;
      if (typeof Tone === "undefined"
          || typeof globalThis.KLOTHO_BUILD_INSTRUMENTS !== "function"
          || typeof globalThis.KlothoPlayer === "undefined") return false;
      _aInstruments = globalThis.KLOTHO_BUILD_INSTRUMENTS((audioPayload && audioPayload.instruments) || {});
      _aPlayer = globalThis.KlothoPlayer.create();
      return true;
    }

    async function _ensureSSReady() {
      if (_ssReady) return true;
      if (typeof globalThis.__ensureSuperSonic !== "function") return false;
      try {
        var sonic = await globalThis.__ensureSuperSonic();
        if (!sonic) return false;
        _ssSonic = sonic;
        _ssScheduler = new globalThis.BrowserScheduler({
          sonic: sonic,
          manifest: (typeof globalThis.__klothoManifest !== "undefined") ? globalThis.__klothoManifest : { synths: {}, inserts: {} },
          ringTime: ringTime,
        });
        _ssReady = true;
        return true;
      } catch(e) {
        return false;
      }
    }

    async function ensureReady() {
      if (engine === "supersonic") return _ensureSSReady();
      return _hasToneAudio();
    }

    function hasPlayableEvents() {
      if (engine === "supersonic") return _scEvents().length > 0;
      return _toneEvents().length > 0;
    }

    function eventEnd(ev) {
      var pf = ev && ev.pfields ? ev.pfields : {};
      if (ev && ev.duration != null) return ev.start + ev.duration;
      if (pf.dur != null) return ev.start + pf.dur;
      if (ev && ev.type === "release") return ev.start;
      return ev && ev.start ? ev.start : 0;
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
      if (engine === "supersonic") return !!(_ssScheduler && _ssScheduler.isPlaying);
      return !!(_aPlayer && _aPlayer.isPlaying());
    }

    async function stop() {
      if (engine === "supersonic") {
        if (_ssScheduler && _ssScheduler.isPlaying) await _ssScheduler.stop();
        return;
      }
      if (_aPlayer && _aPlayer.isPlaying()) _aPlayer.stop();
    }

    async function resumeAudio() {
      if (engine === "supersonic") {
        if (_ssSonic && _ssSonic.audioContext && _ssSonic.audioContext.state === "suspended") {
          await _ssSonic.audioContext.resume();
        }
        return;
      }
      if (typeof Tone !== "undefined" && Tone.context && Tone.context.state === "suspended") {
        try { await Tone.start(); } catch(_) {}
        try { await Tone.context.resume(); } catch(_) {}
      }
    }

    async function play(events, options) {
      options = options || {};
      var loop = !!options.loop;
      var onEvent = options.onEvent || null;
      var onFinish = options.onFinish || null;

      if (engine === "supersonic") {
        var evts = Array.isArray(events) ? events : _scEvents();
        if (!_ssScheduler || evts.length === 0) {
          if (onFinish) onFinish();
          return;
        }
        var first = true;
        function playOnce() {
          _ssScheduler.play(evts, {
            _skipStop: !first,
            onEvent: onEvent || function(){},
            onFinish: function() {
              if (loop) playOnce();
              else if (onFinish) onFinish();
            }
          });
          first = false;
        }
        playOnce();
        return;
      }

      var toneEvts = Array.isArray(events) ? events : _toneEvents();
      if (!_aPlayer || toneEvts.length === 0) {
        if (onFinish) onFinish();
        return;
      }
      await _aPlayer.play(toneEvts, _aInstruments, {
        loop: loop,
        onEvent: onEvent || function(){},
        onStop: function() { if (onFinish) onFinish(); },
        onFinish: function() { if (onFinish) onFinish(); },
      });
    }

    return {
      engine: engine,
      ensureReady: ensureReady,
      hasPlayableEvents: hasPlayableEvents,
      isPlaying: isPlaying,
      stop: stop,
      resumeAudio: resumeAudio,
      play: play,
      getEvents: function() { return engine === "supersonic" ? _scEvents() : _toneEvents(); },
      filterEventsForGroup: filterEventsForGroup,
      reorderEventsFrom: reorderEventsFrom,
    };
  }

  globalThis.KlothoPlaybackBridge = buildBridge;
})();
