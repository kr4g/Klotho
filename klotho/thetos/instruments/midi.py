from .base import Instrument
from ._shared import GM_PROGRAM_NAMES


class MidiInstrument(Instrument):
    """A General MIDI instrument identified by program number.

    Every GM program is also available as a named classmethod constructor
    (e.g. ``MidiInstrument.Violin()``, ``MidiInstrument.Marimba()``), plus
    ``MidiInstrument.DrumKit()`` for the standard drum kit.

    Parameters
    ----------
    name : str or None, optional
        Display name. Defaults to the GM program name (or
        ``'Standard Drum Kit'`` when ``is_Drum`` is True).
    prgm : int, optional
        General MIDI program number, 0-127 (default is 0).
    is_Drum : bool, optional
        If True, the instrument plays on a percussion channel (default is False).
    default_values : dict, optional
        Overrides for the ``note``, ``velocity``, and ``expression`` pfields.
    """

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
        """int : The General MIDI program number (0-127)."""
        return self._prgm

    @property
    def is_Drum(self):
        """bool : Whether this instrument plays on a percussion channel."""
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
        """Create a MidiInstrument for GM program 0 (Acoustic Grand Piano)."""
        cls._validate_default_values(kwargs)
        return cls(name=GM_PROGRAM_NAMES[0], prgm=0, is_Drum=False, default_values=kwargs)

    @classmethod
    def DrumKit(cls, **kwargs):
        """Create a MidiInstrument for the standard GM drum kit (percussion channel)."""
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
    _ctor.__doc__ = (
        f"Create a MidiInstrument for GM program {program_num} "
        f"({GM_PROGRAM_NAMES[program_num]})."
    )
    return classmethod(_ctor)


_used_method_names = set()
for _idx, _gm_name in enumerate(GM_PROGRAM_NAMES):
    _method_name = _gm_method_name(_gm_name)
    if _method_name in _used_method_names:
        _method_name = f"{_method_name}Program{_idx}"
    _used_method_names.add(_method_name)
    setattr(MidiInstrument, _method_name, _make_gm_classmethod(_idx))
