from typing import Union, Optional, Any
from fractions import Fraction
import pandas as pd

from klotho.chronos import TemporalUnit, RhythmTree, Meas
from klotho.chronos.temporal_units.temporal import Chronon
from klotho.thetos.parameters import ParameterTree
from klotho.thetos.instruments import Instrument


class Event(Chronon):
    """
    An enhanced Chronon that includes parameter field access.
    
    Extends the basic temporal event data (start, duration, etc.) with 
    access to musical parameters stored in a synchronized ParameterTree.
    """
    
    __slots__ = ('_pt',)
    
    def __init__(self, node_id: int, rt: RhythmTree, pt: ParameterTree):
        super().__init__(node_id, rt)
        self._pt = pt
    
    @property
    def parameters(self):
        """
        Get all active parameter fields for this event.
        
        Returns
        -------
        dict
            Dictionary of active parameter field names and values
        """
        return self._pt[self._node_id].active_items()
    
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
        return self._pt.get(self._node_id, key) or default
    
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
        temporal_attrs = {'start', 'duration', 'end', 'proportion', 'metric_ratio', 'node_id', 'is_rest'}
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
                 pfields  : Union[dict, list, None]                = None):
        
        # Initialize TemporalUnit components without calling _set_nodes yet
        self._type = None
        self._rt = self._set_rt(span, abs(Meas(tempus)), prolatio)
        self._beat = Fraction(beat) if beat else Fraction(1, self._rt.meas._denominator)
        self._bpm = bpm if bpm else 60
        self._offset = offset
        
        # Create parameter tree before setting nodes
        self._pt = self._create_synchronized_parameter_tree(pfields)
        
        # Now set the events (which creates Event objects needing both _rt and _pt)
        self._events = self._set_nodes()
    
    def _create_synchronized_parameter_tree(self, pfields: Union[dict, list, None]) -> ParameterTree:
        """
        Create a ParameterTree with identical structure to the RhythmTree but blank node data.
        
        Parameters
        ----------
        pfields : Union[dict, list, None]
            Parameter fields to initialize
            
        Returns
        -------
        ParameterTree
            A parameter tree matching the rhythm tree structure with clean nodes
        """
        pt = ParameterTree(self._rt.meas.numerator, self._rt._subdivisions)
        
        # Clear all node attributes to ensure PT contains no RT data
        for node in pt.graph.nodes():
            # Keep only essential Tree attributes, clear everything else
            node_data = pt.graph.nodes[node]
            label = node_data.get('label')  # Preserve the structural label
            node_data.clear()
            if label is not None:
                node_data['label'] = label
        
        if pfields is not None:
            self._initialize_parameter_fields(pt, pfields)
        
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
    
    def _set_nodes(self):
        """
        Updates node timings and returns Event objects instead of Chronon objects.
        
        Returns
        -------
        tuple of Event
            Events containing both temporal and parameter data
        """
        super()._set_nodes()
        leaf_nodes = self._rt.leaf_nodes
        return tuple(Event(node_id, self._rt, self._pt) for node_id in leaf_nodes)
    
    @property
    def pt(self) -> ParameterTree:
        """
        The ParameterTree of the CompositionalUnit (returns a copy).
        
        Returns
        -------
        ParameterTree
            A copy of the parameter tree maintaining structural synchronization with RhythmTree
        """
        return self._pt.copy()
    
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
    def events(self):
        """
        Enhanced events DataFrame including both temporal and parameter data.
        
        Returns
        -------
        pandas.DataFrame
            DataFrame with temporal properties and all parameter fields
        """
        base_data = []
        for event in self._events:
            event_dict = {
                'node_id': event.node_id,
                'start': event.start,
                'duration': event.duration,
                'end': event.end,
                'is_rest': event.is_rest,
                's': event.proportion,
                'metric_ratio': event.metric_ratio,
            }
            event_dict.update(event.parameters)
            base_data.append(event_dict)
        
        return pd.DataFrame(base_data, index=range(len(self._events)))
    
    def set_pfields(self, node: int, **kwargs) -> None:
        """
        Set parameter field values for a specific node and its descendants.
        
        Parameters
        ----------
        node : int
            The node ID to set parameters for
        **kwargs
            Parameter field names and values to set
        """
        self._pt.set_pfields(node, **kwargs)
    
    def set_instrument(self, node: int, instrument: Instrument, exclude: Union[str, list, set, None] = None) -> None:
        """
        Set an instrument for a specific node, applying its parameter fields.
        
        Parameters
        ----------
        node : int
            The node ID to set the instrument for
        instrument : Instrument
            The instrument to apply
        exclude : Union[str, list, set, None], optional
            Parameter fields to exclude from application
        """
        self._pt.set_instrument(node, instrument, exclude)
    
    def get_parameter(self, node: int, key: str, default=None):
        """
        Get a parameter value for a specific node.
        
        Parameters
        ----------
        node : int
            The node ID to query
        key : str
            The parameter field name
        default : Any, optional
            Default value if parameter not found
            
        Returns
        -------
        Any
            The parameter value or default
        """
        return self._pt.get(node, key) or default
    
    def clear_parameters(self, node: int = None) -> None:
        """
        Clear parameter values for a node and its descendants.
        
        Parameters
        ----------
        node : int, optional
            The node ID to clear. If None, clears all nodes
        """
        self._pt.clear(node)
    
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
        return self._events[idx].parameters
    
    def copy(self):
        """
        Create a deep copy of this CompositionalUnit.
        
        Returns
        -------
        CompositionalUnit
            A new CompositionalUnit with copied structure and parameters
        """
        new_cu = CompositionalUnit(
            span=self.span,
            tempus=self.tempus,
            prolatio=self.prolationis,
            beat=self._beat,
            bpm=self._bpm,
            offset=self._offset
        )
        
        for node in self._pt.graph.nodes():
            node_params = self._pt.items(node)
            if node_params:
                new_cu.set_pfields(node, **node_params)
        
        return new_cu