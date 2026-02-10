(() => {
  if (globalThis._KLOTHO_PLAYER_SESSION === globalThis._KLOTHO_SESSION) return;
  globalThis._KLOTHO_PLAYER_SESSION = globalThis._KLOTHO_SESSION;

  let audioReady = false;

  async function ensureAudio() {
    if (audioReady) return true;
    try {
      await Tone.start();
      if (Tone.context.state !== "running") await Tone.context.resume();
      Tone.Transport.start();
      audioReady = true;
      return true;
    } catch(e) {
      return false;
    }
  }

  function deferDispose(oldInsts, oldGain, delaySec) {
    setTimeout(function() {
      if (oldInsts) {
        for (var k in oldInsts) {
          if (oldInsts[k] && !oldInsts[k].disposed) {
            try { oldInsts[k].dispose(); } catch(_) {}
          }
        }
      }
      if (oldGain && !oldGain.disposed) {
        try { oldGain.dispose(); } catch(_) {}
      }
    }, delaySec * 1000);
  }

  function createPlayer() {
    let gain = null;
    let part = null;
    let insts = null;
    let stopTimer = null;
    let playing = false;
    let pieceDuration = 0;

    function stop() {
      playing = false;
      if (stopTimer) { clearTimeout(stopTimer); stopTimer = null; }
      if (part) {
        try { part.stop(); } catch(_) {}
        if (!part.disposed) { try { part.dispose(); } catch(_) {} }
      }
      if (gain) { try { gain.gain.value = 0; gain.disconnect(); } catch(_) {} }
      if (insts) {
        for (var k in insts) { try { insts[k].disconnect(); } catch(_) {} }
      }
      deferDispose(insts, gain, pieceDuration + 3);
      part = null;
      gain = null;
      insts = null;
    }

    function startPlayback(events, instruments, options) {
      var myGain = new Tone.Gain(0.85).toDestination();
      gain = myGain;
      var myInsts = {};

      var needed = new Set(events.map(function(e) { return e.instrument; }));
      needed.forEach(function(name) {
        var spec = instruments[name];
        if (!spec) return;
        myInsts[name] = spec.create();
        spec.connect(myInsts[name], myGain);
      });
      insts = myInsts;

      var end = events.length ? Math.max.apply(null, events.map(function(e) { return e.start + e.duration; })) : 0;
      pieceDuration = end;

      var myPart = new Tone.Part(function(time, ev) {
        if (!playing) return;
        var spec = instruments[ev.instrument];
        var inst = myInsts[ev.instrument];
        if (!spec || !inst) return;
        var pf = ev.pfields || {};
        var vel = pf.vel != null ? pf.vel : (pf.amp != null ? pf.amp : (spec.defaults.vel != null ? spec.defaults.vel : 0.6));
        var freq = pf.freq != null ? pf.freq : (spec.defaults.freq != null ? spec.defaults.freq : 440);
        spec.trigger(inst, freq, Math.max(0.01, ev.duration), time,
                     Math.max(0, Math.min(1, vel)), pf);
      }, events.map(function(ev) { return [ev.start, ev]; }));

      part = myPart;
      playing = true;

      if (options.loop) {
        myPart.loop = true;
        myPart.loopStart = 0;
        myPart.loopEnd = end;
      } else {
        myPart.loop = false;
        var refPart = myPart;
        stopTimer = setTimeout(function() {
          if (playing && part === refPart) {
            stop();
            if (options.onFinish) options.onFinish();
          }
        }, (end + 0.5) * 1000);
      }

      myPart.start("+0.05");
    }

    async function play(events, instruments, options) {
      stop();
      options = options || {};

      if (!audioReady) {
        var ok = await ensureAudio();
        if (!ok) {
          if (options.onFinish) options.onFinish();
          return;
        }
      }

      startPlayback(events, instruments, options);
    }

    function isPlaying() {
      return playing;
    }

    return { play: play, stop: stop, isPlaying: isPlaying };
  }

  globalThis.KlothoPlayer = { create: createPlayer };
})();
