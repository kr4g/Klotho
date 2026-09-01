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

from typing import Union, Optional, Any, Literal, NamedTuple
from fractions import Fraction
from dataclasses import dataclass, field
from contextlib import contextmanager
import copy
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


class _BindDraw(NamedTuple):
    """One memoized :class:`Bind` evaluation, stamped with its source Bind.

    ``_bind_memo`` used to hold the drawn value alone, so a draw outlived
    the ``Bind`` that produced it. Every door that REPLACES a Bind had to
    invalidate the memo by hand, and only the public verbs did:
    ``uc.set_pfields`` calls ``_invalidate_bind_memo_subtree``, while the
    raw door ``uc._rt.set_pfields`` reaches the parameter layer directly
    and announces nothing. Measured (LAYER-15): after a raw rebind
    ``uc.events`` served ``0.9664`` and ``uc.copy().events`` served
    ``999.0`` for the same node of the same unit -- two handles disagreeing
    about the music.

    Carrying *bind* makes the memo self-validating: a draw is served only
    while the Bind it came from is still the one the tree holds, so every
    door is closed by construction rather than one override per verb.
    """

    bind: Bind
    value: Any

    def __deepcopy__(self, memo):
        """Share *bind* with the clone; deep-copy only the drawn value.

        ``GraphCore.__deepcopy__`` freshens each node's payload DICT but
        shares the objects inside it, so a deep copy of a unit holds the
        very same ``Bind`` instance its source does. The stamp has to be
        shared the same way, or every deep copy would fail its own identity
        check and silently re-roll every stochastic draw -- measured, that
        was the one regression this class introduced before this method
        existed.
        """
        return _BindDraw(self.bind, copy.deepcopy(self.value, memo))



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

        The overlays ABSORB it: the new leaves take the ex-leaf's place in
        every span it anchored, which is the single policy for every path
        (Ryan, 2026-08-30 for slurs, 2026-08-31 for control envelopes).
        There used to be an ``_owner_absorbs_leaf_growth`` flag here, set by
        ``UC.subdivide``/``UC.graft_subtree`` to SUPPRESS this seam so their
        own richer heal could absorb instead. That flag existed only because
        the seam dropped while those two verbs absorbed -- one musical
        question answered two ways depending on the handle the caller held.
        With one policy there is nothing left to suppress and the flag is
        gone.

        The marker is read by ``_relocate_id_keyed_state``: only an
        announcement from HERE may rebake a control envelope. The same
        observer is also reached mid-mutation from ``Tree.insert_child``,
        which announces its relocation BEFORE ``_post_mutation`` runs -- at
        that moment the new node has no ``metric_duration`` at all and a
        rebake dies inside ``_compute_timing_cache``. Here, ``super()`` has
        returned and the metric layer is complete.
        """
        self._announcing_leaf_surface = True
        try:
            self._notify_nodes_relocated({n: n for n in self.nodes})
        finally:
            self._announcing_leaf_surface = False

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

    def insert_child(self, parent, index, **attr):
        """Insert a child (see :meth:`Tree.insert_child`), announcing the
        leaf-surface change when *parent* was a LEAF.

        The third door, and the one that had none. Neither shipped seam
        fires for an insert into a childless leaf: the node is still in the
        tree, so DEATH's ``n not in tree`` test is false, and
        :meth:`Tree.insert_child` announces a relocation only when a sibling
        actually shifted -- an insert into a node with no children shifts
        nothing, so nothing at all was announced. The overlays went on
        naming a node that is interior now, and their markers inherited onto
        every child it grew: measured, three slur heads for one slur, and a
        slur left with a head and no tail.

        The guard used to be ``was_leaf`` alone, on the reasoning that an
        insert under a node that already had children moves siblings and the
        relocation seam reports that. MEASURED FALSE for an APPEND:
        :meth:`Tree.insert_child` announces a relocation only when a sibling
        actually shifts, and appending at ``index == len(children)`` shifts
        nothing. So the second and third of three sequential inserts under
        one node announced NOTHING, and under the absorb policy that left a
        stored slur straddling leaves no seam had ever seen -- a spec
        violating the contiguity ``apply_slur`` enforces, which is the one
        state this whole mechanism exists to prevent. Every insert announces
        now; adding a leaf anywhere changes the leaf surface.

        ``_has_node``, not ``parent in self``: ``__contains__`` is
        re-definable over a different address space by a subclass, and this
        must address nodes by index. The rule is stated on
        :meth:`~klotho.topos.graphs.core.GraphCore._has_node`.
        """
        result = super().insert_child(parent, index, **attr)
        self._announce_leaf_surface_change()
        return result

    def insert(self, index, duration):
        """Insert events into the decomposed surface (see
        :meth:`RhythmTree.insert`), announcing the leaf-surface change.

        ENV-9 part A. The preserved-family verbs rewrite the WHOLE leaf
        surface through ``_respell``, so every real onset moves -- and a
        control envelope's stored values were computed against those onsets.
        ``_respell`` does announce its id relocation, but it announces it
        mid-mutation, before the new nodes have a metric layer, and the
        rebake gate is closed there for exactly that reason: forcing a rebake
        at that moment dies inside ``_compute_timing_cache``. So the envelope
        kept values describing durations that no longer existed.

        Announcing again HERE, after ``super()`` has returned and the metric
        layer is complete, is the same three lines every other door in this
        class carries. Measured before it: a 0->1 ramp over four beats became
        ``[0.1, 0.0, 0.25, 0.5, 0.75]`` -- the inserted leaf with no envelope
        value at all, and the ramp starting after it.

        This was already incoherent with its own neighbour: subdividing a
        leaf the envelope never named rebakes correctly, while ``insert``,
        which moves every onset the envelope depends on, did not.
        """
        result = super().insert(index, duration)
        self._announce_leaf_surface_change()
        return result

    def extract(self, index):
        """Remove events from the decomposed surface (see
        :meth:`RhythmTree.extract`), announcing the leaf-surface change.

        ENV-9 part A, the other half; see :meth:`insert`. Measured before
        this: extracting the first of four beats left the ramp starting at
        ``0.25``, so the envelope never reached its own start.
        """
        result = super().extract(index)
        self._announce_leaf_surface_change()
        return result

    #: Node-data keys that define the SOUNDING and TIE surface an overlay is
    #: drawn against. A write touching one of these changes what the overlay
    #: means without moving a single id.
    _SURFACE_KEYS = frozenset({'tied', 'proportion'})

    def _announce_if_surface_write(self, keys):
        """Announce only when the write touched the sounding/tie surface.

        Every pfield and mfield write goes through the same node-data
        writers, and ``_bake_envelope`` writes through them in a loop, so
        announcing unconditionally would run the whole overlay heal on the
        hottest path in the library. Announcing on ``tied``/``proportion``
        alone costs one set intersection per write.
        """
        if self._SURFACE_KEYS.intersection(keys):
            self._announce_leaf_surface_change()

    def set_node_data(self, node, **attr):
        """Write node data (see :meth:`Tree.set_node_data`), announcing when
        the write changes the sounding or tie surface.

        ``uc._rt.set_node_data(leaf, tied=True)`` is the ONLY way to author a
        tie in this codebase, and it reproduced TIE-4 byte for byte after
        TIE-4 was closed: tying a slurred note back to its predecessor
        swallows the arc's first member into the tie group, the
        ``_slur_start`` disappears with it, and the arc reaches playback with
        an end marker and no start. ``make_rest`` and ``make_sounding`` were
        wired and this -- the door a composer actually uses -- was not.
        """
        result = super().set_node_data(node, **attr)
        self._announce_if_surface_write(attr)
        return result

    def update_node_data(self, node, attrs: dict):
        """Merge node data (see :meth:`Tree.update_node_data`), announcing a
        sounding/tie surface change. See :meth:`set_node_data`."""
        result = super().update_node_data(node, attrs)
        self._announce_if_surface_write(attrs or {})
        return result

    def replace_node_data(self, node, attrs: dict):
        """Replace node data (see :meth:`Tree.replace_node_data`), announcing
        a sounding/tie surface change.

        A REPLACE can change the surface by OMISSION -- dropping ``tied``
        where it used to be set -- so this announces whenever the surface
        keys appear on either side of the write, not only in the incoming
        dict.
        """
        before = set(self[node]) if self._has_node(node) else set()
        result = super().replace_node_data(node, attrs)
        self._announce_if_surface_write(set(attrs or {}) | before)
        return result

    def make_rest(self, node):
        """Rest a node and its subtree (see :meth:`RhythmTree.make_rest`),
        announcing the change to the TIE and REST surface.

        A FOURTH kind of event, and the first one that moves no id and kills
        no node. The leaf surface is untouched -- every leaf is still a leaf
        -- but two things an overlay is defined against did change: a leaf
        that was sounding is now silent, and ``make_rest`` clears ``tied``
        on the way down (a tied rest is illegal, charter §1), so a leaf that
        was a tie CONTINUATION has stopped being one.

        Neither was announced, and the consequence was TIE-3. ``apply_slur``
        snaps a selection onto tie-group heads, so a continuation sits in an
        arc's SPAN but never in its member set; ``_split_slurs_for_rests``
        guards on ``leaf_set.intersection(nodes_to_rest)``, which a
        continuation cannot satisfy. Measured on a four-beat unit with leaf
        3 tied to leaf 2 and a slur over 2..4: resting leaf 3 left the arc
        stored as ``(2, 4)`` with a rest at 3 sitting inside its span, drawn
        across that rest all the way to the lowering, and warned nothing.

        The heal needed no new rule. ``_remap_slur_specs`` re-derives
        leaf-ness, tie groups and rests from the tree, and
        ``_contiguous_slur_segments`` already refuses a gap leaf that is not
        a continuation of the member before it -- asked about the defective
        state above it returns ``[]``, correctly, because two one-note runs
        are not a slur. What was missing was only that anyone asked it.
        """
        result = super().make_rest(node)
        self._announce_leaf_surface_change()
        return result

    def make_sounding(self, node):
        """Un-rest a node and its subtree (see
        :meth:`RhythmTree.make_sounding`), announcing the change to the TIE
        and REST surface.

        The other half of the fourth event, and the direction that is easy
        to miss: un-resting a leaf can make the leaf AFTER it a tie
        continuation, because that leaf's ``tied`` flag was inert only while
        its predecessor was silent. TIE-4 is what follows when the newly
        swallowed leaf is an arc's FIRST member -- it stops producing an
        event at all, the ``_slur_start`` sitting on ``leaf_nodes[0]``
        vanishes with it, and ``_sc_assembly`` takes the not-a-start branch
        for every event of the arc. Measured: one ``_slur_end`` and no
        ``_slur_start`` anywhere, an arc reaching playback that no note
        opens.

        Again the rule already existed. Charter §8 makes tie groups atomic
        for slur membership and snaps a selection to the head; applying that
        same rule after the fact re-heads the arc onto the leaf that now
        carries the attack, and ``_contiguous_slur_segments`` accepts the
        result because the swallowed member is a legal gap -- it is a
        continuation of the member immediately before it.
        """
        result = super().make_sounding(node)
        self._announce_leaf_surface_change()
        return result

    def add_child(self, parent, **attr):
        """Add a child (see :meth:`Tree.add_child`), announcing the
        leaf-surface change.

        The FOURTH door, found 2026-08-31 while auditing why this class
        carries seven hand-written copies of the same three lines. Nothing
        announced here: ``add_child`` appends, so :meth:`Tree.insert_child`'s
        relocation announcement -- which fires only when a sibling actually
        shifts -- never ran, and there was no override to announce the
        leaf-surface change either. Measured on a two-note slur: three
        ``add_child`` calls on a member produced a spec still naming the now
        interior node and **three slur heads for one slur** on the lowering
        surface, byte-identical to the corruption ``LAYER-12`` was written to
        close. It reached the freed-id hazard too: the stale member survives
        until the id is reused.
        """
        result = super().add_child(parent, **attr)
        self._announce_leaf_surface_change()
        return result

    def add_subtree(self, parent, subtree, **kwargs):
        """Attach a subtree (see :meth:`Tree.add_subtree`), announcing the
        leaf-surface change.

        The FIFTH door, and the same omission: measured, a slurred leaf that
        gained a subtree kept its stale spec and showed TWO slur heads.
        """
        result = super().add_subtree(parent, subtree, **kwargs)
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
    # These overrides exist for the raw ``uc._rt.*`` path, which nothing
    # intercepted. (An earlier comment here said the unit's own deleters
    # suppressed the seam via ``_owner_absorbs_leaf_growth``; they never set
    # that flag -- only ``UC.subdivide`` and ``UC.graft_subtree`` did -- and
    # the flag no longer exists.)

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

        A memoized draw is served only while *value* is still the very Bind
        it was drawn from (see :class:`_BindDraw`). Replacing the Bind by
        any door -- including the raw ``uc._rt.set_pfields``, which
        announces nothing to this unit -- therefore retires its draw
        without a per-verb invalidation call.
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
        if not selection_bound:
            memoized = self._bind_memo.get(memo_key)
            if memoized is not None and memoized.bind is value:
                return memoized.value
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
            self._bind_memo[memo_key] = _BindDraw(value, result)
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

    def _slur_state_key(self):
        """A digest of slur MEMBERSHIP, shared by the two snapshot memos.

        DERIVED, never maintained -- and that is the whole point. The
        effective-PT snapshot used to key on
        ``(_next_slur_id, len(_slur_specs))``, which notices a membership
        change only when an id is minted or an arc appears or dies.
        SLUR-1's identity rule (an unsplit arc keeps the id ``apply_slur``
        returned) deliberately stopped minting on the commonest reshape,
        so one of those two signals went quiet -- NEW-42 filed that as a
        caution and it is load-bearing now. ``uc.events`` had NEITHER
        term, so a DataFrame read once before a slur was drawn was served
        forever afterwards and the slur columns never appeared: playback
        stayed correct while the inspection surface lied, which is the
        worse way round for a composer checking their work (EVENTS-1).

        Reading the membership itself cannot go stale. There is no counter
        for a future writer to forget to bump -- the failure mode behind
        this defect and behind PLUMB-1 alike -- and the cost is a tuple
        over the arcs, against a materialization of every event.
        """
        return tuple(sorted(
            (slur_id, tuple(spec['leaf_nodes']))
            for slur_id, spec in self._slur_specs.items()
        ))

    def _build_effective_parameter_tree(self, _fresh=False):
        """Effective PT snapshot (binds materialized, slur markers set).

        Internal callers share a snapshot memoized on (structure version,
        slur state, instrument version) — event iteration used to clone
        the whole tree per event context. ``_fresh=True`` (the public
        ``.pt`` property) always builds a new object, preserving its
        documented copy semantics for user mutation.
        """
        key = (self._rt._structure_version, self._slur_state_key(),
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
               getattr(self._rt._param_layer, '_instruments_version', 0),
               self._slur_state_key())
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
        if 'group' in kwargs:
            # ``group`` is half of the overlay identity (ruling six: the
            # scheduler re-points the out bus by group), so changing it is an
            # instrument change for an overlay's purposes and gets the same
            # treatment ``set_instrument`` gets.
            #
            # This is ``Score.track``'s own documented per-leaf routing
            # idiom, so it is not an exotic door. Measured before this line:
            # re-routing one slurred leaf to another track left ONE arc
            # spanning both, and the lowering silently played that leaf
            # through the slur head's synth on the head's track -- the
            # routing the caller asked for did not happen and nothing said
            # so, while ``_same_overlay_instrument`` already answered False
            # for the pair.
            self._resplit_overlays_at_instrument_changes()

    def _bake_envelope(self, selected, envelope, pfields_list, endpoint,
                       curve_window=None):
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
        # ``curve_window`` is the slice of the WHOLE curve these leaves
        # carry, as fractions of its normalised time. It is what makes a
        # split envelope keep its values (Ryan's ruling): each half stretches
        # the FULL curve so that its own window lands on its own leaves, then
        # samples only inside that window -- so a crescendo drawn under a
        # phrase still ramps continuously across a split, and only the
        # bookkeeping changed. Without it each half re-runs the whole curve
        # over its own sub-span, which measured [0.1, 0.3, 0.5, 0.7] turning
        # into [0.1, 0.5, 0.1, 0.5]: two hairpins where the composer drew
        # one.
        #
        # ``None`` means the whole curve, and then every line below is
        # arithmetically what it was before this parameter existed.
        window_start, window_end = curve_window or (0.0, 1.0)
        window = window_end - window_start
        if window <= 0:
            # A run one leaf wide has zero width -- ``endpoint=False`` makes
            # this ordinary. Falling back to the WHOLE curve threw away the
            # window's position as well as its width, so every such run baked
            # at the curve's first value: measured, a four-note crescendo
            # split across four instruments came out [0.0, 0.0, 0.0, 0.0],
            # entirely silent. Keep the position; borrow only the width.
            window = 1.0
        full_duration = duration / window
        raw_total = sum(envelope.times)
        scaled_envelope = Envelope(
            values=envelope.values,
            times=envelope.times,
            curve=envelope.curve,
            warp=envelope.warp,
            time_scale=full_duration / raw_total if raw_total > 0 else 1.0
        )
        window_offset = window_start * scaled_envelope.total_time
        self._invalidate_bind_memo_subtree(sounding, pfields_list)
        with self._rt.batch_writes():
            for node in sounding:
                event_time = times[node]['real_onset'] + offset
                relative_time = max(0, min(window_offset + event_time - start_time,
                                           scaled_envelope.total_time))
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
            # ``curve_window`` must ride through, or the first structural
            # edit after a split undoes the split's own value preservation
            # and each half restarts the gesture.
            self._bake_envelope(sounding, desc["envelope"], desc["pfields"],
                                desc["endpoint"],
                                curve_window=desc.get("curve_window"))
        desc["baked_leaves"] = tuple(sounding)

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

        # An envelope splits at an instrument change, exactly as a slur does
        # (Ryan, 2026-08-31) -- but it keeps its OWN constraints. There is no
        # ">= 2 targets" rule here and no split at a rest: a slur is an arc
        # over sounding notes, an envelope is a curve over a span, so a
        # one-leaf run is still a legitimate envelope.
        runs = self._partition_by_instrument(sounding)
        env_ids = []
        for run, window in zip(runs, self._curve_windows(runs, endpoint)):
            self._bake_envelope(run, envelope, pfields_list, endpoint,
                                curve_window=window)
            env_id = self._next_envelope_id
            self._next_envelope_id += 1
            run_set = set(run)
            self._control_envelopes[env_id] = {
                "envelope": envelope,
                "pfields": list(pfields_list),
                "endpoint": endpoint,
                "anchor_node": anchor_node,
                "leaf_subset": (leaf_subset if len(runs) == 1
                                else tuple(n for n in selected if n in run_set)),
                # what the baked values were computed against. A structural
                # edit rebakes ONLY when this no longer matches -- see
                # ``_queue_envelope_rebakes``.
                "baked_leaves": tuple(run),
                # the slice of the whole curve this descriptor carries, so a
                # later rebake reproduces its VALUES rather than restarting
                # the gesture. ``(0.0, 1.0)`` for an unsplit envelope.
                "curve_window": window,
            }
            env_ids.append(env_id)
        if not env_ids:
            return None
        return env_ids[0] if len(env_ids) == 1 else env_ids

    def _curve_windows(self, runs, endpoint):
        """The slice of the whole curve each run carries, in normalised time.

        Computed from the runs' real onsets, so a split reproduces exactly
        the values the unsplit envelope had: run *k* stretches the full curve
        so that its own window lands on its own leaves, and samples only
        inside it. That is what Ryan's ruling asks for -- a crescendo drawn
        under a phrase keeps ramping across the split, because splitting is
        about not sending control messages across an instrument boundary,
        not about restarting the gesture.
        """
        if len(runs) <= 1:
            return [(0.0, 1.0)] * len(runs)
        self._ensure_timing_cache()
        times = self._real_times
        offset = self._offset

        def bounds(leaves):
            start = min(times[n]['real_onset'] + offset for n in leaves)
            if endpoint:
                end = max(times[n]['real_onset'] + offset
                          + abs(times[n]['real_duration']) for n in leaves)
            else:
                end = max(times[n]['real_onset'] + offset for n in leaves)
            return start, end

        whole_start, whole_end = bounds([n for run in runs for n in run])
        total = whole_end - whole_start
        if total <= 0:
            return [(0.0, 1.0)] * len(runs)
        windows = []
        for run in runs:
            start, end = bounds(run)
            windows.append(((start - whole_start) / total,
                            (end - whole_start) / total))
        return windows

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
                # The slice of the curve THIS descriptor carries. Without it
                # the runtime sampled the whole curve per descriptor, so a
                # split envelope played one hairpin per half -- ruling seven
                # violated in the only path that makes a sound, while the
                # baked pfields (what ``uc.events`` shows) looked correct.
                "curve_window": desc.get("curve_window") or (0.0, 1.0),
            })
        return result

    def remove_envelope(self, env_id) -> None:
        """
        Remove a previously-applied control envelope by handle.

        The baked pfield values written by this envelope are unset so that
        each affected leaf falls back to its inherited (parent/instrument)
        default. Only control-mode envelopes allocate handles; bake-mode
        envelopes are one-shot writes with no state to remove.

        Parameters
        ----------
        env_id : int or iterable of int
            The identifier returned by ``apply_envelope(..., control=True)``.
            A LIST is accepted because ``apply_envelope`` returns one when the
            selection crosses an instrument change and the envelope splits:
            the documented round trip -- keep the handle, remove it later --
            has to keep working when the split happens, and a caller cannot
            be expected to know in advance whether their span crosses a
            change. Removing a list removes every part of that one gesture.

        Raises
        ------
        KeyError
            If ``env_id`` is not a live envelope handle on this UC.
        """
        if isinstance(env_id, (list, tuple, set, frozenset)):
            for one in list(env_id):
                self.remove_envelope(one)
            return
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
            Target parameter field(s). Overlap is allowed across different
            fields. Two overlapping spans on the SAME field are rejected only
            when ``control=True``; with ``control=False`` the later
            application simply overwrites the earlier one. That asymmetry is
            deliberate: a baked envelope writes its values once and is done,
            so two of them resolve last-write-wins, which is well defined.
            Two CONTROL envelopes on one field and span are two live signals
            driving one parameter, which is not.
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
        int | list[int] | None
            With ``control=True``: the envelope identifier, or a list of them
            when ``scope="per_node"`` (per-node scope always returns a list).
            With ``control=False`` (the default) the envelope is baked into
            the pfield values and there is no identifier to hand back, so the
            return is ``None``.

        Raises
        ------
        ValueError
            If the selection is invalid or non-contiguous, ``offset``/``take``
            overflows the bounds, ``scope`` is invalid, or -- **only when
            ``control=True``** -- a same-pfield overlap is detected.
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

    def _same_overlay_instrument(self, a, b):
        """Whether two leaves count as the same instrument for an OVERLAY.

        Ryan, 2026-08-31: *"Slurs only make sense across the same
        instrument. Same with control envs."* This is the predicate that
        sentence needs, and it reuses the ties charter's own rather than
        inventing a second definition of "same instrument":
        ``_tie_instruments_join`` is §5's ``instrument_key`` component,
        already implemented for tie joining, with all of its normalisation
        (UNBOUND is its own kind and never silently the default synth;
        strings by canonical def name; instances by identity, else equality
        AND equal ``defName``, because bare ``==`` is defName-blind).

        Plus ``group``, and only plus ``group``. The rest of §5's composite
        key is deliberately out, measured rather than assumed:

        * ``kit_voice_key`` differs between consecutive leaves of a rotating
          family BY CONSTRUCTION -- §5 says so -- so reusing it would
          shatter every slur over a kit passage into single-note runs, and a
          run under two members dissolves. Measured, the lowering already
          sounds that same passage as ONE synth with no warning.
        * ``voice_count`` would split a slur running from a single note into
          a double stop, which is ordinary notation. A tie needs matching
          arity because it MERGES two notes into one sound; a slur merges
          nothing, and the lowering already expands every event in an arc to
          the group maximum so the voice count never changes mid-slur.

        ``group`` stays in for the reason §5 puts it there: the scheduler
        re-points the out bus by group, and a slur additionally pools voices
        at lowering, so a cross-track slur carries the hazard a cross-track
        tie carries.

        Comparison is always on the RESOLVED walk, never on binding
        presence -- adjacent leaves routinely agree purely by inheritance.
        """
        # deferred, matching this package's idiom for reaching into
        # utils.playback: _sc_assembly imports thetos.instruments at module
        # scope, so a top-level import here would close the cycle.
        from klotho.utils.playback._sc_assembly import _tie_instruments_join
        if not _tie_instruments_join(self.get_instrument(a),
                                     self.get_instrument(b)):
            return False
        return self.get_mfield(a, 'group') == self.get_mfield(b, 'group')

    def _partition_by_instrument(self, leaves):
        """Split a run of leaves wherever the instrument or the track changes.

        Each leaf is compared against its RUN'S HEAD rather than its
        neighbour, matching the shape ``_tie_join_reason`` uses for a tie
        group: the head is what the run is, so it is what a candidate has to
        match.
        """
        runs = []
        current = []
        for leaf in leaves:
            if current and not self._same_overlay_instrument(current[0], leaf):
                runs.append(current)
                current = [leaf]
            else:
                current.append(leaf)
        if current:
            runs.append(current)
        return runs

    def _split_segments_at_instrument_changes(self, segments):
        """Apply the instrument split to already-rest-partitioned runs.

        A slur needs at least two adjacent sounding leaves, so a run left
        alone on one instrument is not a slur and is dropped here -- exactly
        as ``_partition_non_rest_segments`` drops a run of one beside a rest.
        """
        out = []
        for segment in segments:
            for run in self._partition_by_instrument(list(segment)):
                if len(run) >= 2:
                    out.append(tuple(run))
        return out

    def _refuse_slur_with_no_run(self, selected, rest_set):
        """Say why, when the reason is an instrument change.

        Ryan, 2026-08-31: *"we can certainly have 'sorry, you can't do that'
        warnings/errors where appropriate. We don't need to accommodate
        every application, especially when it doesnt make sense."* A caller
        who asked for a slur and got no slur is owed the reason, and the
        instrument case is the one where the reason is NOT guessable from
        the selection: every note is sounding, they are adjacent, and the
        thing that refused them is invisible in the argument list.

        The all-rest case keeps its shipped contract and returns an empty
        list. That silence is arguably wrong too -- the caller is equally
        empty-handed -- but it is a shipped, tested behaviour on a different
        question, and widening a ruling about instruments into a contract
        change about rests is how scope creeps. Filed rather than fixed.
        """
        sounding = [n for n in selected if n not in rest_set]
        if len(self._partition_by_instrument(sounding)) > 1:
            raise ValueError(
                "Slur selection crosses an instrument change and leaves no "
                "run of two or more adjacent notes on one instrument. A slur "
                "only means something within one instrument on one track.")

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

        Notes
        -----
        **A slur survives later edits by ABSORBING them.** If a slurred leaf
        grows children -- through ``subdivide``, ``graft_subtree``,
        ``insert_child``, ``move_subtree``, or the same verbs reached through
        ``uc._rt`` -- those children take its place in the arc. A rest among
        them splits the arc into the runs either side of it, and a run left
        with fewer than two adjacent sounding leaves dissolves with a
        ``RuntimeWarning``. A note inserted among music the arc does NOT
        already cover is an intruder and splits it: a slur is authored by
        explicit selection, never by an edit landing nearby.

        There is no bound on how far an arc can grow this way. A three-note
        slur under a forty-leaf graft becomes a forty-two-note slur, without
        a warning -- a slur is a phrase marking, not a size contract.

        **Growing a leaf in one step and in several steps may give different
        arcs**, and this is deliberate rather than a rounding error. Each
        edit heals against the music that exists at that moment, which is the
        honest reading of an incremental API. Measured on a four-note slur
        whose second note grows three children, the middle one a rest::

            uc.subdivide(n, (1, -1, 1))          -> two arcs, the second
                                                    covering the third child
            three separate insert_child calls    -> two arcs, the second NOT
                                                    covering the third child

        The third child differs because in the stepwise form the rest has
        already split the arc by the time it arrives, so it is no longer
        landing inside music the arc covers. Nothing batches edits to hide
        this.

        See Also
        --------
        make_rest : splits any slur it silences, by the same rule.
        """
        if mode == "span":
            selected = self._resolve_leaf_selection(node=node)
            selected = self._apply_offset_take(selected, offset=offset, take=take)
            selected = self._snap_to_tie_heads(selected)
            if len(selected) < 2:
                raise ValueError("Slur requires at least two leaves")
            rest_set = {n for n in selected if self._rt[n].get('proportion', 1) < 0}
            segments = self._split_segments_at_instrument_changes(
                self._partition_non_rest_segments(selected, rest_set))
            if not segments:
                self._refuse_slur_with_no_run(selected, rest_set)
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
            # PLANNED WHOLE, INSTALLED AT THE END, for the reason
            # ``_reshape_slur`` states and this branch used to ignore: a
            # refusal partway through must not leave arcs registered under
            # ids the caller never received. Measured before this: a
            # per-node call over two groups, the second crossing an
            # instrument change, raised -- and left ``{0: (2, 3)}`` behind
            # with ``_next_slur_id`` advanced. The composer's call failed, so
            # they reasonably believe nothing happened, while those notes are
            # silently pooled into a legato they cannot name to remove.
            #
            # ``_validate_slur_segment`` already checks each candidate
            # against both the live specs and the segments reserved earlier
            # in this same call, so planning changes nothing about which
            # selections are legal -- only about what survives a refusal.
            planned = []
            reserved_sets = []
            for group in groups:
                selected = self._apply_offset_take(group, offset=offset, take=take)
                selected = self._snap_to_tie_heads(selected)
                rest_set = {n for n in selected if self._rt[n].get('proportion', 1) < 0}
                segments = self._split_segments_at_instrument_changes(
                    self._partition_non_rest_segments(selected, rest_set))
                if not segments:
                    self._refuse_slur_with_no_run(selected, rest_set)
                for segment in segments:
                    self._validate_slur_segment(segment, reserved_sets)
                    reserved_sets.append(set(segment))
                    planned.append(segment)
            return [self._register_slur(segment) for segment in planned]
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

    def _reshape_slur(self, slur_id, segments):
        """Install the segments one arc became, under ONE identity rule.

        The first surviving segment keeps the id ``apply_slur`` returned;
        only genuine fragments mint. That is the rule ``_remap_slur_specs``
        applies, and these two pre-heals used to contradict it -- they
        deleted the spec and re-registered every segment, so an arc that
        merely lost a member came back under a NEW id through
        ``uc.prune``/``uc.remove_subtree`` while the identical edit through
        ``uc._rt.prune`` preserved it. ``_slur_id`` is not internal:
        ``apply_slur`` returns it, it is a column of ``uc.events``, and the
        lowering keys voice pooling and slur teardown on it, so a caller
        holding the documented handle simply lost the arc.

        Computed whole, installed at the end, for the same reason the seam
        is: a refusal partway through must not leave a half-rewritten spec
        under an id the caller never saw (SLUR-A1).
        """
        rebuilt = {}
        next_id = self._next_slur_id
        for i, segment in enumerate(segments):
            if i == 0:
                new_id = slur_id
            else:
                new_id = next_id
                next_id += 1
            rebuilt[new_id] = {
                'leaf_nodes': tuple(segment),
                'leaf_set': set(segment),
                'index_range': tuple(self._selection_index_range(segment)),
            }
        del self._slur_specs[slur_id]
        self._slur_specs.update(rebuilt)
        self._next_slur_id = next_id
        if not segments:
            warnings.warn(
                "Slur removed: fewer than two adjacent sounding leaves remain",
                RuntimeWarning, stacklevel=4
            )

    def _resplit_overlays_at_instrument_changes(self):
        """Re-apply the instrument split to every live overlay.

        The THIRD enforcement site, and the one that is not optional. Ryan's
        ruling says an overlay splits at an instrument change; authoring and
        the structural heal between them do not deliver that, because
        ``set_instrument`` changes the instrument without touching the
        structure. Measured before this existed: binding a mid-arc leaf to a
        different synth bumped ``_instruments_version``, ran no heal, and
        left the arc spanning two instruments -- so an arc drawn before the
        binding quietly kept a shape the ruling forbids, and the mid-slur
        warning at lowering stayed reachable.

        The accepted cost, stated plainly because a caller meets it:
        ``set_instrument`` can now rewrite a slur the caller is holding, and
        mint an id they never saw. That is the trade Ryan took over leaving
        the hole open.

        An envelope's halves are NOT rebaked. Their values are already on
        the leaves and each half inherits its own slice of the parent's
        curve window, so the split changes bookkeeping and nothing audible
        -- which is the ruling for envelopes.
        """
        # ``set_instrument`` runs during ``__init__``, before either overlay
        # store exists, and it is hot enough that the common case -- a unit
        # with no overlays at all -- should cost one attribute lookup.
        slur_specs = getattr(self, '_slur_specs', None)
        control_envelopes = getattr(self, '_control_envelopes', None)
        if not slur_specs and not control_envelopes:
            return
        for slur_id, spec in list((slur_specs or {}).items()):
            members = list(spec['leaf_nodes'])
            runs = self._partition_by_instrument(members)
            if len(runs) <= 1:
                continue
            self._reshape_slur(slur_id, [tuple(run) for run in runs
                                         if len(run) >= 2])

        for env_id, desc in list((control_envelopes or {}).items()):
            self._split_envelope_at_instrument_changes(env_id, desc)

    def _split_envelope_at_instrument_changes(self, env_id, desc):
        """Split one control envelope wherever its leaves change instrument.

        Shared by ``set_instrument`` and the structural heal, so the two
        cannot drift into answering the same musical question differently --
        the failure this whole area exists to remove.

        The halves are NOT rebaked. Their values are already on the leaves,
        and each half inherits its own slice of the parent's curve window, so
        the split changes bookkeeping and nothing audible. That is Ryan's
        ruling for envelopes: splitting keeps control messages inside one
        instrument, it does not restart the gesture.
        """
        resolved = self._resolve_control_envelope_leaves(desc)
        runs = self._partition_by_instrument(resolved)
        if len(runs) <= 1:
            return
        start, end = desc.get("curve_window") or (0.0, 1.0)
        width = end - start
        del self._control_envelopes[env_id]
        for run, (inner_start, inner_end) in zip(
                runs, self._curve_windows(runs, desc["endpoint"])):
            new_id = env_id if run is runs[0] else self._next_envelope_id
            if run is not runs[0]:
                self._next_envelope_id += 1
            self._control_envelopes[new_id] = {
                **desc,
                "leaf_subset": tuple(run),
                "baked_leaves": tuple(run),
                "curve_window": (start + inner_start * width,
                                 start + inner_end * width),
            }

    def _split_slurs_for_rests(self, nodes_to_rest: set[int]):
        for slur_id, spec in list(self._slur_specs.items()):
            if not spec['leaf_set'].intersection(nodes_to_rest):
                continue
            segments = self._partition_non_rest_segments(
                list(spec['leaf_nodes']), nodes_to_rest)
            self._reshape_slur(slur_id, segments)

    def _invalidate_slurs_for_removed_nodes(self, removed_set):
        for slur_id, spec in list(self._slur_specs.items()):
            if not spec['leaf_set'].intersection(removed_set):
                continue
            remaining = [n for n in spec['leaf_nodes'] if n not in removed_set]
            rest_set = {n for n in remaining
                        if self._rt[n].get('proportion', 1) < 0}
            segments = self._partition_non_rest_segments(remaining, rest_set)
            self._reshape_slur(slur_id, segments)

    # ``_heal_slurs_after_subdivide`` and ``_heal_envelopes_after_subdivide``
    # lived here. They were the ABSORB implementation, reachable from exactly
    # two verbs; the seam now absorbs on every path, so they became dead the
    # moment ``_owner_absorbs_leaf_growth`` went. Their logic is not lost --
    # it is in ``_remap_slur_specs`` and ``_remap_control_envelopes``, with
    # the five amendments the originals lacked (tie-head snapping, a
    # foreign-slur split point, dedupe, time ordering, and an atomic rewrite).

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

        Overlays are MOVED here, and a control envelope is additionally
        REBAKED -- but only when the leaf-surface announcement is what
        reached this function, and only when the edit actually changed the
        leaves that envelope resolves to. ``_queue_envelope_rebakes`` holds
        both gates and explains them.

        (This docstring used to say overlays are never rebaked, "because
        re-resolving them here would read a timing cache the mutation has
        not finished invalidating". Both halves were wrong. The cache keying
        is correct -- ``_ensure_timing_cache`` tests
        ``_timing_cache_version != _rt._structure_version`` -- and the real
        hazard is that this same observer is ALSO reached mid-mutation, from
        ``Tree.insert_child`` before ``_post_mutation`` runs and from
        ``RhythmTree._respell`` before it writes node data.
        At those two moments the new nodes have no metric layer at all and a
        rebake dies inside ``_compute_timing_cache``. That is what the
        announcement gate is for.)
        """
        self._remap_bind_memo(mapping)
        self._remap_slur_specs(mapping)
        self._remap_control_envelopes(mapping)
        # The slur half splits at an instrument change inside its own
        # segmentation, where identity and ordering are settled together.
        # The envelope half has no such segmentation -- it is a curve over a
        # span, not an arc over notes -- so it splits here, through the SAME
        # method ``set_instrument`` uses. One implementation, because two
        # would be two answers to one musical question.
        for env_id, desc in list(self._control_envelopes.items()):
            self._split_envelope_at_instrument_changes(env_id, desc)
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
        """Follow every slur through a structural edit, ABSORBING growth.

        Ryan's ruling, 2026-08-30: *"if I subdivide a leaf inside a slur
        group, the subdivisions also participate in the slur. If those
        subdivs include a rest, we split the slur. Slurs must connect at
        least two adjacent leaves."* So a member that survived the edit but
        stopped being a leaf hands its place to the leaves it grew, rather
        than being dropped -- which is what this function used to do, and
        what made the raw tree and the owning unit answer one musical
        question two different ways.

        The whole rewrite is computed into a fresh dict and installed at the
        end. That is not tidiness: the old code deleted a spec before
        re-registering its segments, so a mid-heal refusal left the slur
        simply gone, or half-rewritten under an id the caller never saw
        (SLUR-A1). Nothing here can raise, and nothing is visible until all
        of it is.
        """
        if not self._slur_specs:
            return
        leaf_order = list(self._rt.leaf_nodes)
        leaf_index = {leaf: i for i, leaf in enumerate(leaf_order)}
        current_leaves = set(leaf_order)

        # PASS 1 -- resolve members. Absence from the mapping is death;
        # a survivor that is no longer a leaf is absorbed into what it grew.
        resolved = {}
        held = {}
        for slur_id, spec in self._slur_specs.items():
            members = []
            for leaf in spec['leaf_nodes']:
                target = mapping.get(leaf)
                if target is None:
                    continue
                if target in current_leaves:
                    members.append(target)
                    held[target] = slur_id
                else:
                    members.extend(self._rt.subtree_leaves(target))
            resolved[slur_id] = members

        # PASS 2 -- shape each member list into spans ``apply_slur`` could
        # have authored, then install. ``held`` is complete before any of
        # this runs, which is what lets a foreign claim act as a split point.
        rebuilt = {}
        dissolved = 0
        next_id = self._next_slur_id
        for slur_id, members in resolved.items():
            # a leaf another slur still holds DIRECTLY is a split point, not
            # a member and not an error (SLUR-A1). Absorbing an ancestor's
            # span must never swallow a slur drawn inside it: the deeper,
            # more specific arc keeps its notes.
            def mine(node):
                """False for a leaf another slur still holds directly.

                One definition, used at both points where a node can enter
                this arc: the member expansion below, and again after tie
                snapping, which can fold a member onto a head a different
                slur owns. Two hand-written copies of this test would let a
                later reader delete one and measure no change.
                """
                return held.get(node, slur_id) == slur_id

            kept, seen = [], set()
            for node in members:
                if not mine(node) or node in seen:
                    continue
                seen.add(node)
                kept.append(node)
            # TIME order, not splice order: the effective-PT build marks
            # ``leaf_nodes[0]`` and ``leaf_nodes[-1]``, so a spec stored out
            # of order puts the arc's markers on the wrong notes (SLUR-A3).
            kept = self._absorb_leaves_grown_inside(
                [n for n in kept if n in leaf_index], leaf_index)
            # Tie groups are atomic for slur membership (07_TIES_CHARTER
            # sect 8): a continuation is part of the head's sound and can
            # never be a member. ``apply_slur`` snaps; this heal never did,
            # so a graft could register a continuation and even land
            # ``_slur_end`` on it (SLUR-A4).
            #
            # This runs AFTER the grown-inside pass, not before. Subdividing
            # a tie continuation MAKES a new continuation -- the first child
            # inherits the tie -- so snapping first leaves a fresh
            # continuation to be absorbed as an ordinary member by the very
            # next step. Measured while writing this: the arc came back as
            # (2, 7, 8, 4) with 7 a continuation of member 2.
            kept = [n for n in self._snap_to_tie_heads(kept)
                    if n in leaf_index and mine(n)]
            kept.sort(key=leaf_index.__getitem__)

            rest_set = {n for n in kept
                        if self._rt[n].get('proportion', 1) < 0}
            segments = []
            # ...and split at an instrument change, the third site Ruling B
            # names. Growth inherits its parent's instrument, so absorb
            # cannot itself mix two -- but ``move_subtree`` and
            # ``graft_subtree`` carry bindings in with them. Measured before
            # this line: moving a ``kl_tri`` leaf into a ``kl_saw`` arc left
            # the arc stored across both.
            for run in self._partition_non_rest_segments(kept, rest_set):
                for piece in self._contiguous_slur_segments(list(run)):
                    segments.extend(
                        self._split_segments_at_instrument_changes([piece]))

            for i, segment in enumerate(segments):
                if i == 0:
                    new_id = slur_id      # an unsplit slur keeps its identity
                else:
                    new_id = next_id
                    next_id += 1
                rebuilt[new_id] = {
                    'leaf_nodes': tuple(segment),
                    'leaf_set': set(segment),
                    'index_range': tuple(self._selection_index_range(segment)),
                }
            if not segments:
                dissolved += 1

        self._slur_specs = rebuilt
        self._next_slur_id = next_id
        if dissolved:
            # the envelope half has warned on the identical death since it
            # was written; the slur half died silently (SLUR-B1)
            warnings.warn(
                f"Slur removed: fewer than two adjacent sounding leaves "
                f"remain ({dissolved} slur{'s' if dissolved > 1 else ''})",
                RuntimeWarning, stacklevel=3
            )

    def _absorb_leaves_grown_inside(self, members, leaf_index):
        """Take in a leaf that appeared INSIDE music this overlay covers.

        Used by BOTH overlays. The arc language below is written for slurs
        because that is where the rule was derived, but a control envelope
        needs exactly the same thing and for the same reason: without it the
        two heal one edit differently and the envelope is left with a hole
        in its ramp.

        Ryan made R12 the tie-breaker for the remaining edge cases on
        2026-08-31: where two readings are defensible, take the one a
        composer would guess. Two cases need it, and one rule answers both.

        A tie CONTINUATION is not a note, it is the tail of the head's
        sound, so it is never a member (charter sect 8) and growth under it
        is invisible to a rule keyed on membership. Subdivide a tied-over
        half note inside a slur and every player reads the first half as
        still tied and the second as a new note UNDER THE SAME SLUR -- a
        slur breaks at a rest or where the composer lifts it, not because
        someone shortened a note underneath it. Without this the arc
        dissolved (SLUR-B4).

        The second case is sequential growth: after the first of three
        inserts under a slurred note, the ex-leaf is no longer a member, so
        inserts two and three would land as intruders and split the arc that
        one ``subdivide`` keeps whole (SLUR-A5). Ryan ruled that sequential
        and one-shot growth MAY diverge and must not be hidden by batching
        edits -- this is not batching. Each edit still heals against what
        exists at that moment; the rule simply reads what the new leaf IS.

        The test is provenance, not proximity: every OTHER leaf under the
        newcomer's parent must already belong to this overlay, as a member
        or as a tie continuation of one, and the newcomer must fall strictly
        INSIDE the span. So a note inserted beside music the overlay does
        not already cover is still an intruder and still splits, which is
        the property ``_remap_slur_specs`` has always defended -- a slur is
        authored by explicit selection, never by an edit landing nearby.

        **Rests are skipped in the sibling scan, and that is load-bearing.**
        A rest can NEVER be a member: ``apply_slur`` partitions them out and
        this remapper strips them again at the end. So requiring a rest
        sibling to be covered is a test nothing can pass, and it disabled
        absorption permanently under any parent holding one. Measured, the
        cost was not merely a missed absorption: the newcomer then read as
        an intruder, the arc split into two one-note runs, and BOTH were
        discarded -- a rest sitting OUTSIDE the arc entirely destroyed a
        slur the composer had authored. Rests are handled correctly further
        down, where one among the members splits the arc.

        **There is no exemption for the root, and that is also deliberate.**
        An earlier version skipped ``parent is root`` on the reasoning that
        top-level beats are the piece itself. Measured, that made the answer
        depend on an invisible structural detail rather than on the music:
        ``prolatio=(1,1,1,1)`` and ``prolatio=((4,(1,1,1,1)),)`` are the same
        four beats with identical onsets and durations, and the same edit
        absorbed under the wrapper and split the arc in two under the flat
        tree. One musical question, two answers, decided by where the
        brackets happened to fall -- which is the exact failure this whole
        chunk exists to remove.
        """
        if len(members) < 2:
            return members
        head_of = {}
        for group in self._rt.tie_groups:
            for continuation in group[1:]:
                head_of[continuation] = group[0]
        # min/max, not first/last: the caller has not normalised order yet,
        # and this must not become a second place that guarantees it. Time
        # ordering is settled at ONE point, after tie snapping.
        current = list(members)
        # EVERY leaf is a candidate, and the positional window that used to
        # stand here is gone. It restricted the scan to ``low < i < high``
        # over the members' own positions -- so growth at the FIRST member
        # arrived before ``low`` and growth at the LAST arrived after
        # ``high``, and neither could ever be seen. Measured on a two-note
        # slur whose last member grew three children: ``uc.subdivide`` gave
        # the whole growth, three ``add_child`` calls gave one leaf of three,
        # and the arc's ``_slur_end`` moved from t=2.667 to t=2.0 -- the
        # legato releasing two thirds of a beat early with two sounding
        # leaves left outside the arc.
        #
        # It was never the rule. Provenance is, and the geometry contradicted
        # a principle this file's own tests already state by name: the tail
        # EXTENDS, it does not retreat. A window that silently narrows a
        # correctness rule to buy speed is the wrong trade, so the speed is
        # bought below instead, where it costs no meaning.
        # ONE pass, judged against the arc as it stood when the edit arrived.
        #
        # This used to iterate to a fixpoint, re-judging each round against
        # the leaves it had just absorbed, and that is what let an OUTSIDER
        # in. Measured on a four-beat unit with the arc on beats 2-3 and
        # beat 3 grown: round one correctly refuses beat 1, because a leaf
        # of the growth is not covered yet; round two absorbs that leaf, and
        # now every other leaf under the root IS covered, so beat 1 -- a
        # note the composer looked at and did not select -- joins the arc.
        # The arc ate the music it was drawn to exclude.
        #
        # A single pass is also the honest reading of the rule. Growth UNDER
        # a member is not this function's job at all: pass 1 above already
        # expands a member that stopped being a leaf into everything it
        # grew, however many leaves that is. What is left for this pass is
        # the sequential case -- one new leaf arriving beside music the arc
        # already covers, one announcement at a time -- so a second round
        # can only ever be answering a question no edit asked.
        covered = set(current)
        positions = [leaf_index[n] for n in current]
        low, high = min(positions), max(positions)
        # STRICTLY INSIDE THE SPAN, and the attempt to widen this is worth
        # recording because it produced a worse defect than the one it fixed.
        #
        # The window is genuinely wrong at the EDGES: growth under the first
        # member lands before ``low`` and under the last after ``high``, so
        # stepwise edge growth keeps only the first child of what the member
        # grew and the legato releases early. That is a real defect and it is
        # filed (ABSORB-1), with its pins marked xfail rather than deleted.
        #
        # It was fixed here by also admitting a candidate whose parent was
        # "a node the arc reaches into without lying wholly within"
        # (``0 < held < len(covered)``). MEASURED, that predicate does not
        # mean what it says: it is true of the parent of ANY edge member of
        # ANY arc in a nested tree. Combined with the sibling test -- vacuous
        # whenever that parent has exactly one uncovered sounding leaf -- an
        # arc whose edge sits inside an eighth-note pair swallowed the other
        # eighth, triggered by a structural edit ANYWHERE in the unit,
        # including at the far end of the bar. A fuzz over disjoint edits gave
        # 645 over-admissions in 2296 cases where the shipped code gave none,
        # and the envelope half made it audible: a note the composer never
        # named driven to amp 0.0, i.e. silent.
        #
        # The two defects are NOT symmetrical. Refusing growth loses an
        # extension a composer can re-apply; admitting an outsider silently
        # rewrites music they did select, and no oracle here catches it --
        # ``slur_contract_violations`` returns clean for a widened arc,
        # because a widened arc is still contiguous, ordered and authorable.
        #
        # And the discriminator is genuinely NEWNESS, not shape: in the
        # append case the admitted leaf is new, in the failing case it is a
        # leaf the composer looked at and did not select, and the two are
        # structurally identical. Newness is not derivable here -- the
        # announcement passes an identity mapping over the post-edit nodes --
        # so closing ABSORB-1 means giving the seam the pre-edit leaf
        # surface, which is a contract change and belongs to its own chunk.
        newcomers = []
        # ``subtree_leaves`` memoized per parent: the scan is over every
        # leaf, but a parent's leaves are walked once, which is what the
        # positional window was really paying for.
        sounding_under = {}
        for leaf, i in leaf_index.items():
            if leaf in covered:
                continue
            parent = self._rt.parent(leaf)
            if parent is None:
                continue
            if not low < i < high:
                continue
            siblings = sounding_under.get(parent)
            if siblings is None:
                siblings = [n for n in self._rt.subtree_leaves(parent)
                            if self._rt[n].get('proportion', 1) >= 0]
                sounding_under[parent] = siblings
            others = [n for n in siblings if n != leaf]
            if not others:
                continue
            if all(n in covered or head_of.get(n) in covered
                   for n in others):
                newcomers.append(leaf)
        return current + newcomers

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
        """Follow every control envelope through a structural edit.

        Ryan, 2026-08-31, asked whether control envelopes should absorb the
        way slurs now do: *"Yes. The overall theme here is 'common sense'
        and 'reasonable expectations'."* So a target that stopped being a
        leaf hands its place to the leaves it grew, exactly as a slur member
        does.

        Absorption is the ONLY rule shared with slurs. An envelope is a
        curve over a SPAN, not an arc over sounding notes: it does not split
        at a rest, and one surviving target does not dissolve it. Those are
        properties of a slur, derived from what a slur IS, and copying them
        across by symmetry would be a different feature wearing this one's
        clothes.
        """
        if not self._control_envelopes:
            return
        leaf_index = {leaf: i for i, leaf in enumerate(self._rt.leaf_nodes)}
        touched = []
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
            # ``baked_leaves`` records which leaves the STORED VALUES were
            # computed for, and the gate in ``_queue_envelope_rebakes``
            # compares it against the leaves the envelope resolves to now.
            # It has to move with the ids or the gate is comparing two
            # different address spaces and can only ever answer "changed" --
            # measured: an ``insert_child`` at the top of the bar re-asserted
            # an envelope over a span it never touched, reverting the user's
            # own later ``set_pfields`` and flattening a stored ``Bind`` to
            # the float it happened to evaluate to. That is both halves of
            # the regression ``784a3b5`` fixed, alive through the relocation
            # door that commit never covered, and it breaks ENV-6's promise
            # that a later write wins.
            #
            # Ids ONLY, never expanded through growth: a baked leaf that grew
            # children SHOULD read as changed, because the values genuinely no
            # longer cover what the envelope now spans. The remap removes the
            # FALSE positives and keeps every true one.
            #
            # A DEATH is a true positive and needs saying explicitly. Simply
            # dropping the dead id was the first version here, and measured,
            # it made the gate MATCH: ``extract`` killed a leaf, the survivors
            # remapped one-to-one, and baked equalled resolved -- so an
            # envelope whose span had just lost a note read as untouched and
            # kept every value it had computed for the longer span. The
            # values were computed for a set that no longer exists, so the
            # descriptor reads as stale, and ``None`` is the one thing no
            # resolved tuple can equal.
            baked = desc.get("baked_leaves") or ()
            desc["baked_leaves"] = (
                None if any(n not in mapping for n in baked)
                else tuple(mapping[n] for n in baked)
            )
            if desc["leaf_subset"] is None:
                # anchor-based: targets are re-derived from the subtree on
                # every resolve, so membership needs no repair -- but the
                # BAKED values do, and only the UC verbs used to rebake them
                touched.append(desc)
                continue
            moved, seen = [], set()
            for n in desc["leaf_subset"]:
                target = mapping.get(n)
                if target is None:
                    continue
                grown = ((target,) if target in leaf_index
                         else tuple(self._rt.subtree_leaves(target)))
                for g in grown:
                    if g in leaf_index and g not in seen:
                        seen.add(g)
                        moved.append(g)
            if not moved:
                warnings.warn(
                    "Control envelope removed: all target leaves were destroyed",
                    RuntimeWarning, stacklevel=3
                )
                del self._control_envelopes[env_id]
                continue
            # time order, so the stored subset reads as the span it is
            moved.sort(key=leaf_index.__getitem__)
            # ...and the SAME grown-inside rule the slur half uses. Without
            # it the two overlays heal one edit differently: measured, after
            # two sequential inserts under a shared target the slur read
            # (1, 2, 6, 7, 4) and the subset read (1, 2, 6, 4), leaving leaf
            # 7 -- a sounding leaf strictly inside the envelope's span --
            # with NO value for the pfield the envelope controls. A hole in
            # the ramp, and a stored subset with a positional gap that
            # ``apply_envelope`` refuses to author ("Selection must be
            # contiguous in left-to-right tree order").
            #
            # Ryan ruled that sequential and one-shot growth may diverge. He
            # did not rule that two overlays may heal the same edit
            # differently, and neither reading licenses an unauthorable spec.
            moved = self._absorb_leaves_grown_inside(moved, leaf_index)
            # the helper appends newcomers, so time order is settled HERE,
            # after it -- exactly as the slur half settles it after snapping
            moved.sort(key=leaf_index.__getitem__)
            desc["leaf_subset"] = tuple(moved)
            touched.append(desc)
        if touched:
            self._queue_envelope_rebakes(touched)

    def _queue_envelope_rebakes(self, descriptors):
        """Rebake now, or after the caller's last node-data write.

        A rebake WRITES pfields. ``UC.subdivide`` copies the ex-leaf's
        pfields onto every new child AFTER the structural edit -- i.e. after
        this seam has already run -- so a rebake here would be overwritten
        by that copy and the envelope would silently flatten. The unit's own
        verbs therefore hold the rebake open until they have finished
        writing; a raw ``uc._rt.*`` edit has no such tail and rebakes at
        once.

        Rebaking is gated on the leaf-surface announcement. The same
        observer is reached mid-mutation from :meth:`Tree.insert_child`,
        which announces BEFORE ``_post_mutation`` has written
        ``metric_duration`` for the new node -- a rebake there dies inside
        ``_compute_timing_cache``. (``_relocate_id_keyed_state`` used to
        blame a stale timing cache for this; measured, the cache keying is
        correct -- it tests ``_timing_cache_version != _structure_version``
        -- and the real hazard is the missing metric layer at that other
        seam.)
        """
        if not getattr(self._rt, '_announcing_leaf_surface', False):
            return
        # ONLY the envelopes this edit actually changed. Queueing every
        # surviving descriptor was measured to re-assert every envelope in
        # the unit on ANY structural edit anywhere -- which silently
        # overwrote a later ``control=False`` envelope on the same pfield
        # (Ryan's ENV-6 ruling promises those resolve last-write-wins) and
        # replaced a ``Bind`` stored inside the span with a scalar, so the
        # callable never ran again. Before this seam rebaked at all, an edit
        # outside an envelope's span could not touch its values; that
        # property is restored here rather than traded away.
        descriptors = [d for d in descriptors
                       if tuple(self._resolve_control_envelope_leaves(d))
                       != tuple(d.get("baked_leaves") or ())]
        if not descriptors:
            return
        pending = getattr(self, '_pending_envelope_rebakes', None)
        if pending is None:
            pending = []
            self._pending_envelope_rebakes = pending
        for desc in descriptors:
            if not any(desc is held for held in pending):
                pending.append(desc)
        if not getattr(self, '_rebake_deferral_depth', 0):
            self._flush_envelope_rebakes()

    def _flush_envelope_rebakes(self):
        """Rebake every queued envelope once, after all splicing is done.

        Once, and at the end: a rebake bumps ``_structure_version``, which
        invalidates the timing cache it just read. Timings are provably
        unchanged across that bump, so interleaving rebakes with splices is
        a cost rather than a correctness bug -- one full timing recompute
        per envelope instead of one for all of them.
        """
        pending = getattr(self, '_pending_envelope_rebakes', None)
        if not pending:
            return
        self._pending_envelope_rebakes = []
        live = list(self._control_envelopes.values())
        for desc in pending:
            if any(desc is held for held in live):
                self._rebake_control_envelope(desc)

    @contextmanager
    def _deferred_envelope_rebakes(self):
        """Hold rebakes open across a verb that still has node writes to make."""
        self._rebake_deferral_depth = getattr(self, '_rebake_deferral_depth', 0) + 1
        try:
            yield
        finally:
            self._rebake_deferral_depth -= 1
            if not self._rebake_deferral_depth:
                self._flush_envelope_rebakes()

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
        # The slur pre-heal that used to run HERE is gone. Since the verb was
        # wired to the seam (TIE-3/TIE-4), the seam heals this edit anyway --
        # from inside the write, against the tree as it actually ends up --
        # so the pre-heal was a second mechanism answering the same question
        # a moment too early.
        #
        # And it answered WRONG. ``make_rest`` clears ``tied`` on every leaf
        # it silences (a tied rest is illegal, charter sect1), so a leaf that
        # was a continuation of a rested note is an ordinary NOTE once the
        # write lands -- but the pre-heal, running first, still saw a
        # continuation and dropped it out of the arc. Measured over 2430
        # cases across four tree shapes: 46 disagreements between
        # ``uc.make_rest`` and ``uc._rt.make_rest``, and in every one the
        # seam-only answer kept music the pre-heal discarded. Removing it
        # takes the count to zero and changes no other test in the suite.
        #
        # R12 lens 2 is what it broke: one musical question, two answers
        # depending on the handle -- and here the PUBLIC handle was the wrong
        # one.
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

        # The tree's own leaf-surface seam absorbs the new leaves into every
        # span the ex-leaf anchored, so this verb no longer heals anything
        # itself -- it only has to hold the envelope REBAKE open until the
        # pfield copy below is done, or the copy would overwrite the values
        # the rebake just wrote.
        with self._deferred_envelope_rebakes():
            self._rt.subdivide(node, S)
            self._invalidate_timing_cache()
            new_children = list(self._rt.successors(node))
            for child in new_children:
                if pfields:
                    self._rt.set_pfields(child, **pfields)
                if mfields:
                    self._rt.set_mfields(child, **mfields)

    def graft_subtree(self, node: int, subtree, mode: str = 'replace'):
        """Graft *subtree* at a leaf, healing slurs and control envelopes.

        Same contract as :meth:`TemporalUnit.graft_subtree`; this override
        exists so the graft heals the spans that reference the replaced leaf,
        exactly as :meth:`subdivide` does. Without it the two ways of adding
        structure agree about parameters but not about slurs.
        """
        with self._deferred_envelope_rebakes():
            result = self._rt.graft_subtree(node, subtree, mode)
            self._invalidate_timing_cache()
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
        # An overlay splits at an instrument change (Ryan, 2026-08-31), and
        # this is where a change actually happens. Authoring and the
        # structural heal cannot cover it between them: binding a leaf moves
        # no ids and grows no leaves, so neither seam fires, and an arc drawn
        # before the binding kept a shape the ruling forbids.
        self._resplit_overlays_at_instrument_changes()

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
                # ``curve_window`` and ``baked_leaves`` travel with the
                # descriptor or the copy silently differs from its source:
                # a dropped window restarts each half of a split envelope on
                # the copy's first structural edit, and a dropped
                # ``baked_leaves`` makes the rebake gate false-positive on
                # that edit -- the exact pair 784a3b5 and this session both
                # paid for once already.
                "curve_window": desc.get("curve_window") or (0.0, 1.0),
                "baked_leaves": desc.get("baked_leaves"),
            }

        return new_cu
    
    def __deepcopy__(self, memo):
        """Deep-copy the unit, then REBIND its id-state observer.

        :meth:`~klotho.topos.graphs.trees.Tree.__deepcopy__` clears the
        observer deliberately, and the rule is written on
        :meth:`~klotho.topos.graphs.trees.Tree.set_id_state_observer`:
        "A clone gets NO observer: it belongs to a different owner, which
        rebinds itself." This unit IS that owner. Three routes already
        rebind -- the constructor, :meth:`copy` and :meth:`_copy_rebuild`,
        which also backs :meth:`from_subtree` -- and ``copy.deepcopy`` was
        the fourth with no rebinder, so the clone's ``_slur_specs``,
        ``_bind_memo`` and ``_control_envelopes`` stopped following their
        content. rustworkx reuses freed node ids, so a stale entry does not
        leak: it re-attaches to whatever later lands in the slot, and a slur
        reaches playback on a note that did not exist when it was drawn.

        The copy itself is the default one -- every attribute deep-copied
        into a blank instance, with *memo* seeded first so cycles and shared
        references resolve exactly as they did before. Only the rebinding is
        added.

        Written at the UNIT level, not on ``Tree``: carrying the observer
        through ``Tree.__deepcopy__`` would break the bare-tree contract that
        ``test_a_clone_carries_no_observer`` pins.
        """
        cls = self.__class__
        clone = cls.__new__(cls)
        memo[id(self)] = clone
        for key, value in self.__dict__.items():
            clone.__dict__[key] = copy.deepcopy(value, memo)
        clone._rt.set_id_state_observer(clone._relocate_id_keyed_state)
        return clone

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
                "curve_window": desc.get("curve_window") or (0.0, 1.0),
                "baked_leaves": desc.get("baked_leaves"),
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
                "curve_window": desc.get("curve_window") or (0.0, 1.0),
                "baked_leaves": desc.get("baked_leaves"),
            }
        c._next_envelope_id = self._next_envelope_id

        c._attributed = self._attributed  # rebuild passed every slot; restore truth
        c._offset = self._offset
        c._invalidate_timing_cache()
        return c
