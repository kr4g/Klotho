"""
Temporal units.

A temporal unit binds a rhythm tree to a tempo and beat reference, producing
concrete onset times and durations in seconds. Temporal units can be
collected into sequences and blocks for polyphonic or multi-layered timing
structures.

Sources and attribution (docket DOC-1/2/3/4)
--------------------------------------------
``tempus``, ``prolatio`` and the object this module calls a
:class:`TemporalUnit` are **Karim Haddad's**, and were unattributed here
until 2026-08-29. He defines both Latin terms verbatim on p. 30 of the 2008
chapter cited below, where the object itself is called a *time-block*.

The three sources, correctly cited:

1. Haddad, Karim. "*Livre Premier de Motets* ("First Book of Motets"): The
   Time-Block Concept in OpenMusic." In *The OM Composer's Book 2*, ed.
   Jean Bresson, Carlos Agon and Gerard Assayag, 21-53. Paris: Editions
   Delatour France / IRCAM-Centre Pompidou, 2008. **Written in English.**
   This is the PRIMARY source for time-block material.
2. Haddad, Karim. "TimeSculpt in OpenMusic." In *The OM Composer's Book 1*,
   ed. Carlos Agon, Gerard Assayag and Jean Bresson. Paris: Editions
   Delatour France / IRCAM-Centre Pompidou, 2006. **Written in English.**
   *The printed page range is not recoverable from the author's preprint
   and is deliberately left blank here rather than invented; it needs the
   printed volume.* Note also that "TimeSculpt" names an article and
   nothing else -- no system, no library, no class.
3. Haddad, Karim. *L'Unite Temporelle : Une approche pour l'ecriture de la
   duree et de sa quantification* ("The Temporal Unit: An approach to the
   writing of duration and its quantification"), doctoral thesis, Sorbonne
   Universite, 2020, HAL ``tel-03258984``.

**The papers PREDATE the thesis by 12-14 years.** 2006 and 2008 against
2020: they are the original statements and the thesis is the late
synthesis. Anything attributing time-block material to "Haddad 2020" is
citing the derivative source.

**The attribution used to run backwards.** ``autoref``, ``decompose`` and
the rotation modes -- the three things that genuinely reproduce his
published figures -- all cited him, while ``tempus``, ``prolatio``,
``TemporalUnit`` and ``TemporalBlock``, which wear his vocabulary, cited
nobody. Both halves are fixed here: :class:`TemporalUnit` claims the
lineage it has, and :class:`TemporalBlock` disclaims the lineage it does
not.
"""
from dataclasses import dataclass
from fractions import Fraction
import numbers
from typing import Any, Callable, Iterable, Iterator, Optional, Union
from ..rhythm_trees import Meas, RhythmTree
from ..rhythm_trees.algorithms import auto_subdiv
from klotho.chronos.utils import calc_onsets, beat_duration, seconds_to_hmsms

from enum import Enum
import pandas as pd
import copy
import warnings

# Distinguishes "omitted" from "explicitly passed the default value" for
# constructor slots whose default is a real value (tempus). See
# TemporalUnit.attributed.
_UNSET = object()


class ProlatioTypes(Enum):
    """
    Enum of prolatio (subdivision) types for a temporal unit.

    The four types describe how a time signature is subdivided:

    - **DURATION** -- a single sustained note spanning the entire measure.
    - **REST** -- a single rest spanning the entire measure.
    - **PULSE** -- evenly spaced pulses matching the numerator.
    - **SUBDIVISION** -- a custom subdivision tuple.

    Each type also carries a set of string aliases for convenient parsing.
    """
    DURATION    = 'Duration'
    REST        = 'Rest'
    PULSE       = 'Pulse'
    SUBDIVISION = 'Subdivision'
    DURTYPES    = {'d', 'duration', 'dur'}
    RESTYPES    = {'r', 'rest', 'silence'}
    PULSTYPES   = {'p', 'pulse', 'phase'}
    SUBTYPES    = {'s', 'subdivision', 'subdivisions'}


class TemporalMeta(type):
    """Metaclass for all temporal structures."""
    pass


class _RepeatableTemporal:
    """Provides :meth:`repeat` for temporal objects that can be sequenced.

    Any object a :class:`TemporalUnitSequence` accepts as a member
    (``TemporalUnit``/``CompositionalUnit``, ``TemporalUnitSequence``,
    ``TemporalBlock``) can be repeated; the sequence's ``extend`` makes
    the independent copies.
    """

    def repeat(self, n):
        """
        Create a :class:`TemporalUnitSequence` of *n* copies of this object.

        Parameters
        ----------
        n : int
            Number of repetitions.

        Returns
        -------
        TemporalUnitSequence
            A new sequence containing *n* independent copies.
        """
        uts = TemporalUnitSequence()
        uts.extend([self] * n)
        return uts

    def __setattr__(self, name, value):
        """Refuse a public assignment that is not a settable property.

        Every field on these classes is private and read back through a
        property, so a public assignment was always a mistake -- and a silent
        one: ``ut.offset = 0.1`` created a fresh instance attribute that read
        back as 0.1 while every timing calculation went on using ``_offset``.
        """
        if not name.startswith('_'):
            descriptor = getattr(type(self), name, None)
            if not (isinstance(descriptor, property) and descriptor.fset is not None):
                raise AttributeError(
                    f"{type(self).__name__} has no settable attribute {name!r}. "
                    f"Assigning to it used to create a dead attribute that read "
                    f"back but changed nothing. Placement is edited through "
                    f"Score/ScoreItem."
                )
        object.__setattr__(self, name, value)


class UTNodeHandle:
    """Owner-bound handle to a single node in a :class:`TemporalUnit`.

    Handles are the canonical node-selection currency (handle-first API):
    they pair a node id with the owning unit, so structural and data
    operations can validate ownership. Obtained via ``ut.root``,
    ``ut.leaves``, or selector subscripting; a handle compares equal only
    to a handle for the same node of the same owner.
    """

    __slots__ = ("_owner", "_node_id")

    def __init__(self, owner: Any, node_id: int):
        self._owner = owner
        self._node_id = node_id

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._node_id})"

    def __hash__(self) -> int:
        return hash((id(self._owner), self._node_id))

    def __eq__(self, other):
        if isinstance(other, UTNodeHandle):
            return self._owner is other._owner and self._node_id == other._node_id
        if isinstance(other, int):
            return self._node_id == other
        return NotImplemented

    @property
    def id(self) -> int:
        """int : The raw integer node id."""
        return self._node_id

    @property
    def node_id(self) -> int:
        """int : The raw integer node id (alias of :attr:`id`)."""
        return self._node_id

    def _rt_node(self):
        return self._owner._rt[self._node_id]

    @property
    def depth(self) -> int:
        """int : The node's depth in the tree (root = 0)."""
        return self._owner._rt.depth_of(self._node_id)

    @property
    def sibling_index(self) -> int:
        """int : This node's position among its siblings (0 for the root)."""
        parent = self._owner._rt.parent(self._node_id)
        siblings = list(self._owner._rt.successors(parent)) if parent is not None else [self._node_id]
        return siblings.index(self._node_id)

    @property
    def sibling_total(self) -> int:
        """int : The number of siblings including this node (1 for the root)."""
        parent = self._owner._rt.parent(self._node_id)
        siblings = list(self._owner._rt.successors(parent)) if parent is not None else [self._node_id]
        return len(siblings)

    @property
    def path(self) -> tuple:
        """tuple of int : Child indices from the root down to this node.

        ``()`` at the root, ``len(path) == depth``, and ``path[-1] ==
        sibling_index``. The same tuple you would get by walking ``parent``
        upward collecting each ``sibling_index``, in one pass. Note it walks
        the branch, so it costs the same as ``sibling_index`` and does not
        belong in a hot per-leaf loop.
        """
        rt = self._owner._rt
        return rt.path_signature(rt.root, self._node_id)

    @property
    def parent(self) -> Optional["UTNodeHandle"]:
        """UTNodeHandle or None : A handle to the parent node (None at the root)."""
        parent_id = self._owner._rt.parent(self._node_id)
        if parent_id is None:
            return None
        return self._owner._build_node_handle(parent_id)

    @property
    def proportion(self):
        """int or float : The node's proportional weight (negative = rest, float = tied)."""
        return self._rt_node().get("proportion")

    @property
    def is_rest(self):
        """bool : Whether this node is a rest (negative proportion)."""
        return (self._rt_node().get("proportion", 1) or 0) < 0

    @property
    def metric_onset(self):
        """Fraction : Onset as a fraction of a whole note."""
        return self._rt_node().get("metric_onset")

    @property
    def metric_duration(self):
        """Fraction : Duration as a fraction of a whole note."""
        return self._rt_node().get("metric_duration")

    @property
    def real_onset(self):
        """float : Onset in seconds (computes the timing cache on first access)."""
        self._owner._ensure_timing_cache()
        return self._owner._real_times[self._node_id]["real_onset"] + self._owner._offset

    @property
    def real_duration(self):
        """float : Duration in seconds (computes the timing cache on first access).

        Signed: a rest reads negative, which is how rests are marked. Use
        :attr:`duration` for the unsigned value.
        """
        self._owner._ensure_timing_cache()
        return self._owner._real_times[self._node_id]["real_duration"]

    @property
    def start(self):
        """float : Absolute onset in seconds."""
        return self.real_onset

    @property
    def duration(self):
        """float : Duration in seconds, unsigned -- a rest reads positive.

        Mirrors :attr:`Chronon.duration`. :attr:`real_duration` keeps the
        negative sign that marks a rest; this is the length you would draw.
        """
        return abs(self.real_duration)

    @property
    def end(self):
        """float : Absolute end time in seconds."""
        return self.start + self.duration

    @property
    def leaves(self) -> "UTNodeSelector":
        """UTNodeSelector : Selection of this node's subtree leaves (the node itself if it is a leaf)."""
        rt = self._owner._rt
        if self._node_id in rt.leaf_index_map:
            ids = (self._node_id,)
        else:
            ids = tuple(rt.subtree_leaves(self._node_id))
        return self._owner._node_selector_class(self._owner, ids)

    @property
    def children(self) -> "UTNodeSelector":
        """UTNodeSelector : Selection of this node's direct children."""
        return self._owner._node_selector_class(
            self._owner, tuple(self._owner._rt.successors(self._node_id))
        )

    @property
    def first_leaf(self):
        """UTNodeHandle : Handle to the first leaf of this node's subtree."""
        return self.leaves.first

    @property
    def last_leaf(self):
        """UTNodeHandle : Handle to the last leaf of this node's subtree."""
        return self.leaves.last

    @property
    def first_child(self):
        """UTNodeHandle : Handle to this node's first child."""
        return self.children.first

    @property
    def last_child(self):
        """UTNodeHandle : Handle to this node's last child."""
        return self.children.last

    def make_rest(self):
        """Turn this node (and its subtree) into a rest; see :meth:`TemporalUnit.make_rest`."""
        return self._owner.make_rest(self._node_id)

    def make_sounding(self):
        """Bring this node (and its subtree) back out of rest; see :meth:`TemporalUnit.make_sounding`."""
        return self._owner.make_sounding(self._node_id)

    def subdivide(self, S):
        """Subdivide this node by proportions ``S``; see :meth:`TemporalUnit.subdivide`. Returns the owner."""
        self._owner.subdivide(self._node_id, S)
        return self._owner

    def sparsify(self, probability, seed=None):
        """Randomly rest leaves in this node's subtree; see :meth:`TemporalUnit.sparsify`."""
        return self._owner.sparsify(probability, node=self._node_id, seed=seed)

    def __getitem__(self, key):
        if key in ("real_onset", "real_duration"):
            return getattr(self, key)
        return self._rt_node()[key]

    def get(self, key, default=None):
        """Read a node-data key (or real-time field), returning ``default`` when absent."""
        if key in ("real_onset", "real_duration"):
            return getattr(self, key)
        return self._rt_node().get(key, default)

    def __contains__(self, key):
        if key in ("real_onset", "real_duration"):
            return True
        return key in self._rt_node()


@dataclass(frozen=True)
class NodeContext:
    """A node handle enriched with its position in the current selection.

    Wraps a :class:`UTNodeHandle` (``ref``) together with ``index`` (this
    node's position in the selection) and ``total`` (the selection size);
    every other attribute is forwarded to the underlying handle.
    """

    ref: UTNodeHandle
    index: int
    total: int

    @property
    def id(self) -> int:
        """int : The raw integer node id."""
        return self.ref.id

    @property
    def parent(self) -> Optional[UTNodeHandle]:
        """UTNodeHandle or None : A handle to the parent node (None at the root)."""
        return self.ref.parent

    def __getattr__(self, key):
        return getattr(self.ref, key)

    def __dir__(self):
        # __getattr__ forwards to the handle, so the forwarded names --
        # depth, path, sibling_index, sibling_total, proportion,
        # real_onset, leaves, children ... -- are invisible to plain dir()
        # and to tab completion. That invisibility is how an audit once
        # concluded they were missing. Advertise them.
        return sorted(set(object.__dir__(self)) | set(dir(self.ref)))


