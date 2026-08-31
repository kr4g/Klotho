"""
Compositional units combining temporal structure with parameterized events.

This module provides ``CompositionalUnit``, which extends ``TemporalUnit``
by replacing its rhythm tree with a single **fused** ``CompositionalTree``
carrying rhythm and parameters on one topology -- for hierarchical parameter
management, envelope application, slur marking, and instrument assignment.
The ``Parametron`` class extends ``Chronon`` with parameter field access.

**There is no synchronized ``ParameterTree``, and there never was one to
synchronize** (docket DOC-8). This header used to claim a shadow tree that
the class docstring and :class:`CompositionalTree` both explicitly deny;
the header was simply wrong. The one tree is ``uc._rt``; ``uc.rt`` returns
a *copy* of it and ``uc.pt`` builds an *effective* ``ParameterTree``
snapshot on demand. Neither is stored, and mutating either does not reach
the unit.
"""

from typing import Union, Optional, Any, Literal
from fractions import Fraction
from dataclasses import dataclass, field
import inspect
import warnings
import weakref
import numpy as _np
import pandas as pd

_PARAMETRON_TEMPORAL_ATTRS = frozenset({
    'start', 'duration', 'end', 'proportion', 'metric_duration',
    'metric_onset', 'node_id', 'is_rest', 'real_onset', 'real_duration'})

from klotho.chronos import TemporalUnit, RhythmTree, Meas
from klotho.chronos.temporal_units.temporal import Chronon, NodeContext, UTNodeHandle, UTNodeSelector
from klotho.chronos.temporal_units.temporal import _UNSET as _UT_UNSET
from klotho.thetos.parameters import ParameterTree
from klotho.thetos.parameters.parameter_tree import ParameterApiMixin, ParameterLayer
from klotho.thetos.parameters.bind import Bind
from klotho.thetos.instruments import Instrument
from klotho.thetos.instruments.base import Effect
from klotho.thetos.instruments.base import Kit
from klotho.dynatos.envelopes import Envelope
from klotho.topos.collections.sequences import Pattern


class CompositionalTree(ParameterApiMixin, RhythmTree):
    """A single tree carrying both a rhythm layer and a parameter layer.

    This fuses what were previously two topologically-mirrored trees (an
    ``RhythmTree`` and a ``ParameterTree``) into one topology, so there is no
    sync to maintain: node ids are shared by construction. Rhythm data
    (``proportion``/``tied`` -> ``metric_duration``/``metric_onset``) is owned by
    the inherited :class:`RhythmLayer`; parameter data (pfields/mfields,
    instruments, inheritance) is owned by an attached :class:`ParameterLayer`
    and exposed through :class:`ParameterApiMixin`.
    """

    def _init_layers(self):
        super()._init_layers()
        self._param_layer = self.attach_layer(ParameterLayer())

    def _after_subtree_built(self, new_tree, node_mapping, renumber):
        """Carry the parameter layer onto a subtree extracted from this tree.

        Without this hook ``uc._rt.subtree(node)`` came back rhythm-only:
        the field registries, every per-node override and every instrument
        binding were dropped, and silently. It is the same gap NEW-21 closed
        on the graft path, which fixed only the direction it was scoped to.

        Values are written as **effective** values at every node, matching
        what :class:`ParameterTree` already does -- its subtree copies each
        node's effective dict -- and what the graft path does. The subtree's
        root has lost its ancestors, so anything it inherited from outside
        would otherwise vanish. The governing instrument is carried across
        for the same reason: it is inherited by the same ancestor walk, and
        a subtree that keeps its pfields but loses its instrument does not
        play.

        Writes route through ``set_pfields``/``set_mfields`` rather than
        ``update_node_data``, because on a ``CompositionalTree`` the rhythm
        layer owns the write path and rejects param keys.
        """
        new_tree.register_pfields(self.pfield_names)
        new_tree.register_mfields(self.mfield_names)

        pfield_names = self.pfield_names
        mfield_names = self.mfield_names
        for old_node, new_node in node_mapping.items():
            effective = self.items(old_node)
            pfields = {k: v for k, v in effective.items() if k in pfield_names}
            mfields = {k: v for k, v in effective.items() if k in mfield_names}
            if pfields:
                new_tree.set_pfields(new_node, **pfields)
            if mfields:
                new_tree.set_mfields(new_node, **mfields)

        for old_node, instrument in self.node_instruments.items():
            mapped = node_mapping.get(old_node)
            if mapped is not None:
                new_tree.set_instrument(mapped, instrument)

        if new_tree.get_instrument(new_tree.root) is None:
            source_root = next(
                (old for old, new in node_mapping.items() if new == new_tree.root),
                None,
            )
            if source_root is not None:
                governing = self.get_instrument(source_root)
                if governing is not None:
                    new_tree.set_instrument(new_tree.root, governing)

        new_tree._param_layer._effective_cache = None

    def _announce_leaf_surface_change(self):
        """The THIRD id-state event: a leaf that STOPPED BEING A LEAF.

        ``subdivide``/``graft_subtree`` destroy no ids and move none -- the
        edited node keeps its id in place -- but it is interior now, and the
        id-keyed overlays that name it (slur members, control-envelope
        subsets) would inherit their markers onto every note of the subtree
        it grew. The relocation handlers already re-derive leaf-ness from
        the tree, so the event is announced as the identity relocation over
        the (unmoved, undestroyed) survivors.

        The owning unit's verbs suppress this: they follow the edit with a
        richer heal that ABSORBS the new leaves into the spans the ex-leaf
        anchored (``_heal_slurs_after_subdivide``), and that heal has to see
        the specs un-stripped.
        """
        if getattr(self, '_owner_absorbs_leaf_growth', False):
            return
        self._notify_nodes_relocated({n: n for n in self.nodes})

    def subdivide(self, node, S):
        """Subdivide leaf node(s) (see :meth:`RhythmTree.subdivide`),
        announcing the leaf-surface change so overlays drop the
        now-interior node."""
        result = super().subdivide(node, S)
        self._announce_leaf_surface_change()
        return result

    def graft_subtree(self, target_node, subtree, mode='replace'):
        """Graft at a leaf (see :meth:`RhythmTree.graft_subtree`),
        announcing the leaf-surface change so overlays drop the
        now-interior node."""
        result = super().graft_subtree(target_node, subtree, mode)
        self._announce_leaf_surface_change()
        return result

    def move_subtree(self, node, new_parent):
        """Re-parent a subtree (see :meth:`Tree.move_subtree`), announcing
        the leaf-surface change.

        ``new_parent`` may have been a leaf a moment ago; it is interior
        now. That is the same THIRD event ``subdivide`` and
        ``graft_subtree`` announce, and it was the one member of the class
        left unwired -- so a slur's end marker landed on the note that
        moved IN, which was never in the slur."""
        result = super().move_subtree(node, new_parent)
        self._announce_leaf_surface_change()
        return result

    # DEATH through a verb reached on the raw tree. ``_announce_leaf_surface_change``
    # publishes the identity relocation over the SURVIVORS, and
    # ``_notify_nodes_relocated`` reads absence from that mapping as destroyed --
    # so the one seam serves both events and no third mechanism is introduced.
    # The owning unit's own deleters suppress it via ``_owner_absorbs_leaf_growth``
    # and run their richer heal instead; these overrides exist for the raw
    # ``uc._rt.*`` path, which nothing intercepted.

    def prune(self, node):
        """Prune a leaf (see :meth:`Tree.prune`), announcing the death so
        no overlay keeps naming the freed id."""
        result = super().prune(node)
        self._announce_leaf_surface_change()
        return result

    def remove_subtree(self, node):
        """Remove a subtree (see :meth:`Tree.remove_subtree`), announcing
        the death so no overlay keeps naming a freed id."""
        result = super().remove_subtree(node)
        self._announce_leaf_surface_change()
        return result

    def prune_leaves(self, n):
        """Prune leaves (see :meth:`Tree.prune_leaves`), announcing the
        deaths so no overlay keeps naming a freed id."""
        result = super().prune_leaves(n)
        self._announce_leaf_surface_change()
        return result

    def prune_to_depth(self, max_depth):
        """Truncate below a depth (see :meth:`Tree.prune_to_depth`),
        announcing the deaths so no overlay keeps naming a freed id."""
        result = super().prune_to_depth(max_depth)
        self._announce_leaf_surface_change()
        return result


@dataclass(frozen=True)
class ParentDistributionView:
    """Read-only view of a parent node during pfield/mfield distribution.

    Carries the parent's structural handle (``ref``), rest status, current
    effective ``pfields``/``mfields``, and resolved ``instrument``.
    Selection fields (``index``/``total``) are intentionally absent —
    parents are not part of the current distribution selection. ``parent``
    chains upward lazily, so ``ctx.parent.parent.depth`` is valid up to the
    root. Unknown attributes forward to the handle -- the same structural,
    timing and navigation set as :class:`NodeContext`, minus
    ``index``/``total``. ``dir()`` lists them.
    """

    ref: UTNodeHandle
    is_rest: bool
    pfields: dict
    mfields: dict
    instrument: Any
    _owner: Any = field(repr=False, compare=False)

    @property
    def id(self) -> int:
        """int : The raw integer node id."""
        return self.ref.id

    @property
    def parent(self) -> Optional['ParentDistributionView']:
        """ParentDistributionView or None : Lazy view of the next parent up (None at the root)."""
        return self._owner._build_parent_distribution_view(self.id)

    def __getattr__(self, key):
        return getattr(self.ref, key)

    def __dir__(self):
        # __getattr__ forwards to the handle, so the forwarded names --
        # depth, path, sibling_index, sibling_total, proportion,
        # real_onset, leaves, children ... -- are invisible to plain dir()
        # and to tab completion. That invisibility is how an audit once
        # concluded they were missing. Advertise them.
        return sorted(set(object.__dir__(self)) | set(dir(self.ref)))


@dataclass(frozen=True)
class DistributionContext(NodeContext):
    """Per-node context handed to callables during pfield/mfield distribution.

    Extends :class:`NodeContext` (``index``/``total`` within the selection,
    plus every forwarded handle attribute -- ``depth``, ``path``,
    ``sibling_index``, ``sibling_total``, ``proportion``, ``real_onset``,
    ``real_duration``, ``leaves``, ``children`` ...) with the node's rest
    status, current
    effective ``pfields``/``mfields``, and resolved ``instrument``.
    ``ctx.parent`` returns a :class:`ParentDistributionView`.
    """

    is_rest: bool
    pfields: dict
    mfields: dict
    instrument: Any
    _owner: Any = field(repr=False, compare=False)

    @property
    def parent(self) -> Optional[ParentDistributionView]:
        """ParentDistributionView or None : View of the parent node (None at the root)."""
        return self._owner._build_parent_distribution_view(self.id)


PFieldContext = DistributionContext

# Meta-field names the playback engine consumes (poly-voice strum spread and
# track/group routing). The unified ``set()`` routes bare kwargs with these
# names to mfields; everything else goes to pfields.
ENGINE_MFIELDS = frozenset({'strum', 'group'})


def _leaf_ordinal(pt, node):
    """Position of *node* among the tree's leaves (0 for non-leaves).

    The rotation ordinal for family round-robin: keyed on tree position
    rather than call order, so resolving the same leaf any number of
    times (display, IR build, per-voice lowering) picks the same member
    and replays are identical.
    """
    try:
        return pt.leaf_index_map.get(node, 0)
    except AttributeError:
        return 0


def _concretize_family_selector(kit, selector_val, pt, node):
    """Map family names in a selector value to concrete member keys.

    Scalars rotate by the leaf's position among the tree's leaves; tuple
    elements offset that ordinal by their position, so simultaneous
    voices drawing from one pool get different variants. Non-family
    values pass through unchanged (``is``-identity preserved).
    """
    if isinstance(selector_val, str) and selector_val in kit._families:
        return kit._family_member_key_at(selector_val, _leaf_ordinal(pt, node))
    if isinstance(selector_val, tuple) and selector_val:
        base = None
        out = list(selector_val)
        changed = False
        for i, el in enumerate(selector_val):
            if isinstance(el, str) and el in kit._families:
                if base is None:
                    base = _leaf_ordinal(pt, node)
                out[i] = kit._family_member_key_at(el, base + i)
                changed = True
        return tuple(out) if changed else selector_val
    return selector_val


def _merge_kit_member_defaults(kit, selector_tuple):
    """Element-wise merge of member default pfields for a tuple selector.

    Each element of *selector_tuple* resolves to a Kit member; for every
    default pfield key across those members, the merged dict carries a
    scalar when all members agree and a tuple aligned with the selector
    tuple otherwise (so each expanded voice gets its own member's
    defaults, e.g. per-voice ``buf`` for sampler kits).
    """
    members = [kit._resolve(k, advance=False) for k in selector_tuple]
    dicts = [dict(m.pfields) if hasattr(m, 'pfields') else {} for m in members]
    keys = []
    for d in dicts:
        for k in d:
            if k not in keys:
                keys.append(k)
    merged = {}
    for k in keys:
        values = [d.get(k) for d in dicts]
        present = [v for v in values if v is not None]
        if not present:
            continue
        first = present[0]
        if all(v == first for v in present):
            merged[k] = first
        else:
            merged[k] = tuple(v if v is not None else first for v in values)
    return merged


def _resolve_kit_member(inst, pt, node):
    if isinstance(inst, Kit):
        selector_val = pt.get_pfield(node, inst.selector)
        selector_val = _concretize_family_selector(inst, selector_val, pt, node)
        if isinstance(selector_val, tuple) and selector_val:
            from types import SimpleNamespace
            return SimpleNamespace(
                pfields=_merge_kit_member_defaults(inst, selector_val)
            )
        # Compose-time introspection: never step the loose-Event rotation
        # counters (families were concretized above anyway).
        return inst._resolve(selector_val, advance=False)
    return inst


def _build_pfield_context(uc, node: int, index: int, total: int, is_rest: bool) -> DistributionContext:
    _ = is_rest
    return uc._build_node_context(node, index, total)


_CALLABLE_ARITY_MEMO = weakref.WeakKeyDictionary()


