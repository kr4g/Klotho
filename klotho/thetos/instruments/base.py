from uuid import uuid4

from klotho.utils.data_structures.dictionaries import SafeDict


class Instrument:
    def __init__(self, name='default', pfields=None):
        self._name = name
        if pfields is None:
            pfields = {}
        self._pfields = pfields if isinstance(pfields, SafeDict) else SafeDict(pfields)

    @property
    def name(self):
        return self._name

    @property
    def pfields(self):
        return self._pfields.copy()

    def __eq__(self, other):
        if not isinstance(other, Instrument):
            return NotImplemented
        return self._name == other._name and dict(self._pfields) == dict(other._pfields)

    def __hash__(self):
        return hash((self._name, tuple(sorted(self._pfields.items()))))

    def __getitem__(self, key):
        return self._pfields[key]

    def __str__(self):
        return f"Instrument(name='{self._name}', pfields={dict(self._pfields)})"

    def __repr__(self):
        return self.__str__()


class Effect:
    """Base class for insert effects -- long-lived FX nodes in a track's chain.

    Unlike ``Instrument`` (which represents a per-note voice), an Effect
    represents a persistent node whose parameters are automated via ``set``
    events.  Identity is by ``uid``, not by name or pfields.
    """

    def __init__(self, name='default', pfields=None):
        self._name = name
        self._uid = uuid4().hex[:12]
        if pfields is None:
            pfields = {}
        self._pfields = pfields if isinstance(pfields, SafeDict) else SafeDict(pfields)

    @property
    def name(self):
        return self._name

    @property
    def uid(self):
        return self._uid

    @property
    def pfields(self):
        return self._pfields.copy()

    def __eq__(self, other):
        if not isinstance(other, Effect):
            return NotImplemented
        return self._uid == other._uid

    def __hash__(self):
        return hash(self._uid)

    def __getitem__(self, key):
        return self._pfields[key]

    def __str__(self):
        return f"Effect(name='{self._name}', uid='{self._uid}', pfields={dict(self._pfields)})"

    def __repr__(self):
        return self.__str__()