class UTNodeSelector:
    """An ordered, owner-bound collection of node IDs with fluent selection ops.

    Carries UT-level structural verbs (``make_rest``, ``subdivide``,
    ``sparsify``). Subclasses add domain-specific action verbs; in particular,
    :class:`~klotho.thetos.composition.compositional.UCNodeSelector` adds
    parameter/envelope/slur verbs.

    The selector preserves ownership identity: operations that return another
    selector always point at the same owner (UT/UC) so that subsequent verb
    calls dispatch to the owning object's mutators.

    Indexing, slicing, fancy-indexing, ``filter``, ``where``, and set-algebra
    operations all return a new selector of the same concrete subclass.

    Equality is strict: two selectors compare equal iff they share the same
    owner (``is``) and hold the same ids in the same order; a selector also
    compares equal to a ``tuple`` or ``list`` with matching ids (enabling
    tuple-based test assertions). Any other type returns ``NotImplemented`` -
    in particular, ``selector == int`` is always False via Python's fallback,
    surfacing mistakes loudly rather than silently.
    """

    __slots__ = ('_owner', '_ids')

    def __init__(self, owner: Any, ids: Iterable[int]):
        object.__setattr__(self, '_owner', owner)
        object.__setattr__(self, '_ids', tuple(ids))

    # --- Sequence protocol ---
    def __len__(self) -> int:
        return len(self._ids)

    def __iter__(self) -> Iterator[UTNodeHandle]:
        owner = self._owner
        return (owner._build_node_handle(n) for n in self._ids)

    def __contains__(self, node) -> bool:
        if isinstance(node, UTNodeHandle):
            if node._owner is not self._owner:
                return False
            node = node.id
        return node in self._ids

    def __bool__(self) -> bool:
        return bool(self._ids)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self._ids)})"

    def __eq__(self, other):
        if isinstance(other, UTNodeSelector):
            return self._owner is other._owner and self._ids == other._ids
        if isinstance(other, (tuple, list)):
            return self._ids == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((id(self._owner), self._ids))

    # --- Raw access ---
    @property
    def ids(self) -> tuple:
        """Underlying tuple of node IDs."""
        return self._ids

    @property
    def first(self) -> UTNodeHandle:
        """The first node handle in the selection."""
        return self._owner._build_node_handle(self._ids[0])

    @property
    def last(self) -> UTNodeHandle:
        """The last node handle in the selection."""
        return self._owner._build_node_handle(self._ids[-1])

    @property
    def first_id(self) -> int:
        """int : The first raw node id in the selection."""
        return self._ids[0]

    @property
    def last_id(self) -> int:
        """int : The last raw node id in the selection."""
        return self._ids[-1]

    @property
    def owner(self):
        """The UT/UC this selector is bound to."""
        return self._owner

    # --- Indexing (always returns same subclass) ---
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._owner._build_node_handle(self._ids[key])
        if isinstance(key, slice):
            return type(self)(self._owner, self._ids[key])
        if isinstance(key, (list, tuple)):
            return type(self)(self._owner, tuple(self._ids[i] for i in key))
        raise TypeError(
            f"Invalid selector index: {type(key).__name__}; "
            f"expected int, slice, or list/tuple of ints"
        )

    # --- Sub-selection on the underlying tree ---
    def _require_singleton(self, name: str) -> int:
        if len(self._ids) != 1:
            raise ValueError(
                f"{name} requires a single-node selector; got {len(self._ids)} nodes. "
                f"Iterate (for branch in sel:) or use {type(self._owner).__name__.lower()}.select(...)"
            )
        return self._ids[0]

    def selectors(self):
        """Split this selection into a tuple of single-node selectors, one per node."""
        cls = type(self)
        owner = self._owner
        return tuple(cls(owner, (n,)) for n in self._ids)

    def singletons(self):
        """Alias of :meth:`selectors` — one single-node selector per selected node."""
        return self.selectors()

    @property
    def leaves(self) -> 'UTNodeSelector':
        """Leaves of the subtree rooted at this single selected node."""
        n = self._require_singleton("leaves")
        rt = self._owner._rt
        if n in rt.leaf_nodes:
            ids = (n,)
        else:
            ids = tuple(rt.subtree_leaves(n))
        return type(self)(self._owner, ids)

    @property
    def children(self) -> 'UTNodeSelector':
        """Direct children of this single selected node."""
        n = self._require_singleton("children")
        return type(self)(self._owner, tuple(self._owner._rt.successors(n)))

    @property
    def first_leaf(self) -> 'UTNodeSelector':
        """UTNodeHandle : First leaf of this single node's subtree."""
        return self.leaves[0]

    @property
    def last_leaf(self) -> 'UTNodeSelector':
        """UTNodeHandle : Last leaf of this single node's subtree."""
        return self.leaves[-1]

    @property
    def first_child(self) -> 'UTNodeSelector':
        """UTNodeHandle : First direct child of this single node."""
        return self.children[0]

    @property
    def last_child(self) -> 'UTNodeSelector':
        """UTNodeHandle : Last direct child of this single node."""
        return self.children[-1]

    @property
    def sounding(self) -> 'UTNodeSelector':
        """Only the non-rest nodes of this selection.

        The long form ``sel.filter(lambda c: not c.is_rest)`` does the same
        thing; this exists because the loops that get rests wrong are the
        hand-zipped ones outside the selector API, and those are the ones
        that need a short spelling to reach for.
        """
        return type(self)(self._owner, tuple(
            n for n in self._ids
            if (self._owner._rt[n].get('proportion', 1) or 0) >= 0
        ))

    # --- Composition (all preserve subclass) ---
    def filter(self, predicate: Callable[['NodeContext'], bool]) -> 'UTNodeSelector':
        """Keep nodes for which ``predicate(NodeContext)`` returns truthy."""
        total = len(self._ids)
        return type(self)(self._owner, tuple(
            n for i, n in enumerate(self._ids)
            if predicate(self._owner._build_node_context(n, i, total))
        ))

    def where(self, mask: Iterable[bool]) -> 'UTNodeSelector':
        """Keep nodes where the corresponding mask entry is truthy."""
        mask_list = list(mask)
        if len(mask_list) != len(self._ids):
            raise ValueError(
                f"where() mask length mismatch: got {len(mask_list)}, "
                f"expected {len(self._ids)}"
            )
        return type(self)(
            self._owner,
            tuple(n for n, m in zip(self._ids, mask_list) if m),
        )

    def __or__(self, other):
        if not isinstance(other, UTNodeSelector) or other._owner is not self._owner:
            return NotImplemented
        seen = set(self._ids)
        tail = tuple(n for n in other._ids if n not in seen)
        return type(self)(self._owner, self._ids + tail)

    def __and__(self, other):
        if not isinstance(other, UTNodeSelector) or other._owner is not self._owner:
            return NotImplemented
        other_set = set(other._ids)
        return type(self)(self._owner, tuple(n for n in self._ids if n in other_set))

    def __sub__(self, other):
        if not isinstance(other, UTNodeSelector) or other._owner is not self._owner:
            return NotImplemented
        other_set = set(other._ids)
        return type(self)(self._owner, tuple(n for n in self._ids if n not in other_set))

    # --- UT-level mutators ---
    def make_rest(self):
        """Rest every node in the selection (and its subtree)."""
        return self._owner.make_rest(self)

    def make_sounding(self):
        """Bring every node in the selection (and its subtree) back out of rest."""
        return self._owner.make_sounding(self)

    def subdivide(self, S):
        """Subdivide every node in the selection with structure ``S``."""
        for n in self._ids:
            self._owner.subdivide(n, S)
        return self._owner

    def sparsify(self, probability, seed=None):
        """Sparsify leaves under the selection's nodes with ``probability``.

        An optional ``seed`` (int or ``numpy.random.Generator``) makes the
        result reproducible: ``unit.leaves.sparsify(0.5, my_seed)``.
        """
        return self._owner.sparsify(probability, node=self, seed=seed)


class UTNodeView:
    """View of UT nodes; subscripting returns a Chronon for that node."""

    def __init__(self, ut):
        self._ut = ut

    def __getitem__(self, node):
        self._ut._ensure_timing_cache()
        node_id = self._ut._coerce_singleton_node_target(node, "nodes")
        return self._ut._make_node_proxy(node_id)

    def __iter__(self):
        return iter(self._ut._rt.nodes)

    def __contains__(self, node):
        try:
            node_id = self._ut._coerce_singleton_node_target(node, "nodes")
        except (TypeError, ValueError):
            return False
        return node_id in self._ut._rt

    def __len__(self):
        return len(self._ut._rt)

    def __call__(self, data=False):
        self._ut._ensure_timing_cache()
        if data:
            for node in self._ut._rt.nodes:
                yield (node, self._ut._make_node_proxy(node))
        else:
            for node in self._ut._rt.nodes:
                yield node


class Chronon(metaclass=TemporalMeta):
    """
    A node in its temporal context within a :class:`TemporalUnit`.

    Exposes real-time onset/duration and metric data for any node (leaf or branch).
    Supports dict-like access (e.g. chronon['real_onset']) for compatibility.

    Parameters
    ----------
    node_id : int
        The node identifier within the rhythm tree.
    ut : TemporalUnit
        The parent temporal unit that owns this node.
    """
    __slots__ = ('_node_id', '_ut', '_group_nodes')

    def __init__(self, node_id: int, ut: 'TemporalUnit', group=None):
        self._node_id = node_id
        self._ut = ut
        # A multi-member tie group makes this Chronon the whole sounding
        # event (07_TIES_CHARTER.md sect2): anchored at the head node, with
        # duration reads summed over the members. None for the ordinary
        # one-leaf event, so the singleton paths stay exactly as they were.
        self._group_nodes = (tuple(group)
                             if group is not None and len(group) > 1 else None)

    def _rt_node(self):
        return self._ut._rt[self._node_id]

    def _real_data(self):
        """Raw (offset-free) timing entry for this node — internal only;
        every outward-facing read adds ``self._ut._offset`` to onsets."""
        self._ut._ensure_timing_cache()
        return self._ut._real_times.get(self._node_id, {})

    def _event_real_duration(self):
        """The event's real duration: the leaf's own for a one-leaf event,
        the sum over members for a tied group (charter sect2)."""
        group = self._group_nodes
        if group is None:
            return self._real_data()['real_duration']
        self._ut._ensure_timing_cache()
        times = self._ut._real_times
        return sum(times[n]['real_duration'] for n in group)

    def __dir__(self):
        # __getattr__ serves node-data keys plus the two real-time fields;
        # without this they never reach dir() or tab completion.
        try:
            keys = set(self._rt_node().keys())
        except Exception:
            keys = set()
        return sorted(set(object.__dir__(self)) | keys
                      | {"real_onset", "real_duration"})

    def __getattr__(self, key):
        if key == 'real_onset':
            return self._real_data()[key] + self._ut._offset
        if key == 'real_duration':
            return self._event_real_duration()
        try:
            return self._rt_node()[key]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{key}'")

    def __getitem__(self, key):
        if key == 'real_onset':
            return self._real_data()[key] + self._ut._offset
        if key == 'real_duration':
            return self._event_real_duration()
        return self._rt_node()[key]

    def get(self, key, default=None):
        """Read a node-data key (or real-time field), returning ``default`` when absent."""
        if key in ('real_onset', 'real_duration'):
            data = self._real_data()
            if key not in data:
                return default
            if key == 'real_onset':
                return data[key] + self._ut._offset
            return self._event_real_duration()
        return self._rt_node().get(key, default)

    def __contains__(self, key):
        if key in ('real_onset', 'real_duration'):
            return key in self._real_data()
        return key in self._rt_node()

    @property
    def start(self):
        """The absolute start time in seconds."""
        return abs(self.real_onset)

    @property
    def duration(self):
        """The absolute duration in seconds."""
        return abs(self.real_duration)

    @property
    def end(self):
        """The absolute end time in seconds."""
        return self.start + abs(self.duration)

    @property
    def proportion(self):
        """The integer proportion value from the rhythm tree."""
        return self._rt_node()['proportion']

    @property
    def metric_duration(self):
        """The fractional metric duration relative to the measure.

        For a tied-group event this is the sum over the members — a derived
        read; the members' own node data is never widened (charter sect3).
        Dict-style access (``chronon['metric_duration']``) stays the head
        node's raw value, which is the leaf surface.
        """
        group = self._group_nodes
        if group is None:
            return self._rt_node()['metric_duration']
        rt = self._ut._rt
        return sum(rt[n]['metric_duration'] for n in group)

    @property
    def tie_group(self):
        """The leaf node ids this event sounds through, head first.

        A one-tuple for an ordinary event; the full member run for a tied
        group. Derived from the RT flags — never stored (charter sect2).
        """
        group = self._group_nodes
        return group if group is not None else (self._node_id,)

    @property
    def metric_onset(self):
        """The fractional metric onset relative to the measure."""
        return self._rt_node()['metric_onset']

    @property
    def node_id(self):
        """The node identifier within the parent rhythm tree."""
        return self._node_id

    @property
    def is_rest(self):
        """Whether this event is a rest (negative proportion)."""
        return self._rt_node()['proportion'] < 0

    def __str__(self):
        # plain formatting — building a 1-row DataFrame per repr made
        # printing events in a loop pathologically slow
        return (
            f"{type(self).__name__}("
            f"node_id={self.node_id}, start={self.start:g}, "
            f"duration={self.duration:g}, end={self.end:g}, "
            f"is_rest={self.is_rest}, proportion={self.proportion}, "
            f"metric_onset={self.metric_onset}, "
            f"metric_duration={self.metric_duration})"
        )

    def __repr__(self):
        return self.__str__()


