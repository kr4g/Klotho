"""
Derivation (parse) trees for rewriting systems.

Where :class:`~klotho.topos.formal_grammars.rewriting.RewriteSystem` keeps
only the flat word of each generation, :func:`derive` records the full
expansion history as a :class:`DerivationTree` — every node remembers which
symbol it expanded from. The tree's shape can then become musical structure:
:meth:`DerivationTree.prolatio` turns it into rhythm-tree subdivision
notation, and :meth:`DerivationTree.to_tree` bridges it into a real
:class:`~klotho.topos.graphs.trees.Tree`.
"""

from .rules import RuleSet, _coerce_rng

__all__ = ['DerivationTree', 'derive']


class DerivationTree:
    """
    A node in a derivation tree.

    A lightweight recursive structure: each node has a ``symbol``, a list of
    ``children`` (empty for leaves), and an open ``data`` dict for arbitrary
    payloads (weights, chords, anything).

    Parameters
    ----------
    symbol : str
        The grammar symbol at this node.
    children : iterable of DerivationTree, optional
        Child nodes.
    **data
        Arbitrary payload entries stored in ``self.data``.
    """

    __slots__ = ('symbol', 'children', 'data')

    def __init__(self, symbol, children=None, **data):
        self.symbol = symbol
        self.children = list(children) if children is not None else []
        self.data = dict(data)

    @property
    def is_leaf(self):
        """bool : True when this node has no children."""
        return not self.children

    def walk(self):
        """Yield every node in the subtree, depth-first, left to right."""
        yield self
        for child in self.children:
            yield from child.walk()

    def leaves(self):
        """All leaf nodes, left to right."""
        if self.is_leaf:
            return [self]
        return [leaf for child in self.children for leaf in child.leaves()]

    def tokens(self):
        """Leaf symbols, left to right."""
        return [leaf.symbol for leaf in self.leaves()]

    def show(self, formatter=None):
        """Print the tree as ASCII art."""
        def _show(node, prefix, is_last):
            connector = '└─ ' if is_last else '├─ '
            text = formatter(node) if formatter is not None else str(node.symbol)
            print(prefix + connector + text)
            child_prefix = prefix + ('   ' if is_last else '│  ')
            for i, child in enumerate(node.children):
                _show(child, child_prefix, i == len(node.children) - 1)
        _show(self, '', True)

    def prolatio(self, head_weight=1):
        """
        Convert to rhythm-tree subdivision notation.

        Each node's children split its time-span. The rightmost child (the
        grammatical head) gets *head_weight*; all others get 1.

        Parameters
        ----------
        head_weight : int, optional
            Proportion assigned to each rightmost child. Default is 1.

        Returns
        -------
        tuple
            Nested proportion tuple in ``(w, (children...))`` notation.
            Empty for a leaf-only tree.
        """
        parts = []
        for i, child in enumerate(self.children):
            weight = head_weight if i == len(self.children) - 1 else 1
            parts.append(weight if child.is_leaf else (weight, child.prolatio(head_weight)))
        return tuple(parts)

    @staticmethod
    def _resolve_spec(node, spec):
        if callable(spec):
            return spec(node)
        if spec == 'symbol':
            return node.symbol
        return node.data.get(spec)

    def to_tree(self, value='symbol', **attr_map):
        """
        Build a :class:`~klotho.topos.graphs.trees.Tree` from this derivation.

        Parameters
        ----------
        value : str or callable, optional
            What feeds each tree node's value attribute: ``'symbol'``
            (default) uses the node symbol, any other string reads
            ``node.data[key]``, and a callable receives the node.
        **attr_map
            Extra node attributes to write onto the tree. Each value is a
            field spec resolved like *value*; ``None`` results are skipped.

        Returns
        -------
        Tree

        Examples
        --------
        >>> tree = derivation.to_tree(chord=lambda n: n.data.get('chord'))
        """
        from ..graphs.trees import Tree

        def build(node):
            v = self._resolve_spec(node, value)
            if node.children:
                return (v, tuple(build(child) for child in node.children))
            return v

        structure = build(self)
        if self.children:
            tree = Tree(structure[0], structure[1])
        else:
            tree = Tree(structure, tuple())

        if attr_map:
            stack = [(self, tree.root)]
            while stack:
                dnode, tnode = stack.pop()
                attrs = {}
                for key, spec in attr_map.items():
                    val = self._resolve_spec(dnode, spec)
                    if val is not None:
                        attrs[key] = val
                if attrs:
                    tree.set_node_data(tnode, **attrs)
                stack.extend(zip(dnode.children, tree.successors(tnode)))
        return tree

    def __repr__(self):
        if self.is_leaf:
            return f"DerivationTree({self.symbol!r})"
        return f"DerivationTree({self.symbol!r}, {len(self.leaves())} leaves)"


def derive(axiom, rules, max_depth=4, rng=None):
    """
    Recursively expand *axiom* into a derivation tree.

    A branch terminates when the depth limit is reached, the symbol has no
    rule, or an identity expansion (``symbol → symbol``) is drawn.

    Parameters
    ----------
    axiom : str
        The start symbol.
    rules : dict or RuleSet
        Production rules (weighted options make the derivation stochastic).
    max_depth : int, optional
        Maximum expansion depth. Default is 4.
    rng : random.Random or int, optional
        Source of randomness (or a seed).

    Returns
    -------
    DerivationTree
    """
    if not isinstance(rules, RuleSet):
        rules = RuleSet(rules)
    rng = _coerce_rng(rng)

    def _expand(symbol, depth):
        node = DerivationTree(symbol)
        if depth <= 0 or symbol not in rules:
            return node
        expansion = tuple(rules.sample(symbol, rng))
        if expansion == (symbol,):
            return node
        node.children = [_expand(s, depth - 1) for s in expansion]
        return node

    return _expand(axiom, max_depth)
