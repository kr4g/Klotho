const KlothoPlayer = (function() {
  let scheduledIds = [];
  let instruments = null;
  let masterGain = null;

  function clamp01(x) {
    return Math.max(0, Math.min(1, x));
  }

  function clearSchedule() {
    for (const id of scheduledIds) {
      Tone.Transport.clear(id);
    }
    scheduledIds = [];
    Tone.Transport.cancel(0);
  }

  function disposeInstruments() {
    if (!instruments) return;
    for (const name of Object.keys(instruments)) {
      const inst = instruments[name];
      if (inst) {
        if (inst.releaseAll) {
          try { inst.releaseAll(); } catch(_) {}
        }
        if (inst.dispose) {
          try { inst.dispose(); } catch(_) {}
        }
      }
    }
    if (masterGain) {
      try { masterGain.dispose(); } catch(_) {}
    }
    instruments = null;
    masterGain = null;
  }

  function buildInstruments() {
    masterGain = new Tone.Gain(0.85).toDestination();
    const instances = {};
    for (const name of Object.keys(KLOTHO_INSTRUMENTS)) {
      const inst = KLOTHO_INSTRUMENTS[name].create();
      inst.connect(masterGain);
      instances[name] = inst;
    }
    return instances;
  }

  function triggerEvent(ev, time) {
    const spec = KLOTHO_INSTRUMENTS[ev.instrument];
    if (!spec) return;

    const inst = instruments[ev.instrument];
    if (!inst) return;

    const pfields = ev.pfields || {};
    const vel = clamp01(pfields.vel ?? spec.defaults.vel ?? 0.6);
    const freq = pfields.freq ?? spec.defaults.freq ?? 440;

    inst.triggerAttackRelease(freq, ev.duration, time, vel);
  }

  async function hardStop() {
    try { Tone.Transport.stop(); } catch (_) {}
    try { Tone.Transport.position = 0; } catch (_) {}
    try { clearSchedule(); } catch (_) {}
    try { disposeInstruments(); } catch (_) {}
  }

  async function play(events, onFinish) {
    await Tone.start();
    await hardStop();

    instruments = buildInstruments();

    for (const ev of events) {
      const id = Tone.Transport.schedule((time) => triggerEvent(ev, time), ev.start);
      scheduledIds.push(id);
    }

    const maxEnd = Math.max(...events.map(e => e.start + e.duration));
    const stopId = Tone.Transport.schedule(async () => {
      await hardStop();
      if (onFinish) onFinish();
    }, maxEnd + 0.3);
    scheduledIds.push(stopId);

    Tone.Transport.start("+0.05");
  }

  async function stop() {
    await hardStop();
  }

  return {
    play: play,
    stop: stop
  };
})();

