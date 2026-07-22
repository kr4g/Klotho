import copy
import random as _random
import warnings
from collections import OrderedDict
from uuid import uuid4

from klotho.utils.data_structures.dictionaries import SafeDict

from .base import Instrument, Effect, _FamilyAccessor
from .synthdef import _TR808_TOM_TUNINGS


def _copy_inserts_with_fresh_uids(inserts):
    result = []
    for ins in inserts:
        new_ins = copy.copy(ins)
        new_ins._uid = uuid4().hex[:12]
        result.append(new_ins)
    return result


def _copy_instrument(inst):
    """Shallow-copy an instrument with its own pfields dict, so included
    members don't share mutable state with the source ensemble."""
    new = copy.copy(inst)
    new._pfields = SafeDict(dict(inst._pfields))
    return new

# Family layouts for the bundled instrument banks. Values follow the
# constructor's member-spec forms (list -> member named from the path
# basename; dict -> {generic_name: defName}; a ``(defName, overrides)``
# tuple in either form carries per-member pfield defaults).
_BUNDLED_BANKS = {
    'edm': {
        'drums':  ['edm/kick', 'edm/deepKick', 'edm/kickSoft', 'edm/snare',
                   'edm/snare2', 'edm/ghostSnare', 'edm/clap', 'edm/tom'],
        'hats':   ['edm/hat', 'edm/hat2', 'edm/hatLong', 'edm/hatShort'],
        'perc':   ['edm/woodblock', 'edm/clank', 'edm/blip', 'edm/rubber1',
                   'edm/rubber2', 'edm/ping'],
        'wubs':   ['edm/wub1', 'edm/wub2', 'edm/wub3'],
        'bass':   ['edm/subBass'],
        'sweeps': ['edm/sweep', 'edm/revCymbal', 'edm/chipSweep1',
                   'edm/chipSweep2', 'edm/chipSweep3'],
    },
    'lofi': {
        'glitch':  ['lofi/glitchBurst', 'lofi/glitchZap', 'lofi/glitchBlip'],
        'drums':   {'dustKick': 'lofi/dustKick', 'loSnare': 'lofi/snare',
                    'ghostSnare': 'lofi/ghostSnare', 'rim': 'lofi/rim',
                    'hushHat': 'lofi/hushHat', 'hushHatOpen': 'lofi/hushHatOpen',
                    'tapePop': 'lofi/tapePop', 'tapeTick': 'lofi/tapeTick',
                    'tapeSnap': 'lofi/tapeSnap', 'dustCrackle': 'lofi/dustCrackle'},
        'pads':    ['lofi/hazePad', 'lofi/driftPad', 'lofi/glassLead'],
        'arps':    {'beep': 'lofi/beep', 'dustPluck': 'lofi/dustPluck',
                    'loLead': 'lofi/lead'},
        'bass':    ['lofi/subBass', 'lofi/tapeBass'],
        'accents': ['lofi/wash', 'lofi/cresc', 'lofi/tapeRise', 'lofi/tapeCrash'],
    },
    'chip': {
        'chords': ['chip/pulseChord', 'chip/powerDown'],
        'pads':   {'glassPad': 'chip/glassPad', 'chipRiser': 'chip/riser'},
        'arps':   {'chipLead': 'chip/lead', 'fmBell': 'chip/fmBell',
                   'blipLead': 'chip/blipLead'},
        'coins':  ['chip/coinBlip', 'chip/powerArp', 'chip/zapDown'],
        'bass':   {'chipBass': 'chip/bass'},
        'drums':  ['chip/gridKick', 'chip/bitSnare', 'chip/tickHat'],
    },
    'tr808': {
        'drums':   ['tr808/kick', 'tr808/snare', 'tr808/clap', 'tr808/rim'],
        'toms':    {k: ('tr808/tom', _TR808_TOM_TUNINGS[k])
                    for k in ('lowTom', 'midTom', 'hiTom')},
        'congas':  {k: ('tr808/tom', _TR808_TOM_TUNINGS[k])
                    for k in ('lowConga', 'midConga', 'hiConga')},
        'perc':    ['tr808/clave', 'tr808/maracas', 'tr808/cowbell'],
        'cymbals': ['tr808/hat', 'tr808/hatOpen', 'tr808/cymbal'],
    },
}


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

    def pick(self, *, rng=None):
        """Return a random member of this family, tagged for auto-routing.

        Parameters
        ----------
        rng : random.Random or None
            Source of randomness (module ``random`` if omitted).  The
            bound method is a zero-arg callable, so it can be handed
            directly to ``set_instrument(leaves, ens.drums.pick)`` for
            a fresh draw on every sounding leaf.
        """
        r = _random if rng is None else rng
        return self._tagged(r.choice(self._ensemble._families[self._family]))

    def cycle(self):
        """Return a ``Pattern`` cycling this family's tagged instruments."""
        from klotho.topos.collections.sequences import Pattern
        return Pattern([self._tagged(n)
                        for n in self._ensemble._families[self._family]])

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

    Compositions should speak *generic member names* (``'softPad'``,
    ``'kick'``); the ensemble maps each name onto a concrete instrument,
    so re-assigning a member here re-skins every piece that speaks it.

    Access patterns (dots navigate, brackets look up, methods act)::

        ens['vln_I']               # member by name -> tagged (auto-routes)
        ens.voice('vln_I')         # same, tolerant form (non-strings pass through)
        ens.family['strings']      # family view
        ens.strings                # dot shorthand for the same view
        ens.strings['vln_I']       # member via its family -> tagged
        ens.pick('strings')        # random member of a family -> tagged
        ens.cycle('strings')       # Pattern round-robining the family

    The whole roster can be declared up front.  Member specs are either
    ``Instrument`` instances or SynthDef names (path-style or underscore;
    looked up in the SuperSonic manifest).  A family given as a *list*
    names each member after the last path segment; a *dict* names them
    explicitly (``{generic_name: defName}``)::

        ens = Ensemble('lofi', families={
            'glitch': ['lofi/glitchBurst', 'lofi/glitchZap'],   # members: glitchBurst, glitchZap
            'pads':   {'softPad': 'fd_sinepad',                 # generic -> concrete
                       'hazePad': 'lofi/hazePad'},
        }, ungrouped=['lofi/wash', 'lofi/cresc'])

    Parameters
    ----------
    name : str or None
        Optional name for the ensemble (used as default prefix in ``include``).
    families : dict or None
        Mapping of family name to member spec (list or dict, as above).
    ungrouped : dict or list or None
        Member specs added without a family (they route to master).
    """

    def __init__(self, name: str = None, families: dict = None, ungrouped=None):
        self._name = name
        self._members: OrderedDict = OrderedDict()
        self._member_to_family: dict = {}
        self._families: OrderedDict = OrderedDict()
        self._family_inserts: dict = {}
        self._ungrouped: list = []
        if families:
            for family, members in families.items():
                for member_name, spec in self._iter_member_specs(members):
                    self.add(member_name, self._coerce_instrument(spec, member_name), family=family)
        if ungrouped:
            for member_name, spec in self._iter_member_specs(ungrouped):
                self.add(member_name, self._coerce_instrument(spec, member_name))

    @staticmethod
    def _iter_member_specs(members):
        if isinstance(members, dict):
            yield from members.items()
            return
        for spec in members:
            if isinstance(spec, Instrument):
                yield spec.name, spec
            elif isinstance(spec, str):
                yield spec.rsplit('/', 1)[-1], spec
            elif isinstance(spec, tuple) and spec and isinstance(spec[0], str):
                yield spec[0].rsplit('/', 1)[-1], spec
            else:
                raise TypeError(
                    f"Member spec must be an Instrument, a SynthDef name "
                    f"string, or a (defName, overrides) tuple; "
                    f"got {type(spec).__name__}"
                )

    @staticmethod
    def _coerce_instrument(spec, member_name):
        if isinstance(spec, Instrument):
            return spec
        overrides = {}
        if (isinstance(spec, tuple) and len(spec) == 2
                and isinstance(spec[0], str) and isinstance(spec[1], dict)):
            spec, overrides = spec
        if isinstance(spec, str):
            from .synthdef import SynthDefInstrument
            from ._shared import canonical_def_name, load_ss_manifest
            def_name = canonical_def_name(spec)
            if def_name not in load_ss_manifest():
                raise ValueError(
                    f"Unknown SynthDef name {spec!r} for member "
                    f"{member_name!r}. Names must match the SuperSonic "
                    f"manifest (path-style sugar like 'edm/kick' is allowed)."
                )
            return SynthDefInstrument.from_manifest(
                def_name, name=member_name, **overrides)
        raise TypeError(
            f"Member spec must be an Instrument, a SynthDef name string, "
            f"or a (defName, overrides) tuple; got {type(spec).__name__}"
        )

    @property
    def name(self):
        """str or None : The ensemble name."""
        return self._name

    @property
    def families(self):
        """list of str : Names of all families in the ensemble."""
        return list(self._families.keys())

    @property
    def members(self):
        """OrderedDict : Copy of the mapping from member names to Instruments."""
        return OrderedDict(self._members)

    @property
    def ungrouped(self):
        """list of str : Names of members not assigned to any family."""
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
            if family not in self._families and hasattr(type(self), family):
                raise ValueError(
                    f"Family name '{family}' collides with an Ensemble attribute"
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

    @property
    def family(self) -> _FamilyAccessor:
        """Family namespace: ``ens.family['strings']`` -> :class:`_FamilyView`.

        The returned views yield tagged instruments (auto-route on
        ``set_instrument``).
        """
        return _FamilyAccessor(self)

    def _family_view(self, name):
        if name not in self._families:
            raise KeyError(
                f"Family '{name}' not found (families: {list(self._families)})"
            )
        return _FamilyView(self, name)

    def pick(self, family: str = None, *, rng=None):
        """Return a random member instrument, tagged for auto-routing.

        Parameters
        ----------
        family : str or None
            Draw from this family; ``None`` draws from all members.
        rng : random.Random or None
            Source of randomness (module ``random`` if omitted).  The
            bound method is a zero-arg callable, so it can be handed
            directly to ``set_instrument(leaves, ens.drums.pick)`` for
            a fresh draw on every sounding leaf.
        """
        if family is not None:
            return self._family_view(family).pick(rng=rng)
        r = _random if rng is None else rng
        return self.voice(r.choice(list(self._members)))

    def cycle(self, family: str = None):
        """Return a ``Pattern`` cycling tagged member instruments
        (all members or one family)."""
        if family is not None:
            return self._family_view(family).cycle()
        from klotho.topos.collections.sequences import Pattern
        return Pattern([self.voice(n) for n in self._members])

    @classmethod
    def _bundled(cls, bank, name, only, extras):
        families = _BUNDLED_BANKS[bank]
        if only is not None:
            only = list(only)
            unknown = [f for f in only if f not in families]
            if unknown:
                raise KeyError(
                    f"Unknown {bank} families {unknown}; "
                    f"available: {list(families)}"
                )
            families = {f: families[f] for f in only}
        ens = cls(name or bank, families=families)
        if extras:
            for family, members in extras.items():
                for member_name, spec in cls._iter_member_specs(members):
                    ens.add(member_name, cls._coerce_instrument(spec, member_name), family=family)
        return ens

    @classmethod
    def edm(cls, name='edm', only=None, extras=None):
        """Build the bundled ``edm`` beats ensemble.

        Families: ``drums`` (kick, deepKick, kickSoft, snare, snare2,
        ghostSnare, clap, tom), ``hats`` (hat, hat2, hatLong, hatShort),
        ``perc`` (woodblock, clank, blip, rubber1, rubber2, ping),
        ``wubs`` (wub1-3), ``bass`` (subBass), ``sweeps`` (sweep,
        revCymbal, chipSweep1-3).

        Parameters
        ----------
        name : str
            Ensemble name (default ``'edm'``).
        only : iterable of str or None
            Keep only these families.
        extras : dict or None
            Extra members to graft in, as ``{family: member_spec}``
            (same spec forms as the constructor); families are created
            as needed.
        """
        return cls._bundled('edm', name, only, extras)

    @classmethod
    def lofi(cls, name='lofi', only=None, extras=None):
        """Build the bundled ``lofi`` (Aphex) ensemble.

        Families: ``glitch`` (glitchBurst, glitchZap, glitchBlip),
        ``drums`` (dustKick, loSnare, ghostSnare, rim, hushHat,
        hushHatOpen, tapePop, tapeTick, tapeSnap, dustCrackle),
        ``pads`` (hazePad, driftPad, glassLead), ``arps`` (beep,
        dustPluck, loLead), ``bass`` (subBass, tapeBass), ``accents``
        (wash, cresc, tapeRise, tapeCrash).

        Parameters are as for :meth:`edm`.
        """
        return cls._bundled('lofi', name, only, extras)

    @classmethod
    def chip(cls, name='chip', only=None, extras=None):
        """Build the bundled ``chip`` (retro-console) ensemble.

        Families: ``chords`` (pulseChord, powerDown), ``pads``
        (glassPad, chipRiser), ``arps`` (chipLead, fmBell, blipLead),
        ``coins`` (coinBlip, powerArp, zapDown), ``bass`` (chipBass),
        ``drums`` (gridKick, bitSnare, tickHat).

        Parameters are as for :meth:`edm`.
        """
        return cls._bundled('chip', name, only, extras)

    @classmethod
    def tr808(cls, name='tr808', only=None, extras=None):
        """Build the bundled ``tr808`` drum machine ensemble.

        Families: ``drums`` (kick, snare, clap, rim), ``toms``
        (lowTom, midTom, hiTom), ``congas`` (lowConga, midConga,
        hiConga), ``perc`` (clave, maracas, cowbell), ``cymbals``
        (hat, hatOpen, cymbal).  The tom and conga members share the
        ``tr808_tom`` SynthDef with per-member tunings.

        Parameters are as for :meth:`edm`.
        """
        return cls._bundled('tr808', name, only, extras)

    def voice(self, name):
        """Resolve a member name to its instrument, tagged with its home family.

        The composition-facing lookup: pieces speak generic member names
        and ``voice`` maps them onto whatever instrument the ensemble
        currently assigns, so re-assigning a member re-skins every piece
        that speaks it.  Grouped members come back tagged (their events
        auto-route to the family's Score track); ungrouped members come
        back untagged (they route to master).

        Parameters
        ----------
        name : str or Instrument
            Member name.  Non-string values (already-resolved
            instruments) pass through unchanged, so ``voice`` can wrap
            any ``inst`` argument.

        Returns
        -------
        Instrument
        """
        if not isinstance(name, str):
            return name
        family = self._member_to_family.get(name)
        if family is not None:
            return self._family_view(family)[name]
        if name in self._members:
            return self._members[name]
        raise KeyError(
            f"'{name}' is not a member of ensemble "
            f"{self._name or '(unnamed)'} (members: {', '.join(self._members) or 'none'})"
        )

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

        Member instruments are copied (mutating the source ensemble's
        members afterwards does not affect this one) and insert chains
        get fresh uids.  The check is atomic: on any name collision
        nothing is merged.

        Parameters
        ----------
        ensemble : Ensemble
            Source ensemble.
        prefix : str or None
            Prefix for family and member names.  ``None`` (default) uses
            the source ensemble's name (lowercased), or ``'ensemble'``
            if unnamed, auto-numbering on collision.  Pass ``''`` to
            merge names unchanged (raises on collision).

        Returns
        -------
        Ensemble
            ``self``, for chaining.
        """
        explicit = prefix is not None
        if prefix is None:
            prefix = (ensemble.name or '').strip().lower() or 'ensemble'

        def _renamed(name, pfx):
            return f'{pfx}_{name}' if pfx else name

        def _clashes(pfx):
            found = []
            for f in ensemble._families:
                nf = _renamed(f, pfx)
                if nf in self._families or nf in self._members:
                    found.append(f"family '{nf}'")
                elif hasattr(type(self), nf):
                    found.append(f"family '{nf}' (Ensemble attribute)")
            for m in ensemble._members:
                nm = _renamed(m, pfx)
                if nm in self._members or nm in self._families:
                    found.append(f"member '{nm}'")
            return found

        clashes = _clashes(prefix)
        if clashes and not explicit:
            base = prefix
            n = 2
            while _clashes(prefix):
                prefix = f'{base}_{n}'
                n += 1
            warnings.warn(
                f"Prefix '{base}' causes collision; using '{prefix}'",
                UserWarning,
                stacklevel=2,
            )
            clashes = []
        if clashes:
            raise ValueError(
                f"include() name collisions with prefix {prefix!r}: "
                + ', '.join(clashes)
            )

        for old_family, old_member_names in ensemble._families.items():
            new_family = _renamed(old_family, prefix)
            for old_name in old_member_names:
                self.add(_renamed(old_name, prefix),
                         _copy_instrument(ensemble._members[old_name]),
                         family=new_family)
            old_inserts = ensemble._family_inserts.get(old_family)
            if old_inserts:
                self.set_inserts(new_family, _copy_inserts_with_fresh_uids(old_inserts))

        for old_name in ensemble._ungrouped:
            self.add(_renamed(old_name, prefix),
                     _copy_instrument(ensemble._members[old_name]))

        return self

    def __getitem__(self, key):
        if key in self._families:
            raise KeyError(
                f"'{key}' is a family -- use ens.family['{key}'] (or ens.{key}); "
                f"subscript access looks up members"
            )
        return self.voice(key)

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
        return iter(self._members)

    def items(self):
        """Return ``(name, instrument)`` pairs for all members."""
        return list(self._members.items())

    def __len__(self):
        return len(self._members)

    def __str__(self):
        fam_summary = {f: len(m) for f, m in self._families.items()}
        label = f"'{self._name}'" if self._name else 'unnamed'
        return f"Ensemble({label}, families={fam_summary}, ungrouped={len(self._ungrouped)})"

    def __repr__(self):
        return self.__str__()

    def _repr_html_(self):
        from .base import _collection_repr_html

        def entry(name):
            return (name, getattr(self._members[name], 'defName', None))

        rows = []
        for fname, names in self._families.items():
            note = None
            inserts = self._family_inserts.get(fname)
            if inserts:
                note = 'fx: ' + ' &rarr; '.join(
                    getattr(fx, 'defName', fx.name) for fx in inserts)
            rows.append((fname, [entry(n) for n in names], note))
        if self._ungrouped:
            rows.append(('ungrouped', [entry(n) for n in self._ungrouped], None))
        header = f"Ensemble {self._name!r}" if self._name else "Ensemble"
        sub = f"{len(self._members)} members &middot; {len(self._families)} families"
        return _collection_repr_html(header, sub, rows)
