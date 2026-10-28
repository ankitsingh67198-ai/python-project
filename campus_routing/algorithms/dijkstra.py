"""
Custom Dijkstra shortest-path routing algorithm for Smart Campus Navigation.

Implemented purely using Python's standard library (heapq, typing) without external dependencies.
Maintains full IEEE-754 double precision without premature rounding.
Tracks physical distance in metres separately from weighted routing cost.
"""

from dataclasses import dataclass
import heapq
import math
from typing import Dict, List, Optional, Set, Tuple

from campus_routing.exceptions import (
    InvalidEdgeError,
    NodeNotFoundError,
    PathNotFoundError,
)
from campus_routing.models.edge import Edge
from campus_routing.models.graph import CampusGraph


@dataclass(frozen=True)
class RouteResult:
    """
    Immutable structured result of a shortest-path routing query.

    Attributes:
        nodes: Ordered sequence of node IDs along the route [source, ..., destination].
        total_distance_m: Exact accumulated physical ground distance in metres.
        total_cost: Exact accumulated algorithmic routing cost (impedance).
    """

    nodes: List[str]
    total_distance_m: float
    total_cost: float

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("RouteResult must contain at least one node.")
        if self.total_distance_m < 0.0 or not math.isfinite(self.total_distance_m):
            raise ValueError(f"Invalid total_distance_m: {self.total_distance_m}")
        if self.total_cost < 0.0 or not math.isfinite(self.total_cost):
            raise ValueError(f"Invalid total_cost: {self.total_cost}")

    @property
    def hop_count(self) -> int:
        """Returns the number of pathway segments (hops) along the route."""
        return max(0, len(self.nodes) - 1)

    @property
    def is_empty(self) -> bool:
        """True if the route is a zero-hop trivial path (source == target)."""
        return len(self.nodes) <= 1


def dijkstra_shortest_path(
    graph: CampusGraph,
    source: str,
    target: str,
    accessible_only: bool = False,
) -> RouteResult:
    """
    Computes the minimum-cost route from source to target using Dijkstra's algorithm.

    Theoretical Complexity:
        - Time: O((|E| + |V|) log |V|) using a binary min-heap priority queue.
        - Space: O(|V| + |E|) for distance tables, predecessor map, and heap.

    Args:
        graph: The CampusGraph containing nodes and traversable edges.
        source: Node ID where the journey originates.
        target: Node ID of the destination.
        accessible_only: If True, restricts traversal strictly to wheelchair-accessible edges.

    Returns:
        RouteResult containing the ordered node sequence, total physical distance in metres,
        and total routing cost.

    Raises:
        NodeNotFoundError: If source or target does not exist in graph.
        PathNotFoundError: If target cannot be reached from source.
        InvalidEdgeError: If negative or non-finite edge weights are encountered during traversal.
    """
    # 1. Validate node existence in the graph
    if not graph.has_node(source):
        raise NodeNotFoundError(f"Routing origin '{source}' does not exist in campus graph.")
    if not graph.has_node(target):
        raise NodeNotFoundError(f"Routing destination '{target}' does not exist in campus graph.")

    # 2. Base case: origin equals destination
    if source == target:
        return RouteResult(
            nodes=[source],
            total_distance_m=0.0,
            total_cost=0.0,
        )

    # 3. Data structures for Dijkstra's search
    # best_cost tracks the lowest known routing cost to reach each node
    best_cost: Dict[str, float] = {source: 0.0}

    # predecessors maps node_id -> (predecessor_node_id, Edge traversed)
    predecessors: Dict[str, Tuple[str, Edge]] = {}

    # Priority queue stores tuples of (tentative_cost, node_id)
    pq: List[Tuple[float, str]] = [(0.0, source)]

    # Set of settled nodes whose optimal cost is definitively finalized
    settled: Set[str] = set()

    # 4. Main Dijkstra exploration loop
    while pq:
        curr_cost, u = heapq.heappop(pq)

        # Discard stale heap entries resulting from earlier, suboptimal distance updates
        if curr_cost > best_cost.get(u, float("inf")):
            continue

        if u in settled:
            continue

        settled.add(u)

        # Early stopping: if target is popped from priority queue, its optimal cost is settled
        if u == target:
            break

        # Explore outgoing / traversable neighbors
        for neighbor_id, edge in graph.get_neighbors(
            u, include_blocked=False, accessible_only=accessible_only
        ):
            # Strict defense against negative or non-finite weights
            if edge.effective_cost < 0.0 or not math.isfinite(edge.effective_cost):
                raise InvalidEdgeError(
                    f"Invalid routing cost encountered on edge ({u}, {neighbor_id}): {edge.effective_cost}"
                )
            if edge.distance_m <= 0.0 or not math.isfinite(edge.distance_m):
                raise InvalidEdgeError(
                    f"Invalid physical distance on edge ({u}, {neighbor_id}): {edge.distance_m}"
                )

            tentative_cost = curr_cost + edge.effective_cost

            # Relaxation step
            if tentative_cost < best_cost.get(neighbor_id, float("inf")):
                best_cost[neighbor_id] = tentative_cost
                predecessors[neighbor_id] = (u, edge)
                heapq.heappush(pq, (tentative_cost, neighbor_id))

    # 5. Check if destination was reached
    if target not in best_cost or target not in settled:
        filter_msg = " (with accessibility restrictions)" if accessible_only else ""
        raise PathNotFoundError(
            f"No navigable pathway connects origin '{source}' to destination '{target}'{filter_msg}."
        )

    # 6. Reconstruct ordered path and accumulate physical ground distance
    reversed_nodes: List[str] = [target]
    total_physical_distance: float = 0.0
    curr: str = target

    while curr != source:
        if curr not in predecessors:
            raise PathNotFoundError(f"Failed to reconstruct route: broken predecessor link at '{curr}'")
        pred_node, edge = predecessors[curr]
        reversed_nodes.append(pred_node)
        total_physical_distance += edge.distance_m
        curr = pred_node

    ordered_nodes = list(reversed(reversed_nodes))

    return RouteResult(
        nodes=ordered_nodes,
        total_distance_m=total_physical_distance,
        total_cost=best_cost[target],
    )
