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
from tabulate import tabulate

from klotho.topos.graphs import Tree
from klotho.utils.algorithms.groups import print_subdivisions
from klotho.utils.data_structures import Group
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
        
        super().__init__(Meas(meas).numerator * span, subdivisions)
        
        self._meta['span'] = span
        self._meta['meas'] = str(Meas(meas))
        self._meta['type'] = None
        self._list = Group((Meas(meas).numerator * span, self._cast_subdivs(subdivisions)))
        
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
        return self._list.S

    def _cast_subdivs(self, children):
        def convert_to_tuple(item):
            if isinstance(item, RhythmTree):
                return (item.meas.numerator * item.span, item.subdivisions)
            if isinstance(item, tuple):
                return tuple(convert_to_tuple(x) for x in item)
            return item
        
        return tuple(convert_to_tuple(child) for child in children)

    def _build_subdivisions(self, root_node=None):
        """Build subdivisions structure from the current graph state.
        
        Parameters
        ----------
        root_node : int, optional
            The node to start building from (default: self.root)
            
        Returns
        -------
        tuple
            Nested tuple structure representing subdivisions
        """
        if root_node is None:
            root_node = self.root
        
        def get_node_value(node):
            return self[node].get('proportion', self[node].get('label', 1))
        
        def get_children(node):
            return list(self.successors(node))
        
        return self._build_nested_structure(root_node, get_node_value, get_children)
    
    def _update_group_structure(self):
        """Update the Group structure, preserving D and updating S."""
        if hasattr(self, '_list'):
            new_subdivisions = self._build_subdivisions()
            if isinstance(new_subdivisions, tuple) and len(new_subdivisions) > 1:
                new_s = new_subdivisions[1]
            else:
                new_s = (1,)
            self._list = Group((self._list.D, new_s))
    
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
            f"Subdivs: {print_subdivisions(self.subdivisions)}",
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
    
    def _evaluate(self):
        """
        Evaluate the rhythm tree to compute metric durations and onsets.
        
        This method processes the tree in two phases:
        1. Computation of metric durations and proportions for all nodes
        2. Computation of metric onsets based on durations
        """
        self[self.root]['metric_duration'] = self.meas * self.span
        
        def _process_child_durations(child, div, parent_ratio, parent_is_negative=False):
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
            parent_is_negative : bool, optional
                Whether the parent node has a negative proportion.
            """
            child_data = self[child]
            
            s = child_data['label']
            if 'meta' in child_data:
                s = s * child_data['meta']['span']
            s = int(s) if isinstance(s, float) else s
            
            if parent_is_negative and s > 0:
                s = -s
            
            ratio = Fraction(s, div) * parent_ratio
            if s < 0:
                ratio = -abs(ratio)
            self[child]['metric_duration'] = ratio
            self[child]['proportion'] = s
            if self.out_degree(child) > 0:
                _process_subtree(child, ratio)
            self[child].pop('label', None)
        
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
            node_data = self[node]
            
            if 'meta' in node_data:
                node_data['label'] = node_data['label'] * node_data['meta']['span']
            
            label = node_data['label']
            is_tied = isinstance(label, float)
            self[node]['tied'] = is_tied
            label_value = int(label) if is_tied else label
            
            self[node]['proportion'] = label_value
            children = list(self.successors(node))
            
            if not children:
                ratio = Fraction(label_value) * parent_ratio
                self[node]['metric_duration'] = ratio
                self[node].pop('label', None)
                return
            
            div = int(sum(abs(self[c]['label'] * 
                             self[c]['meta']['span'] if 'meta' in self[c]
                             else self[c]['label']) 
                         for c in children))
            
            node_is_negative = label_value < 0
                        
            for child in children:
                _process_child_durations(child, div, parent_ratio, node_is_negative)
            
            self[node].pop('label', None)
        
        _process_subtree()
        
        leaf_durations = [self[n]['metric_duration'] for n in self.leaf_nodes]
        leaf_onsets = calc_onsets(leaf_durations)
        
        for n, o in zip(self.leaf_nodes, leaf_onsets):
            self[n]['metric_onset'] = o
        
        for node in reversed(list(self.topological_sort())):
            if self.out_degree(node) > 0:
                children = list(self.successors(node))
                leftmost_child = children[0]
                self[node]['metric_onset'] = self[leftmost_child]['metric_onset']

    def _set_type(self):
        div = sum_proportions(self.subdivisions)
        if bin(div).count('1') != 1 and div != self.meas.numerator:
            return 'complex'
        return 'complex' if measure_complexity(self.subdivisions) else 'simple'

    def __len__(self):
        return len(self.durations)

    def __str__(self):
        return f"RhythmTree(span={self.span}, meas={self.meas}, subdivisions={print_subdivisions(self.subdivisions)})"

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
            A new RhythmTree representing the subtree
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
        
        new_rt = RhythmTree(span=1, meas=meas, subdivisions=subdivisions)
        
        if renumber:
            new_rt.renumber_nodes()
        
        return new_rt
    
    def graft_subtree(self, target_node, subtree, mode='replace'):
        """Graft a subtree and re-evaluate the rhythm tree."""
        result = super().graft_subtree(target_node, subtree, mode)
        
        for node in self.nodes:
            node_data = self[node]
            if 'label' not in node_data:
                node_data['label'] = node_data.get('proportion', 1)
        
        self._evaluate()
        return result

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
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
        
        descendants_to_modify = [node] + list(self.descendants(node))
        
        for n in descendants_to_modify:
            node_data = self[n]
            if 'proportion' in node_data and node_data['proportion'] > 0:
                node_data['proportion'] = -abs(node_data['proportion'])
                node_data['metric_duration'] = -abs(node_data['metric_duration'])
        
        self._update_group_structure()
