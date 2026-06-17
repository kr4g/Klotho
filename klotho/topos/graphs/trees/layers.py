"""Tree layer protocol.

A :class:`TreeLayer` is an object attached to a :class:`Tree` that owns a
domain's node-data keys and recompute rules. The tree notifies its attached
layers on structural and data mutations; layers validate/normalize writes for
the keys they own and recompute their derived values. Multiple layers can be
attached to a single tree (e.g. a rhythm layer and a parameter layer on one
``CompositionalTree``), which is what lets a single topology carry several
synchronized data domains without mirroring trees.
"""


class TreeLayer:
    """Base class / protocol for tree layers.

    Subclasses override the hooks they care about. ``owned_keys`` are the node
    attribute keys this layer accepts as writable; ``derived_keys`` are keys
    this layer computes and rejects on direct write.
    """

    owned_keys = frozenset()
    derived_keys = frozenset()

    def on_attach(self, tree):
        """Called when the layer is attached to ``tree``."""
        pass

    def normalize_attrs(self, tree, node, attrs, op):
        """Return a normalized copy of ``attrs`` for an incoming node-data write."""
        return attrs

    def validate_attrs(self, tree, node, attrs, op):
        """Raise if ``attrs`` contains keys this layer forbids."""
        pass

    def data_scope(self, tree, node, changed_keys, op):
        """Return the recompute scope node for a data write, or ``None`` to defer."""
        return None

    def on_structure_changed(self, tree, scope, op):
        """Recompute derived values after a structural or data mutation."""
        pass

    def invalidate(self, tree):
        """Drop any cached state held by the layer."""
        pass

    def on_nodes_remapped(self, tree, mapping):
        """Remap identity-keyed side state when nodes are renumbered/copied.

        ``mapping`` maps old node ids (in the source tree) to new node ids
        (in ``tree``).
        """
        pass

    def on_clone(self, tree):
        """Reinitialize layer state on a freshly cloned/structure-only tree."""
        pass

    def clone_state(self, source_layer, new_tree, memo):
        """Copy identity-keyed side state from ``source_layer`` during deepcopy."""
        pass
