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
                 meas:Union[Meas,Fraction,str] = '4/4',
                 subdivisions:Tuple            = (1,1)):
        
        super().__init__(Meas(meas).numerator, subdivisions)
        
        self._meta['span'] = span
        self._meta['meas'] = str(Meas(meas))
        self._meta['type'] = None
        self._subdivisions = self._cast_subdivs(subdivisions)
        
        self._ratios = self._evaluate()
    
    @classmethod
    def from_tree(cls, tree:Tree, span:int = 1):
        return cls(span = span, meas = Meas(tree[tree.root]['duration_ratio']), subdivisions = tree.group.S)
    
    @classmethod
    def from_ratios(cls, ratios:Tuple[Fraction, float, str], span:int = 1):
        ratios = tuple(Fraction(r) for r in ratios)
        S = ratios_to_subdivs(ratios)
        meas = Meas(sum(abs(r) for r in ratios))
        return cls(span = span, meas = meas, subdivisions = S)

    @property
    def span(self):
        return self._meta['span'].iloc[0]

    @property
    def meas(self):
        return Meas(self._meta['meas'].iloc[0])

    @property
    def subdivisions(self):
        return self._subdivisions

    @property
    def ratios(self):
        return self._ratios
    
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
        self.graph.nodes[self.root]['duration_ratio'] = self.meas
        def _process_subtree(node=0, parent_ratio=self.span * self.meas.to_fraction()):
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
                self.graph.nodes[node]['duration_ratio'] = ratio
                self.graph.nodes[node].pop('label', None)
                return
            
            div = int(sum(abs(self.graph.nodes[c]['label'] * 
                             self.graph.nodes[c]['meta']['span'] if 'meta' in self.graph.nodes[c]
                             else self.graph.nodes[c]['label']) 
                         for c in children))
            
            for child in children:
                child_data = self.graph.nodes[child]
                
                # if 'meta' in child_data:
                    # child_data['label'] = child_data['label'] * child_data['meta']['span']
                
                s = child_data['label']
                if 'meta' in child_data:
                    s = s * child_data['meta']['span']
                s = int(s) if isinstance(s, float) else s
                ratio = Fraction(s, div) * parent_ratio
                self.graph.nodes[child]['duration_ratio'] = ratio
                self.graph.nodes[child]['proportion'] = s
                if self.graph.out_degree(child) > 0:
                    _process_subtree(child, ratio)
                self.graph.nodes[child].pop('label', None)
            
            self.graph.nodes[node].pop('label', None)
        
        _process_subtree()
        onsets = calc_onsets([self.graph.nodes[n]['duration_ratio'] for n in self.leaf_nodes])
        for n, o in zip(self.leaf_nodes, onsets):
            onset = -o if self.graph.nodes[n]['duration_ratio'] < 0 else o
            self.graph.nodes[n]['onset_ratio'] = onset
        
        bfs_order = list(nx.bfs_tree(self.graph, self.root).nodes())
        non_leaf_nodes = [n for n, d in self.graph.out_degree() if d > 0]
        for node in non_leaf_nodes:
            current = node
            while self.graph.out_degree(current) > 0:
                children = list(self.graph.successors(current))
                current = min(children, key=lambda x: bfs_order.index(x))
            self.graph.nodes[node]['onset_ratio'] = self.graph.nodes[current]['onset_ratio']
        
        return tuple(self.graph.nodes[n]['duration_ratio'] for n in self.leaf_nodes)

    def _set_type(self):
        div = sum_proportions(self.subdivisions)
        if bin(div).count('1') != 1 and div != self.meas.numerator:
            return 'complex'
        return 'complex' if measure_complexity(self.subdivisions) else 'simple'

    def __len__(self):
        return len(self._ratios)

    def __str__(self):
        meta_dict = self._meta.iloc[0].to_dict()
        ordered_meta = {k: meta_dict[k] for k in ['span', 'meas', 'type']}
        ordered_meta['depth'] = self.depth
        ordered_meta['k'] = self.k
        meta_str = ' | '.join(f"{k}: {v}" for k, v in ordered_meta.items())
        
        content = [
            meta_str,
            f"Subdivs: {print_subdivisons(self.subdivisions)}",
            f"Ratios:  {', '.join(str(r) for r in self._ratios)}"
        ]
        
        width = max(len(line) for block in content 
                   for line in block.split('\n'))
        border = '-' * width
        
        return (
            f"{border}\n"
            f"{content[0]}\n"
            f"{border}\n"
            f"{content[1]}\n"
            f"{content[2]}\n"
            f"{border}\n"
        )

    def __repr__(self):
        return self.__str__()

    def copy(self):
        return RhythmTree(span=self.span, meas=self.meas, subdivisions=self.subdivisions)


