import numbers
import random as _random
from collections import OrderedDict
from uuid import uuid4

from klotho.utils.data_structures.dictionaries import SafeDict


class _FamilyAccessor:
    """Subscriptable family namespace: ``obj.family['name']`` -> family view.

    Shared by :class:`Kit` and ``Ensemble``; the owner supplies the view
    type via its ``_family_view(name)`` method and the name list via its
    ``_families`` mapping.
    """

    __slots__ = ('_owner',)

    def __init__(self, owner):
        self._owner = owner

    def __getitem__(self, name):
        return self._owner._family_view(name)

    def __iter__(self):
        return iter(self._owner._families)

    def __len__(self):
        return len(self._owner._families)

    def __contains__(self, name):
        return name in self._owner._families

    def __repr__(self):
        return f"FamilyAccessor({list(self._owner._families)})"


class Instrument:
    """Engine-agnostic per-note voice with a name and default pfields.

    An Instrument carries the pfield defaults applied to every event it
    plays. Engine-specific subclasses (``SynthDefInstrument``,
    ``MidiInstrument``, ``ToneInstrument``) add backend details; this base
    class is what node assignment APIs such as ``UC.set_instrument`` accept.

    Parameters
    ----------
    name : str, optional
        Instrument name (default is ``'default'``).
    pfields : dict, optional
        Default parameter-field values for events played by this instrument.
    """

    def __init__(self, name='default', pfields=None):
        self._name = name
        if pfields is None:
            pfields = {}
        self._pfields = pfields if isinstance(pfields, SafeDict) else SafeDict(pfields)

    @property
    def name(self):
        """str : The instrument name."""
        return self._name

    @property
    def pfields(self):
        """dict : Copy of the instrument's default parameter fields."""
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


def _collection_repr_html(header, subheader, rows):
    """Small inline-styled table for notebook reprs of Kit/Ensemble.

    ``rows`` is a list of ``(label, entries, note)`` where ``entries``
    is a list of ``(text, sub)`` pairs (sub may be None) and ``note`` is
    an optional muted suffix line for the row.
    """
    border = "1px solid rgba(127,127,127,0.35)"
    muted = "opacity:0.6;font-size:0.85em;"
    parts = [
        "<div style='display:inline-block;font-family:inherit;'>",
        f"<div style='margin-bottom:4px;'><b>{header}</b>"
        f" <span style='{muted}'>{subheader}</span></div>",
        f"<table style='border-collapse:collapse;border:{border};'>",
    ]
    for label, entries, note in rows:
        chips = " ".join(
            f"<span style='white-space:nowrap;'>{text}"
            + (f"<span style='{muted}'>&thinsp;({sub})</span>" if sub else "")
            + "</span>"
            for text, sub in entries
        )
        if note:
            chips += f"<div style='{muted}'>{note}</div>"
        parts.append(
            f"<tr><td style='border:{border};padding:2px 8px;"
            f"vertical-align:top;text-align:right;'><b>{label}</b></td>"
            f"<td style='border:{border};padding:2px 8px;'>{chips}</td></tr>"
        )
    parts.append("</table></div>")
    return "".join(parts)


class KitFamilyView:
    """Read-only lens into a single Kit family; yields selector keys.

    Everything a view hands out is a *selector key* (the value you pass
    as the kit's ``voice=`` pfield): iteration, ``pick``, and the
    ``Pattern`` from ``cycle`` all speak keys.  ``view['name']`` returns
    the member Instrument itself for introspection.
    """

    __slots__ = ('_kit', '_name')

    def __init__(self, kit, name):
        self._kit = kit
        self._name = name

    @property
    def name(self):
        """str : The family name."""
        return self._name

    def _keys(self):
        return self._kit._families[self._name]

    def __iter__(self):
        return iter(self._keys())

    def __len__(self):
        return len(self._keys())

    def __contains__(self, key):
        return key in self._keys()

    def __getitem__(self, key):
        if key not in self._keys():
            raise KeyError(f"'{key}' is not a member of family '{self._name}'")
        return self._kit._members[key]

    def pick(self, *, rng=None):
        """Return a random selector key from this family.

        Parameters
        ----------
        rng : random.Random or None
            Source of randomness (module ``random`` if omitted).  The
            bound method is a zero-arg callable, so it can be handed
            directly to ``set_pfields(voice=kit.tas.pick)`` for a fresh
            draw on every sounding leaf.
        """
        r = _random if rng is None else rng
        return r.choice(list(self._keys()))

    def cycle(self):
        """Return a ``Pattern`` cycling this family's selector keys."""
        from klotho.topos.collections.sequences import Pattern
        return Pattern(list(self._keys()))

    def __repr__(self):
        return f"KitFamilyView('{self._name}', keys={list(self._keys())})"


