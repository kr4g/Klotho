import copy
import warnings
from collections import OrderedDict
from uuid import uuid4

from .base import Instrument, Effect


def _copy_inserts_with_fresh_uids(inserts):
    result = []
    for ins in inserts:
        new_ins = copy.copy(ins)
        new_ins._uid = uuid4().hex[:12]
        result.append(new_ins)
    return result


_RESERVED_ATTRS = frozenset({
    'name', 'families', 'members', 'ungrouped',
    'add', 'remove', 'family', 'set_inserts', 'inserts', 'include',
    'copy', 'items',
})


class _FamilyView:
    """Read-only lens into a single Ensemble family.

    Instruments returned by subscript carry an ``_ensemble_family`` tag
    so that ``UC.set_instrument`` can auto-set the ``group`` mfield.
    """

    __slots__ = ('_ensemble', '_family')

    def __init__(self, ensemble, family_name):
        self._ensemble = ensemble
        self._family = family_name

    def _tagged(self, member_name):
        inst = self._ensemble._members[member_name]
        tagged = copy.copy(inst)
        tagged._ensemble_family = self._family
        tagged._ensemble_member = member_name
        return tagged

    def __getitem__(self, member_name):
        names = self._ensemble._families.get(self._family, [])
        if member_name not in names:
            raise KeyError(
                f"'{member_name}' is not a member of family '{self._family}'"
            )
        return self._tagged(member_name)

    def __iter__(self):
        return iter(self._ensemble._families.get(self._family, []))

    def __len__(self):
        return len(self._ensemble._families.get(self._family, []))

    def __contains__(self, name):
        return name in self._ensemble._families.get(self._family, [])

    def __repr__(self):
        names = list(self._ensemble._families.get(self._family, []))
        return f"FamilyView('{self._family}', members={names})"


