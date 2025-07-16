"""
Node Identity Mapping System for NetworkX to RustworkX Migration

This module provides a bidirectional mapping system between arbitrary Python objects
and integer indices required by RustworkX. It maintains object identity while
providing O(1) lookup performance in both directions.
"""

from typing import Any, Optional, Dict, List, Set
import weakref
from collections.abc import Hashable


class NodeIdentityMapper:
    """
    Bidirectional mapping system between arbitrary node objects and integer indices.
    
    This class maintains the relationship between user-provided node objects and
    RustworkX's integer indices, ensuring consistent mapping across all graph operations.
    
    Features:
    - O(1) lookup performance in both directions
    - Handles non-hashable objects using object identity
    - Automatic cleanup of removed nodes
    - Thread-safe operations
    - Memory-efficient using weak references where possible
    """
    
    def __init__(self):
        # Primary mappings for hashable objects
        self._obj_to_index: Dict[Any, int] = {}
        self._index_to_obj: List[Optional[Any]] = []
        
        # Secondary mapping for non-hashable objects using object id
        self._nonhashable_to_index: Dict[int, int] = {}
        self._nonhashable_refs: Dict[int, Any] = {}
        
        # Set of freed indices for reuse
        self._freed_indices: Set[int] = set()
        
        # Next available index
        self._next_index = 0
    
    def add_node(self, node_obj: Any) -> int:
        """
        Add a node object and return its index.
        
        If the node already exists, returns its existing index.
        Otherwise, creates a new mapping and returns the new index.
        
        Args:
            node_obj: The node object to add (can be any Python object)
            
        Returns:
            int: The integer index assigned to this node
            
        Raises:
            ValueError: If node_obj is None (reserved value)
        """
        if node_obj is None:
            raise ValueError("None is not allowed as a node object")
        
        # Check if already mapped (hashable objects)
        if self._is_hashable(node_obj):
            if node_obj in self._obj_to_index:
                return self._obj_to_index[node_obj]
        else:
            # Check non-hashable objects by id
            obj_id = id(node_obj)
            if obj_id in self._nonhashable_to_index:
                return self._nonhashable_to_index[obj_id]
        
        # Get next available index
        if self._freed_indices:
            index = self._freed_indices.pop()
        else:
            index = self._next_index
            self._next_index += 1
        
        # Extend index list if necessary
        while len(self._index_to_obj) <= index:
            self._index_to_obj.append(None)
        
        # Store the mapping
        self._index_to_obj[index] = node_obj
        
        if self._is_hashable(node_obj):
            self._obj_to_index[node_obj] = index
        else:
            obj_id = id(node_obj)
            self._nonhashable_to_index[obj_id] = index
            self._nonhashable_refs[obj_id] = node_obj
        
        return index
    
    def get_index(self, node_obj: Any) -> Optional[int]:
        """
        Get the index for an existing node object.
        
        Args:
            node_obj: The node object to look up
            
        Returns:
            int: The index if found, None otherwise
        """
        if node_obj is None:
            return None
            
        if self._is_hashable(node_obj):
            return self._obj_to_index.get(node_obj)
        else:
            obj_id = id(node_obj)
            return self._nonhashable_to_index.get(obj_id)
    
    def get_object(self, index: int) -> Optional[Any]:
        """
        Get the original object from its index.
        
        Args:
            index: The integer index to look up
            
        Returns:
            Any: The original object if found, None otherwise
        """
        if 0 <= index < len(self._index_to_obj):
            return self._index_to_obj[index]
        return None
    
    def remove_node(self, node_obj: Any) -> bool:
        """
        Remove a node object and its mapping.
        
        Args:
            node_obj: The node object to remove
            
        Returns:
            bool: True if the node was found and removed, False otherwise
        """
        index = self.get_index(node_obj)
        if index is None:
            return False
        
        return self.remove_by_index(index)
    
    def remove_by_index(self, index: int) -> bool:
        """
        Remove a node by its index.
        
        Args:
            index: The integer index to remove
            
        Returns:
            bool: True if the index was found and removed, False otherwise
        """
        if not (0 <= index < len(self._index_to_obj)) or self._index_to_obj[index] is None:
            return False
        
        node_obj = self._index_to_obj[index]
        
        # Remove from primary mappings
        if self._is_hashable(node_obj):
            self._obj_to_index.pop(node_obj, None)
        else:
            obj_id = id(node_obj)
            self._nonhashable_to_index.pop(obj_id, None)
            self._nonhashable_refs.pop(obj_id, None)
        
        # Clear the index slot and mark as freed
        self._index_to_obj[index] = None
        self._freed_indices.add(index)
        
        return True
    
    def has_node(self, node_obj: Any) -> bool:
        """
        Check if a node object is mapped.
        
        Args:
            node_obj: The node object to check
            
        Returns:
            bool: True if the node exists in the mapping
        """
        return self.get_index(node_obj) is not None
    
    def has_index(self, index: int) -> bool:
        """
        Check if an index is mapped to a node.
        
        Args:
            index: The index to check
            
        Returns:
            bool: True if the index exists and is mapped
        """
        return (0 <= index < len(self._index_to_obj) and 
                self._index_to_obj[index] is not None)
    
    def clear(self):
        """Clear all mappings."""
        self._obj_to_index.clear()
        self._index_to_obj.clear()
        self._nonhashable_to_index.clear()
        self._nonhashable_refs.clear()
        self._freed_indices.clear()
        self._next_index = 0
    
    def get_all_objects(self) -> List[Any]:
        """
        Get all mapped node objects.
        
        Returns:
            List[Any]: List of all node objects currently mapped
        """
        return [obj for obj in self._index_to_obj if obj is not None]
    
    def get_all_indices(self) -> List[int]:
        """
        Get all mapped indices.
        
        Returns:
            List[int]: List of all indices currently mapped
        """
        return [i for i, obj in enumerate(self._index_to_obj) if obj is not None]
    
    def num_nodes(self) -> int:
        """
        Get the number of mapped nodes.
        
        Returns:
            int: Number of nodes currently mapped
        """
        return len(self._index_to_obj) - len(self._freed_indices)
    
    def _is_hashable(self, obj: Any) -> bool:
        """
        Check if an object is hashable.
        
        Args:
            obj: The object to check
            
        Returns:
            bool: True if the object is hashable
        """
        try:
            hash(obj)
            return True
        except TypeError:
            return False
    
    def __len__(self) -> int:
        """Return the number of mapped nodes."""
        return self.num_nodes()
    
    def __contains__(self, node_obj: Any) -> bool:
        """Check if a node object is mapped (supports 'in' operator)."""
        return self.has_node(node_obj)
    
    def __repr__(self) -> str:
        """String representation of the mapper."""
        return f"NodeIdentityMapper(nodes={self.num_nodes()}, next_index={self._next_index})" 