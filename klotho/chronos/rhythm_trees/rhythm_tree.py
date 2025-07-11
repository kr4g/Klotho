# ------------------------------------------------------------------------------------
# Klotho/klotho/chronos/rhythm_trees/rt.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
A rhythm tree (RT) is a list representing a rhythmic structure. This list is organized 
hierarchically in sub lists , just as time is organized in measures, time signatures, 
pulses and rhythmic elements in the traditional notation.

Hence, the expression form of rhythm trees is crucially different from that of onsets 
and offsets. It can be exacting and not very "ergonomic", from a musician's point of 
view : rhythm trees can be long, with a great number of parenthesis and sub lists 
nested within each others.

see: https://support.ircam.fr/docs/om/om6-manual/co/RT.html
--------------------------------------------------------------------------------------
'''
from fractions import Fraction
from typing import Union, Tuple
import networkx as nx
from tabulate import tabulate

from klotho.topos.graphs import Tree
from klotho.topos.graphs.trees.algorithms import print_subdivisons
from .meas import Meas
from .algorithms import sum_proportions, measure_complexity, ratios_to_subdivs
from ..utils.beat import calc_onsets


class RhythmTree(Tree):
    '''
    A rhythm tree is a list representing a rhythmic structure. This list is organized 
    hierarchically in sub lists, just as time is organized in measures, time signatures, 
    pulses and rhythmic elements in the traditional notation.

    Traditionally, rhythm is broken up into several data : meter, measure(s) and duration(s). 
    Rhythm trees must enclose these information in lists and sub list.

    This elementary rhythm:

    [1/4, 1/4, 1/4, 1/4] --> (four 1/4-notes in 4/4 time)

    can be expressed as follows :

    ( ? ( (4//4 (1 1 1 1) ) ) )

    A tree structure can be reduced to a list : (D (S)).


    >> Main Components : Duration and Subdivisions

    D = a duration , or number of measures : ( ? ) or a number ( n ).
    When D = ?, OM calculates the duration.
    By default, this duration is equal to 1.

    S = subdivisions (S) of this duration, that is a time signature and rhythmic proportions.
    Time signature = n // n   or ( n n ).
    It must be specified at each new measure, even if it remains unchanged.

    Rhythm = proportions : ( n n n n )

    see: https://support.ircam.fr/docs/om/om6-manual/co/RT1.html
    '''
    def __init__(self, 
                 span:int                      = 1,
                 meas:Union[Meas,Fraction,str] = '1/1',
                 subdivisions:Tuple            = (1,1)):
        
        super().__init__(Meas(meas).numerator, subdivisions)
        
        self._meta['span'] = span
        self._meta['meas'] = str(Meas(meas))
        self._meta['type'] = None
        self._subdivisions = self._cast_subdivs(subdivisions)
        
        self._evaluate()
    
    @classmethod
    def from_tree(cls, tree:Tree, span:int = 1):
        return cls(span = span, meas = Meas(tree[tree.root]['metric_duration']), subdivisions = tree.group.S)
    
    @classmethod
    def from_ratios(cls, ratios:Tuple[Fraction, float, str], span:int = 1):
        ratios = tuple(Fraction(r) for r in ratios)
        S = ratios_to_subdivs(ratios)
        meas = Meas(sum(abs(r) for r in ratios))
        return cls(span = span, meas = meas, subdivisions = S)

    @property
    def span(self):
        return self._meta['span']

    @property
    def meas(self):
        return Meas(self._meta['meas'])

    @property
    def subdivisions(self):
        return self._subdivisions

    @property
    def durations(self):
        return tuple(self.nodes[n]['metric_duration'] for n in self.leaf_nodes)
    
    @property
    def onsets(self):
        return tuple(self.nodes[n]['metric_onset'] for n in self.leaf_nodes)
    
    @property
    def info(self):
        ordered_meta = {k: self._meta[k] for k in ['span', 'meas', 'type']}
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
            f"Subdivs: {print_subdivisons(self.subdivisions)}",
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
    
    # @property
    # def type(self):
    #     if self._meta['type'] is None:
    #         self._meta['type'] = self._set_type()
    #     return self._meta['type']

    def subtree(self, node, renumber=True):
        tree_subtree = super().subtree(node, renumber)
        return self.__class__.from_tree(tree_subtree, 1)
    
    def _cast_subdivs(self, children):
        def convert_to_tuple(item):
            if isinstance(item, RhythmTree):
                return (item.meas.numerator * item.span, item.subdivisions)
            if isinstance(item, tuple):
                return tuple(convert_to_tuple(x) for x in item)
            return item
        
        return tuple(convert_to_tuple(child) for child in children)
    
    def _evaluate(self):
        """
        Evaluate the rhythm tree to compute metric durations and onsets.
        
        This method processes the tree in two phases:
        1. Computation of metric durations and proportions for all nodes
        2. Computation of metric onsets based on durations
        
        The evaluation uses optimized algorithms with our Graph/Tree caching.
        """
        self.graph.nodes[self.root]['metric_duration'] = self.meas
        
        def _process_child_durations(child, div, parent_ratio):
            """
            Process duration and proportion for a single child node.
            
            Parameters
            ----------
            child : int
                Child node ID to process.
            div : int
                Sum of all proportions at this level.
            parent_ratio : Fraction
                Parent node's metric duration ratio.
            """
            child_data = self.graph.nodes[child]
            
            s = child_data['label']
            if 'meta' in child_data:
                s = s * child_data['meta']['span']
            s = int(s) if isinstance(s, float) else s
            ratio = Fraction(s, div) * parent_ratio
            self.graph.nodes[child]['metric_duration'] = ratio
            self.graph.nodes[child]['proportion'] = s
            if self.graph.out_degree(child) > 0:
                _process_subtree(child, ratio)
            self.graph.nodes[child].pop('label', None)
        
        def _process_subtree(node=0, parent_ratio=self.span * self.meas.to_fraction()):
            """
            Process a subtree to compute metric durations and proportions.
            
            Parameters
            ----------
            node : int, optional
                Root node of subtree to process (default is 0).
            parent_ratio : Fraction, optional
                Parent node's metric duration ratio.
            """
            node_data = self.graph.nodes[node]
            
            if 'meta' in node_data:
                node_data['label'] = node_data['label'] * node_data['meta']['span']
            
            label = node_data['label']
            is_tied = isinstance(label, float)
            self.graph.nodes[node]['tied'] = is_tied
            label_value = int(label) if is_tied else label
            
            self.graph.nodes[node]['proportion'] = label_value
            children = list(self.graph.successors(node))
            
            if not children:
                ratio = Fraction(label_value) * parent_ratio
                self.graph.nodes[node]['metric_duration'] = ratio
                self.graph.nodes[node].pop('label', None)
                return
            
            div = int(sum(abs(self.graph.nodes[c]['label'] * 
                             self.graph.nodes[c]['meta']['span'] if 'meta' in self.graph.nodes[c]
                             else self.graph.nodes[c]['label']) 
                         for c in children))
            
            for child in children:
                _process_child_durations(child, div, parent_ratio)
            
            self.graph.nodes[node].pop('label', None)
        
        _process_subtree()
        
        leaf_durations = [self.graph.nodes[n]['metric_duration'] for n in self.leaf_nodes]
        leaf_onsets = calc_onsets(leaf_durations)
        
        for n, o in zip(self.leaf_nodes, leaf_onsets):
            self.graph.nodes[n]['metric_onset'] = o
        
        for node in reversed(list(nx.topological_sort(self.graph))):
            if self.graph.out_degree(node) > 0:
                children = list(self.graph.successors(node))
                leftmost_child = children[0]
                self.graph.nodes[node]['metric_onset'] = self.graph.nodes[leftmost_child]['metric_onset']

    def _set_type(self):
        div = sum_proportions(self.subdivisions)
        if bin(div).count('1') != 1 and div != self.meas.numerator:
            return 'complex'
        return 'complex' if measure_complexity(self.subdivisions) else 'simple'

    def __len__(self):
        return len(self.durations)

    def __str__(self):
        return f"RhythmTree(span={self.span}, meas={self.meas}, subdivisions={print_subdivisons(self.subdivisions)})"

    def __repr__(self):
        return self.__str__()
        