class TemporalUnit(_RepeatableTemporal, metaclass=TemporalMeta):
    """
    A rhythmic structure bound to a tempo, producing real-time events.

    A ``TemporalUnit`` combines a :class:`RhythmTree` (defined by
    *tempus* and *prolatio*) with a tempo specification (*beat*, *bpm*)
    to produce concrete onset times and durations in seconds.

    **This class is Karim Haddad's time-block** (docket DOC-3/DOC-4). His
    time-block is one measure: a *tempus* -- the fraction, what is commonly
    called a time signature -- plus a *prolatio*, its subdivisions, each of
    which may itself become a time-block. That is exactly the object below,
    and both Latin words are his, defined verbatim on p. 30 of "The
    Time-Block Concept in OpenMusic" (2008; full citation in the module
    docstring). The 2008 chapter is the primary source; the 2020 thesis
    restates the same material twelve years later.

    What Klotho adds on top of his time-block is the *tempo* half --
    ``beat`` and ``bpm``, and therefore real seconds. **Haddad has no tempo
    at all**: for him the Tempus fraction IS the duration, and the only
    rule on the subject is thesis sect4.4.4. The seconds-producing layer is
    Klotho's own.

    Outside a :class:`~klotho.thetos.composition.score.Score`, a temporal
    unit always starts at time 0 and its duration is fixed after
    construction.  Placement within a timeline and duration adjustment are
    handled by :class:`~klotho.thetos.composition.score.ScoreItem` after
    the unit has been added to a Score.

    Parameters
    ----------
    span : int or Fraction, optional
        Number of measures. Must be positive. ``float`` is refused: it is
        passed through to :class:`~klotho.chronos.rhythm_trees.RhythmTree`
        unconverted and only fails there, long after the unit has reported a
        duration. A non-integer ``Fraction`` is accepted and means what it
        says — ``span=Fraction(1, 2)`` on a ``4/4`` is the same unit as
        ``tempus='2/4'``. Default is 1.
    tempus : Meas, Fraction, int, float, or str, optional
        The time signature. Default is ``'4/4'``.
    prolatio : tuple or str, optional
        The subdivision specification. A tuple gives explicit proportions;
        a string selects a preset (``'d'`` = duration, ``'r'`` = rest,
        ``'p'`` = pulse). The tuple may not be EMPTY at the top level — an
        empty prolatio has no leaves, so the root becomes its own event and
        reports the tempus numerator as its duration. A nested empty group
        (``(1, (1, ()))``) is fine. Default is ``'d'``.
    beat : Fraction, int, float, str, or None, optional
        The beat reference for tempo calculation. When None, defaults to
        ``1/tempus-denominator`` (6/8 gets 1/8) — a default for now, an
        ambient-context read later (NEW-39); never "tempo-free", which is
        what a bare :class:`RhythmTree` is. Zero raises. Default is None.
    bpm : int, float, or None, optional
        Beats per minute. When None, defaults to 60 (same contract as
        *beat*). Zero raises. Default is None.

    Examples
    --------
    >>> ut = TemporalUnit(tempus='4/4', prolatio='p', bpm=120)
    >>> len(ut)
    4
    """
    def __init__(self,
                 span     : Union[int,Fraction]                = 1,
                 tempus   : Union[Meas,Fraction,int,float,str] = _UNSET,
                 prolatio : Union[tuple,str]                   = 'd',
                 beat     : Union[None,Fraction,int,float,str] = None,
                 bpm      : Union[None,int,float]              = None,
        ):

        self._type   = None

        # `span` was never validated, and the hint above used to advertise
        # `float` -- which is the one type that cannot work. It is passed
        # through unconverted to `RhythmTree(span=Meas(tempus).numerator *
        # span)`, so a float builds, reports a plausible `.duration`, and
        # only dies on the first `.events` read, deep inside the tree, with
        # "'float' object has no attribute 'numerator'". Zero and negative
        # never raised at all: `UT(span=-1).duration` was -4.0, a backwards
        # real duration that flows into sequences and blocks as an
        # overlapping timeline. A non-integer Fraction is DELIBERATELY still
        # accepted -- it is exact all the way down and is event-for-event
        # identical to writing the tempus you mean.
        #
        # ONE predicate, TWO unrelated refusals -- and they get TWO raises.
        # A single message covering both was measured saying, to
        # `span=np.int64(0)`, `span=np.int64(-3)`, `span=0` and `span=-3`
        # alike: "the value itself is fine and RhythmTree accepts it; only
        # this check is narrow, so wrap it: span=int(...)". Every clause of
        # that is false on the non-positive branch. `int(np.int64(0))` is
        # `0`, which this same guard refuses again, so the prescribed wrap
        # cannot work; and "RhythmTree accepts it" is true only in the sense
        # that RhythmTree does not validate `span` AT ALL -- which is
        # SPAN-1's live silent-corruption door, not a reassurance.
        #
        # SIGN IS CHECKED FIRST for anything numeric, precisely so that a
        # non-positive numpy integer never receives the int() advice that
        # cannot help it. Every numpy scalar integer and float registers as
        # `numbers.Real`, which is the case that mattered; `Decimal` is
        # `numbers.Number` but not `Real`, and it orders against 0 too, so
        # the predicate is the wider one. `complex` is a Number and does NOT
        # order -- it raises TypeError inside the comparison, so the
        # comparison is guarded and such a value falls through to the type
        # branch, where it belongs. A str, a Meas, or a numpy ARRAY is not a
        # Number at all and never reaches the comparison.
        _non_positive = False
        if isinstance(span, numbers.Number):
            try:
                _non_positive = span <= 0
            except TypeError:
                _non_positive = False
        if _non_positive:
            raise ValueError(
                f"span must be POSITIVE; got {span!r}. A span of 0 has no "
                "duration and a negative span runs backwards -- neither is a "
                "passage a player could read, and no conversion rescues "
                "either: int(np.int64(0)) is still 0 and lands right back "
                "here. Note that RhythmTree does NOT validate span, so it "
                "builds what this refuses and says nothing: "
                "RhythmTree(span=0, meas='4/4', subdivisions=(1, 1)) has "
                "durations (0, 0), and span=-3 gives (-3/2, -3/2) -- a "
                "zero-length or backwards tree, raising nothing (docket "
                "SPAN-1). Write a positive whole number of measures, or "
                "Fraction(1, 2) for half of one."
            )

        # The TYPE branch, and the only place the numpy sentence belongs.
        # `isinstance(np.int64(2), (int, Fraction))` is False while
        # `np.random.randint(1, 5)` returns `np.int64` directly -- so the
        # commonest way to arrive here is not a float at all. A numpy int is
        # NOT the float hazard: it is `numbers.Integral` and carries
        # `.numerator`, so `RhythmTree(span=np.int64(2), ...)` builds and
        # evaluates correctly, and RT and UT therefore disagree about the
        # same value. Whether this predicate should be widened to
        # `numbers.Integral` is a behaviour question and is NOT settled here.
        # Having passed the sign check above, anything reaching this message
        # is positive, so `int()` really is a working way out of it.
        if not isinstance(span, (int, Fraction)):
            raise ValueError(
                "span must be a positive int or Fraction of measures; got "
                f"{span!r}. A float span is never converted -- it reaches "
                "RhythmTree intact and dies with \"'float' object has no "
                "attribute 'numerator'\" the first time you read .events, "
                "after the unit has already reported a duration. Write "
                "span=2 for two measures, Fraction(1, 2) for half of one, or "
                "say it in the tempus: UT(tempus='2/4') rather than "
                "UT(span=0.5, tempus='4/4'). If this is a numpy integer -- "
                "np.random.randint and the numpy-backed generators all "
                "return np.int64, not int -- the value itself is a whole "
                "number of measures and RhythmTree takes it; only this check "
                "is narrow, so wrap it: span=int(np.random.randint(1, 5))."
            )

        # Attribution (NEW-39's prerequisite, ruled with LAYER-5): record
        # which tempo slots were explicitly given. Only the constructor
        # ever knows -- UT(bpm=60) is attributed AT the default value, so
        # the flag cannot be reconstructed later. Inert metadata until the
        # ambient context lands. The sentinel exists because tempus has a
        # real default: without it UT() and UT(tempus='4/4') would be
        # indistinguishable, and that distinction IS the future semantics
        # (explicit stays sticky under an ambient dial, omitted follows).
        attributed = set()
        if tempus is _UNSET:
            tempus = '4/4'
        else:
            attributed.add('tempus')

        self._rt     = self._set_rt(span, abs(Meas(tempus)), prolatio)
        self._real_times = {}

        # `is None`, not truthiness: beat=0/bpm=0 used to coerce silently
        # to the defaults (NEW-38). R13-F: zeros raise, nothing is inferred.
        if beat is None:
            self._beat = Fraction(1, self._rt.meas._denominator)
        else:
            self._beat = Fraction(beat)
            if self._beat == 0:
                raise ValueError(
                    "beat cannot be zero -- a zero beat has no duration and "
                    "no tempo can be inferred from it. Omit beat for the "
                    "default (1/tempus-denominator)."
                )
            attributed.add('beat')
        if bpm is None:
            self._bpm = 60
        else:
            if bpm == 0:
                raise ValueError(
                    "bpm cannot be zero -- nothing is inferred from it. "
                    "Omit bpm for the default (60)."
                )
            self._bpm = bpm
            attributed.add('bpm')
        self._attributed = frozenset(attributed)
        self._offset = 0.0

        self._timing_dirty = True

    @property
    def attributed(self):
        """The tempo slots explicitly given at construction.

        A frozenset drawn from ``{'tempus', 'beat', 'bpm'}``. Explicitly
        passing a slot's default value still counts — attribution is about
        the composer's gesture, not the value, and only the constructor
        can see the difference. Inert metadata today; the future ambient
        musical context (NEW-39) resolves unattributed slots against a
        revisable dial while attributed ones stay sticky.
        """
        return self._attributed
    
    @classmethod
    def from_rt(cls, rt:RhythmTree, beat = None, bpm = None):
        """
        Construct a ``TemporalUnit`` from an existing :class:`RhythmTree`.

        Parameters
        ----------
        rt : RhythmTree
            The rhythm tree to wrap.
        beat : Fraction, int, float, str, or None, optional
            Beat reference. Default is None.
        bpm : int, float, or None, optional
            Beats per minute. Default is None.

        Returns
        -------
        TemporalUnit
        """
        return cls(span     = rt.span,
                   tempus   = rt.meas,
                   prolatio = rt.subdivisions,
                   beat     = beat,
                   bpm      = bpm)
    
    _node_selector_class = UTNodeSelector
    _node_handle_class = UTNodeHandle
    _tree_class = RhythmTree

    @property
    def nodes(self):
        """UTNodeView : Node view; subscripting yields a :class:`Chronon` per node."""
        return UTNodeView(self)

    def _coerce_node_targets(self, node) -> list[int]:
        def _append(item, out):
            if isinstance(item, int):
                out.append(item)
            elif isinstance(item, UTNodeHandle):
                if item._owner is not self:
                    raise ValueError("node handle belongs to a different owner")
                out.append(item.id)
            elif isinstance(item, UTNodeSelector):
                if item.owner is not self:
                    raise ValueError("selector belongs to a different owner")
                out.extend(item.ids)
            else:
                raise TypeError("node must be int, node handle, selector, or iterable thereof")

        if isinstance(node, (int, UTNodeHandle, UTNodeSelector)):
            ids = []
            _append(node, ids)
        else:
            ids = []
            for item in node:
                _append(item, ids)
        if not ids:
            raise ValueError("Selection cannot be empty")
        return ids

    def _coerce_singleton_node_target(self, node, name: str) -> int:
        ids = self._coerce_node_targets(node)
        if len(ids) != 1:
            raise ValueError(
                f"{name} requires a single-node selector; got {len(ids)} nodes. "
                "Iterate (for branch in sel:) and call subtree helpers on each singleton."
            )
        return ids[0]

    def _build_node_handle(self, node_id: int) -> UTNodeHandle:
        self._ensure_timing_cache()
        if node_id not in self._rt.nodes:
            raise ValueError(f"Node {node_id} not found in tree")
        return self._node_handle_class(self, node_id)

    def _build_node_ref(self, node_id: int) -> UTNodeHandle:
        return self._build_node_handle(node_id)

    def _build_node_context(self, node_id: int, index: int, total: int) -> NodeContext:
        return NodeContext(ref=self._build_node_handle(node_id), index=index, total=total)

    # ------------------------------------------------------------------
    # Node-returning traversal (returns selector bound to this UT/UC)
    # ------------------------------------------------------------------

    @property
    def leaves(self):
        """All leaves in left-to-right order (selector form of RT.leaf_nodes)."""
        return self._node_selector_class(self, self._rt.leaf_nodes)

    @property
    def root(self):
        """1-element selector for the root node.

        Chain mutations: ``uc.root.set_pfields(amp=0.3)``.
        """
        return self._node_selector_class(self, (self._rt.root,))

    def leaves_of(self, node):
        """Leaves of the subtree rooted at ``node`` (selector form of RT.subtree_leaves)."""
        node_id = self._coerce_singleton_node_target(node, "leaves_of")
        return self._node_selector_class(self, self._rt.subtree_leaves(node_id))

    def at_depth(self, d: int, operator: str = '=='):
        """Nodes at a specific depth (selector form of RT.at_depth)."""
        return self._node_selector_class(self, self._rt.at_depth(d, operator))

    def successors(self, node):
        """Direct children of ``node`` (selector form of RT.successors)."""
        node_id = self._coerce_singleton_node_target(node, "successors")
        return self._node_selector_class(self, self._rt.successors(node_id))

    def select(self, *ids):
        """Build an ad-hoc selector from ints/selectors or iterables thereof."""
        if len(ids) == 1:
            selected = self._coerce_node_targets(ids[0])
        else:
            selected = self._coerce_node_targets(ids)
        return self._node_selector_class(self, tuple(selected))

    # ------------------------------------------------------------------
    # Non-node scalar forwards (unchanged return types)
    # ------------------------------------------------------------------

    @property
    def depth(self):
        """Maximum depth of the underlying RT."""
        return self._rt.depth

    @property
    def k(self):
        """Maximum branching factor of the underlying RT."""
        return self._rt.k

    def depth_of(self, node):
        """Depth of ``node`` in the underlying RT."""
        return self._rt.depth_of(node)

    def out_degree(self, node):
        """Out-degree of ``node`` in the underlying RT."""
        return self._rt.out_degree(node)

    def topological_sort(self):
        """Topological sort of the underlying RT's nodes."""
        return self._rt.topological_sort()

    @property
    def span(self):
        """The number of measures that the TemporalUnit spans."""
        return self._rt.span

    @property
    def tempus(self):
        """The time signature of the TemporalUnit.

        *Tempus* is **Haddad's term**, not Klotho's (docket DOC-3): p. 30
        of the 2008 chapter, where it names the fraction of a time-block.
        It is not merely a synonym for "time signature" -- ``3/4`` as a
        Tempus is a *quantity* that reduces, which is why the arithmetic
        elsewhere in ``chronos`` distinguishes it from ``3/4`` as a meter.
        """
        return self._rt.meas

    @property
    def prolationis(self):
        """The S-part of a RhythmTree which describes the subdivisions of the TemporalUnit.

        *Prolatio* is **Haddad's term** too (docket DOC-3), defined
        alongside *tempus* on p. 30 of the 2008 chapter: the subdivisions
        of a time-block, each of which may itself be a time-block. The
        property name is the genitive ``prolationis``; the constructor
        argument is the nominative ``prolatio``, which is his spelling.
        """
        return self._rt.subdivisions
    
    # @prolationis.setter
    # def prolationis(self, prolatio: Union[tuple, str]):
    #     self._rt = self._set_rt(self.span, self.tempus, prolatio)
    
    @property
    def rt(self):
        """The RhythmTree of the TemporalUnit (returns a copy)."""
        return self._rt.copy()

    @property
    def metric_durations(self):
        """The metric durations from the RhythmTree which describe the proportional durations of the TemporalUnit."""
        return self._rt.durations

    @property
    def metric_onsets(self):
        """The metric onsets from the RhythmTree which describe the proportional onset times of the TemporalUnit."""
        return self._rt.onsets

    @property
    def beat(self):
        """The rhythmic ratio that describes the beat of the TemporalUnit."""
        return self._beat
    
    @property
    def bpm(self):
        """The beats per minute of the TemporalUnit."""
        return self._bpm
    
    @property
    def type(self):
        """The type of the TemporalUnit."""
        return self._type
    
    @property
    def start(self) -> float:
        """Absolute start time in seconds.

        Always ``0`` for a unit outside a Score.  Inside a Score the start
        time is assigned by placement kwargs on
        :meth:`~klotho.thetos.composition.score.Score.add`.
        """
        return self._offset
    
    @property
    def onsets(self):
        """The real-time onset of each sounding event in seconds.

        Event surfaces count tie groups (07_TIES_CHARTER.md sect2): one
        entry per group (anchored at its head) plus rests. Identical to
        per-leaf onsets on a tie-free unit.
        """
        self._ensure_timing_cache()
        offset = self._offset
        return tuple(self._real_times[g[0]]['real_onset'] + offset
                     for g in self._rt.tie_groups)

    @property
    def durations(self):
        """The real-time duration of each sounding event in seconds.

        One entry per tie group — the sum of the members' durations — plus
        rests, whose entries stay signed (WL-19's pinned choice). Identical
        to per-leaf durations on a tie-free unit.
        """
        self._ensure_timing_cache()
        times = self._real_times
        return tuple(
            times[g[0]]['real_duration'] if len(g) == 1
            else sum(times[n]['real_duration'] for n in g)
            for g in self._rt.tie_groups
        )

    @property
    def attacks(self):
        """Selector of attack leaves: the head of every sounding tie group.

        The companion of ``leaves.sounding`` (which keeps continuations —
        they do sound): ``attacks`` keeps only the leaves that START a
        sound. On a tie-free unit this is exactly the sounding leaves.
        """
        rx = self._rt._rx
        heads = tuple(g[0] for g in self._rt.tie_groups
                      if rx.get_node_data(g[0]).get('proportion', 1) >= 0)
        return self._node_selector_class(self, heads)

    @property
    def duration(self):
        """The total duration (in seconds) of the TemporalUnit."""
        # duration depends only on (meas x span, beat, bpm); meas/span are
        # fixed after construction, so the cache keys on (bpm, beat) and
        # needs no explicit invalidation hooks (container re-layout reads
        # this once per member per cascade — it was 3,930 calls per
        # notebook-score build)
        key = (self._bpm, self._beat)
        cached = self.__dict__.get('_duration_cache')
        if cached is not None and cached[0] == key:
            return cached[1]
        value = beat_duration(ratio      = (self._rt.meas * self._rt.span).to_fraction(),
                              beat_ratio = self.beat,
                              bpm        = self.bpm
                )
        self.__dict__['_duration_cache'] = (key, value)
        return value
    
    @property
    def end(self) -> float:
        """Absolute end time in seconds (``start + duration``)."""
        return self._offset + self.duration

    @property
    def time(self):
        """The absolute start and end times (in seconds) of the TemporalUnit."""
        return self._offset, self._offset + self.duration
    
    @property
    def events(self):
        """
        A :class:`~pandas.DataFrame` of all leaf events with timing and metric data.

        Returns
        -------
        pandas.DataFrame
        """
        key = (self._rt._structure_version, self._bpm, self._beat, self._offset)
        cached = self.__dict__.get('_events_df_cache')
        if cached is not None and cached[0] == key and not self._rt._write_batch_depth:
            return cached[1].copy()
        events = self._materialize_events()
        df = pd.DataFrame([{
            'node_id': c.node_id,
            'start': c.start,
            'duration': c.duration,
            'end': c.end,
            'is_rest': c.is_rest,
            's': c.proportion,
            'metric_onset': c.metric_onset,
            'metric_duration': c.metric_duration,
        } for c in events], index=range(len(events)))
        if not self._rt._write_batch_depth:
            self.__dict__['_events_df_cache'] = (key, df)
            return df.copy()
        return df
        
    def _scale_bpm(self, factor: float) -> None:
        """Multiply bpm by ``factor`` (private; used by ``ScoreItem``).

        A factor of ``0.5`` halves the bpm, doubling the resulting duration.
        This method is deliberately private: outside a Score, a unit's
        duration is immutable; duration editing is mediated by
        :meth:`klotho.thetos.composition.score.ScoreItem.set_duration`.
        """
        self._bpm = self._bpm * factor
        self._invalidate_timing_cache()

    def make_rest(self, node) -> None:
        """
        Turn a node (or each node in an iterable) and all descendants into rests.

        Delegates to :meth:`RhythmTree.make_rest` and re-evaluates timing once
        at the end (batched across all provided nodes).

        Parameters
        ----------
        node : int or iterable of int
            A single node ID, or an iterable of node IDs, to convert to rests.

        Raises
        ------
        ValueError
            If any node is not found in the rhythm tree.
        """
        nodes = self._coerce_node_targets(node)
        for n in nodes:
            self._rt.make_rest(n)
        self._invalidate_timing_cache()

    def make_sounding(self, node) -> None:
        """
        Bring a node (or each node in an iterable), and all its descendants,
        back out of rest.

        Delegates to :meth:`RhythmTree.make_sounding` and re-evaluates
        timing once at the end (batched across all provided nodes).

        Parameters
        ----------
        node : int or iterable of int
            A single node ID, or an iterable of node IDs, to bring back.

        Raises
        ------
        ValueError
            If any node is not found in the rhythm tree.

        Notes
        -----
        This restores the RHYTHM only. :meth:`make_rest` is lossy -- it
        clears ``tied`` and records nothing about what it cleared -- so a
        leaf that was tied before it was rested comes back untied. It also
        un-rests the target's ancestor chain, because a rest on an
        enclosing group would otherwise re-assert itself on the next
        recompute and the call would silently do nothing.
        """
        nodes = self._coerce_node_targets(node)
        for n in nodes:
            self._rt.make_sounding(n)
        self._invalidate_timing_cache()

    def subdivide(self, node: int, S) -> None:
        """
        Subdivide a leaf node with structure (D, S).

        Delegates to :meth:`RhythmTree.subdivide` and invalidates cached events.

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
        self._rt.subdivide(node, S)
        self._invalidate_timing_cache()

    def graft_subtree(self, node: int, subtree, mode: str = 'replace'):
        """
        Graft *subtree* at a leaf; see :meth:`RhythmTree.graft_subtree`.

        Parameters
        ----------
        node : int
            The leaf node to graft onto.
        subtree : Tree
            The tree to graft. A ParameterTree or CompositionalTree brings
            its own pfield/mfield registries and instrument bindings with it.
        mode : str, optional
            ``'replace'`` (default) or ``'adopt'``.

        Returns
        -------
        int
            The node id the graft landed on.

        Notes
        -----
        This is the public route. ``ut.rt`` returns a *copy*, so grafting on
        it mutates a throwaway and silently does nothing.
        """
        result = self._rt.graft_subtree(node, subtree, mode)
        self._invalidate_timing_cache()
        return result

    def sparsify(self, probability, node=None, seed=None):
        """
        Randomly convert leaf events to rests with a given probability.

        Parameters
        ----------
        probability : float
            Probability (0--1) that each eligible leaf becomes a rest.
        node : int, list of int, or None, optional
            Restrict to leaves under this node (or nodes). When None,
            all leaves are candidates. Default is None.
        seed : int, numpy.random.Generator, or None, optional
            Seed for reproducible sparsification (anything accepted by
            ``numpy.random.default_rng``). When None (default), draws
            from the global numpy random stream.
        """
        import numpy as _np
        rng = _np.random if seed is None else _np.random.default_rng(seed)
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

        for leaf in targets:
            if rng.uniform() < probability:
                self.make_rest(leaf)

    def _set_rt(self, span:int, tempus:Union[Meas,Fraction,str], prolatio:Union[tuple,str]) -> RhythmTree:
        tree_cls = self._tree_class
        match prolatio:
            case tuple():
                # RT-30, the TemporalUnit door. A TOP-LEVEL empty tuple builds
                # a tree with only a root, so the root is its own single event
                # and carries `Meas.numerator * span` as its metric duration
                # instead of the measure: UT(tempus='6/8', prolatio=()) reported
                # .duration == 6.0 while its one event ran 36.0 seconds. The
                # RhythmTree constructor refuses this too, but in its own
                # `subdivisions` vocabulary -- a UT caller who wrote `prolatio`
                # is owed a message about `prolatio`.
                #
                # Scoped to the top level ON PURPOSE. A NESTED empty group --
                # the (1, ()) pair inside (1, (1, ())) -- is correct today,
                # sums to the measure, and is real emitted data (the
                # asymmetric tree in tests/test_decompose.py).
                if not prolatio:
                    raise ValueError(
                        "prolatio cannot be an empty tuple -- an empty "
                        "prolatio builds a unit whose single event runs "
                        f"{tempus._numerator}x longer than the unit reports. "
                        "Pass 'd' for one undivided event, or (1,), or 'r' "
                        "for a rest. (A nested empty group -- the (1, ()) "
                        "pair inside (1, (1, ())) -- is still accepted.)"
                    )
                self._type = ProlatioTypes.SUBDIVISION
                return tree_cls(span = span, meas = tempus, subdivisions = prolatio)
            
            case str():
                prolatio = prolatio.lower()
                match prolatio:
                    case p if p.lower() in ProlatioTypes.PULSTYPES.value:
                        self._type = ProlatioTypes.PULSE
                        return tree_cls(
                            span = span,
                            meas = tempus,
                            subdivisions = (1,) * tempus._numerator
                        )
                    
                    case d if d.lower() in ProlatioTypes.DURTYPES.value:
                        self._type = ProlatioTypes.DURATION
                        return tree_cls(
                            span = span,
                            meas = tempus,
                            subdivisions = (1,)
                        )
                    
                    case r if r.lower() in ProlatioTypes.RESTYPES.value:
                        self._type = ProlatioTypes.REST
                        return tree_cls(
                            span = span,
                            meas = tempus,
                            subdivisions = (-1,)
                        )
                    
                    case _:
                        raise ValueError(f'Invalid string: {prolatio}')
            
            case _:
                raise ValueError(f'Invalid prolatio type: {type(prolatio)}')

    def _compute_timing_cache(self):
        """Recompute real-time onset/duration cache for all nodes.

        Inlines :func:`~klotho.chronos.utils.beat_duration` with the
        per-unit factors hoisted out of the loop; the float operation
        order matches beat_duration exactly, so results are bit-identical.

        Onsets are stored OFFSET-FREE: ``self._offset`` is added at the
        read sites (node handles, Chronon accessors, ``onsets``). Container
        re-layout (`_reoffset`) therefore only rewrites ``_offset`` and
        never invalidates this cache. Adding the offset at read preserves
        the historical operation order (offset was always added last).
        """
        self._real_times.clear()
        tempo_factor = 60 / self.bpm
        beat = self._beat
        beat_factor = beat.denominator / beat.numerator
        rt = self._rt
        rx = rt._rx
        # Read the version BEFORE the loop: stamping an older version can
        # only cost a redundant recompute, stamping a newer one would hide
        # a mutation that landed mid-computation.
        version = rt._structure_version
        for node in rt.nodes:
            data = rx.get_node_data(node)
            md = data['metric_duration']
            mo = data['metric_onset']
            real_duration = tempo_factor * (md.numerator / md.denominator) * beat_factor
            real_onset = tempo_factor * (mo.numerator / mo.denominator) * beat_factor
            self._real_times[node] = {'real_duration': real_duration, 'real_onset': real_onset}
        self._timing_cache_version = version
        self._timing_dirty = False

    # Class-level default so every construction path starts consistent
    # without help — __init__, and the __new__ + manual-setup fast copies in
    # TemporalUnit.copy and CompositionalUnit.copy (same idiom as
    # Graph._trav_cache_version). None never equals a real version, so a
    # freshly built unit always computes.
    _timing_cache_version = None

    def _ensure_timing_cache(self):
        # Keyed on the TREE'S STRUCTURE VERSION, not on the node count.
        # A count is blind to every mutation that keeps the node count:
        # rt.scale, rt.replace_node and rt.move_subtree all rewrite the
        # rhythm in place, so a unit whose events had been read once kept
        # serving its pre-mutation onsets and durations forever (RT-27).
        # _structure_version is bumped by _post_mutation, which every
        # structural mutator and every node-data write already runs, so it
        # moves whenever the timings it feeds can have moved.
        #
        # bpm/beat changes touch no node and no version: _timing_dirty is
        # still the signal for those, and both halves are required.
        if (self._timing_dirty
                or self._timing_cache_version != self._rt._structure_version):
            self._compute_timing_cache()

    def _make_node_proxy(self, node_id: int):
        return Chronon(node_id, self)

    def _event_context(self):
        self._ensure_timing_cache()
        return None

    def _make_event(self, node_id: int, event_context=None, group=None):
        return Chronon(node_id, self, group=group)

    def _materialize_events(self):
        """Materialize event Chronons lazily from current tree state.

        One event per tie group (07_TIES_CHARTER.md sect2), anchored at the
        group's head; on a tie-free tree this is one event per leaf, exactly
        as before ties meant anything.
        """
        event_context = self._event_context()
        return tuple(self._make_event(g[0], event_context, group=g)
                     for g in self._rt.tie_groups)

    def _invalidate_timing_cache(self):
        self._timing_dirty = True

    def __getitem__(self, idx):
        groups = self._rt.tie_groups
        event_context = self._event_context()
        if isinstance(idx, slice):
            return tuple(self._make_event(g[0], event_context, group=g)
                         for g in groups[idx])
        g = groups[idx]
        return self._make_event(g[0], event_context, group=g)

    def __iter__(self):
        event_context = self._event_context()
        for g in self._rt.tie_groups:
            yield self._make_event(g[0], event_context, group=g)

    def __len__(self):
        # sounding events, not leaves: n_events <= n_leaves, equal exactly
        # when no ties (charter sect2). The leaf count is len(self.leaves).
        return len(self._rt.tie_groups)

    # ------------------------------------------------------------------
    # Magnitude scaling (OPS-6)
    # ------------------------------------------------------------------

    @staticmethod
    def _exact_scale_factor(value) -> Fraction:
        """Exact rational form of a magnitude-scaling factor.

        Mirrors ``_exact_tempo_ratio`` in
        :mod:`klotho.chronos.temporal_units.algorithms` (kept local so the
        operator surface owns its own coercion): floats are snapped by
        ``limit_denominator(10**6)``, which recovers the intended rational
        for every musically plausible value (1.5 is exactly 3/2, 0.3 is
        exactly 3/10) rather than the exact-but-monstrous binary expansion.
        """
        if isinstance(value, float):
            return Fraction(value).limit_denominator(10**6)
        return Fraction(value.numerator, value.denominator)

    def _scaled(self, k: Fraction):
        """Build the unit *k* times as long, by rewriting the tempus.

        The tempus is assembled from RAW INTS -- never through
        ``Meas.__mul__``, which gcd-reduces even at identity (``Meas(6, 20)
        * 1`` is 3/10). This is the TEMPO-5 / R13-D discipline shared with
        ``modulate_tempo`` and ``fuse``; reducing a Tempus changes the
        unit's nature (Haddad sect4.4.2/4.4.5).
        """
        if k == 0:
            raise ValueError(
                "cannot scale a TemporalUnit by zero -- a zero tempus has "
                "no duration and no notation, and nothing is inferred from "
                "it (the same contract as beat=0/bpm=0)."
            )
        if k < 0:
            raise ValueError(
                f"cannot scale a TemporalUnit by a negative factor ({k}) -- "
                "a negative measure has no meaning, and the constructor "
                "absolutizes the tempus, so the sign would silently vanish "
                "and `ut * -1` would read back as `ut * 1`."
            )

        # factor = k x span as one exact Fraction, then applied to the
        # tempus as raw ints -- Fraction reduces k*span internally, but the
        # tempus' own numerator/denominator are never cancelled against
        # each other. Identical shape to `modulate_tempo`/`fuse`.
        factor = k * Fraction(self.span)
        new_tempus = Meas(self.tempus.numerator * factor.numerator,
                          self.tempus.denominator * factor.denominator)

        from klotho.thetos.composition.compositional import CompositionalUnit
        if isinstance(self, CompositionalUnit):
            out = CompositionalUnit(
                span=1,
                tempus=new_tempus,
                prolatio=self.prolationis,
                beat=self.beat,
                bpm=self.bpm,
            )
            # NO `pfields=` here. It looked like registry carry and was not:
            # `self.pfields` is the sorted list of registered NAMES, and the
            # constructor's list branch means "declare these and default them
            # to 0.0". Every name the source had merely registered came back
            # pinned to 0.0 at the root and inherited down -- amp=0.0 is
            # silence, gate=0.0 never opens the envelope -- so `uc * 1`, a
            # documented no-op, muted the unit. `_mirror_param_state` does
            # the registration itself (`dst.register_pfields(...)`), so the
            # argument was redundant as well as harmful.
            out._mirror_param_state(self)
            out._slur_specs = self._copy_slur_specs()
            out._next_slur_id = self._next_slur_id
            out._control_envelopes = self._copy_control_envelopes()
            out._next_envelope_id = self._next_envelope_id
            # Scaling scales the unit AS IT IS (Ryan, 2026-08-31), so the
            # draws a stochastic Bind has already made come across with
            # everything else. Rebuilding without them made `uc * Fraction(1,
            # 1)` -- an identity -- return different music.
            out._bind_memo = self._copy_bind_memo()
        else:
            out = TemporalUnit(
                span=1,
                tempus=new_tempus,
                prolatio=self.prolationis,
                beat=self.beat,
                bpm=self.bpm,
            )
        # Attribution (NEW-39's lift rule, as in `flatten`): the computed
        # tempus is attributed by definition; beat/bpm are carried verbatim
        # and so keep the source's attribution.
        out._attributed = frozenset(
            {'tempus'} | (self._attributed & {'beat', 'bpm'}))
        return out

    def __mul__(self, other):
        """Scale the unit's magnitude by a rational factor.

        ``ut * Fraction(3, 2)`` makes the unit half again as long by
        REWRITING THE TEMPUS -- 4/4 becomes 12/8 -- and leaves *beat* and
        *bpm* exactly as they were. This is TEMPO-1's *follows* policy:
        the Tempus changes, the tempo is fixed, and both the real duration
        and the notation move with it.

        This is the homothetia trap, and the fence around it. Rescaling the
        bpm instead (60 -> 40) reaches a byte-identical sound from a
        different page, so no listening test separates the two; the
        notation is what the composer wrote, so the tempus is what moves.
        (The complementary operation -- hold the Tempus and rescale the
        contents -- is the *preserved* half of the same axis and is not
        this operator.)

        VOCABULARY. **Haddad never writes "Tempus-preserving" or
        "Tempus-following."** The axis is his -- he states it outright on
        p. 128 -- but his labels for the two halves are « prolationnelle
        stricte » ("strictly prolational") for the preserving family and
        « relative » ("relative") for this one. The English pair is
        **Klotho's coinage**, kept because it names the mechanism rather
        than the grammar. His notation is systematic and worth knowing:
        a BOX means the Tempus follows (⊞ ⊟ ⊠), a CIRCLE means the Tempus
        is preserved (⊕ ⊖ ⊗).

        The result always has ``span=1``, with the source's span folded
        into the tempus numerator (span 2 of 6/20 scaled by 1 comes back as
        12/20), the same span collapse `modulate_tempo` and `fuse` apply.
        Prolationes are carried verbatim, so the event count never changes.
        Scaling by 1 is a true no-op on the spelling: 6/20 stays 6/20.

        ONLY THE TIMING MOVES. On a
        :class:`~klotho.thetos.composition.compositional.CompositionalUnit`
        nothing is re-evaluated: parameters, instruments, slurs, envelopes
        and -- since 2026-08-31 -- the draws a stochastic
        :class:`~klotho.thetos.parameters.bind.Bind` has already made all
        come across unchanged (Ryan: *"we simply scale the ut/uc as it is.
        No need to re-eval things."*). ``uc * Fraction(1, 1)`` used to
        re-roll every draw, so an identity returned different music. Note
        the asymmetry with
        :meth:`~klotho.thetos.composition.compositional.CompositionalUnit.copy`,
        which still re-rolls deliberately: a copy is a fresh instance of the
        recipe, scaling is a transformation of this music. That docstring
        carries the full argument.

        Parameters
        ----------
        other : Fraction, Meas, str, or float
            The scaling factor. Must be strictly positive. A ``str`` is
            read as a fraction (``'3/2'``); a ``float`` is snapped by
            ``limit_denominator(10**6)``. A bare ``int`` is REFUSED -- see
            Raises.

        Returns
        -------
        TemporalUnit or CompositionalUnit
            A new unit; the source is untouched.

        Raises
        ------
        TypeError
            If *other* is a bare ``int``. ``ut * 3`` has two honest
            readings -- three copies (Python's sequence convention, and
            :meth:`repeat` ships it) or three times as long (arithmetic) --
            so Klotho refuses to guess and names both.
        ValueError
            If *other* is zero or negative.

        Examples
        --------
        >>> ut = TemporalUnit(tempus='4/4', prolatio=(2, 1, 2), beat='1/4', bpm=60)
        >>> (ut * Fraction(3, 2)).tempus
        12/8
        >>> (ut * Fraction(3, 2)).bpm
        60
        """
        if isinstance(other, int):  # bool included, deliberately
            raise TypeError(
                f"TemporalUnit * {other!r} is ambiguous and Klotho will not "
                f"guess: it could mean {other} copies of the unit -- write "
                f"ut.repeat({other}) -- or {other} times as long -- write "
                f"ut * Fraction({other}). Pick the one you meant."
            )
        if isinstance(other, (Meas, Fraction, float)):
            return self._scaled(self._exact_scale_factor(other))
        if isinstance(other, str):
            # Only the PARSE goes inside the try. Wrapping the _scaled call
            # swallowed its deliberate zero/negative refusals into
            # NotImplemented, and Python then reported a string-repetition
            # error for a factor this method documents as first-class.
            # `__truediv__` below already has this shape.
            try:
                factor = Fraction(other)
            except ValueError:
                raise TypeError(
                    f"TemporalUnit * {other!r}: a str factor is read as a "
                    f"fraction ('3/2'), and {other!r} does not parse as one."
                ) from None
            return self._scaled(factor)
        return NotImplemented

    def __rmul__(self, other):
        """Scalar scaling reads as commutative: ``Fraction(3, 2) * ut``."""
        return self.__mul__(other)

    def __truediv__(self, other):
        """Scale the unit's magnitude down: ``ut / k == ut * (1/k)``.

        The same tempus rewrite as :meth:`__mul__`, so ``4/4`` divided by
        3/2 is written ``8/12`` and the bpm never moves.

        A bare ``int`` IS accepted here, unlike in :meth:`__mul__`: the
        refusal there exists only because :meth:`repeat` gives ``*`` a
        second reading, and division has no such reading. ``ut / 2`` can
        only mean "half as long".

        Parameters
        ----------
        other : Fraction, Meas, int, str, or float
            The divisor. Must be strictly positive.

        Returns
        -------
        TemporalUnit or CompositionalUnit

        Raises
        ------
        ZeroDivisionError
            If *other* is zero.
        ValueError
            If *other* is negative.
        """
        if isinstance(other, (Meas, Fraction, float, int)):
            divisor = self._exact_scale_factor(
                other if not isinstance(other, int) else Fraction(other))
            if divisor == 0:
                raise ZeroDivisionError("division by zero")
            return self._scaled(1 / divisor)
        if isinstance(other, str):
            try:
                divisor = Fraction(other)
            except ValueError:
                return NotImplemented
            if divisor == 0:
                raise ZeroDivisionError("division by zero")
            return self._scaled(1 / divisor)
        return NotImplemented

    def __str__(self):
        result = (
            f'Tempus:   {self._rt.meas}' + (f' (x{self._rt.span})' if self._rt.span > 1 else '') + '\n' +
            f'Prolatio: {self._type.value}\n' +
            f'Events:   {len(self)}\n' +
            f'Tempo:    {self._beat} = {self._bpm}\n' +
            f'Time:     {seconds_to_hmsms(self.time[0])} - {seconds_to_hmsms(self.time[1])} ({seconds_to_hmsms(self.duration)})\n' +
            f'{"-" * 50}\n'
        )
        return result

    def __repr__(self):
        return self.__str__()

    def copy(self):
        """Create a deep copy of this TemporalUnit.

        The copy preserves any internal placement (``_offset``) so that
        containers like :class:`TemporalUnitSequence` can rebuild cleanly.
        """
        if type(self) is not TemporalUnit:
            return self._copy_rebuild()
        c = TemporalUnit.__new__(TemporalUnit)
        c._type = self._type
        c._rt = self._rt.structural_clone()
        c._real_times = {}
        c._beat = self._beat
        c._bpm = self._bpm
        c._attributed = self._attributed
        c._offset = self._offset
        c._timing_dirty = True
        return c

    def _copy_rebuild(self):
        """Legacy copy path: reconstruct from prolatio (renumbers node ids).

        Kept for subclasses without their own ``copy()`` (which have always
        received a plain ``TemporalUnit`` here) and as an equivalence oracle
        for the structural-clone fast path.
        """
        c = TemporalUnit(
            span=self.span,
            tempus=self.tempus,
            prolatio=self.prolationis,
            beat=self.beat,
            bpm=self.bpm,
        )
        c._attributed = self._attributed  # rebuild passed every slot; restore truth
        c._offset = self._offset
        c._invalidate_timing_cache()
        return c


class TemporalUnitSequence(_RepeatableTemporal, metaclass=TemporalMeta):
    """
    An ordered sequence of :class:`TemporalUnit` objects representing
    consecutive temporal events.

    Units are automatically offset so that each begins where the previous
    one ends.  Outside a :class:`~klotho.thetos.composition.score.Score`,
    a sequence always starts at time 0. What is fixed is the **start**,
    not the duration: ``duration`` is the sum of the members' durations,
    so every mutator that changes the membership (``append``,
    ``prepend``, ``insert``, ``remove``, ``replace``, ``extend``,
    ``__setitem__``) changes it, and re-offsets the members after the
    edit. There is no duration setter on the sequence itself; to re-time
    one on a timeline, add it to a ``Score`` and use
    :meth:`~klotho.thetos.composition.score.ScoreItem.set_duration`.

    Like :class:`TemporalBlock`, this container is **Klotho's own**: Haddad
    lays time-blocks end to end as an *operation* (his ``||``, which
    :func:`~klotho.chronos.temporal_units.algorithms.fuse` implements and
    which really does merge two units into one), never as a container
    class. Sequencing here is the opposite of fusing -- ``extend``/
    ``append`` lay units end to end and never fuse them.

    Placement is validated **lazily**, like :class:`TemporalBlock`'s
    alignment: every reader that hands out a live member (``seq``,
    ``s[i]``, iteration, and the printed table) first calls
    ``_ensure_offsets``, which re-runs ``_set_offsets`` when the member
    durations differ from the geometry the last pass saw. That matters
    because a *member* can be a container with mutators of its own --
    ``s[0].append(...)`` lengthens member 0 without any sequence-level
    mutator running, and without it the members would silently overlap.
    Reading ``s._seq`` directly bypasses the check and can observe stale
    offsets.

    ``duration``, ``durations`` and ``onsets`` never needed that check:
    they recompute from the live members every time. That is exactly why
    the stale case was a *contradiction* rather than a uniformly wrong
    answer -- ``onsets`` reported the new placement while the members'
    own ``start`` still reported the old one.

    Parameters
    ----------
    ut_seq : list of TemporalUnit, optional
        Initial sequence of temporal units. Default is an empty list.
    """
    
    def __init__(self, ut_seq:Union[list[TemporalUnit], None]=None):
        if ut_seq is None:
            ut_seq = []
        self._seq    = [ut.copy() for ut in ut_seq]
        self._offset = 0.0
        self._set_offsets()

    @classmethod
    def _adopt(cls, members, offset=0.0):
        """Private: build a sequence that takes ownership of *members*
        WITHOUT copying them. Used by ``copy()`` (whose members are
        already fresh copies) to avoid the constructor's second copy of
        every member."""
        c = cls.__new__(cls)
        c._seq = list(members)
        c._offset = offset
        c._set_offsets()
        return c
    
    def _set_offsets(self):
        """Updates the offsets of all members based on their position in the sequence.

        Members may be ``TemporalUnit``, ``CompositionalUnit``,
        ``TemporalUnitSequence``, or ``TemporalBlock``; ``_reoffset``
        dispatches the correct cascade for each.

        Records the member durations it worked from, so ``_ensure_offsets``
        can tell later whether they still hold.
        """
        running_offset = self._offset
        geometry = []
        for ut in self._seq:
            _reoffset(ut, running_offset)
            duration = ut.duration
            geometry.append(duration)
            running_offset += duration
        self._geometry = tuple(geometry)

    def _read_geometry(self):
        """The member durations, in sequence order -- the only input
        ``_set_offsets`` reads besides ``_offset``.

        Nested containers are asked through the public :attr:`duration`
        reader so that they validate their own placement before answering.
        """
        return tuple(ut.duration for ut in self._seq)

    def _ensure_offsets(self):
        """Re-offset if a member's duration changed since the last pass.

        A sequence hands out its **live** members, and a member may itself
        be a container: ``s[0].append(...)`` or ``s[0].remove(...)``
        changes the running sum ``_set_offsets`` was computed from without
        any sequence-level mutator running. The sequence then reports
        members that overlap -- member 0 ending past where member 1 starts
        -- with no exception and no warning. Every reader that hands out a
        live member goes through here, so the validation is lazy rather
        than eager, exactly as ``TemporalBlock._ensure_aligned`` is for the
        block's row alignment.

        Cheap because it is the same read ``_set_offsets`` would do first
        anyway, and a no-op for a sequence nobody mutated through a member
        -- ``_set_offsets`` assigns offsets absolutely, so re-running it is
        idempotent and never reorders or rebuilds the member list.
        """
        if self._read_geometry() != self._geometry:
            self._set_offsets()

    @property
    def seq(self):
        """The list of TemporalUnit objects in the sequence.

        The members are **live**, so their placement is validated on the way
        out -- a member mutated through its own API since the last pass
        re-offsets every member after it (see ``_ensure_offsets``).
        """
        self._ensure_offsets()
        return self._seq

    @property
    def onsets(self):
        """A tuple of onset times (in seconds) for each TemporalUnit in the sequence."""
        return calc_onsets(self.durations)
    
    @property    
    def durations(self):
        """A tuple of durations (in seconds) for each TemporalUnit in the sequence."""
        return tuple(ut.duration for ut in self._seq)
    
    @property
    def duration(self):
        """The total duration (in seconds) of the sequence."""
        return sum(abs(d) for d in self.durations)
    
    @property
    def start(self) -> float:
        """Absolute start time in seconds (``0`` outside a Score)."""
        return self._offset

    @property
    def end(self) -> float:
        """Absolute end time in seconds (``start + duration``)."""
        return self._offset + self.duration

    @property
    def size(self):
        """The total number of events across all TemporalUnits in the sequence."""
        return sum(len(ut) for ut in self._seq)
    
    @property
    def time(self):
        """The absolute start and end times (in seconds) of the sequence."""
        return self._offset, self._offset + self.duration

    @property
    def events(self):
        """A :class:`~pandas.DataFrame` of every event in the sequence, by date.

        One row per event, flattened across all members and ordered by
        ``start``. Nesting is flattened too: a member may itself be a
        :class:`TemporalUnitSequence` or a :class:`TemporalBlock`.

        This is :attr:`TemporalBlock.events`' contract with one
        substitution, and it exists for the same reason: a
        :class:`~klotho.thetos.composition.compositional.CompositionalUnit`
        placed in a container must not lose its parameters on the way into
        the table (BT-12). The substitution is the identity column --
        see ``member`` below.

        Columns
        -------
        ``member``
            Index of the **top-level** sequence member the event came
            from. Needed because ``node_id`` is *not* unique across
            members: two structurally identical units both number their
            leaves ``1, 2, 3``, so ``(member, node_id)`` is the
            identifying pair.

            Where a block calls this column ``row`` and adds a second,
            ``voice``, a sequence has one column and it is neither.
            Members here are **successive, not simultaneous**:
            :func:`~klotho.chronos.temporal_units.algorithms.interleave`
            calls its result "one single-voice ``TemporalUnitSequence``",
            and ``_walk_block_events`` already declines to extend a
            block's voice path through a sequence for exactly this
            reason. So ``member`` is a position in time, not a part
            assignment, and there is no dotted voice path to report. It
            is an ``int``, not the block's dotted string.
        ``node_id``, ``start``, ``duration``, ``end``, ``is_rest``, ``s``, ``metric_onset``, ``metric_duration``
            Exactly the columns of :attr:`TemporalUnit.events`.

        The nine columns above are the guaranteed contract and always come
        first. AFTER them, a ``CompositionalUnit`` member contributes
        exactly the columns its own ``events`` table shows minus the
        timing ones -- ``instrument``, then one column per pfield, then
        one per mfield -- unioned across every such member and NaN-filled
        wherever a row does not carry them. A sequence with no
        ``CompositionalUnit`` anywhere in it reports the nine columns
        alone. **A mixed sequence is the normal case**, not an edge one:
        ``interleave`` zips whole units untouched, so its result routinely
        holds plain :class:`TemporalUnit`\\ s and ``CompositionalUnit``\\ s
        side by side, and the plain ones simply have no parameters to show.

        A parameter whose name collides with one of the nine (a pfield
        called ``duration``, or one called ``member``) is NOT appended:
        the structural column wins, and the parameter is still readable on
        the unit itself. A name registered as both a pfield and an mfield
        on the same unit resolves the same way ``uc.events`` resolves it --
        the mfield wins the column. Both collisions raise a
        ``UserWarning`` naming the shadowed field(s); a sequence with no
        collision warns about neither.

        ``start`` and ``end`` are **absolute** seconds: they include the
        sequence's own offset and each member's position within it, so a
        member's events are reported where the member sounds rather than
        at its local zero.

        Ordering is by ``start``, then by ``member``; events that share
        both keep their discovery order (the sort is stable). For a flat
        sequence that is already the reading order -- the sort matters
        only where a nested block puts several events on the same date.

        Notes
        -----
        Events are **tie groups**, not leaves (``07_TIES_CHARTER.md`` §2):
        a tied group contributes one event, anchored at its head, whose
        duration is the sum over its members. Rests are present, with
        ``is_rest`` true and a positive ``duration``.

        A member that is a :class:`TemporalBlock` is flattened like any
        other container, but its rows sound **in parallel** and this table
        has no column to say which row an event came from -- they share
        one ``member`` value. That case warns, and the block's own
        :attr:`TemporalBlock.events` is where voice identity lives.

        The table is **computed on every read, not cached**, for the
        reason :attr:`TemporalBlock.events` gives: a correct cache key
        would have to recurse over every member's structure version,
        tempo, beat and offset across four container types, and the
        sequence hands out its members **live**, so a member mutated
        through its own API would defeat an identity-based key.

        Returns
        -------
        pandas.DataFrame
        """
        self._ensure_offsets()
        from klotho.thetos.composition.compositional import (
            CompositionalUnit, Parametron)
        data = []
        param_columns = []          # union of contributed keys, first seen first
        seen = set()
        # Collected across the whole sequence and warned once each, matching
        # the one-warning-per-read shape of ``uc.events`` and
        # ``TemporalBlock.events`` rather than one warning per event.
        shadowed_structural: set = set()
        shadowed_namespace: set = set()
        parallel_members: set = set()
        for i, member in enumerate(self._seq):
            # Seeded with the EMPTY path: a sequence is one voice, so there
            # is no top-level voice index to start from. The walker only
            # extends the path through a nested TemporalBlock, which makes a
            # member that yields more than one distinct path exactly the
            # member whose parallel rows this table cannot tell apart.
            paths = set()
            for path, c in _walk_block_events(member, ''):
                paths.add(path)
                event = {
                    'member': i,
                    'node_id': c.node_id,
                    'start': c.start,
                    'duration': c.duration,
                    'end': c.end,
                    'is_rest': c.is_rest,
                    's': c.proportion,
                    'metric_onset': c.metric_onset,
                    'metric_duration': c.metric_duration,
                }
                if isinstance(c, Parametron):
                    # Exactly the columns this event's own unit would show
                    # in ``uc.events``, minus the timing ones: instrument
                    # first (present even when unbound, as it is there),
                    # then pfields, then mfields.
                    pf = c.pfields
                    mf = c.mfields
                    # A name registered in BOTH namespaces is two
                    # independent values and one column; ``extra.update``
                    # below lets the mfield win, and the warning says so.
                    both = pf.keys() & mf.keys()
                    if both:
                        shadowed_namespace.update(both)
                    extra = {'instrument': CompositionalUnit._instrument_display(
                        c._resolve_instrument())}
                    extra.update(pf)
                    extra.update(mf)
                    for key, value in extra.items():
                        # The nine structural columns are the guaranteed
                        # contract, so they win and the collision is
                        # dropped rather than silently overwriting a timing
                        # value -- or the member index -- with a parameter.
                        if key in _SEQUENCE_EVENT_COLUMNS:
                            shadowed_structural.add(key)
                            continue
                        if key not in seen:
                            seen.add(key)
                            param_columns.append(key)
                        event[key] = value
                data.append(event)
            if len(paths) > 1:
                parallel_members.add(i)
        if shadowed_structural:
            warnings.warn(
                f"{sorted(shadowed_structural)} name structural columns of "
                f"TemporalUnitSequence.events and are not shown in the "
                f"table: the sequence's own member/node_id/start/duration/"
                f"end/is_rest/s/metric_onset/metric_duration always win "
                f"there. The field itself is unaffected -- it still reaches "
                f"the synth, and you can read it with uc.get_pfield(node, "
                f"key) / uc.get_mfield(node, key) or on uc.pt. Rename it if "
                f"you want it in the table.",
                UserWarning,
                stacklevel=2,
            )
        if shadowed_namespace:
            warnings.warn(
                f"{sorted(shadowed_namespace)} name both a pfield and an "
                f"mfield on a unit in this sequence; the table shows the "
                f"mfield. They are separate values -- read the pfield with "
                f"uc.get_pfield(node, key) on the unit itself, and it "
                f"still reaches the synth.",
                UserWarning,
                stacklevel=2,
            )
        if parallel_members:
            warnings.warn(
                f"members {sorted(parallel_members)} of this "
                f"TemporalUnitSequence hold a TemporalBlock, whose rows "
                f"sound in parallel. A sequence is one voice, so this table "
                f"has no voice column and those parallel rows share a "
                f"single member value -- their events are flattened "
                f"together and (member, node_id) does not identify a row "
                f"there. Read that TemporalBlock's own .events for voice "
                f"identity.",
                UserWarning,
                stacklevel=2,
            )
        df = pd.DataFrame(data,
                          columns=list(_SEQUENCE_EVENT_COLUMNS) + param_columns)
        if len(df):
            df = df.sort_values(['start', 'member'], kind='stable',
                                ignore_index=True)
        return df

    def _scale_bpm(self, factor: float) -> None:
        """Multiply every member's bpm by ``factor`` and recompute offsets.

        Private; used by :class:`~klotho.thetos.composition.score.ScoreItem`
        to stretch a sequence's total duration while preserving the relative
        durations between its members.
        """
        for ut in self._seq:
            ut._scale_bpm(factor)
        self._set_offsets()

    
    def append(self, ut: TemporalUnit, repeat: int = 1) -> None:
        """
        Append a temporal unit to the end of the sequence.

        Parameters
        ----------
        ut : TemporalUnit
            The unit to append.
        repeat : int, optional
            Number of independent copies to append. Default is 1.
        """
        for _ in range(repeat):
            self._seq.append(ut.copy())
        self._set_offsets()
        
    def prepend(self, ut: TemporalUnit) -> None:
        """
        Prepend a temporal unit to the beginning of the sequence.

        Parameters
        ----------
        ut : TemporalUnit
            The unit to prepend.
        """
        self._seq.insert(0, ut.copy())
        self._set_offsets()
        
    def insert(self, index: int, ut: TemporalUnit) -> None:
        """
        Insert a temporal unit at the specified index.

        Parameters
        ----------
        index : int
            The position at which to insert.
        ut : TemporalUnit
            The unit to insert.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._seq) <= index <= len(self._seq):
            raise IndexError(f"Index {index} out of range for sequence of length {len(self._seq)}")
        
        self._seq.insert(index, ut.copy())
        self._set_offsets()
        
    def remove(self, index: int) -> None:
        """
        Remove the temporal unit at the specified index.

        Parameters
        ----------
        index : int
            The index of the unit to remove.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._seq) <= index < len(self._seq):
            raise IndexError(f"Index {index} out of range for sequence of length {len(self._seq)}")
        
        self._seq.pop(index)
        self._set_offsets()
        
    def replace(self, index: int, ut: TemporalUnit) -> None:
        """
        Replace the temporal unit at the specified index.

        Parameters
        ----------
        index : int
            The index of the unit to replace.
        ut : TemporalUnit
            The replacement unit.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._seq) <= index < len(self._seq):
            raise IndexError(f"Index {index} out of range for sequence of length {len(self._seq)}")
        
        self._seq[index] = ut.copy()
        self._set_offsets()
        
    def extend(self, other_seq, repeat: int = 1) -> None:
        """
        Extend the sequence by appending all units from another iterable.

        The operand is read once, up front, before anything is appended. So a
        sequence can extend by itself -- ``seq.extend(seq)`` doubles it, the
        same as ``list.extend`` -- and a one-shot iterable such as a generator
        is repeated ``repeat`` times rather than being exhausted by the first
        pass. Each unit is copied on entry, so the appended units are never the
        operand's own objects.

        Parameters
        ----------
        other_seq : TemporalUnitSequence or iterable of TemporalUnit
            The source of units to append.
        repeat : int, optional
            Number of times to repeat the extension. Default is 1. Every
            repetition appends the operand's *pre-call* contents, so
            ``seq.extend(seq, repeat=n)`` grows the sequence by a factor of
            ``n + 1``, not ``2 ** n``.
        """
        snapshot = list(other_seq)
        for _ in range(repeat):
            for ut in snapshot:
                self._seq.append(ut.copy())
        self._set_offsets()

    def __getitem__(self, idx: int) -> TemporalUnit:
        self._ensure_offsets()
        return self._seq[idx]

    def __setitem__(self, idx: int, ut: TemporalUnit) -> None:
        self._seq[idx] = ut.copy()
        self._set_offsets()

    def __iter__(self):
        self._ensure_offsets()
        return iter(self._seq)

    def __len__(self):
        return len(self._seq)

    def __str__(self):
        self._ensure_offsets()
        rows = []
        for ut in self._seq:
            if hasattr(ut, 'tempus'):
                rows.append({
                    'Tempus': ut.tempus,
                    'Type': ut.type.name[0] if ut.type else '',
                    'Tempo': f'{ut.beat} = {round(ut.bpm, 3)}',
                    'Start': seconds_to_hmsms(ut.time[0]),
                    'Duration': seconds_to_hmsms(ut.duration),
                    'End': seconds_to_hmsms(ut.time[1]),
                })
            else:
                # Container member (TemporalUnitSequence / TemporalBlock)
                rows.append({
                    'Tempus': type(ut).__name__,
                    'Type': '',
                    'Tempo': '',
                    'Start': seconds_to_hmsms(ut.start),
                    'Duration': seconds_to_hmsms(ut.duration),
                    'End': seconds_to_hmsms(ut.end),
                })
        return pd.DataFrame(rows).__str__()

    def __repr__(self):
        return self.__str__()

    def copy(self):
        """Create a deep copy of this TemporalUnitSequence.

        Internal placement (``_offset``) is preserved on the copy so that
        :class:`TemporalBlock` and :class:`~klotho.thetos.composition.score.Score`
        can rebuild their layouts cleanly.
        """
        return TemporalUnitSequence._adopt(
            [ut.copy() for ut in self._seq], offset=self._offset)


