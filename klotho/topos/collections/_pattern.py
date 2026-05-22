from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import cycle as itertools_cycle
from math import lcm
from typing import Any, List, Optional, TypeVar, Union

import numpy as np

T = TypeVar('T')


def _is_pattern(obj) -> bool:
    from klotho.topos.collections.sequences import Pattern

    return isinstance(obj, Pattern)


class SlotKind(Enum):
    LEAF = auto()
    STRUCTURAL = auto()
    DELEGATE_PATTERN = auto()
    DELEGATE_CYCLIC = auto()


@dataclass(frozen=True)
class NodeSpec:
    kind: SlotKind
    value: Any = None
    children: tuple[NodeSpec, ...] = ()
    sequence: tuple[Any, ...] = ()
    period: int = 1


class Cyclic:
    """Finite repeating sequence for use as a Pattern delegate."""

    __slots__ = ('_sequence',)

    def __init__(self, sequence):
        self._sequence = tuple(sequence)
        if not self._sequence:
            raise ValueError("Cyclic sequence cannot be empty")

    @property
    def sequence(self):
        return self._sequence

    def __len__(self):
        return len(self._sequence)

    def __repr__(self):
        return f"Cyclic({list(self._sequence)!r})"


class _CyclicRuntime:
    __slots__ = ('_items', '_index')

    def __init__(self, items: tuple[Any, ...]):
        self._items = items
        self._index = 0

    def __next__(self):
        value = self._items[self._index]
        self._index = (self._index + 1) % len(self._items)
        return value

    def reset(self):
        self._index = 0

    def snapshot(self) -> int:
        return self._index

    def restore(self, index: int):
        self._index = index


class _LeafRuntime:
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value


class _StructuralRuntime:
    __slots__ = ('children', 'index')

    def __init__(self, children):
        self.children = children
        self.index = 0

    def snapshot(self):
        return (self.index, [child_snapshot(c) for c in self.children])

    def restore(self, state):
        self.index, child_states = state
        for child, child_state in zip(self.children, child_states):
            child_restore(child, child_state)


class _DelegateRuntime:
    __slots__ = ('target',)

    def __init__(self, target):
        self.target = target

    def snapshot(self):
        target = self.target
        if _is_pattern(target):
            return ('pattern', target._snapshot())
        return ('cyclic', target.snapshot())

    def restore(self, state):
        kind, payload = state
        if kind == 'pattern':
            self.target._restore(payload)
        else:
            self.target.restore(payload)


def child_snapshot(node):
    if isinstance(node, _LeafRuntime):
        return ('leaf',)
    if isinstance(node, _DelegateRuntime):
        return ('delegate', node.snapshot())
    return ('struct', node.snapshot())


def child_restore(node, state):
    kind = state[0]
    if kind == 'leaf':
        return
    if kind == 'delegate':
        node.restore(state[1])
    else:
        node.restore(state[1])


def _leaf_label(value: Any) -> str:
    text = repr(value)
    return text if len(text) <= 28 else text[:25] + '...'


def _classify(item) -> tuple[SlotKind, Any]:
    if _is_pattern(item):
        return SlotKind.DELEGATE_PATTERN, item
    if isinstance(item, (Cyclic, itertools_cycle)):
        return SlotKind.DELEGATE_CYCLIC, item
    if isinstance(item, list):
        return SlotKind.STRUCTURAL, item
    if isinstance(item, np.ndarray):
        if item.ndim == 0:
            return SlotKind.LEAF, item.item()
        return SlotKind.STRUCTURAL, item
    return SlotKind.LEAF, item


def _normalize_cyclic(item) -> tuple[Any, ...]:
    if isinstance(item, Cyclic):
        return item.sequence
    if isinstance(item, itertools_cycle):
        raise TypeError(
            "itertools.cycle is not supported in Pattern; use Cyclic([...]) "
            "or pass a list directly."
        )
    raise TypeError(f"Expected Cyclic or itertools.cycle, got {type(item)!r}")


