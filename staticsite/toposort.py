from __future__ import annotations

from graphlib import CycleError, TopologicalSorter
from typing import Any, Iterable

__all__ = ["CycleError", "sort"]

Node = Any
Graph = dict[Node, Iterable[Node]]


def sort(graph: Graph) -> list[Node]:
    """
    Linearize a dependency graph, throwing an exception if a cycle is detected.

    When no dependencies intervene in ordering, the algorithm preserves the
    original insertion order of the graph.

    :arg graph: a dict mapping each node to an iterable of their antecedents
    """
    sorter = TopologicalSorter(graph)
    return list(sorter.static_order())
