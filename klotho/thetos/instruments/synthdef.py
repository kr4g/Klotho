import copy

from .base import Instrument, InsertBase
from ._shared import ss_synth_meta


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

    @classmethod
    def Default(cls, name: str = None, **kwargs):
        return cls.from_manifest('default', name=name, **kwargs)

    @classmethod
    def KlTri(cls, name: str = None, **kwargs):
        return cls.from_manifest('kl_tri', name=name, **kwargs)

    @classmethod
    def KlSine(cls, name: str = None, **kwargs):
        return cls.from_manifest('kl_sine', name=name, **kwargs)

    @classmethod
    def KlSqr(cls, name: str = None, **kwargs):
        return cls.from_manifest('kl_sqr', name=name, **kwargs)

    @classmethod
    def KlSaw(cls, name: str = None, **kwargs):
        return cls.from_manifest('kl_saw', name=name, **kwargs)

    @classmethod
    def KlNoiseBPF(cls, name: str = None, **kwargs):
        return cls.from_manifest('kl_noisebpf', name=name, **kwargs)

    @classmethod
    def KlKicktone(cls, name: str = None, **kwargs):
        return cls.from_manifest('kl_kicktone', name=name, **kwargs)

    def __str__(self):
        return f"SynthDefInstrument(name='{self._name}', defName='{self._defName}', pfields={dict(self._pfields)})"


class Insert(InsertBase):
    """A SynthDef-backed insert effect for use in a Score track's FX chain.

    Each ``Insert`` instance represents a unique FX node.  Two instances of
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
        return f"Insert(defName='{self._defName}', uid='{self._uid}', args={dict(self._pfields)})"
