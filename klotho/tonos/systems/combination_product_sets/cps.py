from typing import Union, Dict, Tuple
from math import prod
from fractions import Fraction
import sympy as sp
import math
from tabulate import tabulate

from klotho.topos.collections import CombinationSet as CS
from klotho.topos.graphs import Graph
from klotho.tonos.utils.interval_normalization import equave_reduce
from .master_sets import ALPHA_SYMBOLS, MASTER_SETS

__all__ = [
    'CombinationProductSet',
]

class CombinationProductSet(CS):
  '''
  General class for an arbitrary Combination Product Set (CPS).
  
  Base class for Hexany, Dekany, Pentadekany, and Eikosany class implementations.
  
  A combination product set (CPS) is a scale generated by the following means:
  
      1. A set S of n positive real numbers is the starting point.
      
      2. All the combinations of k elements of the set are obtained, and their 
          products taken.
          
      3. These are combined into a set, and then all of the elements of that set 
          are divided by one of them (which one is arbitrary; if a canonical choice 
          is required, the smallest element could be used).
          
      4. The resulting elements are octave-reduced and sorted in ascending order, 
          resulting in an octave period of a periodic scale (the usual sort of 
          scale, in other words) which we may call CPS(S, k).
  
  see: https://en.xen.wiki/w/Combination_product_set
  '''
  def __init__(self, factors: Tuple[int], r: int, normalized: bool = False, master_set: str = None):
    super().__init__(factors, r)
    self._normalized = normalized
    self._master_set = master_set.lower() if master_set else None
    self._populate_graph()
    if self._master_set and self._master_set in MASTER_SETS:
      self._build_master_set_structure(MASTER_SETS[self._master_set])
    
  def _populate_graph(self):
    """Populate graph nodes with combo, product, ratio, and alias information."""
    directed_graph = self._graph.to_directed()
    # for node, attrs in self._graph.nodes(data=True):
        # directed_graph[node].update(attrs)
    directed_graph._graph.clear_edges()
    self._graph = directed_graph
    
    for node, attrs in self._graph.nodes(data=True):
      if 'combo' in attrs:
        combo = attrs['combo']
        product = prod(combo)
        ratio = equave_reduce(product)
        
        if self._normalized:
          ratio = equave_reduce(ratio / max(self._factors))
        
        symbolic_expr = sp.Integer(1)
        for factor in combo:
          symbolic_expr *= self.factor_to_alias[factor]
        
        self._graph.nodes[node]['product'] = product
        self._graph.nodes[node]['ratio']   = ratio
        self._graph.nodes[node]['alias']   = symbolic_expr
  
  def _build_master_set_structure(self, relationship_dict):
    """
    Enhance the graph with edges based on relationships defined in the provided dictionary.
    
    Args:
        relationship_dict: Dictionary mapping symbolic relationships to values
    """
    if not relationship_dict:
      return
      
    combo_to_node = {}
    for node, attrs in self._graph.nodes(data=True):
      if 'combo' in attrs:
        combo_to_node[attrs['combo']] = node
    
    for c1 in self._combos:
      node1 = combo_to_node[c1]
      for c2 in self._combos:
        if c1 != c2:
          node2 = combo_to_node[c2]
          
          alias1 = self.get_attrs_by('combo', c1)['alias']
          alias2 = self.get_attrs_by('combo', c2)['alias']
          sym_ratio = sp.simplify(alias1 / alias2)
          
          if sym_ratio in relationship_dict:
            self._graph.add_edge(node1, node2, relation=sym_ratio)

  @property
  def master_set(self):
    return self._master_set
  
  @property
  def aliases(self):
    return self.factor_to_alias
    
  @property
  def products(self):
    return tuple(sorted(attrs['product'] for _, attrs in self._graph.nodes(data=True)))
  
  @property
  def ratios(self):
    return tuple(sorted(attrs['ratio'] for _, attrs in self._graph.nodes(data=True)))
  
  def get_node_by(self, attr_name, value):
    for node, attrs in self._graph.nodes(data=True):
      if attrs.get(attr_name) == value:
        return node
    return None
  
  def get_attrs_by(self, attr_name, value):
    for node, attrs in self._graph.nodes(data=True):
      if attrs.get(attr_name) == value:
        return attrs
    return None  
  
  def __str__(self):
    table_data = []
    node_data = [(attrs['combo'], attrs['product'], attrs['ratio']) for _, attrs in self._graph.nodes(data=True)]
    sorted_data = sorted(node_data, key=lambda x: x[2])
    for combo, product, ratio in sorted_data:
      table_data.append([combo, product, str(ratio)])
    return tabulate(table_data, headers=['Combo', 'Product', 'Ratio'], tablefmt='simple', colalign=('center', 'center', 'center'))
  
  def __repr__(self):
    return self.__str__()
