const KLOTHO_INSTRUMENTS = {
  synth: {
    create: () => new Tone.PolySynth(Tone.Synth, {
      maxPolyphony: 16,
      options: {
        oscillator: { type: "triangle" },
        envelope: { attack: 0.01, decay: 0.1, sustain: 0.3, release: 0.3 }
      }
    }),
    defaults: {
      freq: 440,
      vel: 0.6,
    }
  },

  sine: {
    create: () => new Tone.PolySynth(Tone.Synth, {
      maxPolyphony: 32,
      options: {
        oscillator: { type: "sine" },
        envelope: { attack: 0.05, decay: 0.2, sustain: 0.5, release: 0.8 }
      }
    }),
    defaults: {
      freq: 440,
      vel: 0.4,
    }
  },

  membrane: {
    create: () => new Tone.MembraneSynth({
      pitchDecay: 0.008,
      octaves: 6,
      envelope: { attack: 0.001, decay: 0.08, sustain: 0.0, release: 0.03 }
    }),
    defaults: {
      freq: 120,
      vel: 0.85,
    }
  }
};

