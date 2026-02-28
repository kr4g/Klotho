# ------------------------------------------------------------------------------------
# Klotho/klotho/chronos/rhythm_trees/rt.py
# ------------------------------------------------------------------------------------
"""
Rhythm trees.

A rhythm tree (RT) is a list representing a rhythmic structure. This list
is organized hierarchically in sub-lists, just as time is organized in
measures, time signatures, pulses and rhythmic elements in traditional
notation.

See: https://support.ircam.fr/docs/om/om6-manual/co/RT.html
"""
from fractions import Fraction
from typing import Union, Tuple
from tabulate import tabulate

from klotho.topos.graphs import Tree, Group, format_subdivisions
from .meas import Meas
from .algorithms import sum_proportions, measure_complexity, ratios_to_subdivs
from ..utils.beat import calc_onsets


class RhythmTree(Tree):
    _node_value_attr = 'proportion'
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
        """
        Parameters
        ----------
        span : int, optional
            The number of measures the tree spans. Default is 1.
        meas : Meas, Fraction, or str, optional
            The time signature. Default is ``'1/1'``.
        subdivisions : tuple, optional
            The proportional subdivisions of the measure. Elements may
            be integers or nested ``(D, S)`` tuples. Default is ``(1, 1)``.
        """
        casted = self._cast_subdivs(subdivisions)
        super().__init__(Meas(meas).numerator * span, casted)
        
        self._meta['span'] = span
        self._meta['meas'] = str(Meas(meas))
        self._meta['type'] = None
        self._list = Group((Meas(meas).numerator * span, casted))
        
        self._evaluate()

    @classmethod
    def from_tree(cls, tree:Tree, span:int = 1):
        """
        Construct a ``RhythmTree`` from an existing :class:`Tree`.

        Parameters
        ----------
        tree : Tree
            A tree whose root node has a ``'metric_duration'`` attribute.
        span : int, optional
            The number of measures. Default is 1.

        Returns
        -------
        RhythmTree
        """
        return cls(span = span, meas = Meas(tree[tree.root]['metric_duration']), subdivisions = tree.group.S)
    
    @classmethod
    def from_ratios(cls, ratios:Tuple[Fraction, float, str], span:int = 1):
        """
        Construct a ``RhythmTree`` from a flat sequence of fractional ratios.

        The ratios are converted to integer subdivisions and the time
        signature is inferred from the sum of absolute ratios.

        Parameters
        ----------
        ratios : tuple of Fraction, float, or str
            The proportional ratios for each leaf.
        span : int, optional
            The number of measures. Default is 1.

        Returns
        -------
        RhythmTree
        """
        ratios = tuple(Fraction(r) for r in ratios)
        S = ratios_to_subdivs(ratios)
        meas = Meas(sum(abs(r) for r in ratios))
        return cls(span = span, meas = meas, subdivisions = S)

    @property
    def span(self):
        """
        The number of measures this tree spans.

        Returns
        -------
        int
        """
        return self._meta['span']

    @property
    def meas(self):
        """
        The time signature of this tree.

        Returns
        -------
        Meas
        """
        return Meas(self._meta['meas'])

    @property
    def subdivisions(self):
        """
        The proportional subdivisions (S part) of this tree.

        Returns
        -------
        tuple
        """
        return self._list.S

    def _post_structure_clone(self):
        self._meta['span'] = 1
        self._meta['meas'] = '1/1'
        self._meta['type'] = None
        for node in self._graph.node_indices():
            self._graph[node] = {'proportion': 1}
        self._evaluate()
        subdivs = self._build_subdivisions()
        s = subdivs[1] if isinstance(subdivs, tuple) and len(subdivs) > 1 else (1,)
        self._list = Group((1, s))

    def _cast_subdivs(self, children):
        def convert_to_tuple(item):
            if isinstance(item, RhythmTree):
                return (item.meas.numerator * item.span, item.subdivisions)
            if isinstance(item, (tuple, list)):
                return tuple(convert_to_tuple(x) for x in item)
            return item
        
        return tuple(convert_to_tuple(child) for child in children)

    def _validate_s_form(self, s):
        """Validate S is in valid S-form. Each element is non-zero int or (D, S) tuple.
        S must have at least 2 elements (e.g. (1,) is invalid)."""
        if isinstance(s, int):
            if s == 0:
                raise ValueError(f"S element cannot be zero: {s}")
            return
        if isinstance(s, (tuple, list)):
            if len(s) < 2:
                raise ValueError(f"S must have at least 2 elements, got {s}")
            for elem in s:
                if isinstance(elem, int):
                    if elem == 0:
                        raise ValueError(f"S element cannot be zero: {elem}")
                elif isinstance(elem, (tuple, list)):
                    if len(elem) != 2:
                        raise ValueError(f"(D S) must have exactly 2 elements, got {len(elem)}: {elem}")
                    d, sub = elem
                    if not isinstance(d, int) or d == 0:
                        raise ValueError(f"(D S): D must be non-zero integer, got D={d}")
                    self._validate_s_form(sub)
                else:
                    raise ValueError(f"S element must be non-zero int or (D S) tuple, got {type(elem).__name__}: {elem}")
            return
        raise ValueError(f"S must be tuple or int, got {type(s).__name__}: {s}")

    def _normalize_s_for_subdivide(self, S):
        """Normalize S for subdivide: int -> (1,)*S; tuple -> validate and return.
        S must represent at least 2 subdivisions (e.g. S>1 for int, len(S)>=2 for tuple)."""
        if isinstance(S, int):
            if S <= 1:
                raise ValueError(f"S must be > 1 when int, got {S}")
            return (1,) * S
        if isinstance(S, (tuple, list)):
            self._validate_s_form(S)
            return tuple(S)
        raise ValueError(f"S must be tuple or int, got {type(S).__name__}: {S}")

    def _build_subdivisions(self, root_node=None):
        """
        Build a subdivisions structure from the current graph state.

        Parameters
        ----------
        root_node : int, optional
            The node to start building from. Default is ``self.root``.

        Returns
        -------
        tuple
            Nested tuple structure representing subdivisions.
        """
        if root_node is None:
            root_node = self.root
        
        def get_node_value(node):
            return self[node].get('proportion', 1)
        
        def get_children(node):
            return list(self.successors(node))
        
        return self._build_nested_structure(root_node, get_node_value, get_children)
    
    def _update_group_structure(self):
        """Update the Group structure, preserving D and rebuilding S."""
        if hasattr(self, '_list'):
            new_subdivisions = self._build_subdivisions()
            if isinstance(new_subdivisions, tuple) and len(new_subdivisions) > 1:
                new_s = new_subdivisions[1]
            else:
                new_s = (1,)
            self._list = Group((self._list.D, new_s))

    def _post_mutation(self, scope_node=None, op=None):
        for node in self.nodes:
            node_data = self[node]
            if 'proportion' not in node_data:
                node_data['proportion'] = node_data.get('label', 1)
                node_data.pop('label', None)
        super()._post_mutation(scope_node=scope_node, op=op)
        self._evaluate(scope_node)
    
    @property
    def durations(self):
        """
        The metric durations of all leaf nodes.

        Returns
        -------
        tuple of Fraction
        """
        return tuple(self.nodes[n]['metric_duration'] for n in self.leaf_nodes)
    
    @property
    def onsets(self):
        """
        The metric onsets of all leaf nodes.

        Returns
        -------
        tuple of Fraction
        """
        return tuple(self.nodes[n]['metric_onset'] for n in self.leaf_nodes)
    
    @property
    def info(self):
        """
        A formatted string summarizing the tree's metadata, subdivisions,
        durations, and onsets.

        Returns
        -------
        str
        """
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
            f"Subdivs: {format_subdivisions(self.subdivisions)}",
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
    
    def _evaluate(self, root_node=None):
        """
        Evaluate the tree to compute metric durations and onsets.

        Single-pass DFS: computes durations and onsets together in one traversal.
        When root_node is provided, evaluates from that subtree (ancestors must
        already have metric_duration). When None, evaluates from root.

        Parameters
        ----------
        root_node : int, optional
            Subtree root to evaluate from. If None, evaluates from tree root.
        """
        if root_node is None:
            root_node = self.root
        self[self.root]['metric_duration'] = self.meas * self.span
        parent_ratio = self.span * self.meas.to_fraction() if root_node == self.root else Fraction(self[root_node]['metric_duration'])

        leaf_onset_acc = [Fraction(0)]

        def _process_child(child, div, parent_ratio, parent_is_negative):
            child_data = self[child]
            s = child_data.get('proportion', 1)
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
            else:
                self[child]['metric_onset'] = leaf_onset_acc[0]
                leaf_onset_acc[0] += abs(ratio)

        def _process_subtree(node, parent_ratio):
            node_data = self[node]
            if 'meta' in node_data:
                node_data['proportion'] = node_data.get('proportion', 1) * node_data['meta']['span']
            label = node_data.get('proportion', 1)
            is_tied = isinstance(label, float)
            self[node]['tied'] = is_tied
            label_value = int(label) if is_tied else label
            self[node]['proportion'] = label_value
            children = list(self.successors(node))
            if not children:
                ratio = Fraction(label_value) * parent_ratio
                self[node]['metric_duration'] = ratio
                self[node]['metric_onset'] = leaf_onset_acc[0]
                leaf_onset_acc[0] += abs(ratio)
                return
            div = int(sum(
                abs(self[c].get('proportion', 1)) *
                (self[c]['meta']['span'] if 'meta' in self[c] else 1)
                for c in children
            ))
            node_is_negative = label_value < 0
            for child in children:
                _process_child(child, div, parent_ratio, node_is_negative)
            self[node]['metric_onset'] = self[children[0]]['metric_onset']

        if root_node != self.root:
            for n in self.leaf_nodes:
                if n in self.subtree_leaves(root_node):
                    break
                leaf_onset_acc[0] += abs(Fraction(self[n]['metric_duration']))

        _process_subtree(root_node, parent_ratio)

        if root_node != self.root:
            leaves_after = [n for n in self.leaf_nodes if list(self.leaf_nodes).index(n) > max(list(self.leaf_nodes).index(l) for l in self.subtree_leaves(root_node))]
            for n in leaves_after:
                self[n]['metric_onset'] = leaf_onset_acc[0]
                leaf_onset_acc[0] += abs(Fraction(self[n]['metric_duration']))
            for node in reversed(list(self.topological_sort())):
                if self.out_degree(node) > 0 and node != root_node:
                    if node not in self.descendants(root_node):
                        children = list(self.successors(node))
                        self[node]['metric_onset'] = self[children[0]]['metric_onset']
        else:
            for node in reversed(list(self.topological_sort())):
                if self.out_degree(node) > 0:
                    children = list(self.successors(node))
                    self[node]['metric_onset'] = self[children[0]]['metric_onset']

    def _set_type(self):
        div = sum_proportions(self.subdivisions)
        if bin(div).count('1') != 1 and div != self.meas.numerator:
            return 'complex'
        return 'complex' if measure_complexity(self.subdivisions) else 'simple'

    def __len__(self):
        return len(self.durations)

    def __str__(self):
        return f"RhythmTree(span={self.span}, meas={self.meas}, subdivisions={format_subdivisions(self.subdivisions)})"

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
        """
        Graft a subtree onto the tree and re-evaluate metric values.

        Parameters
        ----------
        target_node : int
            The node at which to graft.
        subtree : RhythmTree or Tree
            The subtree to graft.
        mode : str, optional
            Grafting mode (``'replace'`` or ``'append'``). Default is
            ``'replace'``.

        Returns
        -------
        RhythmTree
            The modified tree (self).
        """
        return super().graft_subtree(target_node, subtree, mode)

    def subdivide(self, node, S):
        """
        Subdivide leaf node(s) with structure S.

        Each leaf becomes a parent with children defined by S. The node's
        proportion D is used as the duration; S specifies the subdivisions.

        Parameters
        ----------
        node : int or list of int
            The leaf node(s) to subdivide. Must have no children.
            If a list, subdivide is applied to each.
        S : tuple or int
            Subdivisions. If int, interpreted as ``(1,)*S`` (e.g. ``S=3`` → ``(1, 1, 1)``).
            If tuple, must be valid S-form: each element is a non-zero integer
            or a ``(D, S)`` pair.

        Returns
        -------
        RhythmTree
            self (for chaining)

        Raises
        ------
        ValueError
            If node is not found, is not a leaf, or S is invalid.
        """
        nodes = [node] if isinstance(node, int) else list(node)
        for n in nodes:
            if n not in self:
                raise ValueError(f"Node {n} not found in tree")
            if self.out_degree(n) != 0:
                raise ValueError(f"Node {n} must be a leaf")

        S = self._normalize_s_for_subdivide(S)
        S = self._cast_subdivs(S)

        def add_children(parent, children):
            for child in children:
                if isinstance(child, tuple) and len(child) == 2:
                    D, sub = child
                    child_id = self.add_child(parent, proportion=D)
                    add_children(child_id, sub)
                else:
                    self.add_child(parent, proportion=child)

        for n in nodes:
            add_children(n, S)
        scope = self.parent(nodes[0]) if len(nodes) == 1 else None
        self._post_mutation(scope_node=scope, op='subdivide')
        return self

    def prune(self, node):
        super().prune(node)
        return self

    def remove_subtree(self, node):
        super().remove_subtree(node)
        return self

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