_SORT_ROWS_UNSET = object()


def _validate_axis(axis):
    """Validate and coerce an alignment axis. Single source of truth.

    NEW-11: the setter validated and the constructor did not, so
    ``TemporalBlock(axis=5)`` was accepted and pushed rows outside the
    block's own span, while ``blk.axis = 5`` raised. The setter also
    coerced to float and the constructor did not, so ``BT(axis=0).axis``
    was ``0`` but ``blk.axis = 0`` gave ``0.0``.
    """
    if not -1 <= axis <= 1:
        raise ValueError("Axis must be between -1 and 1")
    return float(axis)


# Column order of TemporalUnit.events -- the shared tail of every container
# table below, so a unit table, a sequence table and a block table can all
# be read the same way. Derived rather than repeated: the "the tail is
# exactly the unit's columns" promise is made in three docstrings, and two
# hand-copied tuples would drift apart silently.
_UNIT_EVENT_COLUMNS = ('node_id', 'start', 'duration', 'end', 'is_rest',
                       's', 'metric_onset', 'metric_duration')

# Column order of TemporalBlock.events: ``row`` and ``voice`` are the two
# identity columns the merge adds, because a block's rows are SIMULTANEOUS
# and row order is voice assignment. These are the GUARANTEED LEADING
# columns: a CompositionalUnit row appends its instrument and parameter
# columns after them (BT-12). See TemporalBlock.events.
_BLOCK_EVENT_COLUMNS = ('row', 'voice') + _UNIT_EVENT_COLUMNS

