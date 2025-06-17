from typing import Union, Optional
from fractions import Fraction

from klotho.chronos import TemporalUnit, RhythmTree, Meas
from klotho.thetos.parameters import ParameterTree
from klotho.thetos.instruments import Instrument


class CompositionalUnit(TemporalUnit):
    """
    A TemporalUnit that maintains synchronized ParameterTrees for each parameter field.
    
    This class extends TemporalUnit to include parameter management capabilities,
    allowing for complex parameter automation synchronized with the temporal structure.
    """
    
    def __init__(self,
                 span: Union[int, float, Fraction] = 1,
                 tempus: Union[Meas, Fraction, int, float, str] = '4/4',
                 prolatio: Union[tuple, str] = 'd',
                 beat: Union[None, Fraction, int, float, str] = None,
                 bpm: Union[None, int, float] = None,
                 offset: float = 0,
                 auto_sync: bool = True,
                 pfields: Union[dict, list, None] = None):
        """
        Initialize a CompositionalUnit.
        
        Args:
            span: Number of measures the unit spans
            tempus: Time signature (e.g., '4/4', Meas(4,4))
            prolatio: Subdivision pattern (tuple) or type ('d', 'r', 'p', 's')
            beat: Beat unit for tempo (e.g., Fraction(1,4) for quarter note)
            bpm: Beats per minute
            offset: Start time offset in seconds
            auto_sync: Whether to automatically sync ParameterTree when RhythmTree changes
            pfields: Parameter fields to initialize. Can be:
                    - dict: {field_name: default_value, ...}
                    - list: [field_name1, field_name2, ...] (defaults to 0.0)
                    - None: No parameter fields initially
        """
        # Initialize the base TemporalUnit
        super().__init__(span, tempus, prolatio, beat, bpm, offset)
        
        # Initialize parameter management
        self._auto_sync = auto_sync
        self._parameter_trees = {}
        self._default_values = {}
        
        # Initialize parameter fields
        if pfields is not None:
            if isinstance(pfields, dict):
                for field_name, default_value in pfields.items():
                    self.add_pfield(field_name, default_value)
            elif isinstance(pfields, list):
                for field_name in pfields:
                    self.add_pfield(field_name, 0.0)
            else:
                raise ValueError("pfields must be a dict, list, or None")
    
    @property
    def prolationis(self):        
        """The S-part of a RhythmTree which describes the subdivisions of the TemporalUnit."""
        return self._rt._subdivisions
    
    @prolationis.setter
    def prolationis(self, prolatio: Union[tuple, str]):
        self._rt = self._set_rt(self.span, self.tempus, prolatio)
        self._events = self._set_nodes()
        
        if self._auto_sync:
            self._synchronize_parameter_trees()
    
    def _synchronize_parameter_trees(self):
        """Synchronize all parameter trees with the current RhythmTree structure."""
        for field_name in self._parameter_trees:
            new_pt = self._create_shadow_parameter_tree()
            
            old_pt = self._parameter_trees[field_name]
            self._transfer_parameter_values(old_pt, new_pt)
            
            self._parameter_trees[field_name] = new_pt
    
    def _create_shadow_parameter_tree(self) -> ParameterTree:
        """Creates a ParameterTree that shadows the RhythmTree structure."""
        rt = self._rt
        pt = ParameterTree(rt._graph.nodes[rt.root]['label'], rt._list[1])
        return pt
    
    def _transfer_parameter_values(self, old_pt: ParameterTree, new_pt: ParameterTree):
        """Transfer parameter values from old tree to new tree where structure matches."""
        try:
            for leaf_node in new_pt.leaf_nodes:
                if leaf_node in old_pt.graph.nodes:
                    if 'value' in old_pt.graph.nodes[leaf_node]:
                        new_pt.graph.nodes[leaf_node]['value'] = old_pt.graph.nodes[leaf_node]['value']
        except:
            pass
    
    @property
    def auto_sync(self) -> bool:
        """Whether parameter trees are automatically synchronized with rhythm tree changes."""
        return self._auto_sync
    
    @auto_sync.setter
    def auto_sync(self, value: bool):
        """Set auto-sync behavior."""
        self._auto_sync = value
        if value:
            self._synchronize_parameter_trees()
    
    @property
    def pfields(self) -> tuple:
        """Return tuple of parameter field names."""
        return tuple(self._parameter_trees.keys())
    
    def add_pfield(self, field_name: str, default_value: float = 0.0) -> None:
        """
        Add a new parameter field with a synchronized ParameterTree.
        
        Args:
            field_name: Name of the parameter field
            default_value: Default value for all nodes in the parameter tree
        """
        if field_name in self._parameter_trees:
            raise ValueError(f"Parameter field '{field_name}' already exists")
        
        # Create a new parameter tree that shadows the rhythm tree
        pt = self._create_shadow_parameter_tree()
        
        # Set default values for all leaf nodes
        for leaf_node in pt.leaf_nodes:
            pt.graph.nodes[leaf_node]['value'] = default_value
        
        self._parameter_trees[field_name] = pt
        self._default_values[field_name] = default_value
    
    def remove_pfield(self, field_name: str) -> None:
        """
        Remove a parameter field and its associated ParameterTree.
        
        Args:
            field_name: Name of the parameter field to remove
        """
        if field_name not in self._parameter_trees:
            raise ValueError(f"Parameter field '{field_name}' does not exist")
        
        del self._parameter_trees[field_name]
        del self._default_values[field_name]
    
    def get_ptree(self, field_name: str) -> ParameterTree:
        """
        Get the ParameterTree for a specific field.
        
        Args:
            field_name: Name of the parameter field
            
        Returns:
            ParameterTree: The parameter tree for the specified field
        """
        if field_name not in self._parameter_trees:
            raise ValueError(f"Parameter field '{field_name}' does not exist")
        
        return self._parameter_trees[field_name]
    
    def set_pfield_values(self, field_name: str, values: Union[list, tuple, dict]) -> None:
        """
        Set parameter values for a specific field.
        
        Args:
            field_name: Name of the parameter field
            values: Values to set. Can be:
                   - list/tuple: Values for each leaf node in order
                   - dict: {node_id: value, ...}
        """
        if field_name not in self._parameter_trees:
            raise ValueError(f"Parameter field '{field_name}' does not exist")
        
        pt = self._parameter_trees[field_name]
        leaf_nodes = pt.leaf_nodes
        
        if isinstance(values, (list, tuple)):
            if len(values) != len(leaf_nodes):
                raise ValueError(f"Expected {len(leaf_nodes)} values, got {len(values)}")
            
            for node, value in zip(leaf_nodes, values):
                pt.graph.nodes[node]['value'] = value
                
        elif isinstance(values, dict):
            for node_id, value in values.items():
                if node_id not in pt.graph.nodes:
                    raise ValueError(f"Node {node_id} not found in parameter tree")
                pt.graph.nodes[node_id]['value'] = value
        else:
            raise ValueError("values must be a list, tuple, or dict")
    
    def get_pfield_values(self, field_name: str) -> list:
        """
        Get parameter values for a specific field.
        
        Args:
            field_name: Name of the parameter field
            
        Returns:
            list: Values for each leaf node in order
        """
        if field_name not in self._parameter_trees:
            raise ValueError(f"Parameter field '{field_name}' does not exist")
        
        pt = self._parameter_trees[field_name]
        return [pt.graph.nodes[node].get('value', self._default_values[field_name]) 
                for node in pt.leaf_nodes]
    
    def sync_now(self):
        """Manually trigger synchronization of ParameterTrees with RhythmTree."""
        self._synchronize_parameter_trees()
    
    # === ENHANCED STRING REPRESENTATION ===
    
    def __str__(self):
        # Get the base TemporalUnit string representation
        temporal_str = super().__str__()
        
        # Add parameter information
        param_info = f'PFields:  {len(self.pfields)} ({", ".join(self.pfields) if self.pfields else "none"})\n'
        
        # Insert parameter info before the final separator
        lines = temporal_str.split('\n')
        # Find the last separator line and insert parameter info before it
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith('-'):
                lines.insert(i, param_info.rstrip())
                break
        
        # Update the header to indicate this is a CompositionalUnit
        for i, line in enumerate(lines):
            if 'Span:' in line:
                lines.insert(i, 'CompositionalUnit')
                lines.insert(i + 1, '-' * 50)
                break
        
        return '\n'.join(lines)
    
    def __repr__(self):
        return self.__str__()
    
    def copy(self):
        """Create a deep copy of this CompositionalUnit."""
        # Create base copy
        copy_unit = CompositionalUnit(
            span=self.span,
            tempus=self.tempus,
            prolatio=self.prolationis,
            beat=self._beat,
            bpm=self._bpm,
            offset=self._offset,
            auto_sync=self._auto_sync
        )
        
        # Copy parameter fields and their values
        for field_name in self.pfields:
            copy_unit.add_pfield(field_name, self._default_values[field_name])
            values = self.get_pfield_values(field_name)
            copy_unit.set_pfield_values(field_name, values)
        
        return copy_unit 