def _compile_item(item) -> NodeSpec:
    kind, payload = _classify(item)
    if kind is SlotKind.LEAF:
        return NodeSpec(SlotKind.LEAF, value=payload, period=1)
    if kind is SlotKind.DELEGATE_PATTERN:
        delegate = payload
        return NodeSpec(
            SlotKind.DELEGATE_PATTERN,
            value=id(delegate),
            period=delegate.length,
        )
    if kind is SlotKind.DELEGATE_CYCLIC:
        sequence = _normalize_cyclic(payload)
        return NodeSpec(
            SlotKind.DELEGATE_CYCLIC,
            sequence=sequence,
            period=len(sequence),
        )
    children_payload = list(payload)
    if not children_payload:
        raise ValueError("Pattern cannot contain empty structural container")
    children = tuple(_compile_item(child) for child in children_payload)
    n = len(children)
    period = lcm(*[n * child.period for child in children])
    return NodeSpec(SlotKind.STRUCTURAL, children=children, period=period)


def _build_runtime(spec: NodeSpec, source_item):
    kind, payload = _classify(source_item)
    if kind is SlotKind.LEAF:
        return _LeafRuntime(spec.value)
    if kind is SlotKind.DELEGATE_PATTERN:
        return _DelegateRuntime(payload)
    if kind is SlotKind.DELEGATE_CYCLIC:
        return _DelegateRuntime(_CyclicRuntime(_normalize_cyclic(payload)))
    return _StructuralRuntime(
        [_build_runtime(child_spec, child_source) for child_spec, child_source in zip(spec.children, payload)]
    )


def _reset_runtime(node):
    if isinstance(node, _StructuralRuntime):
        node.index = 0
        for child in node.children:
            _reset_runtime(child)
    elif isinstance(node, _DelegateRuntime):
        target = node.target
        if _is_pattern(target):
            target.reset()
        else:
            target.reset()


def _advance_runtime(node):
    if isinstance(node, _LeafRuntime):
        return node.value
    if isinstance(node, _DelegateRuntime):
        return next(node.target)
    child = node.children[node.index]
    value = _advance_runtime(child)
    node.index = (node.index + 1) % len(node.children)
    return value


def pattern_to_graph(
    pattern,
    *,
    expand_delegates: bool = True,
):
    """Build a NetworkX DiGraph describing *pattern* structure for plotting."""
    import networkx as nx

    graph = nx.DiGraph()
    counter = 0
    delegate_targets: dict[int, Any] = {}

    def _next_id() -> int:
        nonlocal counter
        node_id = counter
        counter += 1
        return node_id

    def _structural_children(source):
        if isinstance(source, np.ndarray):
            return list(source)
        return list(source)

    def _walk(source, spec: NodeSpec, parent: Optional[int] = None, slot: Optional[int] = None) -> int:
        node_id = _next_id()

        if spec.kind is SlotKind.LEAF:
            graph.add_node(node_id, kind='leaf', label=_leaf_label(spec.value), period=1)
        elif spec.kind is SlotKind.STRUCTURAL:
            child_sources = _structural_children(source)
            graph.add_node(
                node_id,
                kind='structural',
                label=f'cycle x{len(spec.children)}',
                period=spec.period,
                n_slots=len(spec.children),
                child_ids=[],
            )
            for idx, (child_spec, child_source) in enumerate(zip(spec.children, child_sources)):
                child_id = _walk(child_source, child_spec)
                graph.nodes[node_id]['child_ids'].append(child_id)
                graph.add_edge(node_id, child_id, slot=idx, edge_kind='slot')
        elif spec.kind is SlotKind.DELEGATE_PATTERN:
            delegate = source
            delegate_targets[node_id] = delegate
            graph.add_node(
                node_id,
                kind='delegate_pattern',
                label=f'Pattern (len={spec.period})',
                period=spec.period,
                delegate_id=id(delegate),
            )
            if expand_delegates:
                sub_id = _walk(delegate.pattern, delegate.spec)
                graph.add_edge(node_id, sub_id, slot=0, edge_kind='delegate')
        elif spec.kind is SlotKind.DELEGATE_CYCLIC:
            graph.add_node(
                node_id,
                kind='delegate_cyclic',
                label=f'Cyclic {list(spec.sequence)!r}',
                period=spec.period,
                sequence=spec.sequence,
            )

        if parent is not None:
            graph.add_edge(parent, node_id, slot=slot if slot is not None else 0, edge_kind='slot')

        return node_id

    root = _walk(pattern.pattern, pattern.spec)
    graph.graph['root'] = root
    graph.graph['pattern_length'] = pattern.length
    graph.graph['period_sequence'] = list(pattern.materialize_period())
    graph.graph['delegate_targets'] = delegate_targets
    return graph
