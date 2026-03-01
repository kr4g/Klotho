from .base import Instrument
from ._shared import GM_PROGRAM_NAMES


class MidiInstrument(Instrument):
    FIXED_PFIELDS_MELODIC = {'note': 60, 'velocity': 100, 'expression': 127}
    FIXED_PFIELDS_DRUM = {'note': 35, 'velocity': 100, 'expression': 127}

    def __init__(self, name=None, prgm=0, is_Drum=False, default_values=None):
        program = int(prgm) % 128
        resolved_name = name or ('Standard Drum Kit' if is_Drum else GM_PROGRAM_NAMES[program])
        pfields = dict(self.FIXED_PFIELDS_DRUM if is_Drum else self.FIXED_PFIELDS_MELODIC)
        if default_values:
            for key in ('note', 'velocity', 'expression'):
                if key in default_values:
                    pfields[key] = default_values[key]
        super().__init__(name=resolved_name, pfields=pfields)
        self._prgm = program
        self._is_Drum = bool(is_Drum)

    @property
    def prgm(self):
        return self._prgm

    @property
    def is_Drum(self):
        return self._is_Drum

    @classmethod
    def _validate_default_values(cls, kwargs):
        allowed = {'note', 'velocity', 'expression'}
        invalid = set(kwargs.keys()) - allowed
        if invalid:
            raise ValueError(
                f"Invalid MidiInstrument default pfield(s): {sorted(invalid)}. "
                f"Allowed pfields: {sorted(allowed)}"
            )

    @classmethod
    def AcousticGrandPiano(cls, **kwargs):
        cls._validate_default_values(kwargs)
        return cls(name=GM_PROGRAM_NAMES[0], prgm=0, is_Drum=False, default_values=kwargs)

    @classmethod
    def DrumKit(cls, **kwargs):
        cls._validate_default_values(kwargs)
        return cls(name='Standard Drum Kit', prgm=1, is_Drum=True, default_values=kwargs)

    def __str__(self):
        return f"MidiInstrument(name='{self._name}', prgm={self._prgm}, is_Drum={self._is_Drum}, pfields={dict(self._pfields)})"


def _gm_method_name(program_name: str) -> str:
    parts = []
    token = []
    for ch in program_name:
        if ch.isalnum():
            token.append(ch)
        elif token:
            parts.append(''.join(token))
            token = []
    if token:
        parts.append(''.join(token))
    if not parts:
        return "GMProgram"
    normalized = ''.join(p[:1].upper() + p[1:] for p in parts)
    if normalized[0].isdigit():
        normalized = f"GM{normalized}"
    return normalized


def _make_gm_classmethod(program_num: int):
    def _ctor(cls, **kwargs):
        cls._validate_default_values(kwargs)
        return cls(
            name=GM_PROGRAM_NAMES[program_num],
            prgm=program_num,
            is_Drum=False,
            default_values=kwargs,
        )
    _ctor.__name__ = f"GM{program_num}"
    return classmethod(_ctor)


_used_method_names = set()
for _idx, _gm_name in enumerate(GM_PROGRAM_NAMES):
    _method_name = _gm_method_name(_gm_name)
    if _method_name in _used_method_names:
        _method_name = f"{_method_name}Program{_idx}"
    _used_method_names.add(_method_name)
    setattr(MidiInstrument, _method_name, _make_gm_classmethod(_idx))
