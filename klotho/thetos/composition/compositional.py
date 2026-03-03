"""
Compositional units combining temporal structure with parameterized events.

This module provides ``CompositionalUnit``, which extends ``TemporalUnit``
with a synchronized ``ParameterTree`` for hierarchical parameter management,
envelope application, slur marking, and instrument assignment. The ``Parametron``
class extends ``Chronon`` with parameter field access.
"""

from typing import Union, Optional, Any, Literal
from fractions import Fraction
from dataclasses import dataclass
import inspect
import warnings
import pandas as pd

from klotho.chronos import TemporalUnit, RhythmTree, Meas
from klotho.chronos.temporal_units.temporal import Chronon
from klotho.thetos.parameters import ParameterTree
from klotho.thetos.instruments import Instrument
from klotho.thetos.instruments.base import Effect
from klotho.dynatos.envelopes import Envelope
from klotho.topos.collections.sequences import Pattern


@dataclass
class DistributionContext:
    """
    Context object passed to callable parameter-field values during distribution.
    
    Attributes
    ----------
    index : int
        Zero-based position of the current node in the target sequence.
    total : int
        Total number of target nodes being distributed to.
    node : int
        The node ID in the rhythm/parameter tree.
    is_rest : bool
        Whether this node is a rest.
    pfields : dict
        Effective parameter field values (PT overrides instrument).
    mfields : dict
        Meta field values from the PT.
    instrument : Instrument or None
        Resolved instrument for this node.
    """
    index: int
    total: int
    node: int
    is_rest: bool
    pfields: dict
    mfields: dict
    instrument: Any


PFieldContext = DistributionContext


def _build_pfield_context(uc, node: int, index: int, total: int, is_rest: bool) -> DistributionContext:
    pt = uc._pt
    inst = pt.get_instrument(node)
    pfields = {}
    inst_pfields = inst.pfields if (inst is not None and hasattr(inst, 'pfields')) else {}
    for k in pt._meta['pfields']:
        v = pt.get_pfield(node, k)
        if v is None and inst is not None:
            if k in inst_pfields:
                v = inst_pfields[k]
        pfields[k] = v
    mfields = {k: pt.get_mfield(node, k) for k in pt._meta['mfields']}
    return DistributionContext(
        index=index, total=total, node=node, is_rest=is_rest,
        pfields=pfields, mfields=mfields, instrument=inst
    )


def _callable_arity(fn):
    try:
        sig = inspect.signature(fn)
        return len([p for p in sig.parameters.values()
                    if p.default is inspect.Parameter.empty])
    except (ValueError, TypeError):
        return 0