class Kit(Instrument):
    """A collection of Instruments treated as a single instrument with a selector pfield.

    When assigned to a node via ``UC.set_instrument``, the Kit behaves like
    any other Instrument.  A designated selector pfield (default ``'voice'``)
    chooses which member is used for each event at assembly time: a member
    key, or an integer index (wrapping mod the member count).

    Members may optionally be grouped into named *families* (e.g. the
    bundled tabla kit groups its strokes into ``open``/``te``/``tas``/
    ``tun``).  Families are reached with ``kit.family['tas']`` or the
    dot shorthand ``kit.tas``; ``kit.pick('tas')`` draws a random
    selector key and ``kit.cycle('tas')`` returns a round-robin
    ``Pattern`` of keys.

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
    families : dict[str, list[str]] or None
        Optional named groupings of member keys.  Families may overlap;
        names must not collide with member keys or Kit attributes.
    """

    def __init__(self, members: dict, default: str = None, selector: str = 'voice',
                 families: dict = None):
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
        self._families = OrderedDict()
        if families:
            for fname, keys in families.items():
                if not isinstance(fname, str) or not fname:
                    raise ValueError(f"Family name must be a non-empty string, got {fname!r}")
                if fname in self._members:
                    raise ValueError(f"Family name '{fname}' collides with a member key")
                if hasattr(type(self), fname):
                    raise ValueError(
                        f"Family name '{fname}' collides with a {type(self).__name__} attribute"
                    )
                keys = list(keys)
                if not keys:
                    raise ValueError(f"Family '{fname}' has no members")
                unknown = [k for k in keys if k not in self._members]
                if unknown:
                    raise KeyError(f"Family '{fname}' references unknown members {unknown}")
                self._families[fname] = keys
        default_inst = self._members[self._default]
        pfields = dict(default_inst.pfields)
        pfields[self._selector] = self._default
        super().__init__(
            name=f"Kit({self._default})",
            pfields=pfields,
        )

    @property
    def default(self) -> str:
        """str : Key of the default member."""
        return self._default

    @property
    def selector(self) -> str:
        """str : Pfield name used to choose the active member."""
        return self._selector

    @property
    def members(self) -> dict:
        """dict : Copy of the mapping from selector keys to member Instruments."""
        return dict(self._members)

    @property
    def families(self) -> list:
        """list of str : Names of the kit's families."""
        return list(self._families)

    @property
    def family(self) -> _FamilyAccessor:
        """Family namespace: ``kit.family['tas']`` -> :class:`KitFamilyView`."""
        return _FamilyAccessor(self)

    def _family_view(self, name):
        if name not in self._families:
            raise KeyError(
                f"'{name}' is not a family of this kit (families: {list(self._families)})"
            )
        return KitFamilyView(self, name)

    def pick(self, family: str = None, *, rng=None):
        """Return a random selector key.

        Parameters
        ----------
        family : str or None
            Draw from this family; ``None`` draws from all members.
        rng : random.Random or None
            Source of randomness (module ``random`` if omitted).
        """
        r = _random if rng is None else rng
        if family is None:
            return r.choice(list(self._members))
        if family in self._families:
            return r.choice(list(self._families[family]))
        raise KeyError(
            f"'{family}' is not a family of this kit (families: {list(self._families)})"
        )

    def cycle(self, family: str = None):
        """Return a ``Pattern`` cycling selector keys (all members or one family)."""
        from klotho.topos.collections.sequences import Pattern
        if family is None:
            return Pattern(list(self._members))
        if family in self._families:
            return Pattern(list(self._families[family]))
        raise KeyError(
            f"'{family}' is not a family of this kit (families: {list(self._families)})"
        )

    def _member_by_index(self, index):
        keys = list(self._members)
        return self._members[keys[int(index) % len(keys)]]

    def _unknown_selector_error(self, key):
        msg = (f"Unknown {self._selector} {key!r} for Kit "
               f"(members: {list(self._members)})")
        if key in self._families:
            msg += (f". '{key}' is a family -- draw a member with "
                    f"kit.family['{key}'].pick() (or kit.{key}.pick())")
        return KeyError(msg)

    def _resolve(self, key=None):
        if key is None:
            return self._members[self._default]
        if isinstance(key, str):
            if key in self._members:
                return self._members[key]
            raise self._unknown_selector_error(key)
        if key in self._members:
            return self._members[key]
        if isinstance(key, numbers.Integral) and not isinstance(key, bool):
            return self._member_by_index(key)
        return self._members[self._default]

    def __getitem__(self, key):
        if key in self._members:
            return self._members[key]
        if isinstance(key, numbers.Integral) and not isinstance(key, bool):
            return self._member_by_index(key)
        return super().__getitem__(key)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            families = object.__getattribute__(self, '_families')
        except AttributeError:
            raise AttributeError(name)
        if name in families:
            return KitFamilyView(self, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __dir__(self):
        base = list(super().__dir__())
        try:
            base.extend(self._families.keys())
        except AttributeError:
            pass
        return base

    def __contains__(self, key):
        return key in self._members

    def __iter__(self):
        return iter(self._members)

    def __len__(self):
        return len(self._members)

    def __str__(self):
        keys = list(self._members.keys())
        label = f"Kit(members={keys}, default='{self._default}', selector='{self._selector}'"
        if self._families:
            label += f", families={dict(self._families)}"
        return label + ")"

    def __repr__(self):
        return self.__str__()

    def _member_entry(self, key):
        inst = self._members[key]
        sub = getattr(inst, 'defName', None)
        text = key if key != self._default else f"{key}&#8202;*"
        return (text, sub)

    def _repr_html_(self):
        rows = []
        grouped = set()
        for fname, keys in self._families.items():
            grouped.update(keys)
            rows.append((fname, [self._member_entry(k) for k in keys], None))
        rest = [k for k in self._members if k not in grouped]
        if rest:
            label = 'members' if not self._families else '&mdash;'
            rows.append((label, [self._member_entry(k) for k in rest], None))
        sub = (f"{len(self._members)} members &middot; selector "
               f"'{self._selector}' &middot; * default")
        return _collection_repr_html(type(self).__name__, sub, rows)


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
        """str : The effect name."""
        return self._name

    @property
    def uid(self):
        """str : Unique identifier for this effect instance."""
        return self._uid

    @property
    def pfields(self):
        """dict : Copy of the effect's default parameter fields."""
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
