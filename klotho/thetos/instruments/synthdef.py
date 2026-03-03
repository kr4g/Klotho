import copy

from .base import Instrument, Kit, Effect
from ._shared import ss_synth_meta, load_ss_manifest


class SynthDefInstrument(Instrument):
    RELEASE_GATE = 'gate'
    RELEASE_FREE = 'free'

    def __init__(self, name='default', defName=None, release_mode='gate', pfields=None, specs=None):
        if pfields is None:
            pfields = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0}
        if specs is None:
            specs = {}
        defName = 'default' if defName is None else defName
        super().__init__(name=name, pfields=pfields)
        self._defName = defName
        self._release_mode = self._normalize_release_mode(release_mode)
        self._specs = copy.deepcopy(specs)

    @property
    def defName(self):
        return self._defName

    @property
    def release_mode(self):
        return self._release_mode

    @property
    def specs(self):
        return copy.deepcopy(self._specs)

    @staticmethod
    def _normalize_release_mode(release_mode):
        value = (release_mode or '').strip().lower()
        if value == SynthDefInstrument.RELEASE_GATE:
            return SynthDefInstrument.RELEASE_GATE
        if value == SynthDefInstrument.RELEASE_FREE:
            return SynthDefInstrument.RELEASE_FREE
        raise ValueError("release_mode must be 'gate' or 'free'")

    @classmethod
    def from_manifest(cls, defName: str, name: str = None, release_mode: str = None, **overrides):
        meta = ss_synth_meta(defName)
        controls = copy.deepcopy(meta.get('controls', {}))
        controls.update(overrides)
        manifest_release_mode = (meta.get('releaseMode') or 'gate').lower()
        resolved_release_mode = release_mode or manifest_release_mode
        return cls(
            name=name or defName,
            defName=defName,
            release_mode=resolved_release_mode,
            pfields=controls,
            specs=meta.get('specs', {}),
        )

    def __str__(self):
        return f"SynthDefInstrument(name='{self._name}', defName='{self._defName}', pfields={dict(self._pfields)})"


class SynthDefFX(Effect):
    """A SynthDef-backed insert effect for use in a Score track's FX chain.

    Each ``SynthDefFX`` instance represents a unique FX node.  Two instances of
    the same ``defName`` with identical args are still two distinct nodes
    (different ``uid`` values).  The Python object itself serves as the
    handle -- pass it to ``Score.track()`` to place it in a chain, and to
    ``UC.set_instrument()`` to automate its parameters.

    Parameters
    ----------
    defName : str
        SuperCollider SynthDef name (e.g. ``"__reverb"``).
    **initial_args
        Initial parameter values set on the node at creation time.
    """

    def __init__(self, defName, **initial_args):
        super().__init__(name=defName, pfields=initial_args)
        self._defName = defName

    @property
    def defName(self):
        return self._defName

    @property
    def args(self):
        return dict(self._pfields)

    def __str__(self):
        return f"SynthDefFX(defName='{self._defName}', uid='{self._uid}', args={dict(self._pfields)})"


class SynthDefKit(Kit):
    """A Kit whose members are SynthDefInstruments.

    Extends :class:`Kit` with SuperCollider-specific properties and
    a ``from_manifest`` factory.  Each member may have a different
    ``defName`` and ``release_mode``; the assembly layer resolves the
    correct member per event, so these properties delegate to the
    *default* member only as a display/fallback hint.

    Parameters
    ----------
    members : dict[str, SynthDefInstrument]
        Named SynthDef instruments.
    default : str or None
        Key of the default member.
    selector : str
        Pfield name for the selector (default ``'voice'``).
    """

    @property
    def defName(self):
        return getattr(self._members[self._default], 'defName', None)

    @property
    def release_mode(self):
        return getattr(self._members[self._default], 'release_mode', 'gate')

    @classmethod
    def from_manifest(cls, members: dict, default=None, selector='voice', **overrides):
        """Build a SynthDefKit from manifest defNames.

        Parameters
        ----------
        members : dict[str, str]
            Mapping of selector keys to SynthDef defNames.
        default : str or None
            Default selector key.
        selector : str
            Pfield name for the selector.
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        built = {}
        for key, def_name in members.items():
            built[key] = SynthDefInstrument.from_manifest(def_name, name=key, **overrides)
        return cls(built, default=default, selector=selector)

    def __str__(self):
        keys = list(self._members.keys())
        return f"SynthDefKit(members={keys}, default='{self._default}', selector='{self._selector}')"


def _clean_method_name(name: str) -> str:
    cleaned = ''.join(ch if (ch.isalnum() or ch == '_') else '_' for ch in name).strip('_')
    if not cleaned:
        return 'synth'
    if cleaned[0].isdigit():
        cleaned = f"synth_{cleaned}"
    return cleaned


def _base_method_name_for_def(def_name: str) -> str:
    if def_name == 'default':
        return 'default'
    if def_name.startswith('kl_') or def_name.startswith('fd_'):
        return _clean_method_name(def_name[3:])
    return _clean_method_name(def_name)


def _make_synth_classmethod(def_name: str, method_name: str):
    def _ctor(cls, name: str = None, **kwargs):
        return cls.from_manifest(def_name, name=name or method_name, **kwargs)
    _ctor.__name__ = method_name
    return classmethod(_ctor)


_ss_synths = load_ss_manifest().get('synths', {})
_registered_method_names = set()


def _def_sort_key(def_name: str):
    if def_name == 'default':
        return (0, def_name)
    if def_name.startswith('kl_'):
        return (1, def_name)
    if def_name.startswith('fd_'):
        return (2, def_name)
    return (3, def_name)


for _def_name in sorted(_ss_synths.keys(), key=_def_sort_key):
    _base_name = _base_method_name_for_def(_def_name)
    _method_name = _base_name
    if hasattr(SynthDefInstrument, _method_name) or (_method_name in _registered_method_names):
        if _def_name.startswith('fd_'):
            _method_name = f"{_base_name}_fd"
        elif _def_name.startswith('kl_'):
            _method_name = f"{_base_name}_kl"
        else:
            _method_name = f"{_base_name}_synth"
    _suffix = 2
    while hasattr(SynthDefInstrument, _method_name) or (_method_name in _registered_method_names):
        _method_name = f"{_base_name}_{_suffix}"
        _suffix += 1
    _registered_method_names.add(_method_name)
    setattr(SynthDefInstrument, _method_name, _make_synth_classmethod(_def_name, _method_name))
