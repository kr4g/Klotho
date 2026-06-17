"""
Compositional units combining temporal structure with parameterized events.

This module provides ``CompositionalUnit``, which extends ``TemporalUnit``
with a synchronized ``ParameterTree`` for hierarchical parameter management,
envelope application, slur marking, and instrument assignment. The ``Parametron``
class extends ``Chronon`` with parameter field access.
"""

from typing import Union, Optional, Any, Literal
from fractions import Fraction
from dataclasses import dataclass, field
import inspect
import warnings
import pandas as pd

from klotho.chronos import TemporalUnit, RhythmTree, Meas
from klotho.chronos.temporal_units.temporal import Chronon, NodeContext, UTNodeHandle, UTNodeSelector
from klotho.thetos.parameters import ParameterTree
from klotho.thetos.parameters.parameter_tree import ParameterApiMixin, ParameterLayer
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


@dataclass(frozen=True)
class ParentDistributionView:
    ref: UTNodeHandle
    is_rest: bool
    pfields: dict
    mfields: dict
    instrument: Any
    _owner: Any = field(repr=False, compare=False)

    @property
    def id(self) -> int:
        return self.ref.id

    @property
    def parent(self) -> Optional['ParentDistributionView']:
        return self._owner._build_parent_distribution_view(self.id)

    def __getattr__(self, key):
        return getattr(self.ref, key)


@dataclass(frozen=True)
class DistributionContext(NodeContext):
    is_rest: bool
    pfields: dict
    mfields: dict
    instrument: Any
    _owner: Any = field(repr=False, compare=False)

    @property
    def parent(self) -> Optional[ParentDistributionView]:
        return self._owner._build_parent_distribution_view(self.id)


PFieldContext = DistributionContext


def _resolve_kit_member(inst, pt, node):
    if isinstance(inst, Kit):
        selector_val = pt.get_pfield(node, inst.selector)
        return inst._resolve(selector_val)
    return inst


def _build_pfield_context(uc, node: int, index: int, total: int, is_rest: bool) -> DistributionContext:
    _ = is_rest
    return uc._build_node_context(node, index, total)


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
        if effective is not None and hasattr(effective, 'pfields'):
            result.update(dict(effective.pfields))
        for k in self._pt.pfield_names:
            v = self._pt.get_pfield(self._node_id, k)
            if v is not None:
                result[k] = v
            elif effective is not None and hasattr(effective, 'pfields'):
                eff_pfields = effective.pfields
                if k in eff_pfields:
                    result[k] = eff_pfields[k]
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
                for k in self._pt.mfield_names}

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

    def set_instrument(self, instrument):
        """Assign an instrument (or Pattern/callable thereof) to the selection."""
        return self._owner.set_instrument(self, instrument)

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

    def set(self, *, inst=None, mfields=None, pfields=None,
            include_rests: bool = False):
        """Set instrument / mfields / pfields in one call across the selection."""
        return self._owner.set(
            self, inst=inst, mfields=mfields,
            pfields=pfields, include_rests=include_rests,
        )

    # --- Per-node getters (return list aligned with self._ids) ---
    def get_pfield(self, key: str, default=None) -> list:
        return [self._owner.get_pfield(n, key, default) for n in self._ids]

    def get_mfield(self, key: str, default=None) -> list:
        return [self._owner.get_mfield(n, key, default) for n in self._ids]

    def get_instrument(self) -> list:
        return [self._owner.get_instrument(n) for n in self._ids]