class Parametron(Chronon):
    """
    An enhanced Chronon that includes parameter field access.
    
    Extends the basic temporal event data (start, duration, etc.) with 
    access to musical parameters stored in a synchronized ParameterTree.
    """
    
    __slots__ = ('_pt',)

    def __init__(self, node_id: int, ut, pt: ParameterTree):
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
        """
        super().__init__(node_id, ut)
        self._pt = pt
    
    @property
    def pfields(self):
        """
        Get parameter field values for this event (for playback, etc.).
        
        Returns pfield values with instrument fallback.
        Use ``get_mfield`` for meta fields to avoid key collisions.
        
        Returns
        -------
        dict
            Dictionary of parameter field names and values
        """
        result = {}
        inst = self._resolve_instrument()
        if inst is not None and hasattr(inst, 'pfields'):
            result.update(dict(inst.pfields))
        for k in self._pt._meta['pfields']:
            v = self._pt.get_pfield(self._node_id, k)
            if v is not None:
                result[k] = v
            elif inst is not None and hasattr(inst, 'pfields'):
                inst_pfields = inst.pfields
                if k in inst_pfields:
                    result[k] = inst_pfields[k]
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
        return {k: self._pt.get_mfield(self._node_id, k)
                for k in self._pt._meta['mfields']}

    def _resolve_instrument(self):
        return self._pt.get_instrument(self._node_id)

    def get_pfield(self, key: str, default=None):
        value = self._pt.get_pfield(self._node_id, key)
        return default if value is None else value

    def get_mfield(self, key: str, default=None):
        value = self._pt.get_mfield(self._node_id, key)
        return default if value is None else value

    def __getitem__(self, key: str):
        temporal_attrs = {'start', 'duration', 'end', 'proportion', 'metric_duration', 'metric_onset', 'node_id', 'is_rest', 'real_onset', 'real_duration'}
        if key in temporal_attrs:
            return getattr(self, key)
        v = self.get_pfield(key)
        if v is not None:
            return v
        return self.get_mfield(key)


class UCNodeView:
    """View of UC nodes; subscripting returns a Parametron for that node."""

    def __init__(self, uc):
        self._uc = uc

    def __getitem__(self, node):
        self._uc._ensure_timing_cache()
        return Parametron(node, self._uc, self._uc._pt)

    def __iter__(self):
        return iter(self._uc._rt.nodes)

    def __contains__(self, node):
        return node in self._uc._rt

    def __len__(self):
        return len(self._uc._rt)

    def __call__(self, data=False):
        self._uc._ensure_timing_cache()
        if data:
            for node in self._uc._rt.nodes:
                yield (node, Parametron(node, self._uc, self._uc._pt))
        else:
            for node in self._uc._rt.nodes:
                yield node


class CompositionalUnit(TemporalUnit):
    """
    A TemporalUnit enhanced with synchronized parameter management capabilities.
    
    Extends TemporalUnit to include a shadow ParameterTree that maintains 
    identical structural form to the internal RhythmTree. This allows for 
    hierarchical parameter organization where parameter values can be set at 
    any level and automatically propagate to descendant events.
    
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
    offset : float, default=0
        Start time offset in seconds
    pfields : Union[dict, list, None], optional
        Parameter fields to initialize. Can be:
        - dict: {field_name: default_value, ...}
        - list: [field_name1, field_name2, ...] (defaults to 0.0)
        - None: No parameter fields initially
        
    Attributes
    ----------
    pt : ParameterTree
        The synchronized parameter tree matching RhythmTree structure (returns copy)
    pfields : list
        List of all available parameter field names
    """
    
    def __init__(self,
                 span     : Union[int, float, Fraction]            = 1,
                 tempus   : Union[Meas, Fraction, int, float, str] = '4/4',
                 prolatio : Union[tuple, str]                      = 'd',
                 beat     : Union[None, Fraction, int, float, str] = None,
                 bpm      : Union[None, int, float]                = None,
                 offset   : float                                  = 0,
                 inst     : Union[Instrument, None]                = None,
                 mfields  : Union[dict, list, None]                = None,
                 pfields  : Union[dict, list, None]                = None):
        
        super().__init__(span, tempus, prolatio, beat, bpm, offset)
        
        if mfields is None:
            mfields = {}
        if 'group' not in mfields:
            mfields['group'] = 'default'
        
        self._pt = self._create_synchronized_parameter_tree(pfields, mfields)
        
        if inst is not None:
            self.set_instrument(self._pt.root, inst)
        
        self._slur_specs = {}
        self._next_slur_id = 0
        self._control_envelopes = []

    @property
    def nodes(self):
        return UCNodeView(self)
    
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
                   offset   = 0,
                   pfields  = pfields,
                   mfields  = mfields,
                   inst     = inst)
        
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
        return cls(span     = ut.span,
                   tempus   = ut.tempus,
                   prolatio = ut.prolationis,
                   beat     = ut.beat,
                   bpm      = ut.bpm,
                   offset   = ut.offset,
                   pfields  = pfields,
                   mfields  = mfields,
                   inst     = inst)
    
    def _create_synchronized_parameter_tree(self, pfields: Union[dict, list, None], mfields: Union[dict, list, None] = None) -> ParameterTree:
        """
        Create a ParameterTree with identical structure to the RhythmTree but blank node data.
        
        Parameters
        ----------
        pfields : Union[dict, list, None]
            Parameter fields to initialize
        inst : Union[Instrument, None], optional
            Instrument to set on the root node
        mfields : Union[dict, list, None], optional
            Meta fields to initialize
            
        Returns
        -------
        ParameterTree
            A parameter tree matching the rhythm tree structure with clean nodes
        """
        pt = ParameterTree.from_tree_structure(self._rt)
        
        if pfields is not None:
            self._initialize_parameter_fields(pt, pfields)
        
        if mfields is not None:
            self._initialize_meta_fields(pt, mfields)
        
        return pt
    
    def _initialize_parameter_fields(self, pt: ParameterTree, pfields: Union[dict, list]):
        """
        Initialize parameter fields across all nodes in the parameter tree.
        
        Parameters
        ----------
        pt : ParameterTree
            The parameter tree to initialize
        pfields : Union[dict, list]
            Parameter fields to set
        """
        if isinstance(pfields, dict):
            pt.set_pfields(pt.root, **pfields)
        elif isinstance(pfields, list):
            default_values = {field: 0.0 for field in pfields}
            pt.set_pfields(pt.root, **default_values)

    def _initialize_meta_fields(self, pt: ParameterTree, mfields: Union[dict, list]):
        """
        Initialize meta fields across all nodes in the parameter tree.
        
        Parameters
        ----------
        pt : ParameterTree
            The parameter tree to initialize
        mfields : Union[dict, list]
            Meta fields to set
        """
        if isinstance(mfields, dict):
            pt.set_mfields(pt.root, **mfields)
        elif isinstance(mfields, list):
            default_values = {field: '' for field in mfields}
            pt.set_mfields(pt.root, **default_values)

    def _resolve_governing_instrument_node(self, node: int):
        return self._pt._resolve_governing_instrument_node(node)

    def _normalize_node_input(self, node):
        if node is None:
            raise ValueError("node selection is required")
        if isinstance(node, int):
            source_nodes = [node]
        else:
            try:
                source_nodes = list(node)
            except TypeError as exc:
                raise ValueError("node must be an int or an iterable of ints") from exc
        if not source_nodes:
            raise ValueError("Selection cannot be empty")
        return source_nodes

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

    def _build_effective_parameter_tree(self):
        pt_snapshot = self._pt.copy()
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
        return pt_snapshot

    def _event_context(self):
        self._ensure_timing_cache()
        return self._build_effective_parameter_tree()

    def _make_event(self, node_id: int, event_context=None):
        eval_pt = event_context if event_context is not None else self._build_effective_parameter_tree()
        return Parametron(node_id, self, eval_pt)

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
        return self._build_effective_parameter_tree()
    
    @property
    def pfields(self) -> list:
        """
        List of all available parameter field names.
        
        Returns
        -------
        list of str
            Sorted list of parameter field names
        """
        return self._pt.pfields
    
    @property
    def mfields(self) -> list:
        """
        List of all available meta field names.
        
        Returns
        -------
        list of str
            Sorted list of meta field names
        """
        return self._pt.mfields
    
    @property
    def events(self):
        """
        Enhanced events DataFrame including both temporal and parameter data.
        
        Returns
        -------
        pandas.DataFrame
            DataFrame with temporal properties and all parameter fields
        """
        events = self._materialize_events()
        base_data = []
        for event in events:
            inst = self.get_instrument(event.node_id)
            if inst is None:
                inst_display = None
            elif isinstance(inst, (str, int)):
                inst_display = inst
            elif hasattr(inst, 'name') and inst.name not in (None, 'default'):
                inst_display = inst.name
            elif hasattr(inst, 'defName'):
                inst_display = inst.defName
            elif hasattr(inst, 'tonejs_class'):
                inst_display = inst.tonejs_class
            elif hasattr(inst, 'prgm'):
                inst_display = inst.prgm
            else:
                inst_display = str(inst)
            event_dict = {
                'node_id': event.node_id,
                'instrument': inst_display,
                'start': event.start,
                'duration': event.duration,
                'end': event.end,
                'is_rest': event.is_rest,
                's': event.proportion,
                'metric_duration': event.metric_duration,
                'pfields': event.pfields,
                'mfields': event.mfields,
            }
            base_data.append(event_dict)

        return pd.DataFrame(base_data, index=range(len(events)))
    
    def _distribute_to_targets(self, targets, fields, include_rests, setter='pfields'):
        if not include_rests:
            targets = [n for n in targets
                       if self._rt[n].get('proportion', 1) >= 0]

        total = len(targets)
        for i, n in enumerate(targets):
            ctx = _build_pfield_context(
                self, n, i, total,
                is_rest=self._rt[n].get('proportion', 1) < 0
            )
            resolved = {}
            for k, v in fields.items():
                if callable(v):
                    arity = _callable_arity(v)
                    resolved[k] = v(ctx) if arity >= 1 else v()
                elif isinstance(v, Pattern):
                    val = next(v)
                    if val is not None:
                        resolved[k] = val
            if resolved:
                if setter == 'pfields':
                    self._pt.set_pfields(n, **resolved)
                else:
                    self._pt.set_mfields(n, **resolved)

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
        """
        targets = [node] if isinstance(node, int) else list(node)

        distributable_fields = {k: v for k, v in kwargs.items()
                               if callable(v) or isinstance(v, Pattern)}
        static_fields = {k: v for k, v in kwargs.items()
                        if k not in distributable_fields}

        for n in targets:
            if static_fields:
                self._pt.set_pfields(n, **static_fields)

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
        """
        targets = [node] if isinstance(node, int) else list(node)

        distributable_fields = {k: v for k, v in kwargs.items()
                               if callable(v) or isinstance(v, Pattern)}
        static_fields = {k: v for k, v in kwargs.items()
                        if k not in distributable_fields}

        for n in targets:
            if static_fields:
                self._pt.set_mfields(n, **static_fields)

        if distributable_fields:
            self._distribute_to_targets(targets, distributable_fields, include_rests, setter='mfields')

    def _bake_envelope(self, selected, envelope, pfields_list, endpoint):
        self._ensure_timing_cache()
        sounding = [n for n in selected if self.nodes[n].get('proportion', 1) >= 0]
        if not sounding:
            return
        start_time = min(self.nodes[n]['real_onset'] for n in sounding)
        if endpoint:
            end_time = max(self.nodes[n]['real_onset'] + abs(self.nodes[n]['real_duration']) for n in sounding)
        else:
            end_time = max(self.nodes[n]['real_onset'] for n in sounding)
        duration = end_time - start_time
        scaled_envelope = Envelope(
            values=envelope.values,
            times=envelope.times,
            curve=envelope._curve,
            time_scale=duration / envelope.total_time if envelope.total_time > 0 else 1.0
        )
        for node in sounding:
            event_time = self.nodes[node]['real_onset']
            relative_time = max(0, min(event_time - start_time, scaled_envelope.total_time))
            try:
                env_value = scaled_envelope.at_time(relative_time)
            except ValueError:
                env_value = scaled_envelope.values[0] if relative_time <= 0 else scaled_envelope.values[-1]
            self._pt.set_pfields(node, **{pfield: env_value for pfield in pfields_list})

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

    def _resolve_control_envelope_time_span(self, desc, sounding=None):
        if sounding is None:
            sounding = self._resolve_control_envelope_leaves(desc)
        if not sounding:
            return (0.0, 0.0)
        self._ensure_timing_cache()
        start = min(self.nodes[n]['real_onset'] for n in sounding)
        if desc["endpoint"]:
            end = max(self.nodes[n]['real_onset'] + abs(self.nodes[n]['real_duration']) for n in sounding)
        else:
            end = max(self.nodes[n]['real_onset'] for n in sounding)
        return (start, end)

    def _check_envelope_overlap(self, new_pfields, new_leaves):
        new_pf_set = set(new_pfields)
        new_leaf_set = set(new_leaves)
        for desc in self._control_envelopes:
            if not new_pf_set.intersection(desc["pfields"]):
                continue
            existing_leaves = set(self._resolve_control_envelope_leaves(desc))
            if new_leaf_set.intersection(existing_leaves):
                raise ValueError("Overlapping control envelopes on the same pfield")

    def _rebake_control_envelope(self, desc):
        sounding = self._resolve_control_envelope_leaves(desc)
        if sounding:
            self._bake_envelope(sounding, desc["envelope"], desc["pfields"], desc["endpoint"])

    def _record_control_envelope(self, selected, envelope, pfields_list, endpoint):
        self._ensure_timing_cache()
        sounding = [n for n in selected if self._rt[n].get('proportion', 1) >= 0]
        if not sounding:
            return

        anchor_node = selected[0]
        for n in selected[1:]:
            anchor_node = self._rt.lowest_common_ancestor(anchor_node, n)

        all_anchor_leaves = set(self._rt.subtree_leaves(anchor_node))
        leaf_subset = None if set(selected) == all_anchor_leaves else frozenset(selected)

        self._check_envelope_overlap(pfields_list, sounding)
        self._bake_envelope(sounding, envelope, pfields_list, endpoint)

        self._control_envelopes.append({
            "envelope": envelope,
            "pfields": list(pfields_list),
            "endpoint": endpoint,
            "anchor_node": anchor_node,
            "leaf_subset": leaf_subset,
        })

    def resolved_control_envelopes(self):
        self._ensure_timing_cache()
        result = []
        for desc in self._control_envelopes:
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
            apply_fn(selected, envelope, pfields_list, endpoint)
        elif scope == "per_node":
            groups = self._resolve_per_node_leaf_groups(node)
            for group in groups:
                selected = self._apply_offset_take(group, offset=offset, take=take)
                apply_fn(selected, envelope, pfields_list, endpoint)
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
                rest_set = {n for n in selected if self._rt[n].get('proportion', 1) < 0}
                segments = self._partition_non_rest_segments(selected, rest_set)
                for segment in segments:
                    self._validate_slur_segment(segment, reserved_sets)
                    slur_id = self._register_slur(segment)
                    reserved_sets.append(set(segment))
                    slur_ids.append(slur_id)
            return slur_ids
        raise ValueError(f"Unknown mode: {mode}")

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
        new_leaf_set = frozenset(new_leaves)
        for desc in self._control_envelopes:
            needs_rebake = False
            if desc["leaf_subset"] is not None and old_leaf in desc["leaf_subset"]:
                desc["leaf_subset"] = (desc["leaf_subset"] - {old_leaf}) | new_leaf_set
                needs_rebake = True
            elif desc["leaf_subset"] is None:
                ancestor_set = set(self._rt.descendants(desc["anchor_node"])) | {desc["anchor_node"]}
                if old_leaf in ancestor_set:
                    needs_rebake = True
            if needs_rebake:
                self._rebake_control_envelope(desc)

    def _filter_envelopes_for_rests(self, affected_leaves):
        for desc in list(self._control_envelopes):
            touched = False
            if desc["leaf_subset"] is not None:
                if desc["leaf_subset"].intersection(affected_leaves):
                    desc["leaf_subset"] = desc["leaf_subset"] - affected_leaves
                    touched = True
            else:
                anchor_leaves = set(self._rt.subtree_leaves(desc["anchor_node"]))
                if anchor_leaves.intersection(affected_leaves):
                    touched = True
            if touched and not self._resolve_control_envelope_leaves(desc):
                warnings.warn(
                    "Control envelope removed: all target leaves are now rests",
                    RuntimeWarning, stacklevel=3
                )
                self._control_envelopes.remove(desc)

    def _invalidate_envelopes_for_removed_nodes(self, removed_set):
        for desc in list(self._control_envelopes):
            if desc["anchor_node"] in removed_set:
                warnings.warn(
                    "Control envelope removed: anchor node was destroyed",
                    RuntimeWarning, stacklevel=3
                )
                self._control_envelopes.remove(desc)
                continue
            if desc["leaf_subset"] is not None and desc["leaf_subset"].intersection(removed_set):
                desc["leaf_subset"] = desc["leaf_subset"] - removed_set
                if not self._resolve_control_envelope_leaves(desc):
                    warnings.warn(
                        "Control envelope removed: all target leaves were destroyed",
                        RuntimeWarning, stacklevel=3
                    )
                    self._control_envelopes.remove(desc)

    def make_rest(self, node: int) -> None:
        """
        Make a node (and its subtree) a rest, splitting intersecting slurs
        and filtering control envelopes.
        
        Parameters
        ----------
        node : int
            The node ID to convert to a rest.
        """
        affected = set([node] + list(self._rt.descendants(node)))
        affected_leaves = {n for n in affected if n in self._rt.leaf_nodes}
        self._split_slurs_for_rests(affected_leaves)
        super().make_rest(node)
        self._filter_envelopes_for_rests(affected_leaves)

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
        parent_data = self._pt[node].active_items()
        pfields = {k: v for k, v in parent_data.items() if k in self._pt._meta['pfields']}
        mfields = {k: v for k, v in parent_data.items() if k in self._pt._meta['mfields']}

        self._rt.subdivide(node, S)
        self._invalidate_timing_cache()
        new_children = list(self._rt.successors(node))

        for _ in new_children:
            self._pt.add_child(node)
        self._pt._invalidate_caches()

        for child in new_children:
            if pfields:
                self._pt.set_pfields(child, **pfields)
            if mfields:
                self._pt.set_mfields(child, **mfields)

        new_leaves = list(self._rt.subtree_leaves(node))
        self._heal_slurs_after_subdivide(node, new_leaves)
        self._heal_envelopes_after_subdivide(node, new_leaves)

    def add_child(self, parent, **attr):
        if 'label' in attr and 'proportion' not in attr:
            attr = dict(attr)
            attr['proportion'] = attr.pop('label')
        new_rt_node = self._rt.add_child(parent, **attr)
        self._pt.add_child(parent)
        return new_rt_node

    def prune(self, node):
        removed_set = {node}
        self._invalidate_slurs_for_removed_nodes(removed_set)
        self._invalidate_envelopes_for_removed_nodes(removed_set)
        self._rt.prune(node)
        self._pt.prune(node)

    def remove_subtree(self, node):
        removed_set = {node} | set(self._rt.descendants(node))
        self._invalidate_slurs_for_removed_nodes(removed_set)
        self._invalidate_envelopes_for_removed_nodes(removed_set)
        self._rt.remove_subtree(node)
        self._pt.remove_subtree(node)

    def set_instrument(self, node, instrument) -> None:
        """
        Set an instrument for target node(s).
        
        Parameters
        ----------
        node : int or list/tuple of int
            Target node(s). Single node: instrument set on that node, inherits
            to descendants. List of nodes: instrument evaluated once per node.
        instrument : Instrument, str, int, Pattern, or callable
            - Instrument: set directly on node with pfield defaults
            - str: raw synth reference (defName for SC, tonejs_class for Tone.js)
            - int: raw program number (MIDI)
            - Pattern: next() called once per target node
            - Callable: evaluated once per target node (0-arg or 1-arg with DistributionContext)
        """
        targets = [node] if isinstance(node, int) else list(node)

        if isinstance(instrument, (str, int)):
            for n in targets:
                self._pt.set_instrument(n, instrument)
        elif isinstance(instrument, (Instrument, Effect)):
            for n in targets:
                self._pt.set_instrument(n, instrument)
        elif callable(instrument) or isinstance(instrument, Pattern):
            total = len(targets)
            for i, n in enumerate(targets):
                if isinstance(instrument, Pattern):
                    inst = next(instrument)
                else:
                    ctx = _build_pfield_context(
                        self, n, i, total,
                        is_rest=self._rt[n].get('proportion', 1) < 0
                    )
                    arity = _callable_arity(instrument)
                    inst = instrument(ctx) if arity >= 1 else instrument()
                if inst is not None:
                    self._pt.set_instrument(n, inst)

    def set(self, node, inst=None, mfields=None, pfields=None,
            include_rests=False):
        """
        Convenience method to set instrument, meta fields, and parameter fields in one call.
        
        Parameters
        ----------
        node : int or list/tuple of int
            Target node(s).
        inst : Instrument, Pattern, callable, or None, optional
            Instrument to assign.
        mfields : dict or None, optional
            Meta field names and values to set.
        pfields : dict or None, optional
            Parameter field names and values to set.
        include_rests : bool, optional
            When True, rest nodes are included during callable/Pattern
            distribution (default is False).
        """
        if inst is not None:
            self.set_instrument(node, inst)
        if mfields is not None:
            self.set_mfields(node, include_rests=include_rests, **mfields)
        if pfields is not None:
            self.set_pfields(node, include_rests=include_rests, **pfields)

    def sparsify(self, probability, node=None):
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
        """
        if not callable(probability):
            super().sparsify(probability, node)
            return

        import numpy as _np
        if node is None:
            targets = list(self._rt.leaf_nodes)
        elif isinstance(node, int):
            targets = list(self._rt.subtree_leaves(node))
        else:
            seen = set()
            targets = []
            for n in node:
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
        return self._pt.get_instrument(node)

    def get_pfield(self, node: int, key: str, default=None):
        """Parameter field value for node (PT only, no instrument fallback)."""
        value = self._pt.get_pfield(node, key)
        return default if value is None else value

    def get_mfield(self, node: int, key: str, default=None):
        """Meta field value for node."""
        value = self._pt.get_mfield(node, key)
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
        else:
            affected_nodes = {node} | set(self._rt.descendants(node))
            affected_leaves = {n for n in affected_nodes if n in self._rt.leaf_nodes}
            self._split_slurs_for_rests(affected_leaves)
            self._invalidate_envelopes_for_removed_nodes(affected_nodes)
        
        self._pt.clear(node)
    
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

        def _path_signature(tree, root_node, target_node):
            branch = list(tree.branch(target_node))
            root_idx = branch.index(root_node)
            signature = []
            for i in range(root_idx + 1, len(branch)):
                parent = branch[i - 1]
                current = branch[i]
                signature.append(list(tree.successors(parent)).index(current))
            return tuple(signature)

        def _node_from_signature(tree, root_node, signature):
            current = root_node
            for idx in signature:
                current = list(tree.successors(current))[idx]
            return current

        old_to_new_mapping = {}
        for old_node in original_subtree_nodes:
            sig = _path_signature(self._rt, node, old_node)
            old_to_new_mapping[old_node] = _node_from_signature(new_cu._rt, new_cu._rt.root, sig)

        for old_node, new_node in old_to_new_mapping.items():
            old_proportion = self._rt[old_node].get('proportion')
            if old_proportion is not None and old_proportion < 0:
                new_cu.make_rest(new_node)

        for old_node, new_node in old_to_new_mapping.items():
            node_data = self._pt.items(old_node)
            new_cu._pt._graph[new_node] = dict(node_data)
        new_cu._pt._meta['pfields'] = set(self._pt._meta.get('pfields', set()))
        new_cu._pt._meta['mfields'] = set(self._pt._meta.get('mfields', set()))

        subtree_node_set = set(original_subtree_nodes)
        governing_instrument_node = self._pt._resolve_governing_instrument_node(node)
        if (governing_instrument_node is not None
            and governing_instrument_node not in subtree_node_set
            and governing_instrument_node in self._pt._node_instruments):
            new_cu._pt.set_instrument(
                new_cu._pt.root,
                self._pt._node_instruments[governing_instrument_node]
            )
        for old_node in original_subtree_nodes:
            if old_node in self._pt._node_instruments:
                new_cu._pt.set_instrument(
                    old_to_new_mapping[old_node],
                    self._pt._node_instruments[old_node]
                )

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
        for desc in self._control_envelopes:
            if desc["anchor_node"] not in subtree_node_set:
                continue
            new_anchor = old_to_new_mapping[desc["anchor_node"]]
            new_leaf_subset = None
            if desc["leaf_subset"] is not None:
                mapped_leaves = frozenset(
                    old_to_new_mapping[n] for n in desc["leaf_subset"]
                    if n in old_to_new_mapping
                )
                if not mapped_leaves:
                    continue
                new_leaf_subset = mapped_leaves
            new_cu._control_envelopes.append({
                "envelope": desc["envelope"],
                "pfields": list(desc["pfields"]),
                "endpoint": desc["endpoint"],
                "anchor_node": new_anchor,
                "leaf_subset": new_leaf_subset,
            })

        return new_cu
    
    def copy(self):
        """
        Create a deep copy of this CompositionalUnit.
        
        Returns
        -------
        CompositionalUnit
            A new CompositionalUnit with identical structure, parameters,
            instruments, envelopes, and slurs.
        """
        return self.from_subtree(self.rt.root)
