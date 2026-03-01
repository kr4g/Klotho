import copy

from klotho.thetos.instruments.presets import TONEJS_PRESETS
from klotho.utils.data_structures.dictionaries import SafeDict

from .base import Instrument


class ToneInstrument(Instrument):
    def __init__(self, name='Synth', tonejs_class='Synth', pfields=None):
        if pfields is None:
            pfields = {}
        base_pfields = dict(pfields)
        if 'freq' not in base_pfields:
            base_pfields['freq'] = 440.0
        if 'vel' in base_pfields:
            vel = base_pfields['vel']
        elif 'amp' in base_pfields:
            vel = base_pfields['amp']
        else:
            vel = 0.6
        base_pfields['vel'] = vel
        base_pfields.pop('amp', None)
        safe_pfields = SafeDict(base_pfields, aliases={'amp': 'vel'})
        super().__init__(name=name, pfields=safe_pfields)
        self._tonejs_class = tonejs_class

    @property
    def tonejs_class(self):
        return self._tonejs_class

    def __str__(self):
        return f"ToneInstrument(name='{self._name}', tonejs_class='{self._tonejs_class}', pfields={dict(self._pfields)})"

    @classmethod
    def _validate_kwargs(cls, valid_keys, kwargs):
        allowed = set(valid_keys) | {'freq', 'vel', 'amp'}
        invalid = set(kwargs.keys()) - allowed
        if invalid:
            raise ValueError(
                f"Invalid pfield(s): {invalid}. "
                f"Valid pfields: {sorted(allowed)}"
            )

    @classmethod
    def from_preset(cls, preset_name: str, name: str = None, **kwargs):
        preset = TONEJS_PRESETS[preset_name]
        pfields = copy.deepcopy(preset['pfields'])
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or preset_name, tonejs_class=preset['tonejs_class'], pfields=pfields)

    @classmethod
    def Harmonics(cls, name=None, **kwargs):
        return cls.from_preset('Harmonics', name=name, **kwargs)

    @classmethod
    def Tiny(cls, name=None, **kwargs):
        return cls.from_preset('Tiny', name=name, **kwargs)

    @classmethod
    def ElectricCello(cls, name=None, **kwargs):
        return cls.from_preset('ElectricCello', name=name, **kwargs)

    @classmethod
    def Kalimba(cls, name=None, **kwargs):
        return cls.from_preset('Kalimba', name=name, **kwargs)

    @classmethod
    def ThinSaws(cls, name=None, **kwargs):
        return cls.from_preset('ThinSaws', name=name, **kwargs)

    @classmethod
    def Bah(cls, name=None, **kwargs):
        return cls.from_preset('Bah', name=name, **kwargs)

    @classmethod
    def BassGuitar(cls, name=None, **kwargs):
        return cls.from_preset('BassGuitar', name=name, **kwargs)

    @classmethod
    def Bassy(cls, name=None, **kwargs):
        return cls.from_preset('Bassy', name=name, **kwargs)

    @classmethod
    def BrassCircuit(cls, name=None, **kwargs):
        return cls.from_preset('BrassCircuit', name=name, **kwargs)

    @classmethod
    def CoolGuy(cls, name=None, **kwargs):
        return cls.from_preset('CoolGuy', name=name, **kwargs)

    @classmethod
    def Pianoetta(cls, name=None, **kwargs):
        return cls.from_preset('Pianoetta', name=name, **kwargs)

    @classmethod
    def Pizz(cls, name=None, **kwargs):
        return cls.from_preset('Pizz', name=name, **kwargs)

    @classmethod
    def Gravel(cls, name=None, **kwargs):
        return cls.from_preset('Gravel', name=name, **kwargs)

    @classmethod
    def Slap(cls, name=None, **kwargs):
        return cls.from_preset('Slap', name=name, **kwargs)

    @classmethod
    def Swoosh(cls, name=None, **kwargs):
        return cls.from_preset('Swoosh', name=name, **kwargs)

    @classmethod
    def Train(cls, name=None, **kwargs):
        return cls.from_preset('Train', name=name, **kwargs)

    @classmethod
    def AlienChorus(cls, name=None, **kwargs):
        return cls.from_preset('AlienChorus', name=name, **kwargs)

    @classmethod
    def DelicateWindPart(cls, name=None, **kwargs):
        return cls.from_preset('DelicateWindPart', name=name, **kwargs)

    @classmethod
    def DropPulse(cls, name=None, **kwargs):
        return cls.from_preset('DropPulse', name=name, **kwargs)

    @classmethod
    def Lectric(cls, name=None, **kwargs):
        return cls.from_preset('Lectric', name=name, **kwargs)

    @classmethod
    def Marimba(cls, name=None, **kwargs):
        return cls.from_preset('Marimba', name=name, **kwargs)

    @classmethod
    def Steelpan(cls, name=None, **kwargs):
        return cls.from_preset('Steelpan', name=name, **kwargs)

    @classmethod
    def SuperSaw(cls, name=None, **kwargs):
        return cls.from_preset('SuperSaw', name=name, **kwargs)

    @classmethod
    def TreeTrunk(cls, name=None, **kwargs):
        return cls.from_preset('TreeTrunk', name=name, **kwargs)

    @classmethod
    def Kick(cls, name=None, **kwargs):
        pfields = {
            'freq': 52, 'vel': 0.9, 'tuneHz': 52,
            'decay': 0.35, 'pitchDecay': 0.02, 'punch': 6, 'click': 0.25
        }
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or 'Kick', tonejs_class='Kick', pfields=pfields)

    @classmethod
    def Snare(cls, name=None, **kwargs):
        pfields = {
            'freq': 190, 'vel': 0.85, 'tuneHz': 190,
            'decay': 0.18, 'snap': 0.9, 'body': 0.45, 'toneHz': 1800
        }
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or 'Snare', tonejs_class='Snare', pfields=pfields)

    @classmethod
    def TomLow(cls, name=None, **kwargs):
        pfields = {
            'freq': 110, 'vel': 0.75, 'tuneHz': 110,
            'decay': 0.35, 'pitchDecay': 0.01, 'punch': 4
        }
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or 'TomLow', tonejs_class='TomLow', pfields=pfields)

    @classmethod
    def TomMid(cls, name=None, **kwargs):
        pfields = {
            'freq': 160, 'vel': 0.75, 'tuneHz': 160,
            'decay': 0.35, 'pitchDecay': 0.01, 'punch': 4
        }
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or 'TomMid', tonejs_class='TomMid', pfields=pfields)

    @classmethod
    def TomHigh(cls, name=None, **kwargs):
        pfields = {
            'freq': 220, 'vel': 0.75, 'tuneHz': 220,
            'decay': 0.35, 'pitchDecay': 0.01, 'punch': 4
        }
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or 'TomHigh', tonejs_class='TomHigh', pfields=pfields)

    @classmethod
    def HatClosed(cls, name=None, **kwargs):
        pfields = {
            'freq': 420, 'vel': 0.55, 'decay': 0.05,
            'resonance': 5200, 'harmonicity': 5.1, 'modulationIndex': 32,
            'frequency': 420, 'octaves': 1.5
        }
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or 'HatClosed', tonejs_class='HatClosed', pfields=pfields)

    @classmethod
    def HatOpen(cls, name=None, **kwargs):
        pfields = {
            'freq': 420, 'vel': 0.45, 'decay': 0.45,
            'resonance': 5200, 'harmonicity': 5.1, 'modulationIndex': 32,
            'frequency': 420, 'octaves': 1.5
        }
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or 'HatOpen', tonejs_class='HatOpen', pfields=pfields)

    @classmethod
    def Crash(cls, name=None, **kwargs):
        pfields = {
            'freq': 320, 'vel': 0.55, 'decay': 2.8,
            'resonance': 5200, 'harmonicity': 3.7, 'modulationIndex': 18,
            'frequency': 320, 'octaves': 2.2
        }
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or 'Crash', tonejs_class='Crash', pfields=pfields)

    @classmethod
    def Ride(cls, name=None, **kwargs):
        pfields = {
            'freq': 280, 'vel': 0.35, 'decay': 1.7,
            'resonance': 4500, 'harmonicity': 4.2, 'modulationIndex': 12,
            'frequency': 280, 'octaves': 2.0
        }
        if kwargs:
            cls._validate_kwargs(pfields.keys(), kwargs)
            pfields.update(kwargs)
        return cls(name=name or 'Ride', tonejs_class='Ride', pfields=pfields)
