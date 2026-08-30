"""
Rhythm trees.

A rhythm tree (RT) is a list representing a rhythmic structure. This list
is organized hierarchically in sub-lists, just as time is organized in
measures, time signatures, pulses and rhythmic elements in traditional
notation.

See: https://support.ircam.fr/docs/om/om6-manual/co/RT.html
"""
import numbers
from fractions import Fraction
from math import lcm
from typing import Union, Tuple
from tabulate import tabulate

from klotho.topos.graphs import Tree, Group, format_subdivisions
from klotho.topos.graphs.trees import TreeLayer
from .meas import Meas
from .algorithms import ratios_to_subdivs
from ..utils.beat import calc_onsets


# Node-data keys a rebuilt leaf must NOT inherit from the leaf it replaces:
# the rhythm layer recomputes the first four, and `label`/`meta` are
# bookkeeping. Everything else is payload -- pfields, mfields, anything a
# later layer adds -- and travels with its event. The same split is drawn in
# `CompositionalUnit.from_tree`.
_NON_PAYLOAD_KEYS = frozenset({
    'proportion', 'tied', 'metric_duration', 'metric_onset', 'label', 'meta',
})


def _check_proportion_scalar(v, path='proportion', what='proportion'):
    """The ONE scalar rule for a rhythm-tree proportion. (RT-2)

    A proportion is a non-zero integer plus a tie flag. The float encoding
    is exactly that pair -- ``2.0`` means "the integer 2, tied" -- and NOT
    a separate value type with its own arithmetic. Everything downstream
    reads it that way, so a fractional float is not a finer proportion; it
    is a proportion that will be truncated behind the author's back.

    Three surfaces enforce this rule and they used to state it three
    different ways, which is how ``set_node_data(leaf, proportion=1.5)``
    came to be accepted in silence while the constructor refused the same
    value. They now all delegate here and add only their OWN extra rule:

    - the constructor (:meth:`RhythmTree._validate_s_grammar`) adds the
      nested ``(D, S)`` shape;
    - ``subdivide`` (:meth:`RhythmTree._validate_s_form`) adds
      ``len(S) >= 2``, because dividing into one part is a no-op;
    - the write path (:meth:`RhythmLayer.validate_attrs`) adds leaf-only
      ties, since only a leaf sounds and only a sound can be continued.

    Parameters
    ----------
    v : object
        The candidate proportion.
    path : str, optional
        Where ``v`` sits, quoted back in the error so the author can find
        it in a nested structure.
    what : {'proportion', 'D'}, optional
        ``'D'`` marks an interior-node duration, which additionally
        cannot be a float -- ties are leaf-only.

    Returns
    -------
    (int, bool)
        The integer proportion, and whether it carries a tie.

    Raises
    ------
    ValueError
        On a bool, a non-whole float, a float ``D``, a negative float (a
        tied rest), a zero, or any other type.
    """
    if isinstance(v, bool):
        # bool is a subclass of int, so every ``isinstance(x, int)`` test
        # took True for the proportion 1. A boolean is a type confusion,
        # not a duration.
        raise ValueError(
            f"{what} at {path} must be an int or a whole-valued float; "
            f"got bool: {v!r}. A boolean is not a duration."
        )
    if isinstance(v, numbers.Integral):
        value, tied = int(v), False
    elif isinstance(v, float):
        if not v.is_integer():
            raise ValueError(
                f"{what} at {path} must be a whole number "
                f"(an int, or a float marking a tie); got {v!r}. "
                f"Fractional proportions are truncated, not honoured -- "
                f"scale the whole S instead, e.g. (2, 3, 2) for (1, 1.5, 1)."
            )
        if what == 'D':
            # Ties are leaf-only (07_TIES_CHARTER.md sect1, resolved
            # against OpenMusic 2026-08-29: OM6 and om-sharp both give
            # a float group value NO tie meaning -- fullratio and
            # tree2ratio silently round it). Refusing beats silently
            # corrupting.
            raise ValueError(
                f"D at {path} cannot be a float -- ties are leaf-only. "
                f"A tie continues a sound, and only leaves sound; tie "
                f"the group's first leaf instead, e.g. "
                f"({int(v)}, (1.0, ...))."
            )
        if v < 0:
            raise ValueError(
                f"{what} at {path} is a tied rest ({v!r}), which is "
                f"illegal -- a rest continues nothing and nothing "
                f"sounds through it. Use a plain negative int for the "
                f"rest, or a positive float for the tie."
            )
        value, tied = int(v), True
    else:
        raise ValueError(
            f"{what} at {path} must be an int or a whole-valued float; "
            f"got {type(v).__name__}: {v!r}."
        )
    if value == 0:
        raise ValueError(
            f"{what} at {path} cannot be zero -- a zero proportion "
            f"builds a 0-duration leaf and breaks strictly-increasing "
            f"onsets. Use a negative value for a rest."
        )
    return value, tied


class RhythmLayer(TreeLayer):
    """Layer that owns rhythmic proportion data and derives metric timing.

    Owned keys: ``proportion`` (writable), ``tied`` (writable). Derived keys:
    ``metric_duration``, ``metric_onset`` (computed by the tree's ``_evaluate``;
    direct writes are rejected).
    """

    owned_keys = frozenset({'proportion', 'tied'})
    derived_keys = frozenset({'metric_duration', 'metric_onset'})

    def normalize_attrs(self, tree, node, attrs, op):
        """Coerce proportion/tied writes to consistent types (float when tied, int otherwise)."""
        normalized = dict(attrs) if isinstance(attrs, dict) else {}
        if 'label' in normalized:
            raise ValueError("RhythmTree does not accept 'label'; use 'proportion'")

        if op == 'add_child' and 'proportion' not in normalized:
            # default at write time — on_structure_changed no longer scans
            # the whole tree to backfill missing proportions per mutation
            normalized['proportion'] = 1

        if 'tied' in normalized and 'proportion' not in normalized:
            current = tree[node].get('proportion', 1)
            normalized['proportion'] = float(current) if normalized['tied'] else int(current)

        if 'proportion' in normalized and 'tied' in normalized:
            # NEW-32: coerce ONLY a value the scalar rule already accepts.
            # This used to be a bare ``int(proportion)``/``float(proportion)``,
            # which truncated 1.5 to 1 BEFORE validate_attrs ever saw it --
            # so the guard against silent truncation could never fire,
            # because normalization had already done the truncating.
            p = normalized['proportion']
            if (isinstance(p, float) and p.is_integer()) or \
                    (isinstance(p, numbers.Integral) and not isinstance(p, bool)):
                normalized['proportion'] = float(p) if normalized['tied'] else int(p)
            # else: leave it untouched so validate_attrs refuses it by name.

        return normalized

    def validate_attrs(self, tree, node, attrs, op):
        """Reject writes to any key other than ``proportion``/``tied`` (derived keys are read-only)."""
        mutable_keys = {'proportion', 'tied'}
        illegal = [k for k in attrs if k not in mutable_keys]
        if illegal:
            raise ValueError(f"Illegal RhythmTree node attribute update: {illegal}")
        if 'metric_duration' in attrs or 'metric_onset' in attrs:
            raise ValueError("metric_duration and metric_onset are derived and cannot be set directly")
        # The shared scalar rule (RT-2): non-zero int, or a whole float
        # meaning "that int, tied". This is the SAME check the constructor
        # runs, delegated rather than restated -- it closes NEW-05 (zero
        # cannot arrive by mutation, because ``-abs(0) == 0`` leaves a node
        # neither sounding nor resting) and NEW-32 (a fractional float
        # cannot arrive by mutation, because it was stored truncated and
        # tied, silently merging two sounds into one).
        if 'proportion' in attrs:
            _check_proportion_scalar(attrs['proportion'], 'proportion',
                                     'proportion')
        # The write path's OWN addition: ties are leaf-only and never on
        # rests (07_TIES_CHARTER.md sect1). Position is not visible to the
        # scalar rule, so it cannot live there.
        tie_requested = (bool(attrs.get('tied', False))
                         or isinstance(attrs.get('proportion'), float))
        if tie_requested:
            prop = attrs.get('proportion', tree[node].get('proportion', 1))
            if prop < 0:
                raise ValueError(
                    "a rest cannot be tied -- a rest continues nothing and "
                    "nothing sounds through it. Clear the rest first, or tie "
                    "a sounding leaf."
                )
            if op != 'add_child' and tree.out_degree(node) > 0:
                raise ValueError(
                    "tied is leaf-only -- a tie continues a sound, and only "
                    "leaves sound. Tie the group's first leaf instead. "
                    "(Resolved against OpenMusic: a float group value has no "
                    "meaning there either -- OM silently rounds it.)"
                )

    def data_scope(self, tree, node, changed_keys, op):
        """Return the recompute scope for a proportion change: the node's parent (root at the top)."""
        if 'proportion' in changed_keys or 'tied' in changed_keys:
            if node == tree.root:
                return tree.root
            parent = tree.parent(node)
            return tree.root if parent is None else parent
        return None

    def on_structure_changed(self, tree, scope, op):
        """Re-run ``_evaluate`` from the changed scope down.

        Missing proportions default to 1 inside ``_evaluate`` itself (it
        reads with ``.get('proportion', 1)`` and writes the value back), so
        no whole-tree backfill scan is needed here; ``add_child`` inserts
        additionally default at write time via :meth:`normalize_attrs`.
        """
        tree._evaluate(scope)


