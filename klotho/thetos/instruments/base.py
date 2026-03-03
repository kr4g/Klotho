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


class Kit(Instrument):
    """A collection of Instruments treated as a single instrument with a selector pfield.

    When assigned to a node via ``UC.set_instrument``, the Kit behaves like
    any other Instrument.  A designated selector pfield (default ``'voice'``)
    chooses which member is used for each event at assembly time.

    This is the engine-agnostic base.  See ``SynthDefKit`` in
    ``synthdef.py`` for the SuperCollider-specific variant.

    Parameters
    ----------
    members : dict[str, Instrument]
        Named instruments in the kit.  Keys are selector values.
    default : str or None
        Key of the default member.  If ``None``, the first key is used.
    selector : str
        Pfield name used to choose the active member (default ``'voice'``).
    """

    def __init__(self, members: dict, default: str = None, selector: str = 'voice'):
        if not members:
            raise ValueError("Kit requires at least one member")
        for k, v in members.items():
            if not isinstance(v, Instrument):
                raise TypeError(f"Kit member '{k}' must be an Instrument, got {type(v).__name__}")
        self._members = dict(members)
        self._default = default if default is not None else next(iter(members))
        if self._default not in self._members:
            raise KeyError(f"Default key '{self._default}' not found in members")
        self._selector = selector
        default_inst = self._members[self._default]
        pfields = dict(default_inst.pfields)
        pfields[self._selector] = self._default
        super().__init__(
            name=f"Kit({self._default})",
            pfields=pfields,
        )

    @property
    def default(self) -> str:
        return self._default

    @property
    def selector(self) -> str:
        return self._selector

    @property
    def members(self) -> dict:
        return dict(self._members)

    def _resolve(self, key=None):
        if key is None or key not in self._members:
            return self._members[self._default]
        return self._members[key]

    def __getitem__(self, key):
        if key in self._members:
            return self._members[key]
        return super().__getitem__(key)

    def __contains__(self, key):
        return key in self._members

    def __iter__(self):
        return iter(self._members)

    def __len__(self):
        return len(self._members)

    def __str__(self):
        keys = list(self._members.keys())
        return f"Kit(members={keys}, default='{self._default}', selector='{self._selector}')"

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
