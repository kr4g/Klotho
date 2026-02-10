const KlothoPlayer = (function() {
  let session = 0;
  let currentGain = null;
  let stopTimer = null;
  let playing = false;
  let onFinish = null;
  
  const orphaned = [];

  function cleanupOld() {
    const now = Date.now();
    while (orphaned.length > 0 && now - orphaned[0].time > 1000) {
      const old = orphaned.shift();
      try { old.part.stop(); } catch(_) {}
      try { old.part.dispose(); } catch(_) {}
      for (const k in old.insts) { try { old.insts[k].dispose(); } catch(_) {} }
      try { old.gain.dispose(); } catch(_) {}
    }
  }

  function doStop() {
    session++;
    playing = false;
    if (stopTimer) { clearTimeout(stopTimer); stopTimer = null; }
    if (currentGain) { try { currentGain.gain.rampTo(0, 0.01); } catch(_) {} }
    if (onFinish) { const cb = onFinish; onFinish = null; cb(); }
  }

  function deepClone(obj) {
    return obj && typeof obj === "object" ? JSON.parse(JSON.stringify(obj)) : obj;
  }

  function stripNoteFields(pf) {
    const out = {};
    for (const k in pf) {
      if (k === "freq" || k === "vel" || k === "amp") continue;
      out[k] = pf[k];
    }
    return out;
  }

  function diffParams(next, current) {
    const diff = {};
    for (const k in next) {
      const nv = next[k];
      const cv = current ? current[k] : undefined;
      if (nv && typeof nv === "object" && !Array.isArray(nv)) {
        if (!cv || typeof cv !== "object" || Array.isArray(cv)) {
          diff[k] = deepClone(nv);
        } else {
          const child = diffParams(nv, cv);
          if (Object.keys(child).length) diff[k] = child;
        }
      } else if (Array.isArray(nv)) {
        if (!Array.isArray(cv) || JSON.stringify(nv) !== JSON.stringify(cv)) {
          diff[k] = deepClone(nv);
        }
      } else {
        if (nv !== cv) diff[k] = nv;
      }
    }
    return diff;
  }

  async function play(payload, finishCallback) {
    cleanupOld();
    
    session++;
    const mySession = session;
    playing = true;
    onFinish = finishCallback || null;
    
    try {
      await Tone.start();
      if (Tone.context.state !== "running") await Tone.context.resume();
    } catch(e) {
      playing = false;
      return;
    }
    
    if (session !== mySession) return;
    
    if (Tone.Transport.state !== "started") Tone.Transport.start();

    const myGain = new Tone.Gain(0.85).toDestination();
    currentGain = myGain;
    const events = Array.isArray(payload) ? payload : (payload.events || []);
    const instrumentMap = Array.isArray(payload) ? null : (payload.instruments || null);
    const KLOTHO_INSTRUMENTS = globalThis.KLOTHO_BUILD_INSTRUMENTS(instrumentMap);
    const myInsts = {};
    const currentParams = {};
    for (const name of Object.keys(KLOTHO_INSTRUMENTS)) {
      const spec = KLOTHO_INSTRUMENTS[name];
      myInsts[name] = spec.create();
      myInsts[name].connect(myGain);
      currentParams[name] = deepClone(spec.preset || {});
    }

    const end = events.length ? Math.max(...events.map(e => e.start + e.duration)) : 0;

    const myPart = new Tone.Part((time, ev) => {
      if (session !== mySession) return;
      const spec = KLOTHO_INSTRUMENTS[ev.instrument];
      const inst = myInsts[ev.instrument];
      if (!spec || !inst) return;
      const pf = ev.pfields || {};
      const vel = pf.vel ?? pf.amp ?? (spec.defaults && spec.defaults.vel !== undefined ? spec.defaults.vel : 0.6);
      const freq = pf.freq ?? (spec.defaults && spec.defaults.freq !== undefined ? spec.defaults.freq : 440);
      if (spec.custom) {
        try { spec.trigger(inst, freq, Math.max(0.01, ev.duration), time, Math.max(0, Math.min(1, vel)), pf); } catch(_) {}
        return;
      }
      const desired = stripNoteFields(pf);
      const current = currentParams[ev.instrument] || {};
      const delta = diffParams(desired, current);
      if (Object.keys(delta).length) {
        try { inst.set(delta); } catch(_) {}
        currentParams[ev.instrument] = deepClone(desired);
      }
      try { spec.trigger(inst, freq, Math.max(0.01, ev.duration), time, Math.max(0, Math.min(1, vel))); } catch(_) {}
    }, events.map(ev => [ev.start, ev]));

    orphaned.push({ part: myPart, insts: myInsts, gain: myGain, time: Date.now() });

    myPart.loop = false;
    stopTimer = setTimeout(() => { if (session === mySession) doStop(); }, (end + 0.5) * 1000);

    myPart.start("+0.05");
  }

  async function stop() {
    session++;
    onFinish = null;
    playing = false;
    if (stopTimer) { clearTimeout(stopTimer); stopTimer = null; }
    if (currentGain) { try { currentGain.gain.rampTo(0, 0.01); } catch(_) {} }
  }

  return { play, stop };
})();
