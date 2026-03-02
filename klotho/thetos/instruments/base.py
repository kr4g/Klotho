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
