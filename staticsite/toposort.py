from __future__ import annotations

from graphlib import CycleError, TopologicalSorter
from typing import Iterable, Mapping, TypeVar

__all__ = ["CycleError", "sort"]

N = TypeVar("N")


def sort(graph: Mapping[N, Iterable[N]]) -> list[N]:
    """
    Linearize a dependency graph, throwing an exception if a cycle is detected.

    When no dependencies intervene in ordering, the algorithm preserves the
    original insertion order of the graph.

    :arg graph: a dict mapping each node to an iterable of their antecedents
    """
    sorter = TopologicalSorter(graph)
    return list(sorter.static_order())
