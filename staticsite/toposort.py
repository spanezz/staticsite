# Copyright (C) 2014  Enrico Zini <enrico@enricozini.org>
# Based on code by Paul Harrison and Dries Verdegem released under the Public
# Domain.

# From: http://www.logarithmic.net/pfh/blog/01208083168
# and: http://www.logarithmic.net/pfh-files/blog/01208083168/tarjan.py

from typing import Dict, Set, Any, List
from collections import Counter, deque

Node = Any
Graph = Dict[Node, Set[Node]]


def strongly_connected_components(graph: Graph):
    """
    Tarjan's Algorithm (named for its discoverer, Robert Tarjan) is a graph theory algorithm
    for finding the strongly connected components of a graph.

    Based on: http://en.wikipedia.org/wiki/Tarjan%27s_strongly_connected_components_algorithm
    """
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    result = []

    def strongconnect(node: Node):
        # set the depth index for this node to the smallest unused index
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)

        # Consider successors of `node`
        successors = graph.get(node, ())
        for successor in successors:
            if successor not in lowlinks:
                # Successor has not yet been visited; recurse on it
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in stack:
                # the successor is in the stack and hence in the current strongly connected component (SCC)
                lowlinks[node] = min(lowlinks[node], index[successor])

        # If `node` is a root node, pop the stack and generate an SCC
        if lowlinks[node] == index[node]:
            connected_component = []

            while True:
                successor = stack.pop()
                connected_component.append(successor)
                if successor == node:
                    break

            # storing the result
            result.append(connected_component)

    for node in graph:
        if node not in lowlinks:
            strongconnect(node)

    return result


def topological_sort(graph: Graph) -> List[Node]:
    count: Counter = Counter()
    for node in graph:
        for successor in graph[node]:
            count[successor] += 1

    # Use a deque to pop left efficiently, so we can preserve the graph
    # insertion order when no other dependency information kicks in
    ready = deque(node for node in graph if count[node] == 0)

    result = []
    while ready:
        node = ready.popleft()
        result.append(node)

        for successor in graph[node]:
            count[successor] -= 1
            if count[successor] == 0:
                ready.append(successor)

    return result


def sort(graph: Graph) -> List[Node]:
    """
    Linearize a dependency graph, throwing an exception if a cycle is detected.

    When no dependencies intervene in ordering, the algorithm preserves the
    original insertion order of the graph.

    :arg graph: a dict mapping each node to a set() of adjacent nodes
    """
    # Compute the strongly connected components, throwing an exception if we
    # see cycles
    cycles = []
    for items in strongly_connected_components(graph):
        if len(items) > 1:
            cycles.append("({})".format(", ".join(str(x) for x in items)))

    if cycles:
        if len(cycles) > 1:
            raise ValueError("{} cycles detected: {}".format(len(cycles), ", ".join(cycles)))
        else:
            raise ValueError("cycle detected: {}".format(cycles[0]))

    # We know that the graph does not have cycles, so we can run
    # topological_sort on it
    return topological_sort(graph)