class UCNodeHandle(UTNodeHandle):
    def set_pfields(self, include_rests: bool = False, **kwargs):
        return self._owner.set_pfields(self.id, include_rests=include_rests, **kwargs)

    def set_mfields(self, include_rests: bool = False, **kwargs):
        return self._owner.set_mfields(self.id, include_rests=include_rests, **kwargs)

    def set_instrument(self, instrument):
        return self._owner.set_instrument(self.id, instrument)

    def apply_envelope(self, envelope, pfields, *, offset=0, take=None,
                       scope: str = 'span', control: bool = False,
                       endpoint: bool = True):
        return self._owner.apply_envelope(
            envelope, pfields, node=self.id,
            offset=offset, take=take, scope=scope,
            control=control, endpoint=endpoint,
        )

    def apply_slur(self, *, offset=0, take=None, mode: str = 'span'):
        return self._owner.apply_slur(
            node=self.id, offset=offset, take=take, mode=mode
        )

    def clear_parameters(self):
        return self._owner.clear_parameters(self.id)

    def set(self, *, inst=None, mfields=None, pfields=None,
            include_rests: bool = False):
        return self._owner.set(
            self.id, inst=inst, mfields=mfields,
            pfields=pfields, include_rests=include_rests
        )

    @property
    def is_rest(self):
        return self._owner._rt[self.id].get('proportion', 1) < 0

    @property
    def pfields(self):
        return {
            key: self._owner.get_pfield(self.id, key)
            for key in self._owner._rt.pfield_names
        }

    @property
    def mfields(self):
        return {
            key: self._owner.get_mfield(self.id, key)
            for key in self._owner._rt.mfield_names
        }

    @property
    def instrument(self):
        return self._owner.get_instrument(self.id)

    def get_pfield(self, key: str, default=None):
        return self._owner.get_pfield(self.id, key, default)

    def get_mfield(self, key: str, default=None):
        return self._owner.get_mfield(self.id, key, default)

    def get_instrument(self):
        return self._owner.get_instrument(self.id)


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

    Attributes
    ----------
    pt : ParameterTree
        The synchronized parameter tree matching RhythmTree structure (returns copy)
    pfields : list
        List of all available parameter field names
    """

    _node_selector_class = UCNodeSelector
    _node_handle_class = UCNodeHandle
    _tree_class = CompositionalTree

    def __init__(self,
                 span     : Union[int, float, Fraction]            = 1,
                 tempus   : Union[Meas, Fraction, int, float, str] = '4/4',
                 prolatio : Union[tuple, str]                      = 'd',
                 beat     : Union[None, Fraction, int, float, str] = None,
                 bpm      : Union[None, int, float]                = None,
                 inst     : Union[Instrument, None]                = None,
                 mfields  : Union[dict, list, None]                = None,
                 pfields  : Union[dict, list, None]                = None):
        
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
        """Copy raw parameter-layer state from a same-topology source UC.

        Preserves per-node override placement (inheritance structure), the
        pfield/mfield registries, and instrument bindings. Node ids must match
        between the two trees (guaranteed when both are built from the same
        prolatio).
        """
        src = source_uc._rt
        dst = self._rt
        dst.register_pfields(src.pfield_names)
        dst.register_mfields(src.mfield_names)
        keys = src.pfield_names | src.mfield_names
        for node in src.nodes:
            raw = src._rx[node]
            if isinstance(raw, dict):
                own = {k: v for k, v in raw.items() if k in keys}
                if node in dst and own:
                    dst._rx[node].update(own)
        for node, inst in src.node_instruments.items():
            if node in dst:
                dst.set_instrument(node, inst)
        dst._param_layer._effective_cache = None

    def _resolve_governing_instrument_node(self, node: int):
        return self._rt._resolve_governing_instrument_node(node)

    def _resolve_distribution_fields(self, node_id: int):
        inst = self._rt.get_instrument(node_id)
        effective = _resolve_kit_member(inst, self._rt, node_id) if inst is not None else inst
        inst_pfields = effective.pfields if (effective is not None and hasattr(effective, "pfields")) else {}
        pfields = {}
        for key in self._rt.pfield_names:
            value = self._rt.get_pfield(node_id, key)
            if value is None and key in inst_pfields:
                value = inst_pfields[key]
            pfields[key] = value
        mfields = {key: self._rt.get_mfield(node_id, key) for key in self._rt.mfield_names}
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

    def _build_effective_parameter_tree(self):
        pt_snapshot = self._extract_parameter_tree()
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

    def _make_node_proxy(self, node_id: int):
        self._ensure_timing_cache()
        return Parametron(node_id, self, self._rt)

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
        if hasattr(inst, 'tonejs_class'):
            return inst.tonejs_class
        if hasattr(inst, 'prgm'):
            return inst.prgm
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

        return pd.DataFrame(data, index=range(len(rows)))
    
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
        """
        targets = self._coerce_node_targets(node)

        distributable_fields = {k: v for k, v in kwargs.items()
                               if callable(v) or isinstance(v, Pattern)}
        static_fields = {k: v for k, v in kwargs.items()
                        if k not in distributable_fields}

        for n in targets:
            if static_fields:
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
        """
        targets = self._coerce_node_targets(node)

        distributable_fields = {k: v for k, v in kwargs.items()
                               if callable(v) or isinstance(v, Pattern)}
        static_fields = {k: v for k, v in kwargs.items()
                        if k not in distributable_fields}

        for n in targets:
            if static_fields:
                self._rt.set_mfields(n, **static_fields)

        if distributable_fields:
            self._distribute_to_targets(targets, distributable_fields, include_rests, setter='mfields')

    def _bake_envelope(self, selected, envelope, pfields_list, endpoint):
        self._ensure_timing_cache()
        sounding = [n for n in selected if self.nodes[n].get('proportion', 1) >= 0]
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
        start_time = min(self.nodes[n]['real_onset'] for n in sounding)
        if endpoint:
            end_time = max(self.nodes[n]['real_onset'] + abs(self.nodes[n]['real_duration']) for n in sounding)
        else:
            end_time = max(self.nodes[n]['real_onset'] for n in sounding)
        duration = end_time - start_time
        raw_total = sum(envelope.times)
        scaled_envelope = Envelope(
            values=envelope.values,
            times=envelope.times,
            curve=envelope._curve,
            time_scale=duration / raw_total if raw_total > 0 else 1.0
        )
        for node in sounding:
            event_time = self.nodes[node]['real_onset']
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
        start = min(self.nodes[n]['real_onset'] for n in sounding)
        if desc["endpoint"]:
            end = max(self.nodes[n]['real_onset'] + abs(self.nodes[n]['real_duration']) for n in sounding)
        else:
            end = max(self.nodes[n]['real_onset'] for n in sounding)
        return (start, end)

    def _check_envelope_overlap(self, new_pfields, new_leaves):
        new_pf_set = set(new_pfields)
        new_leaf_set = set(new_leaves)
        for desc in self._control_envelopes.values():
            shared_pf = new_pf_set.intersection(desc["pfields"])
            if not shared_pf:
                continue
            existing_leaves = set(self._resolve_control_envelope_leaves(desc))
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
        parent_data = self._rt.items(node)
        pfields = {k: v for k, v in parent_data.items() if k in self._rt.pfield_names}
        mfields = {k: v for k, v in parent_data.items() if k in self._rt.mfield_names}

        self._rt.subdivide(node, S)
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

    def add_child(self, parent, **attr):
        if 'label' in attr and 'proportion' not in attr:
            attr = dict(attr)
            attr['proportion'] = attr.pop('label')
        new_rt_node = self._rt.add_child(parent, **attr)
        return new_rt_node

    def prune(self, node):
        removed_set = {node}
        self._invalidate_slurs_for_removed_nodes(removed_set)
        self._invalidate_envelopes_for_removed_nodes(removed_set)
        self._rt.prune(node)

    def remove_subtree(self, node):
        removed_set = {node} | set(self._rt.descendants(node))
        self._invalidate_slurs_for_removed_nodes(removed_set)
        self._invalidate_envelopes_for_removed_nodes(removed_set)
        self._rt.remove_subtree(node)

    def set_instrument(self, node, instrument) -> None:
        """
        Set an instrument for target node(s).
        
        Parameters
        ----------
        node : int or list/tuple of int
            Target node(s). Single node: instrument set on that node, inherits
            to descendants. List of nodes: instrument evaluated once per node.
        instrument : Instrument, str, int, Pattern, or callable
            - Instrument: set directly on node with pfield defaults.
              If the instrument carries an ``_ensemble_family`` tag (i.e. it
              was accessed through an Ensemble family view), the ``group``
              mfield is automatically set to the family name.
            - str: raw synth reference (defName for SC, tonejs_class for Tone.js)
            - int: raw program number (MIDI)
            - Pattern: next() called once per target node
            - Callable: evaluated once per target node (0-arg or 1-arg with DistributionContext)
        """
        targets = self._coerce_node_targets(node)

        if isinstance(instrument, (str, int)):
            for n in targets:
                self._rt.set_instrument(n, instrument)
        elif isinstance(instrument, (Instrument, Effect)):
            family = getattr(instrument, '_ensemble_family', None)
            for n in targets:
                self._rt.set_instrument(n, instrument)
                if family is not None:
                    self._rt.set_mfields(n, group=family)
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
                    self._rt.set_instrument(n, inst)
                    family = getattr(inst, '_ensemble_family', None)
                    if family is not None:
                        self._rt.set_mfields(n, group=family)

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
        value = self._rt.get_pfield(node, key)
        return default if value is None else value

    def get_mfield(self, node: int, key: str, default=None):
        """Meta field value for node."""
        value = self._rt.get_mfield(node, key)
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
        old_to_new_mapping = self._rt.map_parallel_nodes(
            new_cu._rt,
            self_root=node,
            other_root=new_cu._rt.root,
        )

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

        Returns
        -------
        CompositionalUnit
            A new CompositionalUnit with identical structure, parameters,
            instruments, envelopes, and slurs.
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

        c._offset = self._offset
        c._invalidate_timing_cache()
        return c