def _callable_arity(fn):
    # inspect.signature costs 13-102us per call and target loops used to
    # re-derive it per node; memoize on the function object (weakly, so
    # user lambdas are not pinned)
    try:
        return _CALLABLE_ARITY_MEMO[fn]
    except (KeyError, TypeError):
        pass
    try:
        sig = inspect.signature(fn)
        # count POSITIONAL slots, not required ones: a defaulted positional
        # (lambda c=None: ...) still wants the context, while the documented
        # zero-arg bound-method idiom (ens.drums.pick, signature (*, rng=None))
        # must keep reporting 0 -- so keyword-only and **kwargs never count.
        _POSITIONAL = (inspect.Parameter.POSITIONAL_ONLY,
                       inspect.Parameter.POSITIONAL_OR_KEYWORD,
                       inspect.Parameter.VAR_POSITIONAL)
        arity = len([p for p in sig.parameters.values()
                     if p.kind in _POSITIONAL])
    except (ValueError, TypeError):
        arity = 0
    try:
        _CALLABLE_ARITY_MEMO[fn] = arity
    except TypeError:
        pass
    return arity


def _instrument_shape_error(instrument):
    """Message naming every shape ``set_instrument`` accepts.

    Shared by CompositionalUnit.set_instrument (which rejects the argument
    itself) and ParameterLayer.set_instrument (which rejects whatever a
    callable RETURNED), so both report the same accept-list.
    """
    return (
        f"set_instrument got {type(instrument).__name__!r}, which is not a "
        f"usable instrument: {instrument!r}. Accepted: an Instrument or "
        f"Effect instance, a SynthDef name (str), a synth id (int), a "
        f"Pattern, or a 0-/1-arg callable returning one of those. "
        f"(An Ensemble family view is not itself an instrument -- call it, "
        f"e.g. ens.drums.pick, or index a member.)"
    )


def _reject_fx_as_instrument(def_name):
    """Raise if *def_name* names a known effect or infra SynthDef.

    Voice assignment (``set_instrument``) is for instrument defs only;
    effects belong in a track's insert chain. No-ops for non-strings and
    names of unknown kind (treated as instruments).
    """
    if not isinstance(def_name, str) or not def_name:
        return
    global _ss_synth_kind
    if _ss_synth_kind is None:
        from klotho.thetos.instruments._shared import ss_synth_kind
        _ss_synth_kind = ss_synth_kind
    kind = _ss_synth_kind(def_name)
    if kind == 'fx':
        raise TypeError(
            f"'{def_name}' is an effect SynthDef, not an instrument. Use "
            f"SynthDefFX('{def_name}', ...) in Score.track(inserts=[...]) "
            f"or Ensemble.set_inserts(...) instead of set_instrument."
        )
    if kind == 'infra':
        raise TypeError(
            f"'{def_name}' is an internal engine SynthDef and cannot be "
            f"used as an instrument."
        )


# Lazy singletons for per-call imports in the setter hot paths (the
# imports themselves are cheap dict hits, but 4 of them per coerced value
# added up to 71us per 4-tuple in the audit profile).
_ss_synth_kind = None
_PITCH_TYPES = None


def _pitch_types():
    global _PITCH_TYPES
    if _PITCH_TYPES is None:
        from klotho.tonos import Pitch
        from klotho.tonos.chords.chord import Chord, Voicing
        from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
        _PITCH_TYPES = (Pitch, Chord, Voicing, PitchCollectionBase)
    return _PITCH_TYPES


def _is_pitch_collection_value(value):
    """Pitch collections define ``__call__`` (index delegation), so they must
    be excluded from the callable/distributable classification in setters and
    treated as static values instead."""
    return isinstance(value, _pitch_types()[3])


def _coerce_set_pfield_value(key, value):
    """Set-time normalization of a pfield value.

    - NumPy scalars become Python scalars; NumPy arrays are rejected
      (ambiguous: a tuple means a chord/poly value, a Pattern cycles).
    - For the ``freq`` key: a pitch-name string becomes a :class:`Pitch`
      (parsed eagerly so typos fail at set time); a ``Chord``/``Voicing``
      becomes a tuple of its member Pitches (a chord); any other pitch
      collection is rejected as ambiguous (sequence vs simultaneity).
    - Tuples are normalized element-wise.

    Rich values (``Pitch``, ``Fraction``) are stored as-is in the tree and
    lowered to floats at playback assembly.
    """
    Pitch, Chord, Voicing, PitchCollectionBase = _pitch_types()

    if isinstance(value, Bind):
        return value
    if isinstance(value, _np.generic):
        return value.item()
    if isinstance(value, _np.ndarray):
        raise TypeError(
            f"set_pfields got a numpy array for '{key}'; use a tuple for a "
            f"chord/poly value, or Pattern([...]) to cycle values across nodes"
        )
    if key == 'freq':
        if isinstance(value, str) and value:
            return Pitch(value)
        if isinstance(value, (Chord, Voicing)):
            return tuple(value.pitches)
        if isinstance(value, PitchCollectionBase):
            raise TypeError(
                f"A {type(value).__name__} is ambiguous for 'freq' (it can "
                f"model a sequence or a simultaneity). Use freq=coll.freqs "
                f"for a chord, Pattern(coll.freqs) to cycle across nodes, "
                f"or coll.as_voicing() for an explicit simultaneity."
            )
    if isinstance(value, tuple):
        return tuple(_coerce_set_pfield_value(key, v) for v in value)
    return value


class Parametron(Chronon):
    """
    An enhanced Chronon that includes parameter field access.
    
    Extends the basic temporal event data (start, duration, etc.) with 
    access to musical parameters stored in a synchronized ParameterTree.
    """
    
    __slots__ = ('_pt',)

    def __init__(self, node_id: int, ut, pt: ParameterTree, group=None):
        """
        Initialize a Parametron.

        Parameters
        ----------
        node_id : int
            The node ID in the rhythm tree.
        ut : TemporalUnit or CompositionalUnit
            The temporal unit providing temporal data.
        pt : ParameterTree
            The parameter tree providing field values (including instrument via
            ``pt.get(node_id, 'instrument')``).
        group : tuple of int or None, optional
            The tie-group members when this event is a tied group (head
            first); parameter reads stay head-anchored (charter sect4).
        """
        super().__init__(node_id, ut, group=group)
        self._pt = pt

    def _resolve_bind(self, key, value):
        resolver = getattr(self._ut, '_resolve_bound_value', None)
        if resolver is not None:
            return resolver(self._node_id, key, value)
        return value

    def _bind_key_set(self):
        """Field keys that may hold a Bind, or ``None`` when unknowable.

        ``None`` means "resolve every key" (no bind index available, or the
        index cache is suspended inside a write batch — recomputing the
        all-nodes scan per event would cost more than the skipped calls).
        """
        ut = self._ut
        getter = getattr(ut, '_bind_field_keys', None)
        if getter is None:
            return None
        rt = getattr(ut, '_rt', None)
        if rt is not None and getattr(rt, '_write_batch_depth', 0):
            return None
        return getter()

    @property
    def pfields(self):
        """
        Get parameter field values for this event (for playback, etc.).
        
        Returns pfield values with instrument fallback.  When the governing
        instrument is a Kit, defaults come from the resolved member (based
        on the selector pfield at this node), not the Kit shell.
        
        Returns
        -------
        dict
            Dictionary of parameter field names and values
        """
        result = {}
        inst = self._resolve_instrument()
        effective = _resolve_kit_member(inst, self._pt, self._node_id) if inst is not None else inst
        eff_pfields = None
        if effective is not None and hasattr(effective, 'pfields'):
            eff_pfields = effective.pfields
            result.update(eff_pfields)
        bind_keys = self._bind_key_set()
        pt = self._pt
        nid = self._node_id
        for k in pt.pfield_names:
            v = pt.get_pfield(nid, k)
            if bind_keys is None or k in bind_keys:
                v = self._resolve_bind(k, v)
            if v is not None:
                result[k] = v
            elif eff_pfields is not None and k in eff_pfields:
                result[k] = eff_pfields[k]
        # A family-name selector rotates to a concrete member per leaf;
        # surface the member key (matching the defaults merged above) so
        # the lowered voice events resolve the same member downstream.
        if isinstance(inst, Kit):
            sel = result.get(inst.selector)
            concrete = _concretize_family_selector(inst, sel, self._pt, self._node_id)
            if concrete is not sel:
                result[inst.selector] = concrete
        return result

    @property
    def mfields(self):
        """
        Get meta field values for this event.
        
        Returns
        -------
        dict
            Dictionary of meta field names and values
        """
        bind_keys = self._bind_key_set()
        pt = self._pt
        nid = self._node_id
        return {k: self._resolve_bind(k, pt.get_mfield(nid, k))
                if (bind_keys is None or k in bind_keys)
                else pt.get_mfield(nid, k)
                for k in pt.mfield_names}

    def _resolve_instrument(self):
        return self._pt.get_instrument(self._node_id)

    def get_pfield(self, key: str, default=None):
        """Resolved parameter-field value for this event (``default`` when unset)."""
        value = self._resolve_bind(key, self._pt.get_pfield(self._node_id, key))
        return default if value is None else value

    def get_mfield(self, key: str, default=None):
        """Resolved meta-field value for this event (``default`` when unset)."""
        value = self._resolve_bind(key, self._pt.get_mfield(self._node_id, key))
        return default if value is None else value

    def __getitem__(self, key: str):
        if key in _PARAMETRON_TEMPORAL_ATTRS:
            return getattr(self, key)
        v = self.get_pfield(key)
        if v is not None:
            return v
        return self.get_mfield(key)


class UCNodeSelector(UTNodeSelector):
    """Selector for :class:`CompositionalUnit` owners.

    Extends :class:`UTNodeSelector` with UC-specific verbs that delegate to
    the owning UC's parameter / envelope / slur / instrument mutators. Existing
    UC setter semantics
    (callable-per-node, Pattern-cycling, static tuple-as-poly-event,
    ``include_rests`` filtering, ensemble-family side effects, slur/envelope
    healing) are preserved verbatim.
    """

    # --- Parameter verbs ---
    def set_pfields(self, include_rests: bool = False, **kwargs) -> None:
        """Set parameter field values on every selected node."""
        return self._owner.set_pfields(
            self, include_rests=include_rests, **kwargs
        )

    def set_mfields(self, include_rests: bool = False, **kwargs) -> None:
        """Set meta field values on every selected node."""
        return self._owner.set_mfields(
            self, include_rests=include_rests, **kwargs
        )

    def set_instrument(self, instrument, include_rests: bool = False):
        """Assign an instrument (or Pattern/callable thereof) to the selection."""
        return self._owner.set_instrument(self, instrument, include_rests=include_rests)

    def apply_envelope(self, envelope, pfields, *, offset=0, take=None,
                       scope: str = 'span', control: bool = False,
                       endpoint: bool = True):
        """Apply an envelope to the selection. See :meth:`CompositionalUnit.apply_envelope`."""
        return self._owner.apply_envelope(
            envelope, pfields, node=self,
            offset=offset, take=take, scope=scope,
            control=control, endpoint=endpoint,
        )

    def apply_slur(self, *, offset=0, take=None, mode: str = 'span'):
        """Apply a slur over the selection. See :meth:`CompositionalUnit.apply_slur`."""
        return self._owner.apply_slur(
            node=self, offset=offset, take=take, mode=mode,
        )

    def clear_parameters(self) -> None:
        """Clear parameter values on every selected node (and its subtree)."""
        for n in self._ids:
            self._owner.clear_parameters(n)

    def set(self, *, inst=None, include_rests: bool = False,
            pfields=None, mfields=None, **fields):
        """Set instrument and auto-routed fields in one call across the
        selection. See :meth:`CompositionalUnit.set`."""
        return self._owner.set(
            self, inst=inst, include_rests=include_rests,
            pfields=pfields, mfields=mfields, **fields,
        )

    # --- Per-node getters (return list aligned with self._ids) ---
    def get_pfield(self, key: str, default=None) -> list:
        """Per-node pfield values, one per selected node."""
        return [self._owner.get_pfield(n, key, default) for n in self._ids]

    def get_mfield(self, key: str, default=None) -> list:
        """Per-node mfield values, one per selected node."""
        return [self._owner.get_mfield(n, key, default) for n in self._ids]

    def get_instrument(self) -> list:
        """Per-node resolved instruments, one per selected node."""
        return [self._owner.get_instrument(n) for n in self._ids]


class UCNodeHandle(UTNodeHandle):
    """Node handle for :class:`CompositionalUnit` owners.

    Extends :class:`UTNodeHandle` with the parameter surface — set/get
    pfields, mfields, and instruments, apply envelopes and slurs — all
    delegating to the owning UC with this node as the target.
    """

    def set_pfields(self, include_rests: bool = False, **kwargs):
        """Set parameter fields at this node; see :meth:`CompositionalUnit.set_pfields`."""
        return self._owner.set_pfields(self.id, include_rests=include_rests, **kwargs)

    def set_mfields(self, include_rests: bool = False, **kwargs):
        """Set meta fields at this node; see :meth:`CompositionalUnit.set_mfields`."""
        return self._owner.set_mfields(self.id, include_rests=include_rests, **kwargs)

    def set_instrument(self, instrument, include_rests: bool = False):
        """Assign an instrument at this node; see :meth:`CompositionalUnit.set_instrument`."""
        return self._owner.set_instrument(self.id, instrument, include_rests=include_rests)

    def apply_envelope(self, envelope, pfields, *, offset=0, take=None,
                       scope: str = 'span', control: bool = False,
                       endpoint: bool = True):
        """Apply an envelope over this node's subtree; see :meth:`CompositionalUnit.apply_envelope`."""
        return self._owner.apply_envelope(
            envelope, pfields, node=self.id,
            offset=offset, take=take, scope=scope,
            control=control, endpoint=endpoint,
        )

    def apply_slur(self, *, offset=0, take=None, mode: str = 'span'):
        """Slur this node's subtree; see :meth:`CompositionalUnit.apply_slur`."""
        return self._owner.apply_slur(
            node=self.id, offset=offset, take=take, mode=mode
        )

    def clear_parameters(self):
        """Clear parameters on this node and its subtree; see :meth:`CompositionalUnit.clear_parameters`."""
        return self._owner.clear_parameters(self.id)

    def set(self, *, inst=None, include_rests: bool = False,
            pfields=None, mfields=None, **fields):
        """Set instrument and auto-routed fields in one call; see :meth:`CompositionalUnit.set`."""
        return self._owner.set(
            self.id, inst=inst, include_rests=include_rests,
            pfields=pfields, mfields=mfields, **fields,
        )

    @property
    def pfields(self):
        """dict : Effective pfield values at this node (inherited + overrides)."""
        return {
            key: self._owner.get_pfield(self.id, key)
            for key in self._owner._rt.pfield_names
        }

    @property
    def mfields(self):
        """dict : Effective mfield values at this node (inherited + overrides)."""
        return {
            key: self._owner.get_mfield(self.id, key)
            for key in self._owner._rt.mfield_names
        }

    @property
    def instrument(self):
        """Instrument or None : The instrument governing this node (ancestor walk)."""
        return self._owner.get_instrument(self.id)

    def get_pfield(self, key: str, default=None):
        """Effective pfield value at this node (``default`` when unset)."""
        return self._owner.get_pfield(self.id, key, default)

    def get_mfield(self, key: str, default=None):
        """Effective mfield value at this node (``default`` when unset)."""
        return self._owner.get_mfield(self.id, key, default)

    def get_instrument(self):
        """Instrument or None : The instrument governing this node (ancestor walk)."""
        return self._owner.get_instrument(self.id)