class RhythmTree(Tree):
    """
    A tree of integer proportions defining relative durations within a
    time signature.

    Each node carries a ``proportion`` (negative values are rests;
    float values mark ties); the attached :class:`RhythmLayer` derives
    ``metric_duration`` and ``metric_onset`` for every node as
    fractions of a whole note, recomputed automatically after any
    mutation. Leaf-level results are exposed as :attr:`durations` and
    :attr:`onsets`.

    The nested-tuple notation follows the rhythm-tree tradition of
    OpenMusic and IRCAM: a tree is a ``(D, S)`` pair where ``D`` is a
    duration (here ``span × meas.numerator``) and ``S`` is a tuple of
    proportions, each of which may itself be a nested ``(D, S)`` pair.

    See: https://support.ircam.fr/docs/om/om6-manual/co/RT1.html

    Examples
    --------
    >>> rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, (2, (1, 1)), 1))
    >>> rt.durations
    (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
    """

    _node_value_attr = 'proportion'

    def __init__(self,
                 span:int                      = 1,
                 meas:Union[Meas,Fraction,str] = '1/1',
                 subdivisions:Tuple            = (1,1)):
        """
        Parameters
        ----------
        span : int, optional
            The number of measures the tree spans. Default is 1.
        meas : Meas, Fraction, or str, optional
            The time signature. Default is ``'1/1'``.
        subdivisions : tuple, optional
            The proportional subdivisions of the measure. Elements may
            be integers or nested ``(D, S)`` tuples. Default is ``(1, 1)``.
        """
        casted = self._cast_subdivs(subdivisions)
        self._validate_s_grammar(casted)
        super().__init__(Meas(meas).numerator * span, casted)
        
        self._meta['span'] = span
        self._meta['meas'] = str(Meas(meas))
        self._list = Group((Meas(meas).numerator * span, casted))
        
        self._evaluate()
        self._group_dirty = False

    def _init_layers(self):
        self.attach_layer(RhythmLayer())

    @classmethod
    def from_tree(cls, tree:Tree, span:int = 1):
        """
        Construct a ``RhythmTree`` from an existing :class:`Tree`.

        Parameters
        ----------
        tree : Tree
            A tree whose root node has a ``'metric_duration'`` attribute.
        span : int, optional
            The number of measures. Default is 1.

        Returns
        -------
        RhythmTree
        """
        return cls(span = span, meas = Meas(tree[tree.root]['metric_duration']), subdivisions = tree.group.S)
    
    @classmethod
    def from_ratios(cls, ratios:Tuple[Fraction, float, str], span:int = 1):
        """
        Construct a ``RhythmTree`` from a flat sequence of fractional ratios.

        The ratios are converted to integer subdivisions and the time
        signature is inferred from the sum of absolute ratios.

        Parameters
        ----------
        ratios : tuple of Fraction, float, or str
            The proportional ratios for each leaf.
        span : int, optional
            The number of measures. Default is 1.

        Returns
        -------
        RhythmTree
        """
        ratios = tuple(Fraction(r) for r in ratios)
        S = ratios_to_subdivs(ratios)
        meas = Meas(sum(abs(r) for r in ratios))
        return cls(span = span, meas = meas, subdivisions = S)

    @property
    def span(self):
        """
        The number of measures this tree spans.

        Returns
        -------
        int
        """
        return self._meta['span']

    @property
    def meas(self):
        """
        The time signature of this tree.

        Returns
        -------
        Meas
        """
        # parse once per distinct stored string (Meas is immutable; the
        # identity check invalidates if _meta['meas'] is ever rebound)
        s = self._meta['meas']
        cached = getattr(self, '_meas_cache', None)
        if cached is not None and cached[0] is s:
            return cached[1]
        m = Meas(s)
        self._meas_cache = (s, m)
        return m

    @property
    def subdivisions(self):
        """
        The proportional subdivisions (S part) of this tree.

        Reports the structure AS AUTHORED until the tree is mutated, and
        the structure as rebuilt from the graph afterwards. Those two agree
        on every proportion -- construction-time validation (NEW-04/WL-24)
        rejects the one input class that made them disagree, a non-whole
        float, which used to display as ``(1, 1.5, 1)`` while playing
        ``(1, 1, 1)``. They can still differ in *representation*: a rest
        group authored ``(-1, (1, 1, 1, 1))`` rebuilds as
        ``(-1, (-1, -1, -1, -1))``, which is the same music written the
        other way round.

        Returns
        -------
        tuple
        """
        return self.group.S

    def _post_structure_clone(self):
        super()._post_structure_clone()
        self._meta['span'] = 1
        self._meta['meas'] = '1/1'
        for node in self._rx.node_indices():
            self._rx[node] = {'proportion': 1}
        self._evaluate()
        subdivs = self._build_subdivisions()
        s = subdivs[1] if isinstance(subdivs, tuple) and len(subdivs) > 1 else (1,)
        self._list = Group((1, s))
        self._group_dirty = False

    def _cast_subdivs(self, children):
        def convert_to_tuple(item):
            if isinstance(item, RhythmTree):
                return (item.meas.numerator * item.span, item.subdivisions)
            if isinstance(item, (tuple, list)):
                return tuple(convert_to_tuple(x) for x in item)
            return item
        
        return tuple(convert_to_tuple(child) for child in children)

    @staticmethod
    def _validate_s_grammar(s, _path='S'):
        """Validate the S-form of *subdivisions* at construction time.

        Deliberately more lenient than :meth:`_validate_s_form`, which
        guards ``subdivide`` and legitimately demands at least two parts.
        The divergence is deliberate, not drift: this validator describes a
        STRUCTURE, in which a one-part group is a real shape Klotho emits;
        ``subdivide`` describes an ACTION, and "divide this into one part"
        is a no-op it declines on purpose.

        The scalar rule itself is NOT restated here -- it lives once in
        :func:`_check_proportion_scalar`, shared with ``subdivide`` and
        with the write path. What this method adds is the nested
        ``(D, S)`` shape.

        This one guards the CONSTRUCTOR, so it must accept every shape
        Klotho itself round-trips:

        - any length, including ``()`` and ``(1,)`` -- the ``'d'``/``'r'``
          prolatio presets build length-1 S, and ``subtree``/``decompose``
          emit both;
        - whole-valued floats -- these are the tie markers ``_evaluate``
          writes and re-reads, so ``2.0`` is data, not a typo;
        - negative values -- rests;
        - ``numbers.Integral`` generally, so numpy scalars pass.

        What it rejects is what silently corrupted the tree before: a
        non-whole float (truncated to int and marked tied), a zero (a
        0-duration leaf that breaks strictly-increasing onsets), and a
        malformed pair (previously a bare ``abs()`` TypeError with no
        indication of WHERE).
        """
        if not isinstance(s, (tuple, list)):
            raise ValueError(
                f"subdivisions at {_path} must be a tuple or list; "
                f"got {type(s).__name__}: {s!r}."
            )
        for i, elem in enumerate(s):
            path = f"{_path}[{i}]"
            if isinstance(elem, (tuple, list)):
                if len(elem) != 2:
                    raise ValueError(
                        f"nested element at {path} must be a (D, S) pair of "
                        f"exactly 2 items; got {len(elem)}: {elem!r}."
                    )
                d, sub = elem
                _check_proportion_scalar(d, f"{path}[0]", 'D')
                RhythmTree._validate_s_grammar(sub, f"{path}[1]")
            else:
                _check_proportion_scalar(elem, path, 'proportion')

    def _validate_s_form(self, s, _path='S'):
        """Validate the S handed to :meth:`subdivide`.

        The scalar rule is NOT restated here -- it lives once in
        :func:`_check_proportion_scalar`, shared with the constructor's
        :meth:`_validate_s_grammar` and with the write path. So
        ``subdivide`` now authors exactly what the constructor authors: a
        whole-valued float is a TIE, not a typo, and numpy integers pass.
        Non-whole floats, zeros, tied rests (negative floats), float ``D``
        on an interior node, and bools are refused identically.

        The one rule this surface ADDS is ``len(S) >= 2``. That divergence
        from the constructor is deliberate, not drift: the constructor
        describes a STRUCTURE, in which a one-part group is a real shape
        Klotho emits 218 times internally, while ``subdivide`` describes an
        ACTION, and "divide this into one part" is a no-op the API declines
        rather than performs.
        """
        if not isinstance(s, (tuple, list)):
            # a bare scalar in nested position: same rule, no length rule
            _check_proportion_scalar(s, _path, 'proportion')
            return
        if len(s) < 2:
            raise ValueError(f"S must have at least 2 elements, got {s}")
        for i, elem in enumerate(s):
            path = f"{_path}[{i}]"
            if isinstance(elem, (tuple, list)):
                if len(elem) != 2:
                    raise ValueError(
                        f"(D S) at {path} must have exactly 2 elements, "
                        f"got {len(elem)}: {elem}"
                    )
                d, sub = elem
                _check_proportion_scalar(d, f"{path}[0]", 'D')
                self._validate_s_form(sub, f"{path}[1]")
            else:
                _check_proportion_scalar(elem, path, 'proportion')

    def _normalize_s_for_subdivide(self, S):
        """Normalize S for subdivide: int -> (1,)*S; tuple -> validate and return.
        S must represent at least 2 subdivisions (e.g. S>1 for int, len(S)>=2 for tuple)."""
        if isinstance(S, numbers.Integral) and not isinstance(S, bool):
            S = int(S)
            if S <= 1:
                raise ValueError(f"S must be > 1 when int, got {S}")
            return (1,) * S
        if isinstance(S, (tuple, list)):
            self._validate_s_form(S)
            return tuple(S)
        raise ValueError(f"S must be tuple or int, got {type(S).__name__}: {S}")

    def _build_subdivisions(self, root_node=None):
        """
        Build a subdivisions structure from the current graph state.

        Parameters
        ----------
        root_node : int, optional
            The node to start building from. Default is ``self.root``.

        Returns
        -------
        tuple
            Nested tuple structure representing subdivisions.
        """
        if root_node is None:
            root_node = self.root
        
        def get_node_value(node):
            return self[node].get('proportion', 1)
        
        def get_children(node):
            return list(self.successors(node))
        
        return self._build_nested_structure(root_node, get_node_value, get_children)
    
    def _rebuild_group(self):
        """Rebuild the Group structure, preserving D and rebuilding S."""
        if hasattr(self, '_list'):
            new_subdivisions = self._build_subdivisions()
            if isinstance(new_subdivisions, tuple) and len(new_subdivisions) > 1:
                new_s = new_subdivisions[1]
            else:
                new_s = (1,)
            self._list = Group((self._list.D, new_s))

    @property
    def durations(self):
        """
        The metric durations of all leaf nodes.

        Returns
        -------
        tuple of Fraction
        """
        rx = self._rx
        return tuple(rx.get_node_data(n)['metric_duration'] for n in self.leaf_nodes)
    
    @property
    def onsets(self):
        """
        The metric onsets of all leaf nodes.

        Returns
        -------
        tuple of Fraction
        """
        rx = self._rx
        return tuple(rx.get_node_data(n)['metric_onset'] for n in self.leaf_nodes)

    @property
    def tie_groups(self):
        """
        The tie groups of the leaf surface, derived from node flags.

        A tied group is a maximal run, in leaf order, of leaves where every
        member after the first has ``tied=True`` (07_TIES_CHARTER.md sect1-2).
        The first member is the head; the rest are continuations. Groups
        legitimately span branch boundaries — leaf ORDER, not subtree
        containment, is what joins them. Rests are always singleton groups
        and break runs; a tied leaf whose predecessor is a rest (or which
        starts the tree) heads its own group — a dangling continuation,
        which renders as an attack (charter sect6). Untied leaves are
        singleton groups, so on a tie-free tree there is one group per leaf.

        Derived on every read — nothing is stored, so structural edits can
        never orphan a group.

        Returns
        -------
        tuple of tuple of int
            One tuple of leaf node ids per group, head first.
        """
        rx = self._rx
        groups = []
        current = None
        for n in self.leaf_nodes:
            data = rx.get_node_data(n)
            if data.get('proportion', 1) < 0:
                groups.append((n,))
                current = None
            elif data.get('tied', False) and current is not None:
                current.append(n)
            else:
                current = [n]
                groups.append(current)
        return tuple(tuple(g) if isinstance(g, list) else g for g in groups)
    
    @property
    def info(self):
        """
        A formatted string summarizing the tree's metadata, subdivisions,
        durations, and onsets.

        Returns
        -------
        str
        """
        ordered_meta = {k: self._meta[k] for k in ['span', 'meas']}
        ordered_meta['depth'] = self.depth
        ordered_meta['k'] = self.k
        meta_str = ' | '.join(f"{k}: {v}" for k, v in ordered_meta.items())
        
        table_data = [
            [str(r) for r in self.durations],
            [str(o) for o in self.onsets]
        ]
        
        duration_onset_table = tabulate(
            table_data,
            headers=[],
            tablefmt='plain'
        )
        
        table_lines = duration_onset_table.split('\n')
        durations_line = f"Durations: {table_lines[0]}"
        onsets_line = f"Onsets:    {table_lines[1]}"
        
        content = [
            meta_str,
            f"Subdivs: {format_subdivisions(self.subdivisions)}",
            onsets_line,
            durations_line
        ]
        
        width = max(len(line) for line in content)
        border = '-' * width
        
        return (
            f"{border}\n"
            f"{content[0]}\n"
            f"{border}\n"
            f"{content[1]}\n"
            f"{border}\n"
            f"{content[2]}\n"
            f"{content[3]}\n"
            f"{border}\n"
        )
    
    def _evaluate(self, root_node=None):
        """
        Evaluate the tree to compute metric durations and onsets.

        Single-pass DFS: computes durations and onsets together in one traversal.
        When root_node is provided, evaluates from that subtree (ancestors must
        already have metric_duration). When None, evaluates from root.

        Parameters
        ----------
        root_node : int, optional
            Subtree root to evaluate from. If None, evaluates from tree root.

        Notes
        -----
        **This is a FIXPOINT, not a validator, and it repairs in silence.**
        The grammar is enforced at the three entry surfaces (see
        :func:`_check_proportion_scalar`); the rules below run again here
        because ``_evaluate`` must return a coherent tree from whatever
        state the graph is in, including states no entry surface can
        produce. It does not report what it changed. Specifically it:

        - re-negates a positive child of a negative parent, so resting a
          branch rests everything under it (this is why un-resting a leaf
          is not a per-node sign flip -- see :meth:`make_sounding`);
        - clears ``tied`` on anything negative, because a tied rest is
          illegal (07_TIES_CHARTER.md sect1);
        - truncates a float proportion with ``int()``.

        That last one is now UNREACHABLE from any authoring path: since
        RT-2 the constructor, ``subdivide`` and the write path all refuse a
        non-whole float, so every float arriving here is a whole-valued tie
        marker and ``int()`` loses nothing. Two paths still bypass the
        validators, and neither can ORIGINATE a fractional value:
        ``Tree.add_subtree``/``graft_subtree`` copy donor node data
        verbatim via ``_add_node_raw`` (so they can only propagate what a
        donor already holds, and no public API can put it there), and
        direct ``self._rx[n]['proportion'] = ...`` pokes inside this module.
        """
        if root_node is None:
            root_node = self.root
        self._rx[self.root]['metric_duration'] = self.meas * self.span
        parent_ratio = self.span * self.meas.to_fraction() if root_node == self.root else Fraction(self._rx[root_node]['metric_duration'])

        leaf_onset_acc = [Fraction(0)]

        def _process_child(child, div, parent_ratio, parent_is_negative):
            child_data = self._rx[child]
            s = child_data.get('proportion', 1)
            child_is_tied = isinstance(s, float) or bool(child_data.get('tied', False))
            if 'meta' in child_data:
                s = s * child_data['meta']['span']
            s = int(s) if isinstance(s, float) else s
            if parent_is_negative and s > 0:
                s = -s
            if s < 0:
                # tied rests are illegal (07_TIES_CHARTER.md sect1): a node
                # rested from above sheds any tie instead of carrying it
                child_is_tied = False
            ratio = Fraction(s, div) * parent_ratio
            if s < 0:
                ratio = -abs(ratio)
            self._rx[child]['metric_duration'] = ratio
            self._rx[child]['tied'] = child_is_tied
            self._rx[child]['proportion'] = float(s) if child_is_tied else s
            if self.out_degree(child) > 0:
                _process_subtree(child, ratio)
            else:
                self._rx[child]['metric_onset'] = leaf_onset_acc[0]
                leaf_onset_acc[0] += abs(ratio)

        def _process_subtree(node, parent_ratio):
            node_data = self._rx[node]
            if 'meta' in node_data:
                node_data['proportion'] = node_data.get('proportion', 1) * node_data['meta']['span']
            label = node_data.get('proportion', 1)
            is_tied = isinstance(label, float) or bool(node_data.get('tied', False))
            label_value = int(label) if is_tied else label
            if label_value < 0:
                is_tied = False  # tied rests are illegal (charter sect1)
            self._rx[node]['tied'] = is_tied
            self._rx[node]['proportion'] = float(label_value) if is_tied else label_value
            children = list(self.successors(node))
            if not children:
                ratio = Fraction(label_value) * parent_ratio
                self._rx[node]['metric_duration'] = ratio
                self._rx[node]['metric_onset'] = leaf_onset_acc[0]
                leaf_onset_acc[0] += abs(ratio)
                return
            rx = self._rx
            div = 0
            for c in children:
                c_data = rx[c]
                div += abs(c_data.get('proportion', 1)) * \
                    (c_data['meta']['span'] if 'meta' in c_data else 1)
            div = int(div)
            node_is_negative = label_value < 0
            for child in children:
                _process_child(child, div, parent_ratio, node_is_negative)
            self._rx[node]['metric_onset'] = self._rx[children[0]]['metric_onset']

        if root_node != self.root:
            # hoisted once: leaf order, subtree-leaf set, and leaf->ordinal
            # map (the old code recomputed list(...).index() and
            # subtree_leaves per leaf — quadratic in leaf count)
            leaf_order = self.leaf_nodes
            sub_leaves = self.subtree_leaves(root_node)
            sub_leaf_set = set(sub_leaves)
            for n in leaf_order:
                if n in sub_leaf_set:
                    break
                leaf_onset_acc[0] += abs(Fraction(self._rx[n]['metric_duration']))

        _process_subtree(root_node, parent_ratio)

        if root_node != self.root:
            leaf_index = {leaf: i for i, leaf in enumerate(leaf_order)}
            max_sub_idx = max(leaf_index[l] for l in sub_leaves)
            for n in leaf_order[max_sub_idx + 1:]:
                self._rx[n]['metric_onset'] = leaf_onset_acc[0]
                leaf_onset_acc[0] += abs(Fraction(self._rx[n]['metric_duration']))
            scope_desc = set(self.descendants(root_node))
            for node in reversed(list(self.topological_sort())):
                if self.out_degree(node) > 0 and node != root_node and node not in scope_desc:
                    children = self.successors(node)
                    self._rx[node]['metric_onset'] = self._rx[children[0]]['metric_onset']

    def __len__(self):
        return len(self.leaf_nodes)

    def __str__(self):
        return f"RhythmTree(span={self.span}, meas={self.meas}, subdivisions={format_subdivisions(self.subdivisions)})"

    def __repr__(self):
        return self.__str__()
    
    def subtree(self, node, renumber=True):
        """Extract a rhythm subtree rooted at the given node.
        
        The subtree becomes a new RhythmTree with:
        - span = 1
        - meas = metric_duration of the selected node
        - subdivisions = reconstructed from the subtree structure
        
        Parameters
        ----------
        node : int
            The node to use as the root of the subtree
        renumber : bool, optional
            Whether to renumber the nodes in the new tree (default: True)
            
        Returns
        -------
        RhythmTree
            A new tree of the same class as ``self`` representing the
            subtree. Subclasses that carry data beyond the rhythm — a
            :class:`~klotho.thetos.composition.compositional.CompositionalTree`
            and its parameters — restore it through the
            ``_after_subtree_built`` hook, exactly as :meth:`Tree.subtree`
            does.
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        subdivisions_structure = self._build_subdivisions(node)
        if isinstance(subdivisions_structure, tuple) and len(subdivisions_structure) > 1:
            subdivisions = subdivisions_structure[1]
        else:
            subdivisions = (1,)
        
        node_duration = self[node].get('metric_duration')
        if node_duration is None:
            meas = '1/1'
        else:
            meas = Meas(node_duration)
        
        new_rt = self.__class__(span=1, meas=meas, subdivisions=subdivisions)

        # This override rebuilds the subtree from its S-form rather than
        # copying nodes, so it never reaches Tree.subtree's hook. Call it
        # here, or a subclass silently loses everything but the rhythm.
        after_subtree_built = getattr(self, '_after_subtree_built', None)
        if after_subtree_built is not None:
            mapping = self._subtree_node_mapping(node, new_rt)
            after_subtree_built(new_rt, mapping, renumber)

        if renumber:
            new_rt.renumber_nodes()

        return new_rt

    def _subtree_node_mapping(self, node, new_rt):
        """Map this tree's ids under ``node`` onto ``new_rt``'s ids.

        The rebuilt tree is isomorphic to the source subtree — it is built
        from that subtree's own S-form — so a parallel walk in sorted child
        order pairs the nodes up. The one exception is a leaf: it has no
        S-form of its own, so ``subtree`` gives it the fallback ``(1,)`` and
        the new root gains a child that no source node corresponds to. That
        child needs no mapping — it inherits from the new root, which is
        mapped.

        Only :meth:`subtree` calls this, and only when a subclass hook needs
        the mapping, so plain rhythm trees pay nothing for it.
        """
        mapping = {}
        stack = [(node, new_rt.root)]
        while stack:
            old_node, new_node = stack.pop()
            mapping[old_node] = new_node
            old_children = sorted(self.successors(old_node))
            if not old_children:
                continue
            new_children = sorted(new_rt.successors(new_node))
            if len(old_children) != len(new_children):
                raise RuntimeError(
                    f"subtree rebuild diverged from the source at node {old_node}: "
                    f"{len(old_children)} children became {len(new_children)}"
                )
            stack.extend(zip(old_children, new_children))
        return mapping
    
    def graft_subtree(self, target_node, subtree, mode='replace'):
        """
        Graft a subtree onto the tree and re-evaluate metric values.

        Parameters
        ----------
        target_node : int
            The node at which to graft.
        subtree : RhythmTree or Tree
            The subtree to graft.
        mode : str, optional
            Grafting mode (``'replace'`` or ``'adopt'``). Default is
            ``'replace'``. See :meth:`~klotho.topos.graphs.trees.Tree.graft_subtree`.

        Returns
        -------
        int
            The id of the grafted target node.
        """
        return super().graft_subtree(target_node, subtree, mode)

    def _heads_the_leaf_surface(self, node):
        """True when ``node`` is the first leaf of the whole tree, or would be
        if a child were inserted at its rank 0 -- i.e. every ancestor up to the
        root is itself a first child."""
        while node != self.root:
            parent = self.parent(node)
            if parent is None:
                return False
            if self.successors(parent)[0] != node:
                return False
            node = parent
        return True

    def insert_child(self, parent, index, **attr):
        """Insert a child at a given rank (see :meth:`Tree.insert_child`),
        refusing a tie that would have nothing to continue.

        Positional insertion is the position-dependent write the layer
        validator could never make: ``validate_attrs`` is handed the PARENT,
        so it cannot see where among the siblings the new node lands. A tie
        inserted at the head of the leaf surface has no predecessor, and used
        to be accepted in silence and then ignored by ``tie_groups``.

        Rank 0 is NOT the test -- having no predecessor is. A tie at rank 0 of
        a group that is not itself leftmost binds to the leaf before the group
        (tie groups follow leaf ORDER, not subtree containment;
        07_TIES_CHARTER.md sect1-2), and is legal. At rank k > 0 the tie
        re-binds to the inserted note, which is the point of inserting it.

        Returns
        -------
        int
            The id of the node that now holds the inserted content.
        """
        if parent not in self:
            raise ValueError(f"Node {parent} not found in tree")
        tie_requested = (bool(attr.get('tied', False))
                         or isinstance(attr.get('proportion'), float))
        if tie_requested:
            n = len(self.successors(parent))
            rank = index + n if index < 0 else index
            if rank == 0 and self._heads_the_leaf_surface(parent):
                raise ValueError(
                    "a tie inserted at the head of the leaf surface continues "
                    "nothing -- there is no leaf before it. Insert it "
                    "untied, or insert at a later rank."
                )
        return super().insert_child(parent, index, **attr)

    def subdivide(self, node, S):
        """
        Subdivide leaf node(s) with structure S.

        Each leaf becomes a parent with children defined by S. The node's
        proportion D is used as the duration; S specifies the subdivisions.

        Parameters
        ----------
        node : int or list of int
            The leaf node(s) to subdivide. Must have no children.
            If a list, subdivide is applied to each.
        S : tuple or int
            Subdivisions. If int, interpreted as ``(1,)*S`` (e.g. ``S=3`` → ``(1, 1, 1)``).
            If tuple, must be valid S-form: each element is a non-zero integer
            or a ``(D, S)`` pair.

        Returns
        -------
        RhythmTree
            self (for chaining)

        Raises
        ------
        ValueError
            If node is not found, is not a leaf, or S is invalid.
        """
        nodes = [node] if isinstance(node, int) else list(node)
        for n in nodes:
            if n not in self:
                raise ValueError(f"Node {n} not found in tree")
            if self.out_degree(n) != 0:
                raise ValueError(f"Node {n} must be a leaf")

        S = self._normalize_s_for_subdivide(S)
        S = self._cast_subdivs(S)

        def add_children(parent, children):
            # raw inserts: one _post_mutation (and thus one _evaluate)
            # below instead of a full-tree re-evaluate per added child
            first_id = None
            for child in children:
                if isinstance(child, tuple) and len(child) == 2:
                    D, sub = child
                    child_id = self._add_child_raw(parent, proportion=D)
                    add_children(child_id, sub)
                else:
                    child_id = self._add_child_raw(parent, proportion=child)
                if first_id is None:
                    first_id = child_id
            return first_id

        for n in nodes:
            # Subdividing a tied leaf would strand the tie on an interior
            # node, where it has no meaning (charter sect1, the OpenMusic
            # resolution). "Continues my predecessor" has exactly one
            # lossless landing spot: the group's first leaf.
            was_tied = bool(self._rx[n].get('tied', False))
            if was_tied:
                self._rx[n]['tied'] = False
                self._rx[n]['proportion'] = int(self._rx[n]['proportion'])
            first_child = add_children(n, S)
            if was_tied and first_child is not None:
                self._rx[first_child]['tied'] = True
                self._rx[first_child]['proportion'] = float(
                    self._rx[first_child].get('proportion', 1))
        scope = self.parent(nodes[0]) if len(nodes) == 1 else None
        self._post_mutation(scope_node=scope, op='subdivide')
        return self

    def prune(self, node):
        """Remove a node and promote its children (see :meth:`Tree.prune`); returns self for chaining.

        Notes
        -----
        **``prune`` preserves the Tempus.** Deleting a beat with ``prune``
        does not shorten the bar -- the surviving beats dilate to fill it. In
        Haddad's algebra this is **extraction** (- in a circle), not
        diminution (- in a box). To shorten the bar, use the diminution verb,
        which builds a new tree with a recomputed Tempus.

        On an INTERIOR node ``prune`` additionally promotes the children one
        level, which changes durations unless ``D == sum(S)``::

            rt = RhythmTree(meas='4/4', subdivisions=(1, (5, (1, 1)), 3))
            rt.durations          # 1/9, 5/18, 5/18, 1/3
            rt.prune(2)           # (4 (1 1 1 3))
            rt.durations          # 1/6, 1/6, 1/6, 1/2

        For whole-group extraction use :meth:`extract` (or
        :meth:`remove_subtree`, which it delegates to).

        See Also
        --------
        extract : The named extraction verb, correct on interior nodes too.
        """
        super().prune(node)
        return self

    def remove_subtree(self, node):
        """Remove a node and all its descendants (see :meth:`Tree.remove_subtree`); returns self for chaining."""
        super().remove_subtree(node)
        return self

    # ------------------------------------------------------------------
    # Haddad's Tempus-PRESERVING operator family (sect4.5)
    #
    # His notation is systematic: a BOX means the Tempus FOLLOWS the
    # operation, a CIRCLE means the Tempus is PRESERVED.
    #
    #     add     augmentation  (+ in a box)   insertion   (+ in a circle)
    #     remove  diminution    (- in a box)   extraction  (- in a circle)
    #     scale   dilatation    (x in a box)   expansion/  (x in a circle)
    #                                          compression
    #
    # He states the axis outright on p. 128:
    #
    #     « Les prolationis qui en résultent sont identiques. C'est le
    #     Tempus qui diffère. Dans le cas de la « prolation » stricte, le
    #     Tempus est identique. Dans le deuxième cas, le Tempus est la
    #     somme des prolationis une fois transformés. »
    #
    #     "The resulting prolationis are identical. It is the Tempus that
    #     differs. In the case of strict 'prolation', the Tempus is
    #     identical. In the second case, the Tempus is the sum of the
    #     prolationis once transformed."
    #
    # He never writes "Tempus-preserving" or "Tempus-following": his own
    # terms are « prolationnelle stricte » ("strictly prolational") for the
    # circle family and « relative » ("relative") for the box family. The
    # English pair is Klotho's coinage.
    #
    # This block implements the CIRCLE family only, as methods that mutate
    # and return self -- `meas` and `span` have no setters, so a
    # Tempus-following operator cannot be spelled this way at all and lives
    # elsewhere as a builder of new trees.
    #
    # Every operator is decompose -> operate -> concatenate (sect4.5.2,
    # p. 124):
    #
    #     « Ces opérations utilisent l'ajout équivalent à l'addition, le
    #     retrait à la soustraction, et la substitution (sous forme de
    #     multiplication) après décomposition de l'Unité temporelle
    #     composée suivi de la concaténation de l'ensemble des
    #     prolationis. »
    #
    #     "These operations use addition for adding, subtraction for
    #     removal, and substitution (in the form of multiplication) --
    #     after decomposition of the composite Temporal Unit, followed by
    #     the concatenation of the whole set of prolationis."
    #
    # So `insert` and `scale` FLATTEN: the result is one level, by
    # construction, and nesting is not preserved.
    # ------------------------------------------------------------------
    def _decomposed_durations(self):
        """The decomposed sequence -- one signed Fraction per sounding event.

        The same decomposition :func:`~klotho.chronos.rhythm_trees.algorithms.decompose`
        performs, returned as bare durations: one term per tie GROUP (a tie
        group is one event, charter sect9), signed for rests (ALG-1).
        """
        rx = self._rx
        out = []
        for group in self.tie_groups:
            total = sum(abs(Fraction(rx.get_node_data(n)['metric_duration']))
                        for n in group)
            if rx.get_node_data(group[0])['metric_duration'] < 0:
                total = -total
            out.append(total)
        return out

    @staticmethod
    def _grid_denominator(durations):
        """The finest common unit the sequence can be written on."""
        den = 1
        for d in durations:
            den = lcm(den, d.denominator)
        return den

    def _capture_payloads(self):
        """One payload per decomposed event: everything that is NOT rhythm.

        A preserved-family verb deletes every non-root node and rebuilds the
        leaf surface, so anything the old nodes carried is destroyed unless
        it is captured first. On a plain :class:`RhythmTree` there is nothing
        to carry; on a
        :class:`~klotho.thetos.composition.compositional.CompositionalTree`
        the pfields, mfields and instrument bindings all live in node data
        and would vanish in silence.

        An event's payload is its tie-group HEAD's own overrides, merged over
        those of every ancestor that is about to be DELETED -- an override
        set on a group node is inherited by the leaves under it, and the
        group node does not survive the flatten, so the value has to come
        down with them. The ROOT is deliberately excluded: it survives, keeps
        its own overrides, and goes on cascading to the rebuilt leaves. So a
        value set at the root stays a root value and can still be changed
        once, at the root, afterwards.

        Returns
        -------
        list of (dict, object)
            One ``(node data, instrument or None)`` pair per decomposed
            event, in decomposed order.
        """
        layer = getattr(self, '_param_layer', None)
        bindings = layer._node_instruments if layer is not None else {}
        captured = []
        for group in self.tie_groups:
            merged = {}
            instrument = None
            # root first, head last: the nearer ancestor wins, which is the
            # same precedence the effective-value cache resolves by.
            for n in self.branch(group[0])[1:]:
                data = self._rx[n]
                if isinstance(data, dict):
                    merged.update({k: v for k, v in data.items()
                                   if k not in _NON_PAYLOAD_KEYS})
                if n in bindings:
                    instrument = bindings[n]
            captured.append((merged, instrument))
        return captured

    def _respell(self, durations, sources, op):
        """Rewrite the leaf surface from a decomposed duration sequence.

        The Tempus VALUE is never changed by a preserved-family operator.
        Its SPELLING follows the grid only when the authored spelling WAS
        the grid -- that is, when ``meas.denominator`` already equals the
        finest common unit of the current decomposed sequence. An authored
        spelling that says something else about the bar (``2/2`` over a
        five-part prolatio) is left exactly as written.

        That single rule reproduces Haddad's printed figures on both sides:
        ``2/2 (2 1 2)`` keeps ``2/2`` through an insertion (fig. 4.60),
        while the canonical ``18/18 (4 2 3 6 3)`` is re-spelled ``54/54``
        when a compression refines the grid to fifty-fourths (fig. 4.68).
        Both are the same Tempus value; only the unit it is counted in
        moves.

        Parameters
        ----------
        durations : list of Fraction
            The new decomposed sequence, one signed duration per event.
        sources : list of (int or None)
            Parallel to *durations*: the index each new event had in the
            OLD decomposed sequence, or ``None`` for an event this operation
            created. This map is what carries pfields, mfields and
            instrument bindings across the rebuild; it is explicit because
            an incidental one (same position, same payload) is wrong for
            every verb that inserts or removes.
        """
        payloads = self._capture_payloads()
        old_grid = self._grid_denominator(self._decomposed_durations())
        den = self._grid_denominator(durations)
        S = tuple(int(d * den) for d in durations)

        meas = None
        if self.meas.denominator == old_grid and den != old_grid:
            num = self.meas.to_fraction() * den
            if num.denominator == 1:
                meas = Meas(int(num), den)

        root = self.root
        layer = getattr(self, '_param_layer', None)
        bindings = layer._node_instruments if layer is not None else None
        for n in [x for x in self.nodes if x != root]:
            self._remove_node_raw(n)
        if meas is not None:
            self._meta['meas'] = str(meas)
            self._meas_cache = None
            self._rx[root]['proportion'] = meas.numerator * self.span
        if bindings is not None:
            # freed node indices are REUSED, so a binding left on a deleted
            # node does not merely leak -- it re-attaches to whatever event
            # lands in that slot
            for n in [x for x in bindings if x != root and x not in self]:
                del bindings[n]
        # Freed node indices are reused in no guaranteed order, so the
        # proportions are written by SLOT RANK after the fact rather than
        # trusted to arrive in insertion order.
        new_ids = [self._add_child_raw(root, proportion=1) for _ in S]
        for slot, p, src in zip(sorted(new_ids), S, sources):
            payload, instrument = payloads[src] if src is not None else ({}, None)
            self._write_node_data(slot, {'proportion': p, **payload},
                                  replace=True)
            if instrument is not None and bindings is not None:
                bindings[slot] = instrument
        self._post_mutation(scope_node=root, op=op)
        return self

    @staticmethod
    def _as_fraction(value, what):
        """Coerce a duration/ratio argument to an exact Fraction."""
        if isinstance(value, Meas):
            return value.to_fraction()
        if isinstance(value, float):
            # decimal-exact, not the binary expansion of the float
            return Fraction(str(value))
        try:
            return Fraction(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{what} must be a rational value; got "
                             f"{value!r}") from exc

    @staticmethod
    def _pair_up(indices, values, what):
        """Normalize scalar-or-sequence argument pairs to a list of pairs."""
        idx_seq = isinstance(indices, (list, tuple))
        val_seq = isinstance(values, (list, tuple))
        if idx_seq != val_seq:
            raise ValueError(
                f"index and {what} must both be scalars or both be "
                f"sequences"
            )
        if not idx_seq:
            return [(indices, values)]
        if len(indices) != len(values):
            raise ValueError(
                f"{len(indices)} indices but {len(values)} {what} values"
            )
        return list(zip(indices, values))

    def insert(self, index, duration):
        """Insertion (+ in a circle) -- add a duration without lengthening the bar.

        Haddad's own term; the English is his. It is also already the family
        verb one structural level down (``TemporalUnitSequence.insert``,
        ``TemporalBlock.insert``), with the same ``(index, thing)`` shape.

        The tree is decomposed, the duration spliced into the sequence, and
        the whole re-concatenated -- so the result is ONE level and the
        Tempus is untouched. The inserted value only fixes the new event's
        relative weight: everything compresses to keep the bar the length it
        was. ``2/2 (2 1 2)`` with ``3/10`` at position 2 gives
        ``2/2 (4 2 3 4)`` (fig. 4.60).

        Parameters
        ----------
        index : int or sequence of int
            Where to insert, 0-based into the DECOMPOSED sequence, inserting
            BEFORE that position. Haddad settles the convention on p. 125:
            *« …et position la position de l'ajout par rapport à l'ensemble
            de la séquence décomposée (0 étant la position de tête de
            séquence). »* -- "…and position is the position of the addition
            relative to the whole decomposed sequence (0 being the
            head-of-sequence position)." Indices always refer to the
            ORIGINAL, pre-insertion sequence. Negative indices count from the
            end as in ``list.insert``; out of range raises ``IndexError``.
        duration : Fraction, int, str, float, Meas, or sequence
            The duration(s) to insert, as a fraction of the whole note. A
            NEGATIVE duration inserts a rest. Zero is refused.

        Returns
        -------
        RhythmTree
            self, for chaining.

        Notes
        -----
        Ties do not survive: a tie group decomposes to one event, exactly as
        in :func:`~klotho.chronos.rhythm_trees.algorithms.flatten`.

        **Thesis erratum.** Figure 4.60 prints the source subscript as
        ``(2 1 1)``. The correct input is ``(2 1 2)``, proven three ways --
        the prose says *« trois prolationis de (2 1 2) »* ("three prolationis
        of (2 1 2)"), the engraving is a 5:4 tuplet (5 = 2+1+2), and only
        ``(2 1 2)`` yields ``(4 2 3 4)``. The same broken macro repeats from
        figure 4.58.
        """
        current = self._decomposed_durations()
        n = len(current)
        pairs = self._pair_up(index, duration, 'duration')

        buckets = {}
        for raw_index, raw_duration in pairs:
            k = raw_index + n if raw_index < 0 else raw_index
            if not (0 <= k <= n):
                raise IndexError(
                    f"insert index {raw_index} out of range for a decomposed "
                    f"sequence of {n} events"
                )
            value = self._as_fraction(raw_duration, 'duration')
            if value == 0:
                raise ValueError(
                    "a zero duration is neither a sound nor a rest; insert a "
                    "non-zero duration, or nothing"
                )
            buckets.setdefault(k, []).append(value)

        out, sources = [], []
        for i in range(n + 1):
            for value in buckets.get(i, ()):
                out.append(value)
                sources.append(None)   # a new event: no payload to inherit
            if i < n:
                out.append(current[i])
                sources.append(i)
        return self._respell(out, sources, 'insert')

    def extract(self, node):
        """Extraction (- in a circle) -- delete without shortening the bar.

        The named extraction verb. It delegates to :meth:`remove_subtree`,
        which is correct in general: the survivors dilate to fill the Tempus,
        and a named group leaves as a whole.

        ``prune`` is extraction too, but only for LEAVES -- on an interior
        node it promotes the children one level and changes durations unless
        ``D == sum(S)``. See :meth:`prune`.

        Parameters
        ----------
        node : int or sequence of int
            The node(s) to remove. A node already removed as another's
            descendant is skipped rather than raising.

        Returns
        -------
        RhythmTree
            self, for chaining.
        """
        nodes = list(node) if isinstance(node, (list, tuple, set)) else [node]
        for n in nodes:
            if n not in self:
                raise ValueError(f"Node {n} not found in tree")
            if n == self.root:
                raise ValueError("Cannot extract the root node")
        for n in nodes:
            if n in self:
                self.remove_subtree(n)
        return self

    def scale(self, index, ratio):
        """Expansion/compression (x in a circle) -- reweight events in place.

        Haddad's own term is *expansion/compression*: ONE operator whose
        ratio decides the direction. ``scale`` is Klotho's coinage, chosen
        because ``expand`` is accurate above 1 and actively misleading below
        it.

        The tree is decomposed, the named events multiplied by their ratios,
        and the whole re-concatenated. The Tempus is preserved, so an
        expanded event does not lengthen the bar -- it takes a larger share
        of it and its neighbours take less. ``18/18 (4 2 3 6 3)`` scaled by
        3 at position 2 gives ``18/18 (4 2 9 6 3)`` (fig. 4.65).

        Parameters
        ----------
        index : int or sequence of int
            Which event(s) to scale, 0-based into the DECOMPOSED sequence
            (p. 127: the position or positions, where 0 is the first
            prolatio). Negative indices count from the end; out of range
            raises ``IndexError``.
        ratio : Fraction, int, str, float, or sequence
            The multiplier(s). Must be positive: a sign flip is
            :meth:`make_rest`'s job, not an expansion's, and zero would
            delete the event (that is :meth:`extract`).

        Returns
        -------
        RhythmTree
            self, for chaining.

        Notes
        -----
        When the ratios do not clear against the current grid, the grid is
        refined and the Tempus is re-spelled on it -- same value, finer unit.
        ``18/18 (4 2 3 6 3)`` compressed by ``1/3`` and ``1/9`` at positions
        2 and 3 gives ``54/54 (12 6 3 2 9)`` (fig. 4.68).

        **Thesis erratum.** Never use the prolationis printed in figures 4.68
        and 4.69: both reprint the preceding expansion result
        ``(4 2 9 6 3)``. Figure 4.69's Tempus ``16/27`` is correct, and it is
        what forces the true answer above.
        """
        out = self._decomposed_durations()
        n = len(out)
        for raw_index, raw_ratio in self._pair_up(index, ratio, 'ratio'):
            k = raw_index + n if raw_index < 0 else raw_index
            if not (0 <= k < n):
                raise IndexError(
                    f"scale index {raw_index} out of range for a decomposed "
                    f"sequence of {n} events"
                )
            value = self._as_fraction(raw_ratio, 'ratio')
            if value <= 0:
                raise ValueError(
                    "a scale ratio must be positive -- zero would delete the "
                    "event (use extract) and a negative would rest it (use "
                    "make_rest)"
                )
            out[k] = out[k] * value
        # scale never adds or removes an event, so the map is the identity
        return self._respell(out, list(range(n)), 'scale')

    def make_rest(self, node):
        """
        Make a node and all its descendants into rests by setting their proportions to negative.
        
        Parameters
        ----------
        node : int
            The node ID to make into a rest along with all its descendants.
            
        Raises
        ------
        ValueError
            If the node is not found in the tree.

        Notes
        -----
        **This is a validator BYPASS.** It writes through
        ``_write_node_data`` directly, so ``normalize_attrs`` and
        ``validate_attrs`` never run, and it sets the derived key
        ``metric_duration`` -- which the write path refuses outright. That
        is deliberate: the sign flip is exactly the operation whose result
        is known in advance, so recomputing it would be wasted work. It
        stays safe only because everything it writes is constructed here to
        satisfy the grammar (``-abs(int(...))`` is a non-zero negative int,
        and ``tied`` is forced ``False``). Any new write added here must
        keep that property by hand; the grammar will not catch a mistake.

        See Also
        --------
        make_sounding : The reverse operation, and why it cannot be a plain
            per-node sign flip.
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        descendants_to_modify = [node] + list(self.descendants(node))

        for n in descendants_to_modify:
            node_data = self[n]
            if 'proportion' in node_data and node_data['proportion'] > 0:
                # sign-flips clear `tied` (07_TIES_CHARTER.md sect1) -- a
                # tied rest is illegal, so the flip must not manufacture one
                self._write_node_data(n, {
                    'proportion': -abs(int(node_data['proportion'])),
                    'metric_duration': -abs(node_data['metric_duration']),
                    'tied': False,
                })
        self._invalidate_caches()

    def make_sounding(self, node):
        """
        Bring a node and all its descendants back out of rest.

        The reverse of :meth:`make_rest`: every negative proportion in the
        node's subtree becomes positive again, so the leaves sound.

        Parameters
        ----------
        node : int
            The node ID to make sounding, along with all its descendants.

        Raises
        ------
        ValueError
            If the node is not found in the tree.

        Notes
        -----
        **It also un-rests the ANCESTOR chain, and it has to.** A rest set
        on a group propagates downward: ``_evaluate`` re-negates any
        positive child of a negative parent. So flipping only the target
        node is a silent no-op -- the write lands, the call reports
        success, and the next recompute puts the rest straight back. Every
        negative ancestor up to the nearest positive one is therefore
        flipped as well. Sibling subtrees are untouched: they carry their
        own negative proportions and stay resting, so un-resting one leaf
        does not un-rest the group around it.

        **This is NOT a strict inverse.** :meth:`make_rest` is lossy. It
        clears ``tied`` on the way down and records nothing about what it
        cleared, so a leaf that was tied before being rested comes back
        untied. (Restoring it would be wrong as often as right: a tied
        rest is illegal, so the tie had to go, and nothing says the author
        still wants it.) At the
        :class:`~klotho.thetos.composition.compositional.CompositionalUnit`
        level ``make_rest`` also splits intersecting slurs and drops
        control envelopes, neither of which is stitched back either. What
        this method restores is the RHYTHM, and only the rhythm.

        Like :meth:`make_rest`, this writes through ``_write_node_data``
        and so bypasses the layer validators; every value it writes is
        constructed here to satisfy the grammar (``abs(int(...))`` is a
        non-zero positive int).

        See Also
        --------
        make_rest : The forward operation.
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        # Ancestors FIRST, outermost first: a rest on a group overrides
        # anything positive beneath it, so clearing the leaf without
        # clearing what encloses it changes nothing at all.
        chain = []
        ancestor = self.parent(node)
        while ancestor is not None:
            chain.append(ancestor)
            ancestor = self.parent(ancestor)
        chain.reverse()

        nodes_to_modify = chain + [node] + list(self.descendants(node))

        for n in nodes_to_modify:
            node_data = self[n]
            if 'proportion' in node_data and node_data['proportion'] < 0:
                # `tied` stays False: the tie was destroyed by make_rest and
                # nothing recorded it, so there is nothing honest to restore.
                self._write_node_data(n, {
                    'proportion': abs(int(node_data['proportion'])),
                    'metric_duration': abs(node_data['metric_duration']),
                    'tied': False,
                })
        self._invalidate_caches()