class Ensemble:
    """An organized collection of Instruments with family grouping and insert FX chains.

    Instruments are stored by name and optionally grouped into families.
    Each family can carry an insert FX chain that maps to a Score track.

    Access patterns::

        ens.strings['vln_I']              # dot-access  -> tagged (auto-routes)
        ens['strings']['vln_I']           # subscript   -> tagged (auto-routes)
        ens.family('strings')['vln_I']    # explicit    -> tagged (auto-routes)
        ens['vln_I']                      # direct      -> untagged (no auto-route)

    Parameters
    ----------
    name : str or None
        Optional name for the ensemble (used as default prefix in ``include``).
    """

    def __init__(self, name: str = None):
        self._name = name
        self._members: OrderedDict = OrderedDict()
        self._member_to_family: dict = {}
        self._families: OrderedDict = OrderedDict()
        self._family_inserts: dict = {}
        self._ungrouped: list = []

    @property
    def name(self):
        return self._name

    @property
    def families(self):
        return list(self._families.keys())

    @property
    def members(self):
        return OrderedDict(self._members)

    @property
    def ungrouped(self):
        return list(self._ungrouped)

    def add(self, name_or_inst, instrument=None, family=None):
        """Add an instrument to the ensemble.

        Supports two call signatures:

        - ``ens.add('vln_I', instrument, family='strings')``
        - ``ens.add(instrument, family='strings')``  (uses ``instrument.name``)

        Parameters
        ----------
        name_or_inst : str or Instrument
            Member name (str) or instrument whose ``.name`` is used.
        instrument : Instrument or None
            The instrument (required when first arg is a str).
        family : str or None
            Family to assign to.  If ``None``, the member is ungrouped.

        Returns
        -------
        Ensemble
            ``self``, for chaining.
        """
        if instrument is None:
            if not isinstance(name_or_inst, Instrument):
                raise TypeError(
                    "Single-argument add() requires an Instrument; "
                    f"got {type(name_or_inst).__name__}"
                )
            instrument = name_or_inst
            name = instrument.name
        else:
            name = name_or_inst

        if not isinstance(name, str) or not name:
            raise ValueError("Member name must be a non-empty string")
        if not isinstance(instrument, Instrument):
            raise TypeError(f"Expected Instrument, got {type(instrument).__name__}")
        if name in self._members:
            raise ValueError(f"Member '{name}' already exists")
        if name in self._families:
            raise ValueError(
                f"'{name}' is already a family name; member and family names must not collide"
            )
        if family is not None:
            if family in self._members:
                raise ValueError(
                    f"'{family}' is already a member name; family and member names must not collide"
                )
            if family in _RESERVED_ATTRS:
                raise ValueError(
                    f"'{family}' is a reserved Ensemble attribute; use ens.family('{family}') instead"
                )

        self._members[name] = instrument
        self._member_to_family[name] = family
        if family is not None:
            if family not in self._families:
                self._families[family] = []
            self._families[family].append(name)
        else:
            self._ungrouped.append(name)
        return self

    def remove(self, name: str):
        """Remove a member by name.

        Returns
        -------
        Ensemble
            ``self``, for chaining.
        """
        if name not in self._members:
            raise KeyError(f"Member '{name}' not found")
        family = self._member_to_family.pop(name, None)
        del self._members[name]
        if family is not None and family in self._families:
            self._families[family] = [n for n in self._families[family] if n != name]
            if not self._families[family]:
                del self._families[family]
                self._family_inserts.pop(family, None)
        else:
            self._ungrouped = [n for n in self._ungrouped if n != name]
        return self

    def family(self, name: str):
        """Return a :class:`_FamilyView` for the named family.

        This is the explicit, always-works access path.  The returned view
        yields tagged instruments (auto-route on ``set_instrument``).
        """
        if name not in self._families:
            raise KeyError(f"Family '{name}' not found")
        return _FamilyView(self, name)

    def set_inserts(self, family: str, inserts: list):
        """Set the insert FX chain for a family.

        Replaces any existing chain.  Order matters (signal flows left to right).

        Parameters
        ----------
        family : str
            Must be an existing family name.
        inserts : list of Effect
            The insert FX chain.

        Returns
        -------
        Ensemble
            ``self``, for chaining.
        """
        if family not in self._families:
            raise KeyError(f"Family '{family}' not found")
        for ins in inserts:
            if not isinstance(ins, Effect):
                raise TypeError(f"Expected Effect, got {type(ins).__name__}")
        self._family_inserts[family] = list(inserts)
        return self

    def inserts(self, family: str):
        """Return a copy of the insert chain for a family."""
        return list(self._family_inserts.get(family, []))

    def include(self, ensemble, prefix: str = None):
        """Absorb all members, families, and insert chains from another Ensemble.

        Parameters
        ----------
        ensemble : Ensemble
            Source ensemble.
        prefix : str or None
            Prefix for family and member names.  Defaults to the source
            ensemble's name (lowercased), or ``'ensemble'`` if unnamed.

        Returns
        -------
        Ensemble
            ``self``, for chaining.
        """
        explicit = prefix is not None
        if prefix is None:
            prefix = (ensemble.name or '').strip().lower() or 'ensemble'

        existing_families = set(self._families.keys())
        if any(f'{prefix}_{f}' in existing_families for f in ensemble._families):
            if explicit:
                raise ValueError(f"Explicit prefix '{prefix}' causes family name collision")
            base = prefix
            n = 2
            while any(f'{prefix}_{f}' in existing_families for f in ensemble._families):
                prefix = f'{base}_{n}'
                n += 1
            warnings.warn(
                f"Prefix '{base}' causes collision; using '{prefix}'",
                UserWarning,
                stacklevel=2,
            )

        for old_family, old_member_names in ensemble._families.items():
            new_family = f'{prefix}_{old_family}'
            for old_name in old_member_names:
                new_name = f'{prefix}_{old_name}'
                self.add(new_name, ensemble._members[old_name], family=new_family)
            old_inserts = ensemble._family_inserts.get(old_family)
            if old_inserts:
                self.set_inserts(new_family, _copy_inserts_with_fresh_uids(old_inserts))

        for old_name in ensemble._ungrouped:
            new_name = f'{prefix}_{old_name}'
            self.add(new_name, ensemble._members[old_name])

        return self

    def __getitem__(self, key):
        if key in self._families:
            return _FamilyView(self, key)
        if key in self._members:
            return self._members[key]
        raise KeyError(f"'{key}' is not a family or member name")

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            families = object.__getattribute__(self, '_families')
        except AttributeError:
            raise AttributeError(name)
        if name in families:
            return _FamilyView(self, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __dir__(self):
        base = list(super().__dir__())
        try:
            base.extend(self._families.keys())
        except AttributeError:
            pass
        return base

    def __contains__(self, name):
        return name in self._members

    def __iter__(self):
        return iter(self._members.items())

    def __len__(self):
        return len(self._members)

    def __str__(self):
        fam_summary = {f: len(m) for f, m in self._families.items()}
        label = f"'{self._name}'" if self._name else 'unnamed'
        return f"Ensemble({label}, families={fam_summary}, ungrouped={len(self._ungrouped)})"

    def __repr__(self):
        return self.__str__()