class CompositionalUnit(TemporalUnit):
    """
    A TemporalUnit enhanced with hierarchical parameter management.

    Extends TemporalUnit by using a single fused :class:`CompositionalTree`
    as its internal tree, carrying both rhythmic data (via a rhythm layer)
    and parameter data (via a parameter layer) on one topology. Parameter
    values can be set at any node and automatically propagate to descendant
    events through hierarchical inheritance.

    Attribution -- two separate claims (docket DOC-5, ruling R10)
    -------------------------------------------------------------
    **1. Envelope application follows Haddad.** :meth:`apply_envelope`
    realises what thesis sect8.2.2 calls the Temporal Unit as a
    « reservoir de donnees quelconques » -- "a reservoir of arbitrary
    data": the unit is a carrier for material that is not itself rhythmic.
    That reading is his.

    **2. The fused hierarchical parameter tree is Klotho's OWN.** This is
    verified as an *absence*, not merely unfound: *heritage / herite /
    heriter* ("inheritance / inherits / to inherit") occur **zero times**
    in the thesis, and no occurrence of *parametre* ("parameter") binds a
    parameter to a tree node. Haddad has no notion of a parameter
    inherited down a rhythm tree. Claim it as Klotho's; do not read the
    shared vocabulary as inherited design.

    On the NAME (kept per ruling R10, a rename to ``ParametricUnit`` was
    considered and declined). Haddad's own *unite compositionnelle*
    ("compositional unit") names « l'ensemble des divisions temporelles »
    -- "the set of temporal divisions" -- so on *his* usage Klotho's
    analogue of the term would be :class:`~klotho.thetos.composition.score.Score`,
    not this class. But the term is **Emmanuel Nunes's**, and in Nunes's
    sense -- « restreinte, discrete, composee... d'une gestualite locale et
    localement accomplie », "restricted, discrete, composed... of a local
    gesturality locally accomplished" -- it is a bounded local gesture,
    which is exactly what a ``CompositionalUnit`` is. The tension lives
    inside Haddad, who borrows a local term for an aggregate; Klotho
    matches Nunes.

    Parameters
    ----------
    span : Union[int, float, Fraction], default=1
        Number of measures the unit spans
    tempus : Union[Meas, Fraction, int, float, str], default='4/4'
        Time signature (e.g., '4/4', Meas(4,4))
    prolatio : Union[tuple, str], default='d'
        Subdivision pattern (tuple) or type ('d', 'r', 'p', 's')
    beat : Union[None, Fraction, int, float, str], optional
        Beat unit for tempo (e.g., Fraction(1,4) for quarter note)
    bpm : Union[None, int, float], optional
        Beats per minute
    inst : Instrument or None, optional
        Instrument to assign to the root node.
    mfields : Union[dict, list, None], optional
        Meta fields to initialize (a ``'group'`` field is always present).
    pfields : Union[dict, list, None], optional
        Parameter fields to initialize. Can be:
        - dict: {field_name: default_value, ...}
        - list: [field_name1, field_name2, ...] (defaults to 0.0)
        - None: No parameter fields initially

    Notes
    -----
    Outside a :class:`~klotho.thetos.composition.score.Score`, a
    ``CompositionalUnit`` always starts at time 0 and its duration is
    fixed after construction.  Placement and duration editing are handled
    by :class:`~klotho.thetos.composition.score.ScoreItem` once the UC
    has been added to a Score.

    There is no shadow ParameterTree: rhythm and parameters live on the
    same fused tree. The :attr:`pt` property builds an effective
    ParameterTree snapshot (node ids preserved) on demand.

    Attributes
    ----------
    pt : ParameterTree
        Effective parameter tree snapshot derived from the fused tree
        (a new object on each access; mutating it does not affect the unit)
    pfields : list
        List of all available parameter field names
    """

    _node_selector_class = UCNodeSelector
    _node_handle_class = UCNodeHandle
    _tree_class = CompositionalTree

    def __init__(self,
                 span     : Union[int, float, Fraction]            = 1,
                 tempus   : Union[Meas, Fraction, int, float, str] = _UT_UNSET,
                 prolatio : Union[tuple, str]                      = 'd',
                 beat     : Union[None, Fraction, int, float, str] = None,
                 bpm      : Union[None, int, float]                = None,
                 inst     : Union[Instrument, None]                = None,
                 mfields  : Union[dict, list, None]                = None,
                 pfields  : Union[dict, list, None]                = None):
        
        self._bind_memo = {}
        self._bind_active = set()

        super().__init__(span, tempus, prolatio, beat, bpm)
        
        if mfields is None:
            mfields = {}
        if 'group' not in mfields:
            mfields['group'] = 'default'
        
        self._init_parameter_fields(pfields, mfields)
        
        if inst is not None:
            self.set_instrument(self._rt.root, inst)
        
        self._slur_specs = {}
        self._next_slur_id = 0
        self._control_envelopes: dict[int, dict] = {}
        self._next_envelope_id = 0
        self._mirror_id_map = None
        self._rt.set_id_state_observer(self._relocate_id_keyed_state)

    @classmethod
    def from_rt(cls, rt: RhythmTree, beat: Union[None, Fraction, int, float, str] = None, bpm: Union[None, int, float] = None, pfields: Union[dict, list, None] = None, mfields: Union[dict, list, None] = None, inst: Union[Instrument, None] = None):
        """
        Create a CompositionalUnit from an existing RhythmTree.
        
        Parameters
        ----------
        rt : RhythmTree
            Source rhythm tree whose structure is adopted.
        beat : Fraction, int, float, str, or None, optional
            Beat unit for tempo calculation.
        bpm : int, float, or None, optional
            Beats per minute.
        pfields : dict, list, or None, optional
            Parameter fields to initialize.
        mfields : dict, list, or None, optional
            Meta fields to initialize.
        inst : Instrument or None, optional
            Instrument to assign to the root node.
            
        Returns
        -------
        CompositionalUnit
            A new CompositionalUnit with the rhythm tree's structure.
        """
        return cls(span     = rt.span,
                   tempus   = rt.meas,
                   prolatio = rt.subdivisions,
                   beat     = beat,
                   bpm      = bpm,
                   pfields  = pfields,
                   mfields  = mfields,
                   inst     = inst)
        
    @classmethod
    def from_tree(cls, tree, denom: int = 8,
                  beat: Union[None, Fraction, int, float, str] = None,
                  bpm: Union[None, int, float] = None,
                  inst: Union[Instrument, None] = None,
                  tempus: Union[Meas, Fraction, int, float, str, None] = None,
                  span: Union[int, float, Fraction] = 1,
                  head_weight: int = 1,
                  pfields: Union[dict, list, None] = None,
                  mfields: Union[dict, list, None] = None):
        """
        Create a CompositionalUnit whose rhythm is an arbitrary tree.

        Accepts a plain :class:`~klotho.topos.graphs.trees.Tree` or a
        :class:`~klotho.topos.formal_grammars.derivation.DerivationTree`
        (converted via ``to_tree()``, copying every ``data`` payload).

        Rhythm comes from each node's ``proportion`` attribute (default 1
        when absent); the nested prolatio is rebuilt from the topology.
        Negative proportions (rests) pass through unchanged.

        The meter is resolved in precedence order:

        1. an explicit ``tempus`` argument wins;
        2. else, if the root node has a ``proportion`` attribute,
           ``tempus = Meas(root_proportion, denom)``;
        3. else — the normal case for derivation trees, whose conversion
           writes no root proportion — ``tempus`` is the sum of the root's
           child proportions over ``denom``.

        ``span`` defaults to 1 measure of the resolved tempus.

        Every other node attribute that is not rhythm-owned
        (``proportion``, ``tied``, ``metric_duration``, ``metric_onset``)
        or tree bookkeeping (``label``, ``meta``) is copied into the
        corresponding node's **mfields**, so a derivation tree with
        ``chord`` payloads yields a UC where ``leaf.mfields['chord']`` is
        the chord.

        Parameters
        ----------
        tree : Tree or DerivationTree
            The source tree.
        denom : int, optional
            Meter denominator for the derived tempus. Default is 8.
        beat, bpm : optional
            Tempo, as in the constructor.
        inst : Instrument or None, optional
            Instrument for the root node.
        tempus : optional
            Explicit time signature (overrides derivation from the tree).
        span : int, float, or Fraction, optional
            Number of measures the unit spans, as in the constructor.
            Default is 1.
        head_weight : int, optional
            Only used for DerivationTree input: the rightmost child of
            every expansion gets this proportion (all others get 1),
            exactly as in :meth:`DerivationTree.prolatio`. Default is 1.
        pfields, mfields : dict, list, or None, optional
            Fields to initialize, as in the constructor.

        Returns
        -------
        CompositionalUnit
        """
        from klotho.topos.formal_grammars.derivation import DerivationTree

        if isinstance(tree, DerivationTree):
            data_keys = sorted({k for node in tree.walk() for k in node.data})
            derivation = tree
            tree = derivation.to_tree(**{k: k for k in data_keys})
            if head_weight != 1 and derivation.children:
                stack = [(derivation, tree.root)]
                while stack:
                    dnode, tnode = stack.pop()
                    children = list(tree.successors(tnode))
                    for i, (dchild, tchild) in enumerate(zip(dnode.children, children)):
                        weight = head_weight if i == len(dnode.children) - 1 else 1
                        tree.set_node_data(tchild, proportion=weight)
                        stack.append((dchild, tchild))

        def proportion_of(node):
            return tree[node].get('proportion', 1)

        def build_s(node):
            parts = []
            for child in tree.successors(node):
                if tree.successors(child):
                    parts.append((proportion_of(child), build_s(child)))
                else:
                    parts.append(proportion_of(child))
            return tuple(parts)

        subdivisions = build_s(tree.root) or (1,)

        if tempus is None:
            root_proportion = tree[tree.root].get('proportion')
            if root_proportion is not None:
                tempus = Meas(int(abs(root_proportion)), denom)
            else:
                child_sum = sum(abs(proportion_of(c)) for c in tree.successors(tree.root))
                tempus = Meas(int(child_sum) if child_sum else 1, denom)

        new_uc = cls(span=span, tempus=tempus, prolatio=subdivisions,
                     beat=beat, bpm=bpm, inst=inst,
                     pfields=pfields, mfields=mfields)

        rhythm_keys = {'proportion', 'tied', 'metric_duration', 'metric_onset'}
        bookkeeping = {'label', 'meta'}
        skip = rhythm_keys | bookkeeping

        if list(tree.successors(tree.root)):
            mapping = tree.map_parallel_nodes(new_uc._rt)
        else:
            mapping = {tree.root: new_uc._rt.root}

        for old_node, new_node in mapping.items():
            fields = {k: v for k, v in dict(tree[old_node]).items()
                      if k not in skip and v is not None}
            if fields:
                new_uc._rt.set_mfields(new_node, **fields)

        return new_uc

    @classmethod
    def from_ut(cls, ut: TemporalUnit, pfields: Union[dict, list, None] = None, mfields: Union[dict, list, None] = None, inst: Union[Instrument, None] = None):
        """
        Create a CompositionalUnit from an existing TemporalUnit.
        
        Parameters
        ----------
        ut : TemporalUnit
            Source temporal unit whose timing and structure are adopted.
        pfields : dict, list, or None, optional
            Parameter fields to initialize.
        mfields : dict, list, or None, optional
            Meta fields to initialize.
        inst : Instrument or None, optional
            Instrument to assign to the root node.
            
        Returns
        -------
        CompositionalUnit
            A new CompositionalUnit with the temporal unit's structure.
        """
        new_uc = cls(
            span     = ut.span,
            tempus   = ut.tempus,
            prolatio = ut.prolationis,
            beat     = ut.beat,
            bpm      = ut.bpm,
            pfields  = pfields,
            mfields  = mfields,
            inst     = inst,
        )
        new_uc._offset = ut._offset
        new_uc._invalidate_timing_cache()
        return new_uc
    
    def _init_parameter_fields(self, pfields: Union[dict, list, None], mfields: Union[dict, list, None]) -> None:
        """Initialize root-level parameter and meta fields on the fused tree."""
        if pfields is not None:
            if isinstance(pfields, dict):
                self._rt.set_pfields(self._rt.root, **pfields)
            elif isinstance(pfields, list):
                self._rt.set_pfields(self._rt.root, **{field: 0.0 for field in pfields})
        if mfields is not None:
            if isinstance(mfields, dict):
                self._rt.set_mfields(self._rt.root, **mfields)
            elif isinstance(mfields, list):
                self._rt.set_mfields(self._rt.root, **{field: '' for field in mfields})

    def _extract_parameter_tree(self) -> ParameterTree:
        """Extract a standalone ParameterTree snapshot from the fused tree.

        Node ids are preserved so the snapshot lines up with ``self._rt``. Raw
        per-node overrides (not flattened effective values) are copied, along
        with the pfield/mfield registries and instrument bindings.
        """
        src = self._rt
        pt = ParameterTree.from_tree_structure(src)
        pt.register_pfields(src.pfield_names)
        pt.register_mfields(src.mfield_names)
        keys = src.pfield_names | src.mfield_names
        for node in src.nodes:
            raw = src._rx[node]
            if isinstance(raw, dict):
                own = {k: v for k, v in raw.items() if k in keys}
                if own:
                    pt._rx[node].update(own)
        for node, inst in src.node_instruments.items():
            pt.set_instrument(node, inst)
        pt._param_layer._effective_cache = None
        return pt

    def _copy_pt_node_data(self, target_cu: 'CompositionalUnit', mapping: dict[int, int]) -> None:
        src = self._rt
        dst = target_cu._rt
        dst.register_pfields(src.pfield_names)
        dst.register_mfields(src.mfield_names)
        for old_node, new_node in mapping.items():
            eff = src.items(old_node)
            pf = {k: v for k, v in eff.items() if k in src.pfield_names}
            mf = {k: v for k, v in eff.items() if k in src.mfield_names}
            if pf:
                dst.set_pfields(new_node, **pf)
            if mf:
                dst.set_mfields(new_node, **mf)

    def _copy_pt_instruments(self, target_cu: 'CompositionalUnit', mapping: dict[int, int]) -> None:
        for old_node, inst in self._rt.node_instruments.items():
            new_node = mapping.get(old_node)
            if new_node is not None:
                target_cu._rt.set_instrument(new_node, inst)

    def _mirror_param_state(self, source_uc: 'CompositionalUnit') -> None:
        """Copy raw parameter-layer state from a same-SHAPE source UC.

        Preserves per-node override placement (inheritance structure), the
        pfield/mfield registries, and instrument bindings.

        Node ids are NOT assumed to match. This is called by the three
        rebuild-from-prolatio recipes (``_scaled``'s CompositionalUnit arm,
        ``modulate_tempo``, ``modulate_tempus``), and a source that has been
        mutated since construction no longer numbers depth-first -- a
        ``subdivide``d 4/4 carries leaves (5, 6, 2, 3, 4) while its rebuild
        numbers them (2, 3, 4, 5, 6). Copying by raw id therefore ROTATED the
        music, and after a ``remove_subtree`` it dropped a value and let the
        pfield default resurface as real music. The two trees share their
        shape (same prolationis), so the correspondence is positional:
        :meth:`~klotho.topos.graphs.trees.Tree.map_parallel_nodes` walks both
        in lockstep and raises on a shape mismatch rather than guessing.

        The one shape the rebuild does NOT mirror is a source stripped to
        its bare root (``prune``/``remove_subtree`` can do that; docket
        RT-26): ``prolationis`` reports ``(1,)`` there, and rebuilding from
        ``(1,)`` gives root + one child -- 2 nodes against the source's 1.
        That divergence is exact and known, so it is mapped, not fatal:
        root to root, as ``from_tree``/``from_subtree`` already map the
        degenerate shape, with the root's raw overrides reaching the
        rebuilt leaf by inheritance.

        The same recipe then copies the slur specs and envelope anchors, which
        are keyed by node id too -- so the correspondence is published on the
        source for :meth:`_copy_slur_specs` and
        :meth:`_copy_control_envelopes` to follow.
        """
        src = source_uc._rt
        dst = self._rt
        if list(src.successors(src.root)):
            mapping = src.map_parallel_nodes(dst)
        else:
            mapping = {src.root: dst.root}
        dst.register_pfields(src.pfield_names)
        dst.register_mfields(src.mfield_names)
        keys = src.pfield_names | src.mfield_names
        for src_node, dst_node in mapping.items():
            raw = src._rx[src_node]
            if isinstance(raw, dict):
                own = {k: v for k, v in raw.items() if k in keys}
                if own:
                    dst._rx[dst_node].update(own)
        for src_node, inst in src.node_instruments.items():
            dst_node = mapping.get(src_node)
            if dst_node is not None:
                dst.set_instrument(dst_node, inst)
        dst._param_layer._effective_cache = None
        source_uc._mirror_id_map = mapping

    def _resolve_governing_instrument_node(self, node: int):
        return self._rt._resolve_governing_instrument_node(node)

    # ------------------------------------------------------------------
    # Late-bound (Bind) value resolution
    # ------------------------------------------------------------------
    def _bind_origin(self, node: int, key: str) -> int:
        """Nearest ancestor-or-self holding a raw Bind override for *key*."""
        for ancestor in reversed(self._rt.branch(node)):
            raw = self._rt._rx[ancestor]
            if isinstance(raw, dict) and isinstance(raw.get(key), Bind):
                return ancestor
        return node

    def _resolve_bound_value(self, node: int, key: str, value):
        """Resolve *value* if it is a :class:`Bind`; pass anything else through.

        The Bind's callable is evaluated for the reading node with a
        ``DistributionContext`` whose index/total reflect the node's
        position among the leaf descendants of the origin node (the nearest
        ancestor-or-self holding the raw Bind override). Results are
        memoized per ``(node, key)`` so stochastic functions are stable
        across repeated reads and structural edits.
        """
        if not isinstance(value, Bind):
            return value
        memo_key = (node, key)
        # A selection-reading Bind is a pure function of structure, so
        # memoizing it across a structural edit is what makes a pan spread go
        # incoherent: old nodes keep values computed against the old total
        # while new ones use the new one. Stochastic Binds still memoize --
        # that is the point of the memo.
        selection_bound = getattr(value, 'reads_selection', False)
        if not selection_bound and memo_key in self._bind_memo:
            return self._bind_memo[memo_key]
        if memo_key in self._bind_active:
            raise ValueError(
                f"Bind cycle detected: field '{key}' at node {node} is being "
                f"evaluated while already under evaluation"
            )
        origin = self._bind_origin(node, key)
        leaves = self._rt.subtree_leaves(origin)
        try:
            index = leaves.index(node)
        except ValueError:
            index = 0
        total = len(leaves)
        if selection_bound and total < 2 and len(self._rt.leaf_nodes) > 1:
            raise ValueError(
                f"Bind.index for field {key!r} is stored on node {origin}, whose "
                f"read set is that single node -- so every node reading it would "
                f"get index 0 of 1 and the value would be constant. The read set "
                f"is the leaf descendants of the node holding the Bind, so store "
                f"it on the common ancestor of the nodes you want to spread "
                f"across (uc.root.set_pfields({key}=...)) rather than on the "
                f"leaves themselves."
            )
        self._bind_active.add(memo_key)
        try:
            ctx = self._build_node_context(node, index, total)
            arity = _callable_arity(value.fn)
            result = value.fn(ctx) if arity >= 1 else value.fn()
        finally:
            self._bind_active.discard(memo_key)
        if isinstance(result, Bind):
            raise ValueError(
                f"Bind cycle detected: field '{key}' at node {node} resolved "
                f"to another Bind (self-referential pfield read?)"
            )
        if key in self._rt.pfield_names:
            result = _coerce_set_pfield_value(key, result)
        if not selection_bound:
            self._bind_memo[memo_key] = result
        return result

    def _invalidate_bind_memo(self, nodes=None, keys=None):
        """Drop memoized Bind evaluations for the given nodes/keys.

        ``None`` for either argument means "all". Called when a field is
        re-assigned or removed at a node (invalidating its subtree) and
        when nodes are destroyed.
        """
        if not self._bind_memo:
            return
        if nodes is None and keys is None:
            self._bind_memo.clear()
            return
        node_set = set(nodes) if nodes is not None else None
        key_set = set(keys) if keys is not None else None
        for memo_key in list(self._bind_memo):
            n, k = memo_key
            if ((node_set is None or n in node_set)
                    and (key_set is None or k in key_set)):
                del self._bind_memo[memo_key]

    def _invalidate_bind_memo_subtree(self, targets, keys):
        if not self._bind_memo:
            return
        affected = set()
        for n in targets:
            if n in self._rt:
                affected.add(n)
                affected.update(self._rt.descendants(n))
            else:
                affected.add(n)
        self._invalidate_bind_memo(affected, keys)

    def _resolve_distribution_fields(self, node_id: int):
        inst = self._rt.get_instrument(node_id)
        effective = _resolve_kit_member(inst, self._rt, node_id) if inst is not None else inst
        inst_pfields = effective.pfields if (effective is not None and hasattr(effective, "pfields")) else {}
        pfields = {}
        for key in self._rt.pfield_names:
            value = self._rt.get_pfield(node_id, key)
            if value is None and key in inst_pfields:
                value = inst_pfields[key]
            if isinstance(value, Bind) and (node_id, key) not in self._bind_active:
                value = self._resolve_bound_value(node_id, key, value)
            pfields[key] = value
        mfields = {}
        for key in self._rt.mfield_names:
            value = self._rt.get_mfield(node_id, key)
            if isinstance(value, Bind) and (node_id, key) not in self._bind_active:
                value = self._resolve_bound_value(node_id, key, value)
            mfields[key] = value
        is_rest = self._rt[node_id].get("proportion", 1) < 0
        return is_rest, pfields, mfields, inst

    def _build_parent_distribution_view(self, node_id: int) -> Optional[ParentDistributionView]:
        parent_id = self._rt.parent(node_id)
        if parent_id is None:
            return None
        is_rest, pfields, mfields, instrument = self._resolve_distribution_fields(parent_id)
        return ParentDistributionView(
            ref=self._build_node_handle(parent_id),
            is_rest=is_rest,
            pfields=pfields,
            mfields=mfields,
            instrument=instrument,
            _owner=self,
        )

    def _build_node_context(self, node_id: int, index: int, total: int) -> DistributionContext:
        base = super()._build_node_context(node_id, index, total)
        is_rest, pfields, mfields, instrument = self._resolve_distribution_fields(node_id)
        return DistributionContext(
            ref=base.ref,
            index=index,
            total=total,
            is_rest=is_rest,
            pfields=pfields,
            mfields=mfields,
            instrument=instrument,
            _owner=self,
        )

    def _normalize_node_input(self, node):
        if node is None:
            raise ValueError("node selection is required")
        try:
            return self._coerce_node_targets(node)
        except TypeError as exc:
            raise ValueError("node must be int, selector, or iterable thereof") from exc

    def _resolve_leaf_selection(self, node):
        source_nodes = self._normalize_node_input(node)
        leaf_order = list(self._rt.leaf_nodes)
        leaf_index = {leaf: i for i, leaf in enumerate(leaf_order)}
        leaf_set = set(leaf_order)
        selected = set()
        for selected_node in source_nodes:
            if selected_node not in self._rt.nodes:
                raise ValueError(f"Node {selected_node} not found in tree")
            if selected_node in leaf_set:
                selected.add(selected_node)
            else:
                selected.update(self._rt.subtree_leaves(selected_node))
        if not selected:
            raise ValueError("Selection resolves to no leaf nodes")
        ordered = [leaf for leaf in leaf_order if leaf in selected]
        indices = [leaf_index[leaf] for leaf in ordered]
        if indices != list(range(indices[0], indices[-1] + 1)):
            raise ValueError("Selection must be contiguous in left-to-right tree order")
        return ordered

    def _resolve_per_node_leaf_groups(self, node):
        source_nodes = self._normalize_node_input(node)
        leaf_set = set(self._rt.leaf_nodes)
        groups = []
        for selected_node in source_nodes:
            if selected_node not in self._rt.nodes:
                raise ValueError(f"Node {selected_node} not found in tree")
            if selected_node in leaf_set:
                groups.append((selected_node,))
            else:
                groups.append(tuple(self._rt.subtree_leaves(selected_node)))
        return groups

    def _apply_offset_take(self, leaves, offset=0, take=None):
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if offset > len(leaves):
            raise ValueError("offset exceeds selection bounds")
        if take is None:
            result = leaves[offset:]
        else:
            if take <= 0:
                raise ValueError("take must be > 0")
            end = offset + take
            if end > len(leaves):
                raise ValueError("offset/take exceeds UC boundaries")
            result = leaves[offset:end]
        if not result:
            raise ValueError("Resolved span is empty")
        return tuple(result)

    def _ranges_overlap(self, left, right):
        return not (left[1] < right[0] or right[1] < left[0])

    def _selection_index_range(self, leaves):
        leaf_order = list(self._rt.leaf_nodes)
        leaf_index = {leaf: i for i, leaf in enumerate(leaf_order)}
        idx = [leaf_index[leaf] for leaf in leaves]
        return min(idx), max(idx)

    def _bind_field_keys(self):
        """Field keys that carry a Bind override anywhere in the tree.

        Memoized on the tree's structure version (Bind writes go through
        set_pfields/set_mfields, which bump it) — the all-nodes-x-keys
        scan used to run once per effective-tree build.
        """
        version = self._rt._structure_version
        cached = self.__dict__.get('_bind_keys_cache')
        if cached is not None and cached[0] == version:
            return cached[1]
        keys = self._rt.pfield_names | self._rt.mfield_names
        found = set()
        rx = self._rt._rx
        for node in self._rt.nodes:
            raw = rx[node]
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if k in keys and isinstance(v, Bind):
                        found.add(k)
        if not self._rt._write_batch_depth:
            self.__dict__['_bind_keys_cache'] = (version, found)
        return found

    def _materialize_bound_values(self, pt_snapshot):
        """Replace Bind values in a PT snapshot with per-node resolved values.

        Converters/engines must never see a Bind, so snapshots carry only
        concrete values.
        """
        bind_keys = self._bind_field_keys()
        if not bind_keys:
            return
        pfield_keys = bind_keys & self._rt.pfield_names
        mfield_keys = bind_keys & self._rt.mfield_names
        for node in self._rt.nodes:
            for key in pfield_keys:
                value = self._rt.get_pfield(node, key)
                if isinstance(value, Bind):
                    resolved = self._resolve_bound_value(node, key, value)
                    pt_snapshot.set_pfields(node, **{key: resolved})
            for key in mfield_keys:
                value = self._rt.get_mfield(node, key)
                if isinstance(value, Bind):
                    resolved = self._resolve_bound_value(node, key, value)
                    pt_snapshot.set_mfields(node, **{key: resolved})

    def _build_effective_parameter_tree(self, _fresh=False):
        """Effective PT snapshot (binds materialized, slur markers set).

        Internal callers share a snapshot memoized on (structure version,
        slur state, instrument version) — event iteration used to clone
        the whole tree per event context. ``_fresh=True`` (the public
        ``.pt`` property) always builds a new object, preserving its
        documented copy semantics for user mutation.
        """
        key = (self._rt._structure_version, self._next_slur_id,
               len(self._slur_specs),
               getattr(self._rt._param_layer, '_instruments_version', 0))
        if not _fresh and not self._rt._write_batch_depth:
            cached = self.__dict__.get('_eff_pt_cache')
            if cached is not None and cached[0] == key:
                return cached[1]
        pt_snapshot = self._extract_parameter_tree()
        self._materialize_bound_values(pt_snapshot)
        for slur_id, slur_spec in self._slur_specs.items():
            leaves = list(slur_spec['leaf_nodes'])
            if not leaves:
                continue
            first, last = leaves[0], leaves[-1]
            for leaf in leaves:
                pt_snapshot.set_mfields(
                    leaf,
                    _slur_start=1 if leaf == first else 0,
                    _slur_end=1 if leaf == last else 0,
                    _slur_id=slur_id
                )
        if not _fresh and not self._rt._write_batch_depth:
            self.__dict__['_eff_pt_cache'] = (key, pt_snapshot)
        return pt_snapshot

    def _event_context(self):
        self._ensure_timing_cache()
        return self._build_effective_parameter_tree()

    def _make_node_proxy(self, node_id: int):
        self._ensure_timing_cache()
        return Parametron(node_id, self, self._rt)

    def _make_event(self, node_id: int, event_context=None, group=None):
        eval_pt = event_context if event_context is not None else self._build_effective_parameter_tree()
        return Parametron(node_id, self, eval_pt, group=group)

    @property
    def pt(self) -> ParameterTree:
        """
        Effective ParameterTree snapshot for the current UC state.
        
        Returns
        -------
        ParameterTree
            A copy of the parameter tree with UC overlays materialized for plotting
            and inspection (e.g., envelope-applied values and slur markers).
        """
        return self._build_effective_parameter_tree(_fresh=True)
    
    @property
    def pfields(self) -> list:
        """
        List of all available parameter field names.
        
        Returns
        -------
        list of str
            Sorted list of parameter field names
        """
        return self._rt.pfields
    
    @property
    def mfields(self) -> list:
        """
        List of all available meta field names.
        
        Returns
        -------
        list of str
            Sorted list of meta field names
        """
        return self._rt.mfields
    
    @staticmethod
    def _instrument_display(inst):
        if inst is None:
            return None
        if isinstance(inst, (str, int)):
            return inst
        if hasattr(inst, 'name') and inst.name not in (None, 'default'):
            return inst.name
        if hasattr(inst, 'defName'):
            return inst.defName
        return str(inst)

    @property
    def events(self):
        """
        Flattened event DataFrame for inspection.

        Columns (left to right):
        ``node_id``, ``start``, ``dur``, ``metric_dur``, ``instrument``,
        then one column per pfield key, then one column per mfield key.
        Rests are indicated by negative ``metric_dur``.  Pfield/mfield
        columns are the union across all events; missing keys are ``None``.

        Returns
        -------
        pandas.DataFrame
        """
        key = (self._rt._structure_version, self._bpm, self._beat,
               self._offset,
               getattr(self._rt._param_layer, '_instruments_version', 0))
        cached = self.__dict__.get('_events_df_cache')
        in_batch = self._rt._write_batch_depth
        if cached is not None and cached[0] == key and not in_batch:
            return cached[1].copy()
        events = self._materialize_events()
        all_pf_keys: list[str] = []
        all_mf_keys: list[str] = []
        pf_seen: set[str] = set()
        mf_seen: set[str] = set()
        rows = []
        for event in events:
            inst = self.get_instrument(event.node_id)
            pf = event.pfields
            mf = event.mfields
            for k in pf:
                if k not in pf_seen:
                    pf_seen.add(k)
                    all_pf_keys.append(k)
            for k in mf:
                if k not in mf_seen:
                    mf_seen.add(k)
                    all_mf_keys.append(k)
            rows.append((event, inst, pf, mf))

        data = []
        for event, inst, pf, mf in rows:
            row = {
                'node_id': event.node_id,
                'start': event.start,
                'dur': event.duration,
                'metric_dur': event.metric_duration,
                'instrument': self._instrument_display(inst),
            }
            for k in all_pf_keys:
                row[k] = pf.get(k)
            for k in all_mf_keys:
                row[k] = mf.get(k)
            data.append(row)

        df = pd.DataFrame(data, index=range(len(rows)))
        if not in_batch:
            self.__dict__['_events_df_cache'] = (key, df)
            return df.copy()
        return df
    
    def _distribute_to_targets(self, targets, fields, include_rests, setter='pfields'):
        if not include_rests:
            targets = [n for n in targets
                       if self._rt[n].get('proportion', 1) >= 0]

        total = len(targets)
        arities = {k: _callable_arity(v) for k, v in fields.items()
                   if callable(v) and not isinstance(v, Pattern)}
        # batch_writes coalesces cache invalidation across the loop; the
        # incremental effective-cache patch in ParameterLayer keeps a write
        # to target i visible to target i+1's DistributionContext
        with self._rt.batch_writes():
            for i, n in enumerate(targets):
                ctx = _build_pfield_context(
                    self, n, i, total,
                    is_rest=self._rt[n].get('proportion', 1) < 0
                )
                resolved = {}
                for k, v in fields.items():
                    if callable(v):
                        resolved[k] = v(ctx) if arities.get(k, 0) >= 1 else v()
                    elif isinstance(v, Pattern):
                        val = next(v)
                        if val is not None:
                            resolved[k] = val
                if resolved:
                    if setter == 'pfields':
                        resolved = {k: _coerce_set_pfield_value(k, v)
                                    for k, v in resolved.items()}
                        self._rt.set_pfields(n, **resolved)
                    else:
                        self._rt.set_mfields(n, **resolved)

    def set_pfields(self, node, include_rests=False, **kwargs) -> None:
        """
        Set parameter field values for target node(s).
        
        Parameters
        ----------
        node : int or list/tuple/set of int
            Target node(s). Single node: value evaluated once, set on that node,
            PT inheritance cascades. List of nodes: value evaluated once per node.
        include_rests : bool, default=False
            When True, rest nodes are included during callable/Pattern distribution.
        **kwargs
            Parameter field names and values. Value types:

            - Scalar: set directly on target node(s) (includes tuples, lists, or any non-callable/non-Pattern value)
            - Callable: evaluated once per target node (0-arg or 1-arg with DistributionContext)
            - Pattern: next() called once per target node
            - Bind: stored as-is; the wrapped callable re-evaluates per
              reading node (descendants created later included)
        """
        targets = self._coerce_node_targets(node)
        self._invalidate_bind_memo_subtree(targets, kwargs.keys())

        distributable_fields = {k: v for k, v in kwargs.items()
                               if not isinstance(v, Bind)
                               and (isinstance(v, Pattern)
                                    or (callable(v) and not _is_pitch_collection_value(v)))}
        static_fields = {k: _coerce_set_pfield_value(k, v)
                        for k, v in kwargs.items()
                        if k not in distributable_fields}

        if static_fields:
            with self._rt.batch_writes():
                for n in targets:
                    self._rt.set_pfields(n, **static_fields)

        if distributable_fields:
            self._distribute_to_targets(targets, distributable_fields, include_rests, setter='pfields')

    def set_mfields(self, node, include_rests=False, **kwargs) -> None:
        """
        Set meta field values for target node(s).
        
        Parameters
        ----------
        node : int or list/tuple/set of int
            Target node(s). Same scoping rules as set_pfields.
        include_rests : bool, default=False
            When True, rest nodes are included during callable/Pattern distribution.
        **kwargs
            Meta field names and values. Value types:
            - Scalar: set directly on target node(s)
            - Callable: evaluated once per target node (0-arg or 1-arg with DistributionContext)
            - Pattern: next() called once per target node
            - Bind: stored as-is; re-evaluates per reading node
        """
        targets = self._coerce_node_targets(node)
        self._invalidate_bind_memo_subtree(targets, kwargs.keys())

        distributable_fields = {k: v for k, v in kwargs.items()
                               if not isinstance(v, Bind)
                               and (callable(v) or isinstance(v, Pattern))}
        static_fields = {k: v for k, v in kwargs.items()
                        if k not in distributable_fields}

        if static_fields:
            with self._rt.batch_writes():
                for n in targets:
                    self._rt.set_mfields(n, **static_fields)

        if distributable_fields:
            self._distribute_to_targets(targets, distributable_fields, include_rests, setter='mfields')

    def _bake_envelope(self, selected, envelope, pfields_list, endpoint):
        # timing reads go straight to the (offset-free) cache with the
        # offset added exactly as the Chronon accessors do — each
        # self.nodes[n][...] read used to allocate a proxy and re-check
        # the timing cache three times per leaf
        self._ensure_timing_cache()
        rx = self._rt._rx
        times = self._real_times
        offset = self._offset
        sounding = [n for n in selected
                    if rx.get_node_data(n).get('proportion', 1) >= 0]
        if not sounding:
            warnings.warn(
                "apply_envelope: selection resolves to no sounding leaves; envelope not applied",
                RuntimeWarning, stacklevel=3
            )
            return
        if len(sounding) == 1 and not endpoint:
            warnings.warn(
                "apply_envelope: endpoint=False with a single sounding leaf "
                "collapses envelope duration to 0; falling back to endpoint=True",
                RuntimeWarning, stacklevel=3
            )
            endpoint = True
        start_time = min(times[n]['real_onset'] + offset for n in sounding)
        if endpoint:
            end_time = max(times[n]['real_onset'] + offset + abs(times[n]['real_duration'])
                           for n in sounding)
        else:
            end_time = max(times[n]['real_onset'] + offset for n in sounding)
        duration = end_time - start_time
        raw_total = sum(envelope.times)
        scaled_envelope = Envelope(
            values=envelope.values,
            times=envelope.times,
            curve=envelope.curve,
            warp=envelope.warp,
            time_scale=duration / raw_total if raw_total > 0 else 1.0
        )
        self._invalidate_bind_memo_subtree(sounding, pfields_list)
        with self._rt.batch_writes():
            for node in sounding:
                event_time = times[node]['real_onset'] + offset
                relative_time = max(0, min(event_time - start_time, scaled_envelope.total_time))
                try:
                    env_value = scaled_envelope.at_time(relative_time)
                except ValueError:
                    env_value = scaled_envelope.values[0] if relative_time <= 0 else scaled_envelope.values[-1]
                self._rt.set_pfields(node, **{pfield: env_value for pfield in pfields_list})

    def _resolve_control_envelope_leaves(self, desc):
        anchor = desc["anchor_node"]
        if anchor not in self._rt:
            return []
        leaf_subset = desc["leaf_subset"]
        if leaf_subset is None:
            candidates = list(self._rt.subtree_leaves(anchor))
        else:
            current_leaves = set(self._rt.leaf_nodes)
            candidates = [n for n in leaf_subset if n in current_leaves]
        return [n for n in candidates if self._rt[n].get('proportion', 1) >= 0]

    @staticmethod
    def _leaf_subset_contains(leaf_subset, value):
        return value in leaf_subset

    @staticmethod
    def _leaf_subset_intersects(leaf_subset, other):
        other_set = other if isinstance(other, (set, frozenset)) else set(other)
        return any(n in other_set for n in leaf_subset)

    @staticmethod
    def _leaf_subset_subtract(leaf_subset, other):
        other_set = other if isinstance(other, (set, frozenset)) else set(other)
        return tuple(n for n in leaf_subset if n not in other_set)

    @staticmethod
    def _leaf_subset_union(leaf_subset, other):
        seen = set(leaf_subset)
        extras = tuple(n for n in other if n not in seen)
        return tuple(leaf_subset) + extras

    def _resolve_control_envelope_time_span(self, desc, sounding=None):
        if sounding is None:
            sounding = self._resolve_control_envelope_leaves(desc)
        if not sounding:
            return (0.0, 0.0)
        self._ensure_timing_cache()
        times = self._real_times
        offset = self._offset
        start = min(times[n]['real_onset'] + offset for n in sounding)
        if desc["endpoint"]:
            end = max(times[n]['real_onset'] + offset + abs(times[n]['real_duration'])
                      for n in sounding)
        else:
            end = max(times[n]['real_onset'] + offset for n in sounding)
        return (start, end)

    def _resolved_envelope_leaf_set(self, env_id, desc):
        """Resolved leaf set for a control envelope, memoized on the tree's
        structure version plus the descriptor fields that define the
        resolution (anchor + leaf_subset, both replaced — never mutated —
        on healing). Kills the O(envelopes^2 x leaves) re-resolution in
        _check_envelope_overlap."""
        memo = getattr(self, '_envelope_leafset_memo', None)
        if memo is None:
            memo = self._envelope_leafset_memo = {}
        key = (self._rt._structure_version,
               desc["anchor_node"], desc["leaf_subset"])
        hit = memo.get(env_id)
        if hit is not None and hit[0] == key:
            return hit[1]
        leaves = set(self._resolve_control_envelope_leaves(desc))
        memo[env_id] = (key, leaves)
        return leaves

    def _check_envelope_overlap(self, new_pfields, new_leaves):
        new_pf_set = set(new_pfields)
        new_leaf_set = set(new_leaves)
        for env_id, desc in self._control_envelopes.items():
            shared_pf = new_pf_set.intersection(desc["pfields"])
            if not shared_pf:
                continue
            existing_leaves = self._resolved_envelope_leaf_set(env_id, desc)
            shared_leaves = new_leaf_set.intersection(existing_leaves)
            if shared_leaves:
                raise ValueError(
                    "Overlapping control envelopes on the same pfield "
                    f"(pfields={sorted(shared_pf)}, "
                    f"shared_leaves={sorted(shared_leaves)}, "
                    f"existing_pfields={sorted(desc['pfields'])})"
                )

    def _rebake_control_envelope(self, desc):
        sounding = self._resolve_control_envelope_leaves(desc)
        if sounding:
            self._bake_envelope(sounding, desc["envelope"], desc["pfields"], desc["endpoint"])

    def _record_control_envelope(self, selected, envelope, pfields_list, endpoint):
        self._ensure_timing_cache()
        sounding = [n for n in selected if self._rt[n].get('proportion', 1) >= 0]
        if not sounding:
            warnings.warn(
                "apply_envelope: selection resolves to no sounding leaves; envelope not applied",
                RuntimeWarning, stacklevel=3
            )
            return

        anchor_node = selected[0]
        for n in selected[1:]:
            anchor_node = self._rt.lowest_common_ancestor(anchor_node, n)

        all_anchor_leaves = set(self._rt.subtree_leaves(anchor_node))
        leaf_subset = None if set(selected) == all_anchor_leaves else tuple(selected)

        self._check_envelope_overlap(pfields_list, sounding)
        self._bake_envelope(sounding, envelope, pfields_list, endpoint)

        env_id = self._next_envelope_id
        self._next_envelope_id += 1
        self._control_envelopes[env_id] = {
            "envelope": envelope,
            "pfields": list(pfields_list),
            "endpoint": endpoint,
            "anchor_node": anchor_node,
            "leaf_subset": leaf_subset,
        }
        return env_id

    def resolved_control_envelopes(self):
        """Resolve recorded control-envelope descriptors to concrete leaf spans.

        Returns
        -------
        list of dict
            One entry per active control envelope (``control=True`` at
            application time), with its envelope, target pfields, and the
            resolved leaf ids/timing — the payload the playback layer turns
            into runtime bus automation.
        """
        self._ensure_timing_cache()
        result = []
        for desc in self._control_envelopes.values():
            leaves = self._resolve_control_envelope_leaves(desc)
            if not leaves:
                continue
            start, end = self._resolve_control_envelope_time_span(desc, leaves)
            result.append({
                "envelope": desc["envelope"],
                "pfields": desc["pfields"],
                "target_nodes": list(leaves),
                "time_span": (start, end),
            })
        return result

    def remove_envelope(self, env_id: int) -> None:
        """
        Remove a previously-applied control envelope by handle.

        The baked pfield values written by this envelope are unset so that
        each affected leaf falls back to its inherited (parent/instrument)
        default. Only control-mode envelopes allocate handles; bake-mode
        envelopes are one-shot writes with no state to remove.

        Parameters
        ----------
        env_id : int
            The identifier returned by ``apply_envelope(..., control=True)``.

        Raises
        ------
        KeyError
            If ``env_id`` is not a live envelope handle on this UC.
        """
        if env_id not in self._control_envelopes:
            raise KeyError(f"No control envelope with id {env_id}")
        desc = self._control_envelopes.pop(env_id)
        leaves = self._resolve_control_envelope_leaves(desc)
        self._invalidate_bind_memo_subtree(leaves, desc["pfields"])
        for leaf in leaves:
            if leaf not in self._rt:
                continue
            self._rt.remove_fields(leaf, desc["pfields"])

    def apply_envelope(self,
                       envelope: Envelope,
                       pfields: Union[str, list],
                       node: Union[int, list, tuple, set],
                       offset: int = 0,
                       take: Union[int, None] = None,
                       scope: Literal["span", "per_node"] = "span",
                       control: bool = False,
                       endpoint: bool = True) -> Union[int, list[int]]:
        """
        Apply an envelope to a contiguous leaf span within this UC.

        Haddad's, in kind (docket DOC-5): thesis sect8.2.2 treats the
        Temporal Unit as a « reservoir de donnees quelconques » -- "a
        reservoir of arbitrary data" -- and applying a curve across a span
        of its leaves is that idea made concrete. The *hierarchical* half
        of the machinery this writes into is Klotho's own; see the class
        docstring for why the two claims are kept apart.

        Parameters
        ----------
        envelope : Envelope
            Envelope specification to apply.
        pfields : Union[str, list]
            Target parameter field(s). Overlap is allowed across different fields
            but rejected for overlapping spans on the same field.
        node : int | list | tuple | set
            Node selector. A single node resolves to subtree leaves. An iterable
            can be treated either as one combined span (``scope="span"``) or as
            independent per-node applications (``scope="per_node"``).
        offset : int, default=0
            Leaf offset into the resolved contiguous selection.
        take : int, optional
            Number of leaves to include from ``offset``. If omitted, uses all
            leaves from ``offset`` to the end of the resolved selection.
        scope : {"span", "per_node"}, default="span"
            How the node selection is interpreted.  ``"span"`` treats all
            resolved leaves as one contiguous group.  ``"per_node"`` gives
            each node in the iterable its own independent envelope.
        control : bool, default=False
            When ``True``, values are still baked into the ParameterTree
            (for inspection) but a control-envelope descriptor is also
            recorded for runtime bus-based automation via a
            ``__klEnvCtrl`` control synth.
        endpoint : bool, default=True
            If True, envelope span is onset-to-end of the selected sounding
            leaves.  If False, span is onset-to-onset.
            
        Returns
        -------
        int | list[int]
            Envelope identifier, or list of identifiers when
            ``scope="per_node"``. In per-node scope, the return value is
            always a list.

        Raises
        ------
        ValueError
            If selection is invalid/non-contiguous, offset/take overflows
            bounds, a same-pfield overlap is detected, or scope is invalid.
        """
        pfields_list = pfields if isinstance(pfields, list) else [pfields]
        apply_fn = self._record_control_envelope if control else self._bake_envelope
        if scope == "span":
            selected = self._resolve_leaf_selection(node=node)
            selected = self._apply_offset_take(selected, offset=offset, take=take)
            return apply_fn(selected, envelope, pfields_list, endpoint)
        elif scope == "per_node":
            groups = self._resolve_per_node_leaf_groups(node)
            results = []
            for group in groups:
                selected = self._apply_offset_take(group, offset=offset, take=take)
                results.append(apply_fn(selected, envelope, pfields_list, endpoint))
            return results
        else:
            raise ValueError(f"Unknown scope: {scope}")

    def _partition_non_rest_segments(self, leaves, rest_set):
        segments = []
        current = []
        for leaf in leaves:
            if leaf in rest_set:
                if len(current) >= 2:
                    segments.append(tuple(current))
                current = []
            else:
                current.append(leaf)
        if len(current) >= 2:
            segments.append(tuple(current))
        return segments

    def _validate_slur_segment(self, segment, reserved_sets=None):
        proposed_set = set(segment)
        for spec in self._slur_specs.values():
            if proposed_set.intersection(spec['leaf_set']):
                raise ValueError("Slurs cannot overlap")
        if reserved_sets:
            for reserved_set in reserved_sets:
                if proposed_set.intersection(reserved_set):
                    raise ValueError("Slurs cannot overlap within requested per-node applications")
        return proposed_set

    def _validate_slur_selection(self, selected, reserved_sets=None):
        if len(selected) < 2:
            raise ValueError("Slur requires at least two leaves")
        rest_set = {n for n in selected if self._rt[n].get('proportion', 1) < 0}
        segments = self._partition_non_rest_segments(selected, rest_set)
        if not segments:
            raise ValueError("Slur selection has no segment with at least two sounding leaves")
        proposed_set = set(selected)
        proposed_range = self._selection_index_range(selected)
        for spec in self._slur_specs.values():
            if proposed_set.intersection(spec['leaf_set']):
                raise ValueError("Slurs cannot overlap")
        if reserved_sets:
            for reserved_set in reserved_sets:
                if proposed_set.intersection(reserved_set):
                    raise ValueError("Slurs cannot overlap within requested per-node applications")
        return proposed_set, proposed_range

    def _register_slur(self, selected):
        proposed_set, proposed_range = self._validate_slur_selection(selected)
        slur_id = self._next_slur_id
        self._next_slur_id += 1
        self._slur_specs[slur_id] = {
            'leaf_nodes': selected,
            'leaf_set': proposed_set,
            'index_range': proposed_range
        }
        return slur_id

    def apply_slur(self,
                   node: Union[int, list, tuple, set],
                   offset: int = 0,
                   take: Union[int, None] = None,
                   mode: Literal["span", "per_node"] = "span") -> Union[int, list[int]]:
        """
        Apply a slur to a contiguous leaf span within this UC.

        Parameters
        ----------
        node : int | list | tuple | set
            Node selector. A single node resolves to subtree leaves. An iterable
            can be treated either as one combined span (`mode=\"span\"`) or as
            independent per-node applications (`mode=\"per_node\"`).
        offset : int, default=0
            Leaf offset into the resolved contiguous selection.
        take : int, optional
            Number of leaves to include from `offset`. If omitted, uses all leaves
            from `offset` to the end of the resolved selection.
        mode : {"span", "per_node"}, default="span"
            Selection interpretation mode.

        Returns
        -------
        int | list[int]
            Slur identifier, or list of identifiers when `mode=\"per_node\"`
            applies. In per-node mode, the return value is always a list.

        Raises
        ------
        ValueError
            If selection is invalid/non-contiguous, includes rests, overflows
            offset/take bounds, resolves to fewer than two leaves, overlaps an
            existing slur, or mode is invalid.
        """
        if mode == "span":
            selected = self._resolve_leaf_selection(node=node)
            selected = self._apply_offset_take(selected, offset=offset, take=take)
            selected = self._snap_to_tie_heads(selected)
            if len(selected) < 2:
                raise ValueError("Slur requires at least two leaves")
            rest_set = {n for n in selected if self._rt[n].get('proportion', 1) < 0}
            segments = self._partition_non_rest_segments(selected, rest_set)
            slur_ids = []
            reserved_sets = []
            for segment in segments:
                self._validate_slur_segment(segment, reserved_sets)
                slur_id = self._register_slur(segment)
                reserved_sets.append(set(segment))
                slur_ids.append(slur_id)
            return slur_ids[0] if len(slur_ids) == 1 else slur_ids
        if mode == "per_node":
            groups = self._resolve_per_node_leaf_groups(node)
            slur_ids = []
            reserved_sets = []
            for group in groups:
                selected = self._apply_offset_take(group, offset=offset, take=take)
                selected = self._snap_to_tie_heads(selected)
                rest_set = {n for n in selected if self._rt[n].get('proportion', 1) < 0}
                segments = self._partition_non_rest_segments(selected, rest_set)
                for segment in segments:
                    self._validate_slur_segment(segment, reserved_sets)
                    slur_id = self._register_slur(segment)
                    reserved_sets.append(set(segment))
                    slur_ids.append(slur_id)
            return slur_ids
        raise ValueError(f"Unknown mode: {mode}")

    def _snap_to_tie_heads(self, selected):
        """Snap a slur selection onto tie-group heads (charter sect8).

        Tie groups are atomic for slur membership: a continuation is part
        of the head's sound, so a selection touching one has exactly one
        lossless meaning — the group, addressed by its head. Order is
        preserved; duplicates collapse.
        """
        head_of = {}
        for g in self._rt.tie_groups:
            if len(g) > 1:
                for n in g:
                    head_of[n] = g[0]
        if not head_of:
            return selected
        out, seen = [], set()
        for n in selected:
            h = head_of.get(n, n)
            if h not in seen:
                seen.add(h)
                out.append(h)
        return type(selected)(out) if isinstance(selected, tuple) else out

    def _split_slurs_for_rests(self, nodes_to_rest: set[int]):
        for slur_id, spec in list(self._slur_specs.items()):
            if not spec['leaf_set'].intersection(nodes_to_rest):
                continue
            leaves = list(spec['leaf_nodes'])
            segments = self._partition_non_rest_segments(leaves, nodes_to_rest)
            del self._slur_specs[slur_id]
            for segment in segments:
                self._register_slur(segment)

    def _invalidate_slurs_for_removed_nodes(self, removed_set):
        for slur_id, spec in list(self._slur_specs.items()):
            if not spec['leaf_set'].intersection(removed_set):
                continue
            remaining = [n for n in spec['leaf_nodes'] if n not in removed_set]
            del self._slur_specs[slur_id]
            if len(remaining) >= 2:
                rest_set = {n for n in remaining if self._rt[n].get('proportion', 1) < 0}
                segments = self._partition_non_rest_segments(remaining, rest_set)
                for segment in segments:
                    self._register_slur(segment)

    def _heal_slurs_after_subdivide(self, old_leaf, new_leaves):
        for slur_id, spec in list(self._slur_specs.items()):
            if old_leaf not in spec['leaf_set']:
                continue
            old_nodes = list(spec['leaf_nodes'])
            idx = old_nodes.index(old_leaf)
            new_nodes = old_nodes[:idx] + list(new_leaves) + old_nodes[idx + 1:]
            del self._slur_specs[slur_id]
            rest_set = {n for n in new_nodes if self._rt[n].get('proportion', 1) < 0}
            segments = self._partition_non_rest_segments(new_nodes, rest_set)
            for segment in segments:
                self._register_slur(segment)

    def _heal_envelopes_after_subdivide(self, old_leaf, new_leaves):
        for desc in self._control_envelopes.values():
            needs_rebake = False
            if desc["leaf_subset"] is not None and old_leaf in desc["leaf_subset"]:
                without_old = self._leaf_subset_subtract(desc["leaf_subset"], {old_leaf})
                desc["leaf_subset"] = self._leaf_subset_union(without_old, new_leaves)
                needs_rebake = True
            elif desc["leaf_subset"] is None:
                ancestor_set = set(self._rt.descendants(desc["anchor_node"])) | {desc["anchor_node"]}
                if old_leaf in ancestor_set:
                    needs_rebake = True
            if needs_rebake:
                self._rebake_control_envelope(desc)

    def _filter_envelopes_for_rests(self, affected_leaves):
        for env_id, desc in list(self._control_envelopes.items()):
            touched = False
            if desc["leaf_subset"] is not None:
                if self._leaf_subset_intersects(desc["leaf_subset"], affected_leaves):
                    desc["leaf_subset"] = self._leaf_subset_subtract(
                        desc["leaf_subset"], affected_leaves
                    )
                    touched = True
            else:
                anchor_leaves = set(self._rt.subtree_leaves(desc["anchor_node"]))
                if anchor_leaves.intersection(affected_leaves):
                    touched = True
            if not touched:
                continue
            if not self._resolve_control_envelope_leaves(desc):
                warnings.warn(
                    "Control envelope removed: all target leaves are now rests",
                    RuntimeWarning, stacklevel=3
                )
                del self._control_envelopes[env_id]
            else:
                self._rebake_control_envelope(desc)

    def _invalidate_envelopes_for_removed_nodes(self, removed_set):
        for env_id, desc in list(self._control_envelopes.items()):
            if desc["anchor_node"] in removed_set:
                warnings.warn(
                    "Control envelope removed: anchor node was destroyed",
                    RuntimeWarning, stacklevel=3
                )
                del self._control_envelopes[env_id]
                continue
            if (desc["leaf_subset"] is not None
                    and self._leaf_subset_intersects(desc["leaf_subset"], removed_set)):
                desc["leaf_subset"] = self._leaf_subset_subtract(
                    desc["leaf_subset"], removed_set
                )
                if not self._resolve_control_envelope_leaves(desc):
                    warnings.warn(
                        "Control envelope removed: all target leaves were destroyed",
                        RuntimeWarning, stacklevel=3
                    )
                    del self._control_envelopes[env_id]
                else:
                    self._rebake_control_envelope(desc)

    def _relocate_id_keyed_state(self, mapping):
        """Follow the content when the fused tree reassigns node ids.

        Registered as the tree's id-state observer, so a verb reached
        THROUGH ``uc._rt`` -- the preserved family's ``insert``/``extract``/
        ``scale``, or a positional ``insert_child`` -- heals the same
        overlays this unit's own deleters heal. ``mapping`` is total over
        surviving ids: an id absent from it was destroyed.

        Overlays are moved, not rebaked. The baked values themselves live in
        node data and travel with the payload; re-resolving them here would
        read a timing cache the mutation has not finished invalidating.
        """
        self._remap_bind_memo(mapping)
        self._remap_slur_specs(mapping)
        self._remap_control_envelopes(mapping)
        # a correspondence published to a mirror target is keyed by the ids
        # that just moved, so it no longer describes this unit
        self._mirror_id_map = None

    def _remap_bind_memo(self, mapping):
        if not self._bind_memo:
            return
        self._bind_memo = {
            (mapping[node], key): value
            for (node, key), value in self._bind_memo.items()
            if node in mapping
        }

    def _remap_slur_specs(self, mapping):
        if not self._slur_specs:
            return
        current_leaves = set(self._rt.leaf_nodes)
        for slur_id, spec in list(self._slur_specs.items()):
            moved, seen = [], set()
            for leaf in spec['leaf_nodes']:
                target = mapping.get(leaf)
                # a note that stopped being a leaf is no longer slurrable;
                # `seen` guards a mapping that fuses two old ids into one
                if target in current_leaves and target not in seen:
                    seen.add(target)
                    moved.append(target)
            # members were relocated INDEPENDENTLY, so their span can now
            # hold a leaf that was never slurred (an `insert_child` landing
            # mid-slur). Contiguity is the property that DEFINED the slur
            # (`apply_slur` refuses anything else), so the remap must not
            # store its absence: split at every intruder, exactly as
            # `make_rest` splits at a rest, and let fragments below two
            # notes dissolve. The intruder is never swallowed -- a slur is
            # authored by explicit selection, not by an edit landing nearby.
            segments = self._contiguous_slur_segments(moved)
            del self._slur_specs[slur_id]
            for i, segment in enumerate(segments):
                if i == 0:
                    new_id = slur_id  # an unsplit slur keeps its identity
                else:
                    new_id = self._next_slur_id
                    self._next_slur_id += 1
                self._slur_specs[new_id] = {
                    'leaf_nodes': tuple(segment),
                    'leaf_set': set(segment),
                    'index_range': tuple(self._selection_index_range(segment)),
                }

    def _contiguous_slur_segments(self, moved):
        """Partition relocated slur members into spans ``apply_slur`` could
        have authored.

        A stored slur is consecutive in leaf order except for tie
        continuations, which ``_snap_to_tie_heads`` folded onto their heads
        -- those stay legal gaps as long as the head owning them is the
        member just before. Any other leaf inside the span is an intruder,
        and the run splits there. Fragments below two notes are not slurs
        and are dropped.
        """
        if len(moved) < 2:
            return []
        leaf_order = list(self._rt.leaf_nodes)
        leaf_index = {leaf: i for i, leaf in enumerate(leaf_order)}
        head_of = {}
        for g in self._rt.tie_groups:
            for n in g[1:]:
                head_of[n] = g[0]
        ordered = sorted(moved, key=leaf_index.__getitem__)
        segments, current = [], [ordered[0]]
        for prev, nxt in zip(ordered, ordered[1:]):
            gap_ok = all(
                head_of.get(leaf_order[i]) == prev
                for i in range(leaf_index[prev] + 1, leaf_index[nxt])
            )
            if gap_ok:
                current.append(nxt)
            else:
                segments.append(current)
                current = [nxt]
        segments.append(current)
        return [seg for seg in segments if len(seg) >= 2]

    def _remap_control_envelopes(self, mapping):
        if not self._control_envelopes:
            return
        current_leaves = set(self._rt.leaf_nodes)
        for env_id, desc in list(self._control_envelopes.items()):
            anchor = mapping.get(desc["anchor_node"])
            if anchor is None:
                warnings.warn(
                    "Control envelope removed: anchor node was destroyed",
                    RuntimeWarning, stacklevel=3
                )
                del self._control_envelopes[env_id]
                continue
            desc["anchor_node"] = anchor
            if desc["leaf_subset"] is None:
                continue
            # a subset member that stopped being a leaf is no longer a
            # target (resolution would filter it, but the descriptor must
            # not keep naming an id the public API could never select --
            # left behind, it re-attaches when the id is freed and reused)
            moved = tuple(dict.fromkeys(
                mapping[n] for n in desc["leaf_subset"]
                if n in mapping and mapping[n] in current_leaves
            ))
            if not moved:
                warnings.warn(
                    "Control envelope removed: all target leaves were destroyed",
                    RuntimeWarning, stacklevel=3
                )
                del self._control_envelopes[env_id]
                continue
            desc["leaf_subset"] = moved

    def make_rest(self, node) -> None:
        """
        Make one or more nodes (and their subtrees) rests, splitting
        intersecting slurs and filtering control envelopes.

        When multiple nodes are passed, the affected-leaf set is collected
        across all of them before slur splitting and envelope filtering, so
        slurs/envelopes that touch the combined set are healed exactly once.

        Parameters
        ----------
        node : int or iterable of int
            The node ID (or iterable of node IDs) to convert to rests.
        """
        nodes = self._coerce_node_targets(node)
        affected: set = set()
        for n in nodes:
            affected.add(n)
            affected.update(self._rt.descendants(n))
        affected_leaves = {n for n in affected if n in self._rt.leaf_nodes}
        self._split_slurs_for_rests(affected_leaves)
        super().make_rest(nodes)
        self._filter_envelopes_for_rests(affected_leaves)

    def make_sounding(self, node) -> None:
        """
        Bring one or more nodes (and their subtrees) back out of rest.

        Parameters
        ----------
        node : int or iterable of int
            The node ID (or iterable of node IDs) to bring back.

        Notes
        -----
        This override adds nothing to
        :meth:`~klotho.chronos.temporal_units.TemporalUnit.make_sounding`,
        and that absence is the point worth recording here.
        :meth:`make_rest` does two CompositionalUnit-specific things on the
        way down: it SPLITS any slur that crosses the newly rested leaves
        into surviving segments, and it DROPS control envelopes whose
        target leaves all became rests. Neither writes down what it
        destroyed, so neither can be undone. A split slur stays split and a
        dropped envelope stays dropped; re-apply them if you want them
        back.

        What comes back is the rhythm: the leaves sound again, and the
        ancestor chain is un-rested with them so the change survives the
        next recompute. Ties are not restored either -- see
        :meth:`~klotho.chronos.rhythm_trees.RhythmTree.make_sounding`.
        """
        super().make_sounding(node)

    def subdivide(self, node: int, S) -> None:
        """
        Subdivide a leaf node with structure (D, S), syncing PT, cascading
        values, and healing slurs/control envelopes.

        Parameters
        ----------
        node : int
            The leaf node to subdivide.
        S : tuple
            Valid subdivisions tuple (integers or nested (D, S) tuples).

        Raises
        ------
        ValueError
            If the node is not found or is not a leaf.
        """
        # items() returns EFFECTIVE values, so this copy materializes whatever
        # the node inherited as a raw override on each new child. Harmless for
        # a plain value -- the child would have inherited the same thing -- but
        # fatal for a Bind: a raw Bind on a leaf makes that leaf its own read
        # set, so Bind.index collapses to 0 of 1. Binds inherit; do not copy.
        parent_data = self._rt.items(node)
        pfields = {k: v for k, v in parent_data.items()
                   if k in self._rt.pfield_names and not isinstance(v, Bind)}
        mfields = {k: v for k, v in parent_data.items()
                   if k in self._rt.mfield_names and not isinstance(v, Bind)}

        # this verb absorbs the new leaves into the spans below, so the
        # tree's own leaf-surface seam must not strip them first
        self._rt._owner_absorbs_leaf_growth = True
        try:
            self._rt.subdivide(node, S)
        finally:
            self._rt._owner_absorbs_leaf_growth = False
        self._invalidate_timing_cache()
        new_children = list(self._rt.successors(node))
        for child in new_children:
            if pfields:
                self._rt.set_pfields(child, **pfields)
            if mfields:
                self._rt.set_mfields(child, **mfields)

        new_leaves = list(self._rt.subtree_leaves(node))
        self._heal_slurs_after_subdivide(node, new_leaves)
        self._heal_envelopes_after_subdivide(node, new_leaves)

    def graft_subtree(self, node: int, subtree, mode: str = 'replace'):
        """Graft *subtree* at a leaf, healing slurs and control envelopes.

        Same contract as :meth:`TemporalUnit.graft_subtree`; this override
        exists so the graft heals the spans that reference the replaced leaf,
        exactly as :meth:`subdivide` does. Without it the two ways of adding
        structure agree about parameters but not about slurs.
        """
        # this verb absorbs the new leaves into the spans below, so the
        # tree's own leaf-surface seam must not strip them first
        self._rt._owner_absorbs_leaf_growth = True
        try:
            result = self._rt.graft_subtree(node, subtree, mode)
        finally:
            self._rt._owner_absorbs_leaf_growth = False
        self._invalidate_timing_cache()
        new_leaves = list(self._rt.subtree_leaves(result))
        self._heal_slurs_after_subdivide(result, new_leaves)
        self._heal_envelopes_after_subdivide(result, new_leaves)
        return result

    def add_child(self, parent, **attr):
        """Add a child node (``label`` is coerced to ``proportion``); see :meth:`Tree.add_child`."""
        if 'label' in attr and 'proportion' not in attr:
            attr = dict(attr)
            attr['proportion'] = attr.pop('label')
        new_rt_node = self._rt.add_child(parent, **attr)
        self._invalidate_timing_cache()
        return new_rt_node

    def prune(self, node):
        """Remove a node and promote its children, healing slurs/envelopes that referenced it."""
        removed_set = {node}
        self._invalidate_slurs_for_removed_nodes(removed_set)
        self._invalidate_envelopes_for_removed_nodes(removed_set)
        self._invalidate_bind_memo(removed_set)
        self._rt.prune(node)
        self._invalidate_timing_cache()

    def remove_subtree(self, node):
        """Remove a node and its descendants, healing slurs/envelopes that referenced them."""
        removed_set = {node} | set(self._rt.descendants(node))
        self._invalidate_slurs_for_removed_nodes(removed_set)
        self._invalidate_envelopes_for_removed_nodes(removed_set)
        self._invalidate_bind_memo(removed_set)
        self._rt.remove_subtree(node)
        self._invalidate_timing_cache()

    def set_instrument(self, node, instrument, include_rests: bool = False) -> None:
        """
        Set an instrument for target node(s).

        Parameters
        ----------
        node : int or list/tuple of int
            Target node(s). Single node: instrument set on that node, inherits
            to descendants. List of nodes: instrument evaluated once per node.
        instrument : Instrument, str, int, Pattern, or callable
            - Instrument: set directly on node, and its control names are
              registered onto the node -- afterwards the node's ``pfields``
              holds a key for every control of the SynthDef, so each one
              can be addressed and overridden individually. The keys read
              ``None`` until authored; the real default values first appear
              in the lowered event.
              If the instrument carries an ``_ensemble_family`` tag (i.e. it
              was accessed through an Ensemble family view), the ``group``
              mfield is automatically set to the family name.
            - str: raw synth reference (SynthDef name). The name is stored
              as-is and defaults are **not** materialized -- the node's
              ``pfields`` stays empty and the engine applies the SynthDef's
              own defaults at play time. Pass the object form
              (``SynthDefInstrument.from_manifest('kl_tri')``) to get them
              onto the node, or read them without assigning via that
              object's ``.pfields``.
            - Pattern: next() called once per target node
            - Callable: evaluated once per target node (0-arg or 1-arg with DistributionContext)

            During Pattern/callable distribution, a ``None`` result skips
            that node: its existing binding (or inheritance) is left
            untouched. This is the deliberate "leave this one alone" idiom,
            not an error.
        include_rests : bool, default=False
            When True, rest nodes are included during callable/Pattern
            distribution. By default rests are skipped, so a Pattern unrolls
            across sounding nodes only (matching ``set_pfields``). Static
            instruments (str, int, Instrument) always apply to every target
            regardless of this flag.

        Raises
        ------
        TypeError
            If a SynthDef name (or SynthDefInstrument-wrapped defName)
            refers to a known effect or infra def. Effect *instances*
            remain accepted: assigning an Effect to nodes automates the
            insert's parameters via ``set`` events.
        """
        targets = self._coerce_node_targets(node)

        if isinstance(instrument, (str, int)):
            _reject_fx_as_instrument(instrument)
            for n in targets:
                self._rt.set_instrument(n, instrument)
        elif isinstance(instrument, (Instrument, Effect)):
            if not isinstance(instrument, Effect):
                _reject_fx_as_instrument(getattr(instrument, 'defName', None))
            family = getattr(instrument, '_ensemble_family', None)
            with self._rt.batch_writes():
                for n in targets:
                    self._rt.set_instrument(n, instrument)
                    if family is not None:
                        self._rt.set_mfields(n, group=family)
        elif callable(instrument) or isinstance(instrument, Pattern):
            if not include_rests:
                targets = [n for n in targets
                           if self._rt[n].get('proportion', 1) >= 0]
            total = len(targets)
            arity = (None if isinstance(instrument, Pattern)
                     else _callable_arity(instrument))
            with self._rt.batch_writes():
                for i, n in enumerate(targets):
                    if isinstance(instrument, Pattern):
                        inst = next(instrument)
                    else:
                        ctx = _build_pfield_context(
                            self, n, i, total,
                            is_rest=self._rt[n].get('proportion', 1) < 0
                        )
                        inst = instrument(ctx) if arity >= 1 else instrument()
                    if inst is not None:
                        if isinstance(inst, str):
                            _reject_fx_as_instrument(inst)
                        elif isinstance(inst, Instrument) and not isinstance(inst, Effect):
                            _reject_fx_as_instrument(getattr(inst, 'defName', None))
                        self._rt.set_instrument(n, inst)
                        family = getattr(inst, '_ensemble_family', None)
                        if family is not None:
                            self._rt.set_mfields(n, group=family)
        else:
            raise TypeError(_instrument_shape_error(instrument))

    def set(self, node, *, inst=None, include_rests=False,
            pfields=None, mfields=None, **fields):
        """
        Set instrument, parameter fields, and meta fields in one call.

        Bare keyword fields are routed automatically: names in
        :data:`ENGINE_MFIELDS` (currently ``strum`` and ``group``) go to
        meta fields, everything else goes to parameter fields. So::

            uc.set(node, inst='fd_saw', freq='F#3', amp=0.15, strum=0.2)

        is equivalent to ``set_instrument`` + ``set_pfields(freq=...,
        amp=...)`` + ``set_mfields(strum=...)``.

        Parameters
        ----------
        node : int or list/tuple of int
            Target node(s).
        inst : Instrument, str, Pattern, callable, or None, optional
            Instrument to assign (same semantics as :meth:`set_instrument`,
            including the effect-SynthDef guard).
        include_rests : bool, optional
            When True, rest nodes are included during callable/Pattern
            distribution (default is False). Applies to ``inst``
            distribution as well as pfields/mfields, so Patterns passed
            together stay aligned on the same sounding nodes.
        pfields : dict or None, optional
            Explicit parameter fields. Escape hatch: values here always go
            to pfields, even if a name collides with an engine mfield.
        mfields : dict or None, optional
            Explicit meta fields. Escape hatch: values here always go to
            mfields, even if a name collides with a SynthDef control.
        **fields
            Auto-routed fields (see above). Values may be scalars,
            Patterns, or callables, exactly as in ``set_pfields`` /
            ``set_mfields``.
        """
        if inst is not None:
            self.set_instrument(node, inst, include_rests=include_rests)

        routed_mfields = {k: v for k, v in fields.items() if k in ENGINE_MFIELDS}
        routed_pfields = {k: v for k, v in fields.items() if k not in ENGINE_MFIELDS}

        if mfields:
            routed_mfields.update(mfields)
        if pfields:
            routed_pfields.update(pfields)

        if routed_mfields:
            self.set_mfields(node, include_rests=include_rests, **routed_mfields)
        if routed_pfields:
            self.set_pfields(node, include_rests=include_rests, **routed_pfields)

    def sparsify(self, probability, node=None, seed=None):
        """
        Randomly convert sounding leaves to rests.

        Extends the base ``TemporalUnit.sparsify`` to accept a callable
        probability that receives a ``DistributionContext`` for each candidate
        leaf, enabling parameter-aware rest decisions.

        Parameters
        ----------
        probability : float or callable
            If float, the fixed probability (0--1) of each leaf becoming
            a rest. If callable, receives a ``DistributionContext`` and returns
            True to rest the leaf.
        node : int or iterable of int, optional
            Restrict sparsification to this node's subtree leaves.
            If None, all leaves are candidates.
        seed : int, numpy.random.Generator, or None, optional
            Seed for reproducible sparsification when *probability* is a
            float. Ignored for callable probabilities (the callable makes
            the decision itself).
        """
        if not callable(probability):
            super().sparsify(probability, node, seed=seed)
            return

        import numpy as _np
        if node is None:
            targets = list(self._rt.leaf_nodes)
        else:
            seen = set()
            targets = []
            for n in self._coerce_node_targets(node):
                for leaf in self._rt.subtree_leaves(n):
                    if leaf not in seen:
                        seen.add(leaf)
                        targets.append(leaf)

        targets = [n for n in targets
                   if self._rt[n].get('proportion', 1) >= 0]

        total = len(targets)
        for i, leaf in enumerate(targets):
            ctx = _build_pfield_context(self, leaf, i, total, is_rest=False)
            if probability(ctx):
                self.make_rest(leaf)

    def get_instrument(self, node: int):
        """Resolved instrument for node (nearest ancestor with instrument)."""
        return self._rt.get_instrument(node)

    def get_pfield(self, node: int, key: str, default=None):
        """Parameter field value for node (PT only, no instrument fallback)."""
        value = self._resolve_bound_value(node, key, self._rt.get_pfield(node, key))
        return default if value is None else value

    def get_mfield(self, node: int, key: str, default=None):
        """Meta field value for node."""
        value = self._resolve_bound_value(node, key, self._rt.get_mfield(node, key))
        return default if value is None else value

    
    def clear_parameters(self, node: int = None) -> None:
        """
        Clear parameter values and intersecting overlays.
        
        Parameters
        ----------
        node : int, optional
            Node ID to clear. If None, clears all nodes and all UC overlays.
        """
        if node is None:
            self._slur_specs.clear()
            self._control_envelopes.clear()
            self._invalidate_bind_memo()
        else:
            affected_nodes = {node} | set(self._rt.descendants(node))
            affected_leaves = {n for n in affected_nodes if n in self._rt.leaf_nodes}
            self._split_slurs_for_rests(affected_leaves)
            self._invalidate_envelopes_for_removed_nodes(affected_nodes)
            self._invalidate_bind_memo(affected_nodes)
        
        self._rt.clear_fields(node)
    
    def get_event_parameters(self, idx: int) -> dict:
        """
        Get all parameter values for a specific event by index.
        
        Parameters
        ----------
        idx : int
            Parametron index
            
        Returns
        -------
        dict
            Dictionary of parameter field names and values
        """
        e = self[idx]
        return {'pfields': e.pfields, 'mfields': e.mfields}
    
    def from_subtree(self, node: int) -> 'CompositionalUnit':
        """
        Create a new CompositionalUnit from a subtree of this one.
        
        Preserves PT values and instrument assignments for mapped nodes.
        Preserves envelopes/slurs that are fully contained in the subtree leaf set;
        overlays crossing subtree boundaries are discarded.
        
        Parameters
        ----------
        node : int
            The root node of the subtree to extract
            
        Returns
        -------
        CompositionalUnit
            A new CompositionalUnit containing the subtree
        """
        rt_subtree = self._rt.subtree(node, renumber=True)
        new_cu = self.__class__.from_rt(rt_subtree, beat=self.beat, bpm=self.bpm, pfields=None)
        original_subtree_nodes = [node] + list(self._rt.descendants(node))
        if list(self._rt.successors(node)):
            old_to_new_mapping = self._rt.map_parallel_nodes(
                new_cu._rt,
                self_root=node,
                other_root=new_cu._rt.root,
            )
        else:
            new_leaf = list(new_cu._rt.leaf_nodes)[0]
            old_to_new_mapping = {node: new_leaf}

        for old_node, new_node in old_to_new_mapping.items():
            old_proportion = self._rt[old_node].get('proportion')
            if old_proportion is not None and old_proportion < 0:
                new_cu.make_rest(new_node)

        self._copy_pt_node_data(new_cu, old_to_new_mapping)

        subtree_node_set = set(original_subtree_nodes)
        governing_instrument_node = self._rt._resolve_governing_instrument_node(node)
        if (governing_instrument_node is not None
            and governing_instrument_node not in subtree_node_set
            and governing_instrument_node in self._rt.node_instruments):
            new_cu._rt.set_instrument(
                new_cu._rt.root,
                self._rt.node_instruments[governing_instrument_node]
            )
        self._copy_pt_instruments(new_cu, old_to_new_mapping)

        old_leaf_set = set(self._rt.subtree_leaves(node))
        for slur_id, slur_spec in self._slur_specs.items():
            slur_leaf_set = set(slur_spec['leaf_nodes'])
            if slur_leaf_set and slur_leaf_set.issubset(old_leaf_set):
                mapped = []
                for old_leaf in slur_spec['leaf_nodes']:
                    if old_leaf in old_to_new_mapping:
                        mapped.append(old_to_new_mapping[old_leaf])
                if mapped:
                    new_cu.apply_slur(node=mapped)

        subtree_node_set = set(original_subtree_nodes)
        for desc in self._control_envelopes.values():
            if desc["anchor_node"] not in subtree_node_set:
                continue
            new_anchor = old_to_new_mapping[desc["anchor_node"]]
            new_leaf_subset = None
            if desc["leaf_subset"] is not None:
                mapped_leaves = tuple(
                    old_to_new_mapping[n] for n in desc["leaf_subset"]
                    if n in old_to_new_mapping
                )
                if not mapped_leaves:
                    continue
                new_leaf_subset = mapped_leaves
            new_env_id = new_cu._next_envelope_id
            new_cu._next_envelope_id += 1
            new_cu._control_envelopes[new_env_id] = {
                "envelope": desc["envelope"],
                "pfields": list(desc["pfields"]),
                "endpoint": desc["endpoint"],
                "anchor_node": new_anchor,
                "leaf_subset": new_leaf_subset,
            }

        return new_cu
    
    def copy(self):
        """
        Create a deep copy of this CompositionalUnit.

        The copy preserves the original time signature (``tempus``),
        span, pfield / mfield data, instruments, envelopes, slurs, and
        internal placement (``_offset``) so that containers
        (``TemporalUnitSequence``, ``TemporalBlock``) and
        :class:`~klotho.thetos.composition.score.Score` can rebuild
        their layouts cleanly.

        Node ids are preserved (structural clone), so slur specs, envelope
        anchors, and instrument bindings carry over without remapping.
        Parameter values, instruments, and envelope objects are shared
        between the copy and the original; per-node override placement
        (inheritance structure) is preserved as-is.

        Returns
        -------
        CompositionalUnit
            A new CompositionalUnit with identical structure, parameters,
            instruments, envelopes, and slurs.
        """
        if type(self) is not CompositionalUnit:
            return self._copy_rebuild()
        c = CompositionalUnit.__new__(CompositionalUnit)
        c._bind_memo = {}
        c._bind_active = set()
        c._type = self._type
        c._rt = self._rt.structural_clone()
        c._real_times = {}
        c._beat = self._beat
        c._bpm = self._bpm
        c._attributed = self._attributed
        c._offset = self._offset
        c._timing_dirty = True
        # a structural clone preserves node ids, so the overlays come across
        # verbatim -- a correspondence published by an earlier mirror belongs
        # to a different tree entirely and must not be followed here
        c._slur_specs = self._copy_slur_specs(follow_mirror=False)
        c._next_slur_id = self._next_slur_id
        c._control_envelopes = self._copy_control_envelopes(follow_mirror=False)
        c._next_envelope_id = self._next_envelope_id
        c._mirror_id_map = None
        c._rt.set_id_state_observer(c._relocate_id_keyed_state)
        return c

    def _mirror_target_map(self, follow_mirror: bool):
        """The node-id correspondence published by the last mirror, if any.

        ``None`` means "carry ids verbatim", which is right for a structural
        clone (ids preserved) and wrong for a rebuild from prolatio.
        """
        return self._mirror_id_map if follow_mirror else None

    def _copy_slur_specs(self, follow_mirror: bool = True):
        """Fresh containers for slur specs, in the mirror target's ids.

        Node ids are carried verbatim unless a :meth:`_mirror_param_state`
        has just published a correspondence for the unit being rebuilt --
        the three rebuild-from-prolatio recipes call this immediately after
        mirroring, and their destination numbers its nodes differently.
        ``index_range`` needs no recomputation: the mapping is positional, so
        a mapped leaf sits at the same index in the destination.
        """
        mapping = self._mirror_target_map(follow_mirror)
        specs = {}
        for slur_id, spec in self._slur_specs.items():
            leaves = tuple(spec['leaf_nodes']) if mapping is None else tuple(
                mapping[leaf] for leaf in spec['leaf_nodes'] if leaf in mapping
            )
            if not leaves:
                continue
            specs[slur_id] = {
                'leaf_nodes': leaves,
                'leaf_set': set(leaves),
                'index_range': tuple(spec['index_range']),
            }
        return specs

    def _copy_control_envelopes(self, follow_mirror: bool = True):
        """Fresh descriptor containers, in the mirror target's ids.

        Same id contract as :meth:`_copy_slur_specs`. Envelope objects are
        shared (the production copy semantics — envelopes are treated as
        immutable)."""
        mapping = self._mirror_target_map(follow_mirror)
        descs = {}
        for env_id, desc in self._control_envelopes.items():
            anchor = desc["anchor_node"]
            subset = desc["leaf_subset"]
            if mapping is not None:
                if anchor not in mapping:
                    continue
                anchor = mapping[anchor]
                if subset is not None:
                    subset = tuple(mapping[n] for n in subset if n in mapping)
                    if not subset:
                        continue
            elif subset is not None:
                subset = tuple(subset)
            descs[env_id] = {
                "envelope": desc["envelope"],
                "pfields": list(desc["pfields"]),
                "endpoint": desc["endpoint"],
                "anchor_node": anchor,
                "leaf_subset": subset,
            }
        return descs

    def _copy_rebuild(self):
        """Legacy copy path: reconstruct from prolatio and remap node data.

        Kept for subclasses without their own ``copy()`` and as an
        equivalence oracle for the structural-clone fast path.
        """
        c = self.__class__(
            span     = self.span,
            tempus   = self.tempus,
            prolatio = self.prolationis,
            beat     = self.beat,
            bpm      = self.bpm,
        )
        old_to_new_mapping = self._rt.map_parallel_nodes(
            c._rt,
            self_root=self._rt.root,
            other_root=c._rt.root,
        )

        for old_node, new_node in old_to_new_mapping.items():
            old_proportion = self._rt[old_node].get('proportion')
            if old_proportion is not None and old_proportion < 0:
                if c._rt[new_node].get('proportion', 1) >= 0:
                    c.make_rest(new_node)

        self._copy_pt_node_data(c, old_to_new_mapping)
        self._copy_pt_instruments(c, old_to_new_mapping)

        for slur_id, spec in self._slur_specs.items():
            mapped_leaf_nodes = tuple(
                old_to_new_mapping[n]
                for n in spec['leaf_nodes']
                if n in old_to_new_mapping
            )
            if not mapped_leaf_nodes:
                continue
            c._slur_specs[slur_id] = {
                'leaf_nodes': mapped_leaf_nodes,
                'leaf_set': set(mapped_leaf_nodes),
                'index_range': tuple(c._selection_index_range(mapped_leaf_nodes)),
            }
        c._next_slur_id = self._next_slur_id

        for env_id, desc in self._control_envelopes.items():
            if desc["anchor_node"] not in old_to_new_mapping:
                continue
            mapped_leaf_subset = (
                tuple(
                    old_to_new_mapping[n]
                    for n in desc["leaf_subset"]
                    if n in old_to_new_mapping
                )
                if desc["leaf_subset"] is not None
                else None
            )
            c._control_envelopes[env_id] = {
                "envelope": desc["envelope"],
                "pfields": list(desc["pfields"]),
                "endpoint": desc["endpoint"],
                "anchor_node": old_to_new_mapping[desc["anchor_node"]],
                "leaf_subset": mapped_leaf_subset,
            }
        c._next_envelope_id = self._next_envelope_id

        c._attributed = self._attributed  # rebuild passed every slot; restore truth
        c._offset = self._offset
        c._invalidate_timing_cache()
        return c
