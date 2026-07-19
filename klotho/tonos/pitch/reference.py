import copy
import numbers
from typing import Union

from .pitch import Pitch
from .pitch_collections import _resolve_reference


class ReferencePitchAware:
    """Mixin giving graph-like pitch structures a reference pitch and ``root()``.

    Used by the "tone lattice-like" classes (``CombinationProductSet``,
    ``ToneLattice``, ``MasterSet``), whose ratios are anchored to a
    reference pitch (default C4) for playback and plotting, mirroring how
    ``Scale``/``Chord`` carry a root.
    """

    _reference_pitch: Pitch = None

    @property
    def reference_pitch(self) -> Pitch:
        """Pitch : The pitch anchoring this structure's ratios (default C4)."""
        if self._reference_pitch is None:
            return _resolve_reference(None)
        return self._reference_pitch

    def root(self, pitch: Union[Pitch, str]):
        """
        Return a copy of this object rooted at the given pitch.

        The underlying graph is shared with the original (these structures
        are immutable after construction); only the reference pitch differs.

        Parameters
        ----------
        pitch : Pitch or str
            The pitch to use as the reference root.

        Returns
        -------
        Same type as ``self``
        """
        rooted = copy.copy(self)
        rooted._reference_pitch = _resolve_reference(pitch)
        return rooted

    # --- Node hooks --------------------------------------------------
    # Each lattice-family class refers to its nodes in its own way:
    # CombinationProductSet by int node ids, MasterSet by alias-letter
    # strings, ToneLattice by coordinate tuples. The default hooks cover
    # the first (and ToneLattice's ``self[coord]`` lookup); MasterSet and
    # ToneLattice override where their conventions differ.

    def _node_ratio(self, node):
        """The equave-reduced ratio represented by *node*."""
        return self[node]['ratio']

    def _is_node_ref(self, item) -> bool:
        """Whether *item* is a single node reference (vs a group of nodes)."""
        return isinstance(item, (numbers.Integral, str))

    def _node_for_ratio(self, ratio):
        """The node representing *ratio*, or None.

        The query is equave-reduced before matching, so degrees from
        voiced or equave-shifted chords resolve to the same node.
        """
        from klotho.tonos.utils.interval_normalization import equave_reduce
        reduced = equave_reduce(ratio)
        for node, attrs in self.nodes(data=True):
            if attrs.get('ratio') == reduced:
                return node
        return None

    def chord(self, nodes, root: Union[Pitch, str, None] = None, equave=None):
        """
        Build a :class:`~klotho.tonos.chords.chord.Chord` from node
        references, or a :class:`~klotho.tonos.chords.chord.ChordSequence`
        from a list of node groups.

        Parameters
        ----------
        nodes : iterable
            Either a collection of node references (following this
            class's node convention) yielding one Chord, or a list of
            such collections yielding a ChordSequence — e.g. the output
            of :func:`~klotho.tonos.systems.combination_product_sets.match_pattern`.
        root : Pitch, str, or None, optional
            Reference pitch for the chord(s). Defaults to this object's
            :attr:`reference_pitch`.
        equave : optional
            Interval of equivalence for the chord(s). Defaults to this
            object's equave when it has one, else ``'2/1'``.

        Returns
        -------
        Chord or ChordSequence
        """
        from klotho.tonos.chords.chord import Chord, ChordSequence

        root = self.reference_pitch if root is None else root
        if equave is None:
            equave = getattr(self, '_equave', None) or '2/1'

        items = list(nodes)
        node_flags = [self._is_node_ref(item) for item in items]

        def _build(group):
            return Chord([self._node_ratio(n) for n in group],
                         equave=equave, reference_pitch=root)

        if all(node_flags):
            return _build(items)
        if not any(node_flags):
            return ChordSequence([_build(group) for group in items])
        raise ValueError(
            f"Mixed input to {type(self).__name__}.chord(): pass either a "
            f"collection of node references or a list of node groups."
        )
