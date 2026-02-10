(() => {
  const DEFAULT_KLOTHO_INSTRUMENTS = {
  synth: {
    create: () => {
      const synth = new Tone.PolySynth(Tone.Synth, { maxPolyphony: 32 });
      synth.set({
        oscillator: { type: "triangle" },
        envelope: { attack: 0.01, decay: 0.1, sustain: 0.3, release: 0.3 }
      });
      return synth;
    },
    defaults: { freq: 440, vel: 0.6 },
    trigger: (inst, freq, duration, time, vel) => {
      try {
        const dur = Math.max(0.01, duration);
        inst.triggerAttackRelease(freq, dur, time, vel);
      } catch(_) {}
    }
  },

  sine: {
    create: () => {
      const synth = new Tone.PolySynth(Tone.Synth, { maxPolyphony: 128 });
      synth.set({
        oscillator: { type: "sine" },
        envelope: { attack: 0.2, decay: 0.2, sustain: 0.5, release: 0.8 }
      });
      return synth;
    },
    defaults: { freq: 440, vel: 0.4 },
    trigger: (inst, freq, duration, time, vel) => {
      try {
        const dur = Math.max(0.01, duration);
        inst.triggerAttackRelease(freq, dur, time, vel);
      } catch(_) {}
    }
  },

  membrane: {
    create: () => new Tone.MembraneSynth({
      pitchDecay: 0.02,
      octaves: 2,
      envelope: { attack: 0.003, decay: 0.15, sustain: 0.2, release: 0.1 }
    }),
    defaults: { freq: 900, vel: 0.85 },
    trigger: (inst, freq, duration, time, vel) => {
      try {
        const dur = Math.max(0.05, duration);
        const attack = 0.003;
        const release = Math.max(0.01, Math.min(0.08, dur * 0.15));
        const decay = Math.max(0.01, Math.min(dur * 0.3, dur - attack - release));
        const noteDur = Math.max(0.02, dur - release);
        inst.envelope.attack = attack;
        inst.envelope.decay = decay;
        inst.envelope.sustain = 0.25;
        inst.envelope.release = release;
        inst.triggerAttackRelease(freq, noteDur, time, vel);
      } catch(_) {}
    }
  }
  };

function registerBuiltinCustomInstruments(registry) {
  const makeKick = () => ({
    maxPolyphony: 8,
    defaults: { freq: 52, vel: 0.9 },
    pfields: {
      tuneHz: 52,
      decay: 0.35,
      pitchDecay: 0.02,
      punch: 6,
      click: 0.25
    },
    create: () => {
      const body = new Tone.MembraneSynth({
        pitchDecay: 0.02,
        octaves: 6,
        oscillator: { type: "sine" },
        envelope: { attack: 0.001, decay: 0.35, sustain: 0, release: 0.05 }
      });
      const click = new Tone.NoiseSynth({
        noise: { type: "white" },
        envelope: { attack: 0.001, decay: 0.015, sustain: 0 }
      });
      const clickHP = new Tone.Filter({ type: "highpass", frequency: 3500, Q: 0.7 });
      const bodyGain = new Tone.Gain(1);
      const clickGain = new Tone.Gain(0.25);
      const mix = new Tone.Gain(1);
      const output = new Tone.Gain(1);
      body.connect(bodyGain);
      click.chain(clickHP, clickGain);
      bodyGain.connect(mix);
      clickGain.connect(mix);
      mix.connect(output);
      return { body, click, clickHP, bodyGain, clickGain, mix, output };
    },
    connect: (inst, out) => {
      inst.output.connect(out);
    },
    apply: (inst, p) => {
      inst.body.set({
        pitchDecay: p.pitchDecay,
        octaves: p.punch,
        envelope: { attack: 0.001, decay: p.decay, sustain: 0, release: 0.05 }
      });
      inst.clickGain.gain.value = p.click;
    },
    trigger: (inst, freq, duration, time, vel, p) => {
      const hz = p.tuneHz ?? p.freq ?? freq;
      const note = Tone.Frequency(hz, "hz").toNote();
      inst.body.triggerAttackRelease(note, 0.12, time, vel);
      inst.click.triggerAttackRelease(0.03, time, vel);
    }
  });

  const makeSnare = () => ({
    maxPolyphony: 8,
    defaults: { freq: 190, vel: 0.85 },
    pfields: {
      tuneHz: 190,
      decay: 0.18,
      snap: 0.9,
      body: 0.45,
      toneHz: 1800
    },
    create: () => {
      const noise = new Tone.NoiseSynth({
        noise: { type: "pink" },
        envelope: { attack: 0.001, decay: 0.18, sustain: 0 }
      });
      const noiseBP = new Tone.Filter({ type: "bandpass", frequency: 1800, Q: 0.8 });
      const noiseHP = new Tone.Filter({ type: "highpass", frequency: 600, Q: 0.7 });
      const body = new Tone.Synth({
        oscillator: { type: "triangle" },
        envelope: { attack: 0.001, decay: 0.08, sustain: 0, release: 0.02 }
      });
      const noiseGain = new Tone.Gain(0.9);
      const bodyGain = new Tone.Gain(0.45);
      const mix = new Tone.Gain(1);
      const output = new Tone.Gain(1);
      noise.chain(noiseBP, noiseHP, noiseGain);
      body.connect(bodyGain);
      noiseGain.connect(mix);
      bodyGain.connect(mix);
      mix.connect(output);
      return { noise, noiseBP, noiseHP, body, noiseGain, bodyGain, mix, output };
    },
    connect: (inst, out) => {
      inst.output.connect(out);
    },
    apply: (inst, p) => {
      inst.noise.set({ envelope: { attack: 0.001, decay: p.decay, sustain: 0 } });
      inst.body.set({
        envelope: { attack: 0.001, decay: Math.max(0.03, p.decay * 0.45), sustain: 0, release: 0.02 }
      });
      inst.noiseGain.gain.value = p.snap;
      inst.bodyGain.gain.value = p.body;
      inst.noiseBP.frequency.value = p.toneHz;
    },
    trigger: (inst, freq, duration, time, vel, p) => {
      const hz = p.tuneHz ?? p.freq ?? freq;
      const note = Tone.Frequency(hz, "hz").toNote();
      inst.body.triggerAttackRelease(note, 0.06, time, vel);
      inst.noise.triggerAttackRelease(0.12, time, vel);
    }
  });

  const makeTom = (tuneHz) => ({
    maxPolyphony: 8,
    defaults: { freq: tuneHz, vel: 0.75 },
    pfields: {
      tuneHz,
      decay: 0.35,
      pitchDecay: 0.01,
      punch: 4
    },
    create: () => {
      const body = new Tone.MembraneSynth({
        pitchDecay: 0.01,
        octaves: 4,
        oscillator: { type: "sine" },
        envelope: { attack: 0.001, decay: 0.35, sustain: 0, release: 0.05 }
      });
      const output = new Tone.Gain(1);
      body.connect(output);
      return { body, output };
    },
    connect: (inst, out) => {
      inst.output.connect(out);
    },
    apply: (inst, p) => {
      inst.body.set({
        pitchDecay: p.pitchDecay,
        octaves: p.punch,
        envelope: { attack: 0.001, decay: p.decay, sustain: 0, release: 0.05 }
      });
    },
    trigger: (inst, freq, duration, time, vel, p) => {
      const hz = p.tuneHz ?? p.freq ?? freq;
      const note = Tone.Frequency(hz, "hz").toNote();
      inst.body.triggerAttackRelease(note, 0.1, time, vel);
    }
  });

  const makeMetal = (opts) => ({
    maxPolyphony: 8,
    defaults: { freq: opts.frequency, vel: opts.vel },
    pfields: {
      frequency: opts.frequency,
      decay: opts.decay,
      resonance: opts.resonance,
      harmonicity: opts.harmonicity,
      modulationIndex: opts.modulationIndex,
      octaves: opts.octaves
    },
    create: () => {
      const metal = new Tone.MetalSynth({
        frequency: opts.frequency,
        envelope: { attack: 0.001, decay: opts.decay, release: 0.01 },
        harmonicity: opts.harmonicity,
        modulationIndex: opts.modulationIndex,
        resonance: opts.resonance,
        octaves: opts.octaves
      });
      const output = new Tone.Gain(1);
      metal.connect(output);
      return { metal, output };
    },
    connect: (inst, out) => {
      inst.output.connect(out);
    },
    apply: (inst, p) => {
      inst.metal.set({
        frequency: p.frequency,
        resonance: p.resonance,
        harmonicity: p.harmonicity,
        modulationIndex: p.modulationIndex,
        octaves: p.octaves,
        envelope: { attack: 0.001, decay: p.decay, release: 0.01 }
      });
    },
    trigger: (inst, freq, duration, time, vel, p) => {
      const base = p.frequency ?? p.freq ?? freq;
      const dur = Math.max(0.01, duration || 0.05);
      inst.metal.triggerAttackRelease(base, dur, time, vel);
    }
  });

  const builtins = {
    Kick: makeKick(),
    Snare: makeSnare(),
    TomLow: makeTom(110),
    TomMid: makeTom(160),
    TomHigh: makeTom(220),
    HatClosed: makeMetal({
      frequency: 420,
      decay: 0.05,
      resonance: 5200,
      harmonicity: 5.1,
      modulationIndex: 32,
      octaves: 1.5,
      vel: 0.55
    }),
    HatOpen: makeMetal({
      frequency: 420,
      decay: 0.45,
      resonance: 5200,
      harmonicity: 5.1,
      modulationIndex: 32,
      octaves: 1.5,
      vel: 0.45
    }),
    Crash: makeMetal({
      frequency: 320,
      decay: 2.8,
      resonance: 5200,
      harmonicity: 3.7,
      modulationIndex: 18,
      octaves: 2.2,
      vel: 0.55
    }),
    Ride: makeMetal({
      frequency: 280,
      decay: 1.7,
      resonance: 4500,
      harmonicity: 4.2,
      modulationIndex: 12,
      octaves: 2.0,
      vel: 0.35
    })
  };

  for (const name of Object.keys(builtins)) {
    if (!registry[name]) registry[name] = builtins[name];
  }
}

  const KLOTHO_CUSTOM_REGISTRY = globalThis.KLOTHO_CUSTOM_INSTRUMENTS || {};
  registerBuiltinCustomInstruments(KLOTHO_CUSTOM_REGISTRY);
  globalThis.KLOTHO_CUSTOM_INSTRUMENTS = KLOTHO_CUSTOM_REGISTRY;

  function createCustomInstrument(def) {
  const voices = [];
  const maxPolyphony = def.maxPolyphony || def.maxVoices || 8;
  const baseParams = def.pfields || {};
  const preset = def.preset || {};
  let output = null;

  function ensureVoice(time, duration) {
    let voice = null;
    for (const v of voices) {
      if (v.busyUntil <= time) {
        voice = v;
        break;
      }
    }
    if (!voice) {
      if (voices.length < maxPolyphony) {
        const inst = def.create();
        if (output) def.connect(inst, output);
        voice = { inst, busyUntil: 0 };
        voices.push(voice);
      } else {
        voice = voices.reduce((a, b) => (a.busyUntil <= b.busyUntil ? a : b));
      }
    }
    voice.busyUntil = time + Math.max(0.01, duration || 0.01);
    return voice.inst;
  }

  function mergeParams(pfields) {
    return Object.assign({}, baseParams, preset, pfields || {});
  }

  return {
    trigger: (freq, duration, time, vel, pfields) => {
      const inst = ensureVoice(time, duration);
      const params = mergeParams(pfields);
      if (def.apply) def.apply(inst, params);
      def.trigger(inst, freq, duration, time, vel, params);
    },
    connect: (out) => {
      output = out;
      for (const v of voices) {
        def.connect(v.inst, out);
      }
    },
    dispose: () => {
      for (const v of voices) {
        if (def.dispose) {
          try { def.dispose(v.inst); } catch(_) {}
        }
        if (v.inst && typeof v.inst.dispose === "function") {
          try { v.inst.dispose(); } catch(_) {}
        }
      }
    }
  };
  }

  function buildCustomSpec(def) {
  return {
    custom: true,
    create: () => createCustomInstrument(def),
    defaults: def.defaults || { freq: 440, vel: 0.6 },
    preset: def.preset || {},
    trigger: (inst, freq, duration, time, vel, pfields) => {
      inst.trigger(freq, duration, time, vel, pfields);
    }
  };
  }

  function buildKlothoInstruments(instrumentMap) {
  const instruments = Object.assign({}, DEFAULT_KLOTHO_INSTRUMENTS);
  const customRegistry = globalThis.KLOTHO_CUSTOM_INSTRUMENTS || {};
  for (const name of Object.keys(customRegistry)) {
    instruments[name] = buildCustomSpec(customRegistry[name]);
  }
  if (!instrumentMap) return instruments;
  for (const name of Object.keys(instrumentMap)) {
    const def = instrumentMap[name];
    const toneClass = def.tonejs_class || "Synth";
    if (customRegistry[toneClass]) {
      const customDef = Object.assign({}, customRegistry[toneClass], {
        preset: def.preset || customRegistry[toneClass].preset || {},
        maxPolyphony: def.maxPolyphony || customRegistry[toneClass].maxPolyphony
      });
      instruments[name] = buildCustomSpec(customDef);
      continue;
    }
    const preset = def.preset || {};
    const maxPolyphony = def.maxPolyphony || 32;
    instruments[name] = {
      create: () => {
        const voice = Tone[toneClass];
        const synth = new Tone.PolySynth(voice, { maxPolyphony });
        if (preset && Object.keys(preset).length) {
          synth.set(preset);
        }
        return synth;
      },
      defaults: { freq: 440, vel: 0.6 },
      preset,
      trigger: (inst, freq, duration, time, vel) => {
        try {
          const dur = Math.max(0.01, duration);
          inst.triggerAttackRelease(freq, dur, time, vel);
        } catch(_) {}
      }
    };
  }
  return instruments;
  }

  globalThis.KLOTHO_BUILD_INSTRUMENTS = buildKlothoInstruments;
})();
