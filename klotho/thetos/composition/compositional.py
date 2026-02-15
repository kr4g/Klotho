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
from klotho.dynatos.envelopes import Envelope
from klotho.topos.collections.sequences import Pattern


@dataclass
class PFieldContext:
    index: int
    total: int
    node: int
    is_rest: bool
    params: dict


def _callable_arity(fn):
    try:
        sig = inspect.signature(fn)
        return len([p for p in sig.parameters.values()
                    if p.default is inspect.Parameter.empty])
    except (ValueError, TypeError):
        return 0


class Event(Chronon):
    """
    An enhanced Chronon that includes parameter field access.
    
    Extends the basic temporal event data (start, duration, etc.) with 
    access to musical parameters stored in a synchronized ParameterTree.
    """
    
    __slots__ = ('_pt', '_instrument_resolver')
    
    def __init__(self, node_id: int, rt: RhythmTree, pt: ParameterTree, instrument_resolver=None):
        super().__init__(node_id, rt)
        self._pt = pt
        self._instrument_resolver = instrument_resolver
    
    @property
    def parameters(self):
        """
        Get all active parameter fields for this event.
        
        Returns
        -------
        dict
            Dictionary of active parameter field names and values
        """
        params = {}
        instrument, exclude = self._resolve_instrument()
        if instrument is not None:
            params = {k: instrument[k] for k in instrument.keys()}
        params.update(self._pt[self._node_id].active_items())
        if instrument is not None and exclude:
            for key in exclude:
                if key in instrument.keys():
                    params[key] = instrument[key]
        return params

    def _resolve_instrument(self):
        if callable(self._instrument_resolver):
            return self._instrument_resolver(self._node_id)
        return None, set()
    
    def get_parameter(self, key: str, default=None):
        """
        Get a specific parameter value for this event.
        
        Parameters
        ----------
        key : str
            The parameter field name to retrieve
        default : Any, optional
            Default value if parameter not found
            
        Returns
        -------
        Any
            The parameter value or default
        """
        value = self._pt.get(self._node_id, key)
        if value is not None:
            return value
        instrument, _ = self._resolve_instrument()
        if instrument is not None:
            if key == 'synthName':
                return instrument['synth_name']
            if key in instrument.keys():
                return instrument[key]
        return default
    
    def __getitem__(self, key: str):
        """
        Access temporal or parameter attributes by key.
        
        Parameters
        ----------
        key : str
            Attribute name (temporal property or parameter field)
            
        Returns
        -------
        Any
            The requested attribute value
        """
        temporal_attrs = {'start', 'duration', 'end', 'proportion', 'metric_duration', 'node_id', 'is_rest'}
        if key in temporal_attrs:
            return getattr(self, key)
        return self.get_parameter(key)


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
        
        self._node_instruments = {}
        self._instrument_exclusions = {}
        self._active_instrument_cache = {}
        self._instrument_version = 0
        
        if inst is not None:
            self.set_instrument(self._pt.root, inst)
        
        self._env_specs = {}
        self._next_env_id = 0
        self._slur_specs = {}
        self._next_slur_id = 0
    
    @classmethod
    def from_rt(cls, rt: RhythmTree, beat: Union[None, Fraction, int, float, str] = None, bpm: Union[None, int, float] = None, pfields: Union[dict, list, None] = None, mfields: Union[dict, list, None] = None, inst: Union[Instrument, None] = None):
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
        pt = ParameterTree(self._rt.meas.numerator, self._rt.subdivisions)
        
        for node in pt.nodes:
            node_data = pt[node]
            node_data.clear()
        
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

    def _invalidate_instrument_cache(self):
        self._instrument_version += 1
        self._active_instrument_cache.clear()

    def _normalize_exclude(self, exclude):
        if exclude is None:
            return set()
        if isinstance(exclude, str):
            return {exclude}
        if isinstance(exclude, (list, tuple, set)):
            return set(exclude)
        return set(exclude)

    def _resolve_governing_instrument_node(self, node: int):
        if node in self._node_instruments:
            return node
        for ancestor in reversed(self._rt.branch(node)[:-1]):
            if ancestor in self._node_instruments:
                return ancestor
        return None

    def _resolve_instrument_with_exclusions(self, node: int):
        cache_key = (node, self._instrument_version)
        if cache_key in self._active_instrument_cache:
            return self._active_instrument_cache[cache_key]
        governing = self._resolve_governing_instrument_node(node)
        if governing is None:
            result = (None, set())
        else:
            result = (
                self._node_instruments.get(governing),
                self._instrument_exclusions.get(governing, set())
            )
        self._active_instrument_cache[cache_key] = result
        return result

    def get_active_instrument(self, node: int):
        instrument, _ = self._resolve_instrument_with_exclusions(node)
        return instrument

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
        indices = [leaf_order.index(leaf) for leaf in ordered]
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
        idx = [leaf_order.index(leaf) for leaf in leaves]
        return min(idx), max(idx)

    def _build_effective_parameter_tree(self):
        pt_snapshot = self._pt.copy()
        if self._events is None:
            super()._evaluate()
        for env_spec in self._env_specs.values():
            selected_leaves = env_spec['leaf_nodes']
            sounding = [n for n in selected_leaves if self._rt[n].get('proportion', 1) >= 0]
            if not sounding:
                continue
            start_time = min(self._rt[n]['real_onset'] for n in sounding)
            if env_spec['endpoint']:
                end_time = max(self._rt[n]['real_onset'] + abs(self._rt[n]['real_duration']) for n in sounding)
            else:
                end_time = max(self._rt[n]['real_onset'] for n in sounding)
            duration = end_time - start_time
            envelope = env_spec['envelope']
            scaled_envelope = Envelope(
                values=envelope.values,
                times=envelope.times,
                curve=envelope._curve,
                time_scale=duration / envelope.total_time if envelope.total_time > 0 else 1.0
            )
            for node in sounding:
                event_time = self._rt[node]['real_onset']
                relative_time = max(0, min(event_time - start_time, scaled_envelope.total_time))
                try:
                    env_value = scaled_envelope.at_time(relative_time)
                except ValueError:
                    env_value = scaled_envelope.values[0] if relative_time <= 0 else scaled_envelope.values[-1]
                pt_snapshot.set_pfields(node, **{pfield: env_value for pfield in env_spec['pfields']})
        for slur_id, slur_spec in self._slur_specs.items():
            leaves = list(slur_spec['leaf_nodes'])
            if not leaves:
                continue
            first, last = leaves[0], leaves[-1]
            for leaf in leaves:
                pt_snapshot.set_pfields(
                    leaf,
                    _slur_start=1 if leaf == first else 0,
                    _slur_end=1 if leaf == last else 0,
                    _slur_id=slur_id
                )
        return pt_snapshot

    def _evaluate(self):
        """
        Updates node timings and returns Event objects instead of Chronon objects.
        
        Returns
        -------
        tuple of Event
            Events containing both temporal and parameter data
        """
        super()._evaluate()
        eval_pt = self._build_effective_parameter_tree()
        leaf_nodes = self._rt.leaf_nodes
        return tuple(Event(node_id, self._rt, eval_pt, self._resolve_instrument_with_exclusions) for node_id in leaf_nodes)

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
        if self._events is None:
            self._events = self._evaluate()
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
        if self._events is None:
            self._events = self._evaluate()
        base_data = []
        for event in self._events:
            event_dict = {
                'node_id': event.node_id,
                'start': event.start,
                'duration': event.duration,
                'end': event.end,
                'is_rest': event.is_rest,
                's': event.proportion,
                'metric_duration': event.metric_duration,
            }
            event_dict.update(event.parameters)
            base_data.append(event_dict)
        
        return pd.DataFrame(base_data, index=range(len(self._events)))
    
    def _distribute_to_targets(self, targets, fields, include_rests, setter='pfields'):
        if not include_rests:
            targets = [n for n in targets
                       if self._rt[n].get('proportion', 1) >= 0]

        total = len(targets)
        for i, n in enumerate(targets):
            ctx = PFieldContext(
                index=i,
                total=total,
                node=n,
                is_rest=self._rt[n].get('proportion', 1) < 0,
                params=(self._pt[n].active_items()
                        if hasattr(self._pt[n], 'active_items') else {})
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
            - Callable: evaluated once per target node (0-arg or 1-arg with PFieldContext)
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
            - Callable: evaluated once per target node (0-arg or 1-arg with PFieldContext)
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

    def _validate_envelope_selection(self, selected, pfields_list, reserved_ranges=None):
        proposed_range = self._selection_index_range(selected)
        for spec in self._env_specs.values():
            if not set(spec['pfields']).intersection(pfields_list):
                continue
            if self._ranges_overlap(proposed_range, spec['index_range']):
                raise ValueError("Envelope overlap detected for one or more target pfields")
        if reserved_ranges:
            for reserved_range in reserved_ranges:
                if self._ranges_overlap(proposed_range, reserved_range):
                    raise ValueError("Envelope overlap detected within requested per-node applications")
        return proposed_range

    def _register_envelope(self, selected, envelope, pfields_list, endpoint):
        proposed_range = self._validate_envelope_selection(selected, pfields_list)
        env_id = self._next_env_id
        self._next_env_id += 1
        self._env_specs[env_id] = {
            'envelope': envelope,
            'leaf_nodes': selected,
            'pfields': pfields_list,
            'endpoint': endpoint,
            'index_range': proposed_range
        }
        return env_id

    def apply_envelope(self,
                       envelope: Envelope,
                       pfields: Union[str, list],
                       node: Union[int, list, tuple, set],
                       offset: int = 0,
                       take: Union[int, None] = None,
                       mode: Literal["span", "per_node"] = "span",
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
            can be treated either as one combined span (`mode=\"span\"`) or as
            independent per-node applications (`mode=\"per_node\"`).
        offset : int, default=0
            Leaf offset into the resolved contiguous selection.
        take : int, optional
            Number of leaves to include from `offset`. If omitted, uses all leaves
            from `offset` to the end of the resolved selection.
        mode : {"span", "per_node"}, default="span"
            Selection interpretation mode.
        endpoint : bool, default=True
            If True, envelope span is onset-to-end of the selected sounding leaves.
            If False, span is onset-to-onset.
            
        Returns
        -------
        int | list[int]
            Envelope identifier, or list of identifiers when `mode="per_node"`
            applies. In per-node mode, the return value is always a list.

        Raises
        ------
        ValueError
            If selection is invalid/non-contiguous, offset/take overflows bounds,
            a same-pfield overlap is detected, or mode is invalid.
        """
        pfields_list = pfields if isinstance(pfields, list) else [pfields]
        if mode == "span":
            selected = self._resolve_leaf_selection(node=node)
            selected = self._apply_offset_take(selected, offset=offset, take=take)
            env_id = self._register_envelope(selected, envelope, pfields_list, endpoint)
            self._events = None
            return env_id
        if mode == "per_node":
            selections = []
            groups = self._resolve_per_node_leaf_groups(node)
            reserved_ranges = []
            for group in groups:
                selected = self._apply_offset_take(group, offset=offset, take=take)
                selection_range = self._validate_envelope_selection(
                    selected,
                    pfields_list,
                    reserved_ranges=reserved_ranges
                )
                reserved_ranges.append(selection_range)
                selections.append(selected)
            env_ids = []
            for selected in selections:
                env_ids.append(self._register_envelope(selected, envelope, pfields_list, endpoint))
            self._events = None
            return env_ids
        raise ValueError(f"Unknown mode: {mode}")

    def _validate_slur_selection(self, selected, reserved_sets=None):
        if len(selected) < 2:
            raise ValueError("Slur requires at least two leaves")
        if any(self._rt[n].get('proportion', 1) < 0 for n in selected):
            raise ValueError("Slur selections cannot include rests")
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
            slur_id = self._register_slur(selected)
            self._events = None
            return slur_id
        if mode == "per_node":
            selections = []
            groups = self._resolve_per_node_leaf_groups(node)
            reserved_sets = []
            for group in groups:
                selected = self._apply_offset_take(group, offset=offset, take=take)
                proposed_set, _ = self._validate_slur_selection(selected, reserved_sets=reserved_sets)
                reserved_sets.append(proposed_set)
                selections.append(selected)
            slur_ids = []
            for selected in selections:
                slur_ids.append(self._register_slur(selected))
            self._events = None
            return slur_ids
        raise ValueError(f"Unknown mode: {mode}")

    def _remove_slurs_for_nodes(self, nodes_to_remove: set[int]):
        removed = []
        for slur_id, spec in list(self._slur_specs.items()):
            if spec['leaf_set'].intersection(nodes_to_remove):
                removed.append(slur_id)
                del self._slur_specs[slur_id]
        if removed:
            warnings.warn(
                f"Removed slur(s) {removed} because rests were introduced into slurred span(s).",
                RuntimeWarning
            )

    def make_rest(self, node: int) -> None:
        """
        Make a node/subtree rest and remove intersecting slurs.

        Any existing slur touching newly-rested leaves is removed and a warning
        is emitted, then rest mutation is applied to the rhythm tree.
        """
        affected = set([node] + list(self._rt.descendants(node)))
        affected_leaves = set([n for n in affected if n in self._rt.leaf_nodes])
        self._remove_slurs_for_nodes(affected_leaves)
        super().make_rest(node)
        self._events = None
    
    def set_instrument(self, node, instrument, exclude=None) -> None:
        """
        Set an instrument for target node(s).
        
        Parameters
        ----------
        node : int or list/tuple of int
            Target node(s). Single node: instrument set on that node, inherits
            to descendants. List of nodes: instrument evaluated once per node.
        instrument : Instrument, Pattern, or callable
            - Instrument: set directly on node (current behavior)
            - Pattern: next() called once per target node
            - Callable: evaluated once per target node (0-arg or 1-arg with PFieldContext)
        exclude : str, list, set, or None, optional
            Parameter fields to exclude from instrument application
        """
        targets = [node] if isinstance(node, int) else list(node)

        if isinstance(instrument, Instrument):
            for n in targets:
                self._node_instruments[n] = instrument
                self._instrument_exclusions[n] = self._normalize_exclude(exclude)
                self._pt._meta['pfields'].update(instrument.keys())
                self._invalidate_instrument_cache()
        elif callable(instrument) or isinstance(instrument, Pattern):
            total = len(targets)
            for i, n in enumerate(targets):
                if isinstance(instrument, Pattern):
                    inst = next(instrument)
                else:
                    ctx = PFieldContext(
                        index=i,
                        total=total,
                        node=n,
                        is_rest=self._rt[n].get('proportion', 1) < 0,
                        params=(self._pt[n].active_items()
                                if hasattr(self._pt[n], 'active_items') else {})
                    )
                    arity = _callable_arity(instrument)
                    inst = instrument(ctx) if arity >= 1 else instrument()
                if inst is not None:
                    self._node_instruments[n] = inst
                    self._instrument_exclusions[n] = self._normalize_exclude(exclude)
                    self._pt._meta['pfields'].update(inst.keys())
                    self._invalidate_instrument_cache()

    def set(self, node, inst=None, mfields=None, pfields=None,
            exclude=None, include_rests=False):
        if inst is not None:
            self.set_instrument(node, inst, exclude=exclude)
        if mfields is not None:
            self.set_mfields(node, include_rests=include_rests, **mfields)
        if pfields is not None:
            self.set_pfields(node, include_rests=include_rests, **pfields)

    def sparsify(self, probability, node=None):
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
            ctx = PFieldContext(
                index=i, total=total, node=leaf,
                is_rest=False,
                params=(self._pt[leaf].active_items()
                        if hasattr(self._pt[leaf], 'active_items')
                        else {})
            )
            if probability(ctx):
                self.make_rest(leaf)

    def get_parameter(self, node: int, key: str, default=None):
        """
        Get an effective value for a specific node key.
        
        Parameters
        ----------
        node : int
            The node ID to query
        key : str
            Parameter or instrument field name.
        default : Any, optional
            Default value if parameter not found
            
        Returns
        -------
        Any
            The resolved value from PT first, then from active instrument fields.
            Returns default if unresolved.
        """
        value = self._pt.get(node, key)
        if value is not None:
            return value
        instrument = self.get_active_instrument(node)
        if instrument is not None:
            if key == 'synthName':
                return instrument['synth_name']
            if key in instrument.keys():
                return instrument[key]
        return default
    
    def clear_parameters(self, node: int = None) -> None:
        """
        Clear parameter values and intersecting overlays.
        
        Parameters
        ----------
        node : int, optional
            Node ID to clear. If None, clears all nodes and all UC overlays.
        """
        if node is None:
            self._env_specs.clear()
            self._slur_specs.clear()
        else:
            affected_nodes = {node}.union(set(self._rt.descendants(node)))
            affected_leaves = {n for n in affected_nodes if n in self._rt.leaf_nodes}
            for env_id, env_spec in list(self._env_specs.items()):
                if set(env_spec['leaf_nodes']).intersection(affected_leaves):
                    del self._env_specs[env_id]
            self._remove_slurs_for_nodes(affected_leaves)
        
        self._pt.clear(node)
        self._events = None
    
    def get_event_parameters(self, idx: int) -> dict:
        """
        Get all parameter values for a specific event by index.
        
        Parameters
        ----------
        idx : int
            Event index
            
        Returns
        -------
        dict
            Dictionary of parameter field names and values
        """
        if self._events is None:
            self._events = self._evaluate()
        return self._events[idx].parameters
    
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
            new_cu._pt.nodes[new_node].clear()
            new_cu._pt.nodes[new_node].update(node_data)
        new_cu._pt._meta['pfields'] = set(self._pt._meta.get('pfields', set()))
        new_cu._pt._meta['mfields'] = set(self._pt._meta.get('mfields', set()))
        new_cu._pt._invalidate_parameter_caches()

        subtree_node_set = set(original_subtree_nodes)
        governing_instrument_node = self._resolve_governing_instrument_node(node)
        if (governing_instrument_node is not None
            and governing_instrument_node not in subtree_node_set
            and governing_instrument_node in self._node_instruments):
            new_cu.set_instrument(
                new_cu._pt.root,
                self._node_instruments[governing_instrument_node],
                exclude=self._instrument_exclusions.get(governing_instrument_node)
            )
        for old_node in original_subtree_nodes:
            if old_node in self._node_instruments:
                new_cu.set_instrument(
                    old_to_new_mapping[old_node],
                    self._node_instruments[old_node],
                    exclude=self._instrument_exclusions.get(old_node)
                )

        old_leaf_set = set(self._rt.subtree_leaves(node))
        for env_id, env_spec in self._env_specs.items():
            env_leaf_set = set(env_spec['leaf_nodes'])
            if env_leaf_set and env_leaf_set.issubset(old_leaf_set):
                mapped = []
                for old_leaf in env_spec['leaf_nodes']:
                    if old_leaf in old_to_new_mapping:
                        mapped.append(old_to_new_mapping[old_leaf])
                if mapped:
                    new_cu.apply_envelope(
                        envelope=env_spec['envelope'],
                        pfields=env_spec['pfields'],
                        node=mapped,
                        endpoint=env_spec['endpoint']
                    )
        for slur_id, slur_spec in self._slur_specs.items():
            slur_leaf_set = set(slur_spec['leaf_nodes'])
            if slur_leaf_set and slur_leaf_set.issubset(old_leaf_set):
                mapped = []
                for old_leaf in slur_spec['leaf_nodes']:
                    if old_leaf in old_to_new_mapping:
                        mapped.append(old_to_new_mapping[old_leaf])
                if mapped:
                    new_cu.apply_slur(node=mapped)
        
        return new_cu
    
    def copy(self):
        return self.from_subtree(self.rt.root)