# Column order of TemporalUnitSequence.events. One identity column, not
# two, and it is neither of the block's: a sequence's members are
# SUCCESSIVE, so ``member`` is a position in time rather than a part
# assignment. ``interleave`` calls its result "one single-voice
# TemporalUnitSequence" and ``_walk_block_events`` already declines to
# extend the voice path through a sequence for the same reason, so there
# is no voice here to name. See TemporalUnitSequence.events.
_SEQUENCE_EVENT_COLUMNS = ('member',) + _UNIT_EVENT_COLUMNS


class TemporalBlock(_RepeatableTemporal, metaclass=TemporalMeta):
    """
    A collection of parallel temporal structures representing simultaneous events.

    Each row can be a :class:`TemporalUnit`, :class:`TemporalUnitSequence`,
    or another ``TemporalBlock``. Rows are aligned according to the *axis*
    parameter and optionally sorted by duration.

    **This is NOT Haddad's time-block** (docket DOC-4). His *time-block* is
    one measure -- a tempus plus its prolatio -- which is Klotho's
    :class:`TemporalUnit`, not this class. A parallel stack of rows on a
    shared clock with an alignment axis **has no counterpart in Haddad at
    all**: he has no such object and no such term. His polyphony arises
    from *operations on* time-blocks -- canon, homothety, substitution --
    never from a container class.

    So ``TemporalBlock`` is a **Klotho-original polyphonic container**
    wearing a label borrowed from him. The name is kept because renaming is
    a breaking change and is not obviously worth it; this paragraph is the
    cheap fix, and it exists so that nobody reads the name as a citation.

    Parameters
    ----------
    rows : list, optional
        Temporal structures (``TemporalUnit``, ``TemporalUnitSequence``,
        or ``TemporalBlock``). Default is an empty list.

        Rows are **copied on entry**. Mutating the original afterwards
        does not reach the block, and ``blk[0] is row`` is False. The same
        applies to every mutator (``append``, ``prepend``, ``insert``,
        ``replace``, ``extend``).
    axis : float, optional
        Alignment axis from -1 (left) through 0 (center) to 1 (right).
        Default is -1. Must lie in [-1, 1].
    sort_rows : bool, optional
        Whether to sort rows by duration, longest first (index 0). Default
        is True.

        .. warning::
           This default is scheduled to become ``False``. While it is
           True, **row order is not the order you passed**: ``BT([short,
           long])`` comes back ``[long, short]``, which silently renames
           anything keyed by row index -- lane assignment in playback,
           plot lanes, and Score promotion. It also makes ``append``,
           ``prepend`` and ``insert`` positionally meaningless, since
           every mutator re-sorts. Pass ``sort_rows`` explicitly to
           silence the FutureWarning and to pin the behavior you want.

    Notes
    -----
    Outside a :class:`~klotho.thetos.composition.score.Score`, a block
    always starts at time 0. What is fixed is the **start**, not the
    duration: ``duration`` is the longest row's duration, so the block's
    own mutators change it, and so does mutating a row *through the row's
    own API* -- ``rows`` hands out the live row objects, and
    ``blk.rows[0].append(...)`` lengthens the block and re-offsets every
    other row. There is no duration setter on the block itself; to re-time
    one on a timeline, add it to a ``Score`` and use
    :meth:`~klotho.thetos.composition.score.ScoreItem.set_duration`.

    Alignment is validated **lazily**, like ``events``: every reader whose
    answer depends on it (``rows``, ``duration``, ``end``,
    ``principal_row``, ``events``, ``__getitem__``, ``__iter__``) first
    calls ``_ensure_aligned``, which re-runs ``_align_rows`` when the row
    durations differ from the geometry the last alignment saw. Reading
    ``blk._rows`` directly bypasses that and can observe stale offsets.

    The sort is **destructive**: the pre-sort order is not retained, so
    setting ``sort_rows = False`` afterwards realigns but cannot restore
    the order you passed.
    """
    
    def __init__(self,
                 rows:Union[list[Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']], None]=None,
                 axis:float = -1,
                 sort_rows=_SORT_ROWS_UNSET):
        if rows is None:
            rows = []
        explicit = sort_rows is not _SORT_ROWS_UNSET
        if not explicit:
            sort_rows = True
        self._rows = [row.copy() for row in rows] if rows else []
        self._axis = _validate_axis(axis)
        self._offset = 0.0
        self._sort_rows = sort_rows

        pre_sort = list(self._rows)
        self._align_rows()
        # WL-32: warn only when the default actually reordered somebody's
        # rows. Silent for explicit callers, single-row blocks, and blocks
        # that were already in longest-first order -- so the warning marks
        # real exposure to the coming flip, not merely constructing a block.
        if not explicit and sort_rows and len(self._rows) > 1 and self._rows != pre_sort:
            warnings.warn(
                "TemporalBlock currently sorts rows by duration (longest "
                "first), so the row order is not the order you passed. This "
                "default will become sort_rows=False. Pass sort_rows "
                "explicitly to pin the behavior you want and silence this "
                "warning.",
                FutureWarning,
                stacklevel=2,
            )

    @classmethod
    def _adopt(cls, rows, axis=-1, sort_rows=True, offset=0.0):
        """Private: build a block that takes ownership of *rows* WITHOUT
        copying them. Used by ``copy()`` (whose rows are already fresh
        copies) to avoid the constructor's second copy of every row."""
        c = cls.__new__(cls)
        c._rows = list(rows)
        c._axis = _validate_axis(axis)
        c._offset = offset
        c._sort_rows = sort_rows
        c._align_rows()
        return c
      
    # TODO: make free method in UT algos
    # Matrix to Block
    @classmethod
    def from_tree_mat(cls, matrix, meas_denom:int=1, subdiv:bool=False,
                      rotation_offset:int=1, beat=None, bpm=None,
                      axis:float=-1, sort_rows=_SORT_ROWS_UNSET):
        """
        Create a ``TemporalBlock`` from a matrix of tree specifications.

        Parameters
        ----------
        matrix : tuple of tuple
            Matrix where each element is a ``(D, S)`` pair.
        meas_denom : int, optional
            Denominator for measure fractions. Default is 1.
        subdiv : bool, optional
            Whether to apply automatic subdivision. Default is False. That
            path also reverses each cell's S -- see Notes.
        rotation_offset : int, optional
            Base offset for the ``subdiv`` rotation; ignored when ``subdiv``
            is False. Default is 1. See Notes for the formula.
        beat : Fraction, str, float, or None, optional
            Beat ratio specification. Default is None.
        bpm : int, float, or None, optional
            Beats per minute. Default is None.
        axis : float, optional
            Temporal alignment axis for the block: ``-1`` aligns rows at
            their starts, ``1`` at their ends, ``0`` centers them. Default
            is -1.
        sort_rows : bool, optional
            Passed through to the block. When True, rows are reordered by
            duration (longest first), so row order no longer matches the
            matrix. Leaving it unset warns, because the default is scheduled
            to become False.

        Returns
        -------
        TemporalBlock

        Notes
        -----
        A negative ``D`` produces a rest: the measure takes ``abs(D)`` as its
        numerator and the cell's S is discarded in favour of ``'r'``. The sign
        is a rest flag, not a duration.

        With ``subdiv=True`` each cell's S is **reversed** before subdivision
        -- ``auto_subdiv(S[::-1], rotation_offset*i - j - i)`` for the cell at
        row *i*, column *j*. That formula is not the one
        :func:`~klotho.chronos.rhythm_trees.algorithms.auto_subdiv_matrix`
        uses (``j - i + rotation_offset*i``, no reversal); the two are easy to
        assume identical and are not. At the default ``rotation_offset=1`` the
        row index cancels here too -- ``1*i - j - i == -j`` -- so the effective
        offset depends on the column alone and identical input rows give
        identical output rows. Pass ``rotation_offset != 1`` for it to vary by
        row.
        """
        tb = []
        for i, row in enumerate(matrix):
            seq = []
            for j, e in enumerate(row):
                offset = rotation_offset * i
                if subdiv:
                    D, S = e[0], auto_subdiv(e[1][::-1], offset - j - i)
                else:
                    D, S = e[0], e[1]
                seq.append(TemporalUnit(tempus   = Meas(abs(D), meas_denom),
                                        prolatio = S if D > 0 else 'r',
                                        bpm      = bpm,
                                        beat     = beat))
            tb.append(TemporalUnitSequence(seq))
        return cls(tuple(tb), axis=axis, sort_rows=sort_rows)

    def _align_rows(self):
        """
        Aligns the rows based on the current axis value and optionally sorts them by duration.
        If sorting is enabled, the longest duration will be at the bottom (index 0), 
        shortest at the top. If two rows have the same duration, their original order is preserved.
        """
        if not self._rows:
            self._geometry = ()
            return

        row_duration_pairs = [(row, row.duration) for row in self._rows]
        if self._sort_rows:
            row_duration_pairs = sorted(row_duration_pairs, key=lambda pair: -pair[1], reverse=False)
            self._rows = [pair[0] for pair in row_duration_pairs]

        max_duration = max(duration for _, duration in row_duration_pairs)

        for row, row_duration in row_duration_pairs:
            if row_duration == max_duration:
                _reoffset(row, self._offset)
                continue

            duration_diff = max_duration - row_duration
            adjustment = duration_diff * (self._axis + 1) / 2
            _reoffset(row, self._offset + adjustment)

        self._geometry = tuple(duration for _, duration in row_duration_pairs)

    def _read_geometry(self):
        """The row durations, in row order -- the only input ``_align_rows``
        reads besides ``axis``/``offset``.

        Nested blocks are asked through the public :attr:`duration` reader so
        that they validate their own alignment before answering.
        """
        return tuple(row.duration for row in self._rows)

    def _ensure_aligned(self):
        """Realign if a row's duration changed since the last alignment, and
        return the current row durations.

        BT-4 declined to cache :attr:`events` precisely because :attr:`rows`
        hands out the **live** row objects. The alignment offsets are the
        cache that decision missed: a row mutated through its own API
        (``uts.append(...)``, ``uts.remove(...)``) changes the geometry
        ``_align_rows`` was computed from without any block-level mutator
        running, and the block then reports absolute times outside its own
        ``start``..``end``. Every reader whose answer depends on alignment
        goes through here, so validation is as lazy as ``events`` already is.

        Cheap because it is exactly the read ``_align_rows`` would do first
        anyway, and a no-op for a block nobody mutated through a live row --
        ``_align_rows`` is idempotent (offsets are assigned absolutely and
        the duration sort is stable).
        """
        geometry = self._read_geometry()
        if geometry != self._geometry:
            self._align_rows()
            geometry = self._geometry
        return geometry

    @property
    def height(self):
        """The number of rows in the block."""
        return len(self._rows)
    
    @property
    def rows(self):
        """The list of temporal structures in the block.

        The rows are **live**, so their placement is validated on the way out
        -- a row mutated through its own API since the last alignment moves
        every row's offset (see ``_ensure_aligned``).
        """
        self._ensure_aligned()
        return self._rows

    @property
    def duration(self):
        """The total duration (in seconds) of the longest row in the block."""
        geometry = self._ensure_aligned()
        return max(geometry) if geometry else 0.0

    @property
    def axis(self):
        """The temporal axis position of the block."""
        return self._axis
    
    @property
    def start(self) -> float:
        """Absolute start time in seconds (``0`` outside a Score)."""
        return self._offset

    @property
    def end(self) -> float:
        """Absolute end time in seconds (``start + duration``)."""
        return self._offset + self.duration

    @property
    def principal_row(self):
        """The row whose end is latest -- ``None`` for an empty block.

        A **Klotho-original** notion, like the block it belongs to: Haddad
        has no polyphonic container and therefore no "principal row" (see
        the class docstring, docket DOC-4).

        Ties charter sect7 defines "the last leaf of a ``TemporalBlock``" as
        the last leaf of this row. The definition is deliberately
        **axis- and sort-independent**: it reads the geometry that the
        current axis produced instead of assuming ``rows[-1]``, which under
        the ``sort_rows=True`` default is the *shortest* row and need not
        end at the block's end at all.

        Tie-break: the **bottom-most** (highest-index) row among those that
        end latest. Ties are the normal case at ``axis=1``, where every row
        is aligned on its end. Because a shifted row's end is computed as
        ``offset + (max - d) + d``, it can miss the longest row's end by a
        float ulp, so the comparison is made with a small relative
        tolerance rather than by exact equality.

        Returns
        -------
        TemporalUnit, TemporalUnitSequence, TemporalBlock, or None
            The live row object, not a copy.
        """
        if not self._rows:
            return None
        self._ensure_aligned()
        ends = [row.end for row in self._rows]
        latest = max(ends)
        tolerance = 1e-9 * max(1.0, abs(latest))
        for i in range(len(ends) - 1, -1, -1):
            if abs(ends[i] - latest) <= tolerance:
                return self._rows[i]
        return self._rows[-1]

    @property
    def events(self):
        """A :class:`~pandas.DataFrame` of every event in the block, by date.

        One row per event, flattened across all voices and ordered by
        ``start``. Nesting is flattened too: a row may itself be a
        :class:`TemporalUnitSequence` or a nested ``TemporalBlock``.

        Like the block itself, this surface is **Klotho's own** and has no
        Haddad counterpart (docket DOC-4). The row-is-a-voice reading below
        is Klotho's convention, not a citation.

        Columns
        -------
        ``row``
            Index of the **top-level** block row the event came from --
            its "voice", since in this container row order is voice
            assignment.
            Needed because ``node_id`` is *not* unique across rows: two
            structurally identical rows both number their leaves ``1, 2,
            3``, so ``(row, node_id)`` is the identifying pair.
        ``voice``
            Dotted path to the *innermost* block row, as a string: ``'1'``
            for a plain row, ``'0.1'`` for the second row of a block nested
            in row 0. A ``TemporalUnitSequence`` does not extend the path,
            because its members are successive, not simultaneous. Without
            this column the parallel sub-rows of a nested block would merge
            indistinguishably into one ``row`` value, and the
            synchronic/diachronic reading below would be uncomputable
            there.
        ``node_id``, ``start``, ``duration``, ``end``, ``is_rest``, ``s``, ``metric_onset``, ``metric_duration``
            Exactly the columns of :attr:`TemporalUnit.events`.

        The ten columns above are the guaranteed contract and always come
        first. AFTER them, a
        :class:`~klotho.thetos.composition.compositional.CompositionalUnit`
        row contributes exactly the columns its own ``events`` table shows
        minus the timing ones — ``instrument``, then one column per pfield,
        then one per mfield — unioned across every such row and NaN-filled
        wherever a row does not carry them (BT-12). A block with no
        ``CompositionalUnit`` anywhere in it reports the ten columns alone.
        A parameter whose name collides with a timing column (a pfield
        called ``duration``, say) is NOT appended: the timing column wins,
        and the parameter is still readable on the unit itself. A name
        registered as both a pfield and an mfield on the same unit resolves
        the same way ``uc.events`` resolves it -- the mfield wins the
        column. Both collisions raise a ``UserWarning`` naming the
        shadowed field(s); a block with no collision warns about neither.

        ``start`` and ``end`` are **absolute** seconds: they include the
        block's own offset and every row's alignment offset, so the table
        is directly comparable across voices under any ``axis``.

        Ordering is by ``start``, then by ``row``; events that share both
        keep their discovery order (the sort is stable).

        Notes
        -----
        Events are **tie groups**, not leaves (``07_TIES_CHARTER.md`` §2):
        a tied group contributes one event, anchored at its head, whose
        duration is the sum over its members. Rests are present, with
        ``is_rest`` true and a positive ``duration``.

        The table is **computed on every read, not cached**. A correct
        cache key would have to recurse over every leaf unit's structure
        version, tempo, beat and offset, mirroring three container types
        plus ``CompositionalUnit``'s parameter version -- and
        :attr:`rows` hands out the *live* row list, so a row swapped in
        place would defeat any identity-based key without going through
        ``_align_rows``. Correctness is worth more here than the saving.

        Returns
        -------
        pandas.DataFrame
        """
        self._ensure_aligned()
        # BT-12: the ten timing keys below used to be the WHOLE row, so a
        # CompositionalUnit's instrument and pfields — visible in that unit's
        # own ``events`` — vanished the moment it was placed in a block. The
        # sound was never affected (lowering reads the units, not this table);
        # the table lied by omission, which is why the answer is to show the
        # data rather than to refuse anything.
        from klotho.thetos.composition.compositional import (
            CompositionalUnit, Parametron)
        data = []
        param_columns = []          # union of contributed keys, first seen first
        seen = set()
        # Two collision kinds this table can hide, both resolved the same
        # way ``uc.events`` resolves them (the narrower namespace wins) but
        # -- until now -- with no disclosure here at all. Collected across
        # every row and warned once, matching ``uc.events``'s one-warning-
        # per-read shape rather than one per event.
        shadowed_structural: set = set()
        shadowed_namespace: set = set()
        for i, row in enumerate(self._rows):
            for voice, c in _walk_block_events(row, str(i)):
                event = {
                    'row': i,
                    'voice': voice,
                    'node_id': c.node_id,
                    'start': c.start,
                    'duration': c.duration,
                    'end': c.end,
                    'is_rest': c.is_rest,
                    's': c.proportion,
                    'metric_onset': c.metric_onset,
                    'metric_duration': c.metric_duration,
                }
                if isinstance(c, Parametron):
                    # Exactly the columns this event's own unit would show
                    # in ``uc.events``, minus the timing ones: instrument
                    # first (present even when unbound, as it is there),
                    # then pfields, then mfields.
                    pf = c.pfields
                    mf = c.mfields
                    # A name registered in BOTH namespaces (post pfield/
                    # mfield split) is two independent values and one
                    # column; ``extra.update`` below already lets the
                    # mfield win (it is merged in second), silently. Same
                    # shape of gap as the structural one, just newer.
                    both = pf.keys() & mf.keys()
                    if both:
                        shadowed_namespace.update(both)
                    extra = {'instrument': CompositionalUnit._instrument_display(
                        c._resolve_instrument())}
                    extra.update(pf)
                    extra.update(mf)
                    for key, value in extra.items():
                        # A pfield may legitimately be named ``duration``
                        # (the duration-injection control). The timing
                        # columns are the guaranteed contract, so they win
                        # and the collision is dropped rather than silently
                        # overwriting a timing value with a parameter.
                        if key in _BLOCK_EVENT_COLUMNS:
                            shadowed_structural.add(key)
                            continue
                        if key not in seen:
                            seen.add(key)
                            param_columns.append(key)
                        event[key] = value
                data.append(event)
        if shadowed_structural:
            warnings.warn(
                f"{sorted(shadowed_structural)} name structural columns of "
                f"TemporalBlock.events and are not shown in the table: the "
                f"block's own row/voice/node_id/start/duration/end/is_rest/"
                f"s/metric_onset/metric_duration always win there. The "
                f"field itself is unaffected -- it still reaches the synth, "
                f"and you can read it with uc.get_pfield(node, key) / "
                f"uc.get_mfield(node, key) or on uc.pt. Rename it if you "
                f"want it in the table.",
                UserWarning,
                stacklevel=2,
            )
        if shadowed_namespace:
            warnings.warn(
                f"{sorted(shadowed_namespace)} name both a pfield and an "
                f"mfield on a unit in this block; the table shows the "
                f"mfield. They are separate values -- read the pfield with "
                f"uc.get_pfield(node, key) on the unit itself, and it "
                f"still reaches the synth.",
                UserWarning,
                stacklevel=2,
            )
        df = pd.DataFrame(data,
                          columns=list(_BLOCK_EVENT_COLUMNS) + param_columns)
        if len(df):
            df = df.sort_values(['start', 'row'], kind='stable',
                                ignore_index=True)
        return df

    @property
    def sort_rows(self):
        """Whether to sort rows by duration (longest at index 0)."""
        return self._sort_rows
    
    @sort_rows.setter
    def sort_rows(self, sort_rows:bool):
        self._sort_rows = sort_rows
        self._align_rows()
        
    @axis.setter
    def axis(self, axis: float):
        """
        Set the temporal axis and realign rows.

        Parameters
        ----------
        axis : float
            Value between -1 and 1 controlling alignment:
            -1 = left-aligned, 0 = centered, 1 = right-aligned.

        Raises
        ------
        ValueError
            If *axis* is outside [-1, 1].
        """
        self._axis = _validate_axis(axis)
        self._align_rows()

    def _scale_bpm(self, factor: float) -> None:
        """Multiply every row's bpm(s) by ``factor`` and realign.

        Private; used by :class:`~klotho.thetos.composition.score.ScoreItem`
        to stretch a block's total duration while preserving the relative
        durations of its rows.
        """
        for row in self._rows:
            row._scale_bpm(factor)
        self._align_rows()

    def prepend(self, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Add a temporal structure at the beginning (index 0) of the block.

        Note that under the default ``sort_rows=True`` the block re-sorts
        after every mutation, so the resulting position is determined by
        duration, not by this call. Row position is only meaningful with
        ``sort_rows=False``. The row is copied on entry.

        Parameters
        ----------
        row : TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The temporal structure to prepend.
        """
        self._rows.insert(0, row.copy())
        self._align_rows()
        
    def append(self, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Add a temporal structure at the end (highest index) of the block.

        Note that under the default ``sort_rows=True`` the block re-sorts
        after every mutation, so the resulting position is determined by
        duration, not by this call. Row position is only meaningful with
        ``sort_rows=False``. The row is copied on entry.

        Parameters
        ----------
        row : TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The temporal structure to append.
        """
        self._rows.append(row.copy())
        self._align_rows()
        
    def insert(self, index: int, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Insert a temporal structure at the specified index.

        Note that under the default ``sort_rows=True`` the block re-sorts
        after every mutation, so the resulting position is determined by
        duration, not by this call. Row position is only meaningful with
        ``sort_rows=False``. The row is copied on entry.

        Parameters
        ----------
        index : int
            The position at which to insert.
        row : TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The temporal structure to insert.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._rows) <= index <= len(self._rows):
            raise IndexError(f"Index {index} out of range for block of height {len(self._rows)}")
        
        self._rows.insert(index, row.copy())
        self._align_rows()

    def remove(self, index: int) -> None:
        """
        Remove the row at the specified index.

        Parameters
        ----------
        index : int
            The index of the row to remove.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._rows) <= index < len(self._rows):
            raise IndexError(f"Index {index} out of range for block of height {len(self._rows)}")
        
        self._rows.pop(index)
        self._align_rows()
        
    def replace(self, index: int, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Replace the row at the specified index.

        Parameters
        ----------
        index : int
            The index of the row to replace.
        row : TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The replacement temporal structure.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._rows) <= index < len(self._rows):
            raise IndexError(f"Index {index} out of range for block of height {len(self._rows)}")
        
        self._rows[index] = row.copy()
        self._align_rows()
        
    def extend(self, other_block: 'TemporalBlock') -> None:
        """
        Extend the block by appending all rows from another block.

        The operand is read once, up front, before anything is appended, so a
        block can extend by itself -- ``blk.extend(blk)`` doubles its rows, the
        same as ``list.extend``. Each row is copied on entry, so the appended
        rows are never the operand's own objects.

        Note that under the default ``sort_rows=True`` the block re-sorts after
        the extension, so the appended rows do not stay at the end.

        Parameters
        ----------
        other_block : TemporalBlock
            The block whose rows will be appended.
        """
        for row in list(other_block):
            self._rows.append(row.copy())
        self._align_rows()

    def __getitem__(self, idx: int) -> Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']:
        self._ensure_aligned()
        return self._rows[idx]

    def __iter__(self):
        self._ensure_aligned()
        return iter(self._rows)
    
    def __len__(self):
        return len(self._rows)
    
    def __str__(self):
        result = (
            f'Rows:     {len(self._rows)}\n'
            f'Axis:     {self._axis}\n'
            f'Duration: {seconds_to_hmsms(self.duration)}\n'
            f'Time:     {seconds_to_hmsms(self._offset)} - {seconds_to_hmsms(self._offset + self.duration)}\n'
            f'{"-" * 50}\n'
        )
        return result

    def __repr__(self):
        return self.__str__()

    def copy(self):
        """Create a deep copy of this TemporalBlock.

        Internal placement (``_offset``) is preserved on the copy so that
        :class:`~klotho.thetos.composition.score.Score` can rebuild its
        timeline cleanly.
        """
        return TemporalBlock._adopt(
            [row.copy() for row in self._rows],
            axis=self._axis,
            sort_rows=self._sort_rows,
            offset=self._offset,
        )


def _walk_block_events(obj, voice: str):
    """Yield ``(voice, Chronon)`` for every event under *obj*, in order.

    Recursion is over containers only. A nested :class:`TemporalBlock`
    extends the voice path (``'0'`` becomes ``'0.0'``, ``'0.1'``) because
    its rows sound at the same time; a :class:`TemporalUnitSequence` leaves
    the path alone, because its members are successive and are the same
    voice.

    The walk is built from each unit's ``_materialize_events()`` rather
    than from any container's onset tuple, for two reasons:

    * ``TemporalUnitSequence.onsets`` ignores the sequence's own
      ``_offset``, so a sequence placed at a non-zero time reports onsets
      relative to itself while its member units correctly report absolute
      ones. Reading it here would put a whole shifted row at the wrong
      absolute time. (That inconsistency is a separate defect; this walk
      routes around it rather than depending on it.)
    * :class:`~klotho.thetos.composition.compositional.CompositionalUnit`
      overrides ``events`` with a different schema (``dur``,
      ``metric_dur``, ``instrument``), so composing the units' DataFrames
      would give ragged columns. Its events are ``Chronon`` subclasses, so
      the Chronon path stays uniform across both kinds of unit.

    Tie-awareness comes for free: ``_materialize_events`` already yields
    one event per tie group (``07_TIES_CHARTER.md`` §2).
    """
    if isinstance(obj, TemporalBlock):
        for i, row in enumerate(obj._rows):
            yield from _walk_block_events(row, f'{voice}.{i}')
    elif isinstance(obj, TemporalUnitSequence):
        # Iterated publicly, not through ``_seq``: the sequence validates its
        # own member placement on the way out. The block's realign does not
        # cover this, because it fires on row *durations* -- a row whose
        # members shifted internally while its total stayed the same leaves
        # the block's geometry unmoved and the row's offsets stale.
        for member in obj:
            yield from _walk_block_events(member, voice)
    else:
        for chronon in obj._materialize_events():
            yield voice, chronon


def _reoffset(unit, t: float) -> None:
    """Assign ``t`` as the internal offset of *unit* and cascade.

    Used by containers (``TemporalBlock``) and
    :class:`~klotho.thetos.composition.score.Score` to position a unit at
    an absolute time without going through a public setter.
    """
    unit._offset = float(t)
    if isinstance(unit, TemporalUnitSequence):
        unit._set_offsets()
    elif isinstance(unit, TemporalBlock):
        unit._align_rows()
    # Plain units need no cache invalidation: the timing cache stores
    # offset-free onsets and reads add _offset on the fly.
