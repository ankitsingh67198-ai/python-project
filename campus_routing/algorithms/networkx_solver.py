"""
Independent NetworkX reference solver for Smart Campus Navigation.

Used for empirical cross-validation against the custom Dijkstra implementation.
Does NOT call or depend on custom Dijkstra logic.
"""

from typing import List
import networkx as nx

from campus_routing.algorithms.dijkstra import RouteResult
from campus_routing.exceptions import (
    NodeNotFoundError,
    PathNotFoundError,
)
from campus_routing.models.graph import CampusGraph


def build_networkx_graph(
    graph: CampusGraph,
    accessible_only: bool = False,
) -> nx.DiGraph:
    """
    Constructs a NetworkX DiGraph representing the unblocked, accessible pathways of CampusGraph.

    Args:
        graph: CampusGraph source model.
        accessible_only: If True, excludes non-accessible edges.

    Returns:
        nx.DiGraph configured with 'weight' (routing cost) and 'distance_m' (physical distance).
    """
    nx_graph = nx.DiGraph()

    # Add all nodes
    for node in graph.get_nodes():
        nx_graph.add_node(node.id, name=node.name, category=node.category)

    # Add traversable edges
    for edge in graph.get_edges(include_blocked=False):
        if accessible_only and not edge.is_accessible:
            continue

        # Add forward edge
        nx_graph.add_edge(
            edge.source_id,
            edge.target_id,
            weight=edge.effective_cost,
            distance_m=edge.distance_m,
        )

        # If undirected, also add reverse edge
        if not edge.is_directed:
            nx_graph.add_edge(
                edge.target_id,
                edge.source_id,
                weight=edge.effective_cost,
                distance_m=edge.distance_m,
            )

    return nx_graph


def networkx_shortest_path(
    graph: CampusGraph,
    source: str,
    target: str,
    accessible_only: bool = False,
) -> RouteResult:
    """
    Computes shortest path independently using NetworkX Dijkstra functions.

    Args:
        graph: CampusGraph instance.
        source: Origin node ID.
        target: Destination node ID.
        accessible_only: If True, filters out non-accessible edges.

    Returns:
        RouteResult matching the schema of the custom Dijkstra solver.

    Raises:
        NodeNotFoundError: If source or target does not exist in graph.
        PathNotFoundError: If no navigable path exists between source and target.
    """
    if not graph.has_node(source):
        raise NodeNotFoundError(f"Routing origin '{source}' does not exist in campus graph.")
    if not graph.has_node(target):
        raise NodeNotFoundError(f"Routing destination '{target}' does not exist in campus graph.")

    if source == target:
        return RouteResult(
            nodes=[source],
            total_distance_m=0.0,
            total_cost=0.0,
        )

    nx_graph = build_networkx_graph(graph, accessible_only=accessible_only)

    try:
        nx_nodes: List[str] = nx.dijkstra_path(nx_graph, source, target, weight="weight")
        nx_cost: float = float(nx.dijkstra_path_length(nx_graph, source, target, weight="weight"))
    except nx.NetworkXNoPath as err:
        filter_msg = " (with accessibility restrictions)" if accessible_only else ""
        raise PathNotFoundError(
            f"No navigable pathway connects origin '{source}' to destination '{target}'{filter_msg}."
        ) from err
    except nx.NodeNotFound as err:
        raise NodeNotFoundError(str(err)) from err

    # Compute true physical ground distance along the path
    total_physical_dist = 0.0
    for i in range(len(nx_nodes) - 1):
        u, v = nx_nodes[i], nx_nodes[i + 1]
        edge = graph.get_edge(u, v)
        if edge is None:
            raise PathNotFoundError(f"NetworkX path contains invalid edge ({u}, {v})")
        total_physical_dist += edge.distance_m

    return RouteResult(
        nodes=nx_nodes,
        total_distance_m=total_physical_dist,
        total_cost=nx_cost,
    )
